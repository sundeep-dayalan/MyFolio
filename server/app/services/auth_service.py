"""
Authentication service for handling Google OAuth and JWT tokens.
"""
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import jwt, JWTError

from ..models.user import GoogleUserInfo, Token, UserResponse, UserCreate
from ..exceptions import AuthenticationError, ValidationError
from ..utils.logger import get_logger
from ..utils.security import create_access_token, verify_token
from ..config import settings
from .user_service import UserService
from .google_oauth_service import GoogleOAuthService

logger = get_logger(__name__)


class AuthService:
    """Authentication service class."""

    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self.google_oauth = GoogleOAuthService()

    def generate_google_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """Generate Google OAuth authorization URL."""
        return self.google_oauth.generate_auth_url(state)

    async def process_google_oauth_callback(
        self, code: str, state: str
    ) -> Tuple[UserResponse, Token]:
        """Process Google OAuth callback and authenticate user."""
        try:
            # Exchange code for tokens
            tokens = await self.google_oauth.exchange_code_for_tokens(code, state)

            # Verify ID token and get user info
            id_token = tokens.get("id_token")
            if not id_token:
                raise AuthenticationError("No ID token received from Google")

            google_user_info = await self.google_oauth.verify_and_get_user_info(
                id_token
            )

            # Try to get user from database, fallback to mock user if CosmosDB is disabled
            try:
                user = await self.user_service.get_user_by_email(google_user_info.email)

                if not user:
                    # Create new user from Google info
                    user_data = UserCreate(
                        id=google_user_info.sub,  # Use Google's user ID
                        email=google_user_info.email,
                        name=google_user_info.name,
                        given_name=google_user_info.given_name,
                        family_name=google_user_info.family_name,
                        picture=google_user_info.picture,
                    )
                    user = await self.user_service.create_user(user_data)
                    logger.info(f"New user created from Google OAuth: {user.id}")

            except Exception as db_error:
                # If CosmosDB is disabled, create a mock user for testing
                if "CosmosDB" in str(db_error) or "not connected" in str(db_error):
                    logger.warning(
                        "CosmosDB is disabled, creating mock user for testing"
                    )
                    user = UserResponse(
                        id=google_user_info.sub,
                        email=google_user_info.email,
                        name=google_user_info.name,
                        given_name=google_user_info.given_name,
                        family_name=google_user_info.family_name,
                        picture=google_user_info.picture,
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
            token = self.google_oauth.create_app_token(user)

            logger.info(f"User authenticated successfully via OAuth: {user.id}")
            return user, token

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during Google OAuth callback: {str(e)}")
            raise AuthenticationError("OAuth authentication failed")

    async def authenticate_google_user(
        self, google_credential: str
    ) -> Tuple[UserResponse, Token]:
        """Authenticate user with Google credential and return user data with access token."""
        try:
            # For backward compatibility with client-side tokens
            # In the future, this method can be deprecated in favor of OAuth flow
            google_user_info = self._decode_google_jwt(google_credential)

            # Check if user exists, create if not
            user = await self.user_service.get_user_by_email(google_user_info.email)

            if not user:
                # Create new user from Google info
                user_data = UserCreate(
                    id=google_user_info.sub,  # Use Google's user ID
                    email=google_user_info.email,
                    name=google_user_info.name,
                    given_name=google_user_info.given_name,
                    family_name=google_user_info.family_name,
                    picture=google_user_info.picture,
                )
                user = await self.user_service.create_user(user_data)
                logger.info(f"New user created from Google auth: {user.id}")

            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("User account is deactivated")

            # Create access token
            access_token = self._create_user_token(user)

            # Create token response
            token = Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            )

            logger.info(f"User authenticated successfully: {user.id}")
            return user, token

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during Google authentication: {str(e)}")
            raise AuthenticationError("Authentication failed")
            if not user.is_active:
                raise AuthenticationError("User account is deactivated")

            # Create access token
            access_token = self._create_user_token(user)

            # Create token response
            token = Token(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            )

            logger.info(f"User authenticated successfully: {user.id}")
            return user, token

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during Google authentication: {str(e)}")
            raise AuthenticationError("Authentication failed")

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

    def _decode_google_jwt(self, token: str) -> GoogleUserInfo:
        """Decode Google JWT token without verification (for demo purposes)."""
        try:
            # In production, you should verify the token with Google's public keys
            # For now, we'll just decode it to get the user info

            # Split the token
            parts = token.split(".")
            if len(parts) != 3:
                raise ValidationError("Invalid JWT format")

            # Decode the payload
            payload = parts[1]

            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding

            # Decode base64
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_str = decoded_bytes.decode("utf-8")
            payload_data = json.loads(decoded_str)

            # Create GoogleUserInfo from payload
            return GoogleUserInfo(**payload_data)

        except (ValueError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error decoding Google JWT: {str(e)}")
            raise AuthenticationError("Invalid Google credential")

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
