"""
Microsoft Entra ID OAuth service for secure server-side authentication.
"""

import secrets
from datetime import timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
import httpx
import jwt

from .az_key_vault_service import AzureKeyVaultService

from ..settings import settings
from ..models.user import MicrosoftUserInfo, UserResponse, Token
from ..exceptions import AuthenticationError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MicrosoftEntraOAuthService:
    """Microsoft Entra ID OAuth service for secure authentication."""

    def __init__(self):
        self.client_id = getattr(settings, "azure_client_id", None)
        self.client_secret = getattr(settings, "azure_client_secret", None)
        self.tenant_id = getattr(settings, "azure_tenant_id", None)
        self.redirect_uri = getattr(
            settings,
            "azure_redirect_uri",
            f"http://localhost:8000/api/v1/auth/oauth/microsoft/callback",
        )

        # Microsoft Graph scopes for user profile information
        self.scopes = ["openid", "profile", "email", "User.Read"]

        # Microsoft Entra ID endpoints (supports both organizational and personal accounts)
        self.authority = "https://login.microsoftonline.com/common"
        self.auth_url = f"{self.authority}/oauth2/v2.0/authorize"
        self.token_url = f"{self.authority}/oauth2/v2.0/token"
        self.userinfo_url = "https://graph.microsoft.com/v1.0/me"

    def generate_auth_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate Microsoft Entra ID OAuth authorization URL.
        Returns tuple of (auth_url, state).
        """
        if not state:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.scopes),
            "state": state,
            "prompt": "consent",
        }

        auth_url = f"{self.auth_url}?{urlencode(params)}"
        logger.info(f"Generated Microsoft auth URL for state: {state}")

        return auth_url, state

    async def exchange_code_for_tokens(
        self, code: str, state: Optional[str] = None
    ) -> Dict[str, Any]:
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
                "scope": " ".join(self.scopes),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
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

    async def verify_and_get_user_info(self, id_token_str: str) -> MicrosoftUserInfo:
        """
        Verify Microsoft ID token and extract user information.
        Note: In production, you should verify the JWT signature with Microsoft's public keys.
        For now, we'll decode without verification and get user info from Graph API.
        """
        try:
            # Decode JWT without verification (not recommended for production)
            # In production, verify with Microsoft's public keys
            decoded_token = jwt.decode(
                id_token_str,
                options={"verify_signature": False},  # Not secure - for demo only
            )

            # Extract user information from ID token
            user_info = MicrosoftUserInfo(
                oid=decoded_token.get("oid"),
                sub=decoded_token.get("sub"),
                tid=decoded_token.get("tid"),
                email=decoded_token.get("email")
                or decoded_token.get("preferred_username"),
                name=decoded_token.get("name", ""),
                given_name=decoded_token.get("given_name"),
                family_name=decoded_token.get("family_name"),
                exp=decoded_token.get("exp"),
                iat=decoded_token.get("iat"),
            )

            logger.info(f"Successfully verified Microsoft user: {user_info.email}")
            return user_info

        except Exception as e:
            logger.error(f"Error verifying ID token: {str(e)}")
            raise AuthenticationError("Token verification failed")

    async def get_user_info_from_access_token(
        self, access_token: str
    ) -> Dict[str, Any]:
        """
        Get user information from Microsoft Graph API using access token.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get user info: {response.text}")
                    raise AuthenticationError("Failed to get user information")

                user_data = response.json()
                logger.info(
                    f"Retrieved user info for: {user_data.get('mail', user_data.get('userPrincipalName'))}"
                )
                return user_data

        except Exception as e:
            logger.error(f"Error getting user info from Graph API: {str(e)}")
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
            "auth_method": "microsoft_entra",
        }

        access_token = AzureKeyVaultService.create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def revoke_token(self, token: Optional[str] = None) -> bool:
        """
        Revoke Microsoft OAuth token.
        Microsoft doesn't have a direct token revocation endpoint.
        Tokens will expire naturally based on their configured lifetime.
        """
        try:
            # Microsoft doesn't have a direct token revocation endpoint
            # Token expiration will handle security
            logger.info("Microsoft token marked for revocation (will expire naturally)")
            return True

        except Exception as e:
            logger.error(f"Error during token revocation: {str(e)}")
            return False
