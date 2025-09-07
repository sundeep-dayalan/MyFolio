"""
User service for business logic using CosmosDB.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError

from ..models.user import UserCreate, UserUpdate, UserResponse
from ..exceptions import UserNotFoundError, UserAlreadyExistsError, DatabaseError
from ..utils.logger import get_logger
from ..constants import Containers
from ..utils.security import sanitize_input
from ..database import cosmos_client

logger = get_logger(__name__)


class UserService:
    """User service class using CosmosDB."""

    def __init__(self):
        self.container_name = Containers.USERS

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""
        try:
            # Ensure CosmosDB connection is established
            await cosmos_client.ensure_connected()

            # Check if user already exists
            if await self.get_user_by_id(user_data.id):
                raise UserAlreadyExistsError(user_data.id)

            # Sanitize input data
            sanitized_data = self._sanitize_user_data(user_data.dict())

            # Add timestamps and required fields
            now = datetime.utcnow()
            user_doc = {
                "id": user_data.id,  # CosmosDB requires explicit id
                "userId": user_data.id,  # For partition key
                **sanitized_data,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "is_active": True,
                "metadata": {},
            }

            # Save to CosmosDB
            response = cosmos_client.create_item(
                self.container_name, user_doc, user_data.id
            )

            logger.info(f"User created successfully: {user_data.id}")
            return UserResponse(**response)

        except UserAlreadyExistsError:
            raise
        except CosmosHttpResponseError as e:
            logger.error(f"CosmosDB error creating user {user_data.id}: {str(e)}")
            raise DatabaseError(f"Failed to create user: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating user {user_data.id}: {str(e)}")
            raise DatabaseError(f"Failed to create user: {str(e)}")

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        try:
            # Ensure CosmosDB connection is established
            await cosmos_client.ensure_connected()

            user_doc = cosmos_client.get_item(self.container_name, user_id, user_id)

            if user_doc:
                # Convert datetime strings back to datetime objects for UserResponse
                if isinstance(user_doc.get("created_at"), str):
                    user_doc["created_at"] = datetime.fromisoformat(
                        user_doc["created_at"]
                    )
                if isinstance(user_doc.get("updated_at"), str):
                    user_doc["updated_at"] = datetime.fromisoformat(
                        user_doc["updated_at"]
                    )

                return UserResponse(**user_doc)

            return None

        except CosmosHttpResponseError as e:
            logger.error(f"CosmosDB error getting user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to get user: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to get user: {str(e)}")

    async def get_user_by_email_and_auth_provider(
        self, email: str, provider: str, provider_user_id: str
    ) -> Optional[UserResponse]:
        """Get user by combination of email, auth provider, and provider user id.

        This will try common locations for the provider user id: `metadata.provider_user_id`
        and `metadata.provider_data.<provider>_id` or `metadata.provider_data.<provider>Id`.
        """
        try:
            # Ensure CosmosDB connection is established
            await cosmos_client.ensure_connected()

            # Sanitize inputs
            email_s = sanitize_input(email) if isinstance(email, str) else email
            provider_s = (
                sanitize_input(provider) if isinstance(provider, str) else provider
            )
            pid_s = (
                sanitize_input(provider_user_id)
                if isinstance(provider_user_id, str)
                else provider_user_id
            )

            parameters = [
                {"name": "@email", "value": email_s},
                {"name": "@provider", "value": provider_s},
                {"name": "@pid", "value": pid_s},
            ]

            # First try direct provider_user_id stored on metadata
            queries = [
                (
                    "SELECT * FROM c WHERE c.email = @email AND c.metadata.auth_provider = @provider AND c.metadata.provider_user_id = @pid",
                    parameters,
                )
            ]

            # Try common keys inside metadata.provider_data
            key_variants = [f"{provider_s}_id", f"{provider_s}Id"]
            for key in key_variants:
                q = f"SELECT * FROM c WHERE c.email = @email AND c.metadata.auth_provider = @provider AND c.metadata.provider_data.{key} = @pid"
                queries.append((q, parameters))

            # Execute queries until we find a match
            for query, params in queries:
                results = cosmos_client.query_items(self.container_name, query, params)
                if results:
                    user_doc = results[0]
                    # Convert datetime strings back to datetime objects for UserResponse
                    if isinstance(user_doc.get("created_at"), str):
                        user_doc["created_at"] = datetime.fromisoformat(
                            user_doc["created_at"]
                        )
                    if isinstance(user_doc.get("updated_at"), str):
                        user_doc["updated_at"] = datetime.fromisoformat(
                            user_doc["updated_at"]
                        )

                    return UserResponse(**user_doc)

            return None

        except CosmosHttpResponseError as e:
            logger.error(
                f"CosmosDB error getting user by email/provider {email}/{provider}: {str(e)}"
            )
            raise DatabaseError(f"Failed to get user: {str(e)}")
        except Exception as e:
            logger.error(
                f"Error getting user by email/provider {email}/{provider}: {str(e)}"
            )
            raise DatabaseError(f"Failed to get user: {str(e)}")

    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user."""
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise UserNotFoundError(user_id)

            # Prepare update data
            update_data = {}
            for field, value in user_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = (
                        sanitize_input(str(value)) if isinstance(value, str) else value
                    )

            if update_data:
                update_data["updated_at"] = datetime.utcnow().isoformat()

                # Update in CosmosDB
                cosmos_client.update_item(
                    self.container_name, user_id, user_id, update_data
                )

                logger.info(f"User updated successfully: {user_id}")

            # Return updated user
            return await self.get_user_by_id(user_id)

        except UserNotFoundError:
            raise
        except CosmosHttpResponseError as e:
            logger.error(f"CosmosDB error updating user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to update user: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to update user: {str(e)}")

    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by setting is_active to False)."""
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise UserNotFoundError(user_id)

            # Soft delete
            update_data = {
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat(),
            }

            cosmos_client.update_item(
                self.container_name, user_id, user_id, update_data
            )

            logger.info(f"User deleted successfully: {user_id}")
            return True

        except UserNotFoundError:
            raise
        except CosmosHttpResponseError as e:
            logger.error(f"CosmosDB error deleting user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete user: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise DatabaseError(f"Failed to delete user: {str(e)}")

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get list of users."""
        try:
            # Query active users with pagination
            query = """
            SELECT * FROM c 
            WHERE c.is_active = true 
            ORDER BY c.created_at 
            OFFSET @skip LIMIT @limit
            """

            parameters = [
                {"name": "@skip", "value": skip},
                {"name": "@limit", "value": limit},
            ]

            results = cosmos_client.query_items(self.container_name, query, parameters)

            users = []
            for user_doc in results:
                # Convert datetime strings back to datetime objects for UserResponse
                if isinstance(user_doc.get("created_at"), str):
                    user_doc["created_at"] = datetime.fromisoformat(
                        user_doc["created_at"]
                    )
                if isinstance(user_doc.get("updated_at"), str):
                    user_doc["updated_at"] = datetime.fromisoformat(
                        user_doc["updated_at"]
                    )

                users.append(UserResponse(**user_doc))

            return users

        except CosmosHttpResponseError as e:
            logger.error(f"CosmosDB error getting users: {str(e)}")

            # Fallback: Simple query without ordering
            try:
                logger.info("Falling back to simple query without ordering")
                query = "SELECT * FROM c WHERE c.is_active = true"
                results = cosmos_client.query_items(self.container_name, query)

                users = []
                count = 0
                skipped = 0

                for user_doc in results:
                    if skipped < skip:
                        skipped += 1
                        continue

                    if count >= limit:
                        break

                    # Convert datetime strings back to datetime objects for UserResponse
                    if isinstance(user_doc.get("created_at"), str):
                        user_doc["created_at"] = datetime.fromisoformat(
                            user_doc["created_at"]
                        )
                    if isinstance(user_doc.get("updated_at"), str):
                        user_doc["updated_at"] = datetime.fromisoformat(
                            user_doc["updated_at"]
                        )

                    users.append(UserResponse(**user_doc))
                    count += 1

                return users

            except Exception as fallback_error:
                logger.error(f"Fallback query also failed: {str(fallback_error)}")
                raise DatabaseError(f"Failed to get users: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            raise DatabaseError(f"Failed to get users: {str(e)}")

    def _sanitize_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize user input data."""
        sanitized = {}
        string_fields = ["name", "given_name", "family_name"]

        for key, value in data.items():
            if key in string_fields and isinstance(value, str):
                sanitized[key] = sanitize_input(value)
            else:
                sanitized[key] = value

        return sanitized
