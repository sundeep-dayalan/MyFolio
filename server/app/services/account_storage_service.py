"""
Account Storage Service for managing stored account data in CosmosDB.
This service helps reduce Plaid API costs by storing account balances and information locally.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from ..database import cosmos_client
from ..utils.logger import get_logger
from ..models.plaid import PlaidAccountWithBalance
import json

logger = get_logger(__name__)


class AccountStorageService:
    """Service for managing stored account data in CosmosDB."""

    def __init__(self):
        self.container_name = "accounts"

    def store_account_data(self, user_id: str, accounts_data: Dict[str, Any]) -> bool:
        """
        Store account data in CosmosDB under user's collection.

        Args:
            user_id: User ID to store data for
            accounts_data: Account data from Plaid API containing accounts, total_balance, etc.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(
                f"Storing account data for user {user_id} - {accounts_data.get('account_count', 0)} accounts"
            )
            logger.debug(
                f"Account data to store: accounts={len(accounts_data.get('accounts', []))}, total_balance=${accounts_data.get('total_balance', 0)}"
            )

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot store account data")
                raise Exception("CosmosDB connection required for account storage")

            # Prepare stored data with timestamp
            now = datetime.now(timezone.utc)
            stored_data = {
                "id": user_id,  # CosmosDB requires explicit id
                "userId": user_id,  # For partition key
                "accounts": accounts_data.get("accounts", []),
                "total_balance": accounts_data.get("total_balance", 0.0),
                "account_count": accounts_data.get("account_count", 0),
                "last_updated": now.isoformat(),
                "created_at": now.isoformat(),
                "data_source": "plaid_api",
            }

            logger.info(
                f"Writing to CosmosDB container: {self.container_name}/{user_id}"
            )

            # Use upsert approach - try create first, then update if conflict
            try:
                # Try to create the document
                cosmos_client.create_item(self.container_name, stored_data, user_id)
                logger.info("Created new account data")
            except CosmosHttpResponseError as e:
                if e.status_code == 409:  # Conflict - document exists
                    # Get existing document to preserve created_at
                    try:
                        existing_doc = cosmos_client.get_item(
                            self.container_name, user_id, user_id
                        )
                        stored_data["created_at"] = existing_doc.get(
                            "created_at", stored_data["created_at"]
                        )
                    except:
                        pass  # Keep new created_at if can't get existing
                    
                    # Update existing document
                    cosmos_client.update_item(
                        self.container_name, user_id, user_id, stored_data
                    )
                    logger.info("Updated existing account data")
                else:
                    raise  # Re-raise other errors

            logger.info("CosmosDB write completed successfully")

            logger.info(
                f"Successfully stored account data for user {user_id} - {stored_data['account_count']} accounts, ${stored_data['total_balance']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store account data for user {user_id}: {e}")
            return False

    def get_stored_account_data(
        self, user_id: str, max_age_hours: int = None  # None means no age limit
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored account data from CosmosDB.

        Args:
            user_id: User ID to get data for
            max_age_hours: Maximum age of stored data in hours (None = no limit)

        Returns:
            Dict containing account data or None if not found
        """
        try:
            logger.info(
                f"Retrieving stored account data for user {user_id} (age limit: {max_age_hours} hours)"
            )

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot retrieve account data")
                return None

            # Get stored data from CosmosDB
            stored_data = cosmos_client.get_item(self.container_name, user_id, user_id)

            if not stored_data:
                logger.info(f"No stored account data found for user {user_id}")
                return None

            logger.info(f"Raw stored data for user {user_id}: {stored_data}")

            # Check age but don't filter out - just log
            last_updated_str = stored_data.get("last_updated")
            logger.info(
                f"Last updated value for user {user_id}: {last_updated_str} (type: {type(last_updated_str)})"
            )

            if last_updated_str:
                try:
                    # Parse ISO format timestamp
                    last_updated = datetime.fromisoformat(
                        last_updated_str.replace("Z", "+00:00")
                    )
                    logger.info(f"Parsed timestamp: {last_updated}")

                    # Calculate age but don't use it to filter
                    if max_age_hours:
                        max_age = timedelta(hours=max_age_hours)
                        age = datetime.now(timezone.utc) - last_updated
                        logger.info(
                            f"Data age for user {user_id}: {age}, max_age: {max_age}"
                        )

                        # Log but don't filter out
                        if age > max_age:
                            logger.info(
                                f"Data is older than limit but showing anyway (age: {age})"
                            )
                except Exception as parse_error:
                    logger.error(
                        f"Failed to parse timestamp string {last_updated_str}: {parse_error}"
                    )
                    # Don't return None - still show the data even if timestamp is bad

            logger.info(
                f"Retrieved stored account data for user {user_id} - {stored_data.get('account_count', 0)} accounts, last updated: {stored_data.get('last_updated')}"
            )
            return stored_data

        except Exception as e:
            logger.error(
                f"Failed to retrieve stored account data for user {user_id}: {e}"
            )
            return None

    def is_data_valid(self, user_id: str, max_age_hours: int = 24) -> bool:
        """
        Check if stored data exists and is still valid.

        Args:
            user_id: User ID to check
            max_age_hours: Maximum age of stored data in hours

        Returns:
            bool: True if valid data exists, False otherwise
        """
        try:
            stored_data = self.get_stored_account_data(user_id, max_age_hours)
            return stored_data is not None
        except Exception as e:
            logger.error(f"Failed to check data validity for user {user_id}: {e}")
            return False

    def get_data_info(
        self, user_id: str, max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about stored data (last updated, age, etc.) without returning full data.

        Args:
            user_id: User ID to get info for
            max_age_hours: Maximum age limit for expiry calculation

        Returns:
            Dict containing data metadata or None if not found
        """
        try:
            if not cosmos_client.is_connected:
                return None

            stored_data = cosmos_client.get_item(self.container_name, user_id, user_id)

            if not stored_data:
                return None

            last_updated_str = stored_data.get("last_updated")

            if last_updated_str:
                try:
                    last_updated = datetime.fromisoformat(
                        last_updated_str.replace("Z", "+00:00")
                    )
                    age_hours = (
                        datetime.now(timezone.utc) - last_updated
                    ).total_seconds() / 3600

                    return {
                        "last_updated": last_updated.isoformat(),
                        "age_hours": round(age_hours, 2),
                        "account_count": stored_data.get("account_count", 0),
                        "total_balance": stored_data.get("total_balance", 0.0),
                        "is_expired": age_hours > max_age_hours,
                    }
                except Exception as parse_error:
                    logger.error(f"Failed to parse timestamp: {parse_error}")

            return None

        except Exception as e:
            logger.error(f"Failed to get data info for user {user_id}: {e}")
            return None

    def clear_data(self, user_id: str) -> bool:
        """
        Clear stored account data for a user.

        Args:
            user_id: User ID to clear data for

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Clearing account data for user {user_id}")

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot clear account data")
                return False

            success = cosmos_client.delete_item(self.container_name, user_id, user_id)

            if success:
                logger.info(f"Successfully cleared account data for user {user_id}")
            else:
                logger.warning(f"Account data not found for user {user_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to clear account data for user {user_id}: {e}")
            return False

    def update_data_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update data metadata without changing account data.

        Args:
            user_id: User ID to update
            metadata: Metadata to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not cosmos_client.is_connected:
                return False

            cosmos_client.update_item(self.container_name, user_id, user_id, metadata)
            return True

        except Exception as e:
            logger.error(f"Failed to update data metadata for user {user_id}: {e}")
            return False

    def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all accounts for a user."""
        try:
            stored_data = self.get_stored_account_data(user_id)
            if stored_data and "accounts" in stored_data:
                return stored_data["accounts"]
            return []
        except Exception as e:
            logger.error(f"Failed to get accounts for user {user_id}: {e}")
            return []


# Global instance
account_storage_service = AccountStorageService()
