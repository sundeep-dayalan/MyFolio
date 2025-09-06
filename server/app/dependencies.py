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


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Resolve the current user, caching the result on `request.state.current_user`
    so subsequent lookups in the same request don't hit the database again.

    Behavior:
    - Try bearer token first (verify token + DB lookup via AuthService).
    - Fallback to session-based auth (uses session['user_id']).
    - Cache the resolved user object on `request.state.current_user`.
    """
    # Return cached user if already resolved for this request
    existing = getattr(request.state, "current_user", None)
    if existing:
        return existing

    # If credentials are provided, verify token and fetch user
    if credentials:
        user = await auth_service.verify_access_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Cache for remainder of request
        request.state.current_user = user
        return user

    # Fallback to session-based auth
    try:
        session_token = request.cookies.get("session")
        
        if session_token:
            # Decode JWT token to get user data
            from .services.az_key_vault_service import AzureKeyVaultService
            
            payload = AzureKeyVaultService.verify_token(session_token)
            
            if payload:
                user_data = {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": payload.get("name"),
                }
                # Create a simple user object that matches UserResponse
                from .models.user import UserResponse
                user = UserResponse(**user_data)
                
                # Cache for remainder of request
                request.state.current_user = user
                return user
    except Exception:
        pass

    # If neither method works, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Get current user id directly from JWT token without database lookup.

    This is optimized for cases where you only need the user ID and don't need
    the full user object, avoiding unnecessary database calls.
    """
    # Check if we already have user_id cached from a previous get_current_user call
    existing_user = getattr(request.state, "current_user", None)
    if existing_user:
        try:
            return existing_user.id
        except Exception:
            return existing_user.get("id") if isinstance(existing_user, dict) else None

    # If credentials are provided, extract user_id directly from token
    if credentials:
        try:
            from .services.az_key_vault_service import AzureKeyVaultService

            payload = AzureKeyVaultService.verify_token(credentials.credentials)
            if payload and payload.get("sub"):
                return payload.get("sub")
        except Exception:
            pass

    # If no method works, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id_from_session(request: Request) -> str:
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
