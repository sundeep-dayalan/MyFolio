"""
Authentication service for handling Microsoft Entra ID OAuth and JWT tokens.
"""

import uuid
from datetime import timedelta
from typing import Optional, Tuple

from .az_key_vault_service import AzureKeyVaultService

from ..constants.auth import Providers

from ..models.user import MicrosoftUserInfo, UserCreate, UserUpdate
from ..exceptions import AuthenticationError
from ..utils.logger import get_logger
from ..settings import settings
from .user_service import UserService
from .microsoft_entra_oauth_service import MicrosoftEntraOAuthService

logger = get_logger(__name__)


class AuthService:
    """Authentication service class."""

    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self.microsoft_oauth = MicrosoftEntraOAuthService()

    @staticmethod
    def generate_unique_user_id() -> str:
        """Generate a unique UUID for the user."""
        return str(uuid.uuid4())

    @staticmethod
    def create_provider_metadata(
        provider: str, provider_user_id: str, raw_user_data: dict = None
    ) -> dict:
        """Create provider metadata for storing OAuth provider information."""
        metadata = {
            "auth_provider": provider,
            "provider_user_id": provider_user_id,
            "provider_data": {f"{provider}_id": provider_user_id},
        }

        # Include raw user data if provided
        if raw_user_data:
            metadata["raw_user_data"] = raw_user_data

        return metadata

    def generate_microsoft_auth_url(
        self, state: Optional[str] = None
    ) -> Tuple[str, str]:
        """Generate Microsoft Entra ID OAuth authorization URL."""
        return self.microsoft_oauth.generate_auth_url(state)

    async def process_microsoft_oauth_callback(self, code: str, state: str):
        """Process Microsoft Entra ID OAuth callback and authenticate user."""
        try:
            # Exchange code for tokens
            tokens = await self.microsoft_oauth.exchange_code_for_tokens(code, state)

            # Verify ID token and get user info
            id_token = tokens.get("id_token")
            graph_user_data = (
                None  # Initialize to handle both ID token and Graph API flows
            )

            if not id_token:
                # Fallback to access token to get user info from Graph API
                access_token = tokens.get("access_token")
                if not access_token:
                    raise AuthenticationError("No valid token received from Microsoft")

                # Get user info from Microsoft Graph API
                graph_user_data = (
                    await self.microsoft_oauth.get_user_info_from_access_token(
                        access_token
                    )
                )

                # Create MicrosoftUserInfo from Graph API response
                microsoft_user_info = MicrosoftUserInfo(
                    sub=graph_user_data.get("id", ""),
                    oid=graph_user_data.get("id"),
                    email=graph_user_data.get("mail")
                    or graph_user_data.get("userPrincipalName", ""),
                    name=graph_user_data.get("displayName", ""),
                    given_name=graph_user_data.get("givenName"),
                    family_name=graph_user_data.get("surname"),
                )
            else:
                # Use ID token for user info
                microsoft_user_info = (
                    await self.microsoft_oauth.verify_and_get_user_info(id_token)
                )

                # Even with ID token, get raw user data from Graph API for storage
                access_token = tokens.get("access_token")
                if access_token:
                    try:
                        graph_user_data = (
                            await self.microsoft_oauth.get_user_info_from_access_token(
                                access_token
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to get Graph user data for storage: {e}"
                        )
                        graph_user_data = None

            # Try to get user from database
            try:
                user = await self.user_service.get_user_by_email_and_auth_provider(
                    microsoft_user_info.email,
                    Providers.Microsoft,
                    microsoft_user_info.oid or microsoft_user_info.sub,
                )

                if not user:
                    # Create new user with unique UUID and store provider info in metadata
                    provider_user_id = (
                        microsoft_user_info.oid or microsoft_user_info.sub
                    )
                    unique_user_id = self.generate_unique_user_id()

                    user_data = UserCreate(
                        id=unique_user_id,  # Use unique UUID
                        email=microsoft_user_info.email,
                        name=microsoft_user_info.name,
                        given_name=microsoft_user_info.given_name,
                        family_name=microsoft_user_info.family_name,
                    )
                    user = await self.user_service.create_user(user_data)

                    # Update user with provider metadata
                    provider_metadata = self.create_provider_metadata(
                        Providers.Microsoft, provider_user_id, graph_user_data
                    )
                    await self.user_service.update_user(
                        user.id, UserUpdate(metadata=provider_metadata)
                    )

                    logger.info(
                        f"New user created from Microsoft OAuth with provider metadata: {user.id}"
                    )

            except Exception as db_error:
                logger.error(
                    f"Database error during user lookup/creation: {str(db_error)}"
                )
                raise AuthenticationError("Database error during authentication")

            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("User account is deactivated")

            # Create application token
            token = self.microsoft_oauth.create_app_token(user)

            logger.info(
                f"User authenticated successfully via Microsoft OAuth: {user.id}"
            )
            return user, token

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during Microsoft OAuth callback: {str(e)}")
            raise AuthenticationError("Microsoft OAuth authentication failed")
