"""
Application dependencies.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .database import cosmos_client
from .exceptions import AuthenticationError
from .services.user_service import UserService
from .services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_cosmos_client():
    """Get CosmosDB client dependency."""
    return cosmos_client


def get_user_service() -> UserService:
    """Get user service dependency."""
    return UserService()


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    """Get auth service dependency."""
    return AuthService(user_service)


async def get_current_user(request: Request) -> str:
    """Get current user ID from session cookie.

    This is used for endpoints that have been migrated to use session cookies
    instead of JWT Bearer tokens.
    """
    try:
        session_token = request.cookies.get("session")

        if not session_token:
            raise HTTPException(status_code=401, detail="No active session")

        # Decode JWT token to get user ID
        from .services.az_key_vault_service import AzureKeyVaultService

        payload = AzureKeyVaultService.verify_token(session_token)

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session data")

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Session validation failed")


# Convenience functions for getting services
def get_plaid_service():
    """Get Plaid service instance."""
    from .services.plaid_service import PlaidService

    return PlaidService()
