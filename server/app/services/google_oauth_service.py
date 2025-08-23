"""
Google OAuth service for secure server-side authentication.
"""
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
import httpx
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from ..config import settings
from ..models.user import GoogleUserInfo, UserResponse, Token
from ..exceptions import AuthenticationError, ValidationError
from ..utils.logger import get_logger
from ..utils.security import create_access_token

logger = get_logger(__name__)


class GoogleOAuthService:
    """Google OAuth service for secure authentication."""

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.scopes = [
            "openid",
            "email",
            "profile",
            # Adding Calendar scope to force Google to respect test users restriction
            # This is needed because Google ignores test users for basic scopes only
            "https://www.googleapis.com/auth/calendar.readonly",
        ]

        # OAuth endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    def generate_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate Google OAuth authorization URL.
        Returns tuple of (auth_url, state).
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        auth_url = f"{self.auth_url}?{urlencode(params)}"
        logger.info(f"Generated auth URL for state: {state}")

        return auth_url, state

    async def exchange_code_for_tokens(self, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access tokens.
        """
        try:
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={"Accept": "application/json"},
                )

                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    raise AuthenticationError("Failed to exchange authorization code")

                tokens = response.json()
                logger.info(f"Successfully exchanged code for tokens")
                return tokens

        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise AuthenticationError("Token exchange failed")

    async def verify_and_get_user_info(self, id_token_str: str) -> GoogleUserInfo:
        """
        Verify Google ID token and extract user information.
        """
        try:
            # Verify the ID token
            id_info = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), self.client_id
            )

            # Check if token is valid
            if id_info["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise AuthenticationError("Invalid token issuer")

            # Extract user information
            user_info = GoogleUserInfo(
                sub=id_info["sub"],
                email=id_info["email"],
                name=id_info.get("name", ""),
                given_name=id_info.get("given_name"),
                family_name=id_info.get("family_name"),
                picture=id_info.get("picture"),
                exp=id_info["exp"],
                iat=id_info["iat"],
            )

            logger.info(f"Successfully verified user: {user_info.email}")
            return user_info

        except ValueError as e:
            logger.error(f"Invalid ID token: {str(e)}")
            raise AuthenticationError("Invalid or expired token")
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise AuthenticationError("Token verification failed")

    async def get_user_info_from_access_token(
        self, access_token: str
    ) -> Dict[str, Any]:
        """
        Get user information using access token.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get user info: {response.text}")
                    raise AuthenticationError("Failed to get user information")

                user_data = response.json()
                logger.info(f"Retrieved user info for: {user_data.get('email')}")
                return user_data

        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise AuthenticationError("Failed to retrieve user information")

    def create_app_token(self, user_data: UserResponse) -> Token:
        """
        Create application JWT token for authenticated user.
        """
        token_data = {
            "sub": user_data.id,
            "email": user_data.email,
            "name": user_data.name,
            "type": "access_token",
            "auth_method": "google_oauth",
        }

        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke Google OAuth token.
        """
        try:
            revoke_url = "https://oauth2.googleapis.com/revoke"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    revoke_url,
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    logger.info("Successfully revoked Google token")
                    return True
                else:
                    logger.warning(f"Failed to revoke token: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error revoking token: {str(e)}")
            return False
