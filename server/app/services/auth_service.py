"""
Authentication service for handling Microsoft Entra ID OAuth and JWT tokens.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple

from ..models.user import MicrosoftUserInfo, Token, UserResponse, UserCreate
from ..exceptions import AuthenticationError
from ..utils.logger import get_logger
from ..utils.security import create_access_token, verify_token
from ..config import settings
from .user_service import UserService
from .microsoft_entra_oauth_service import MicrosoftEntraOAuthService

logger = get_logger(__name__)


class AuthService:
    """Authentication service class."""

    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self.microsoft_oauth = MicrosoftEntraOAuthService()

    def generate_microsoft_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """Generate Microsoft Entra ID OAuth authorization URL."""
        return self.microsoft_oauth.generate_auth_url(state)

    async def process_microsoft_oauth_callback(
        self, code: str, state: str
    ) -> Tuple[UserResponse, Token]:
        """Process Microsoft Entra ID OAuth callback and authenticate user."""
        try:
            # Exchange code for tokens
            tokens = await self.microsoft_oauth.exchange_code_for_tokens(code, state)

            # Verify ID token and get user info
            id_token = tokens.get("id_token")
            if not id_token:
                # Fallback to access token to get user info from Graph API
                access_token = tokens.get("access_token")
                if not access_token:
                    raise AuthenticationError("No valid token received from Microsoft")
                
                # Get user info from Microsoft Graph API
                graph_user_data = await self.microsoft_oauth.get_user_info_from_access_token(access_token)
                
                # Create MicrosoftUserInfo from Graph API response
                microsoft_user_info = MicrosoftUserInfo(
                    sub=graph_user_data.get("id", ""),
                    oid=graph_user_data.get("id"),
                    email=graph_user_data.get("mail") or graph_user_data.get("userPrincipalName", ""),
                    name=graph_user_data.get("displayName", ""),
                    given_name=graph_user_data.get("givenName"),
                    family_name=graph_user_data.get("surname"),
                )
            else:
                # Use ID token for user info
                microsoft_user_info = await self.microsoft_oauth.verify_and_get_user_info(id_token)

            # Try to get user from database, fallback to mock user if CosmosDB is disabled
            try:
                user = await self.user_service.get_user_by_email(microsoft_user_info.email)

                if not user:
                    # Create new user from Microsoft info
                    user_id = microsoft_user_info.oid or microsoft_user_info.sub
                    user_data = UserCreate(
                        id=user_id,  # Use Microsoft's user ID (oid preferred, sub as fallback)
                        email=microsoft_user_info.email,
                        name=microsoft_user_info.name,
                        given_name=microsoft_user_info.given_name,
                        family_name=microsoft_user_info.family_name,
                    )
                    user = await self.user_service.create_user(user_data)
                    logger.info(f"New user created from Microsoft OAuth: {user.id}")

            except Exception as db_error:
                # If CosmosDB is disabled, create a mock user for testing
                if "CosmosDB" in str(db_error) or "not connected" in str(db_error):
                    logger.warning(
                        "CosmosDB is disabled, creating mock user for testing"
                    )
                    user_id = microsoft_user_info.oid or microsoft_user_info.sub
                    user = UserResponse(
                        id=user_id,
                        email=microsoft_user_info.email,
                        name=microsoft_user_info.name,
                        given_name=microsoft_user_info.given_name,
                        family_name=microsoft_user_info.family_name,
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                else:
                    raise db_error

            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("User account is deactivated")

            # Create application token
            token = self.microsoft_oauth.create_app_token(user)

            logger.info(f"User authenticated successfully via Microsoft OAuth: {user.id}")
            return user, token

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during Microsoft OAuth callback: {str(e)}")
            raise AuthenticationError("Microsoft OAuth authentication failed")


    async def verify_access_token(self, token: str) -> Optional[UserResponse]:
        """Verify access token and return user if valid."""
        try:
            payload = verify_token(token)
            if not payload:
                return None

            user_id = payload.get("sub")
            if not user_id:
                return None

            # Get user from database
            user = await self.user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                return None

            return user

        except Exception as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None


    def _create_user_token(self, user: UserResponse) -> str:
        """Create JWT access token for user."""
        token_data = {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "type": "access_token",
        }

        return create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

    async def refresh_token(self, current_user: UserResponse) -> Token:
        """Create a new access token for the current user."""
        access_token = self._create_user_token(current_user)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
