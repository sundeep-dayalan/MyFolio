"""
Application dependencies.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .database import cosmos_client
from .exceptions import DatabaseConnectionError, AuthenticationError
from .services.user_service import UserService
from .services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_cosmos_client():
    """Get CosmosDB client dependency."""
    if not cosmos_client.is_connected:
        raise DatabaseConnectionError("CosmosDB client not initialized")
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
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

    # Fallback to session-based authentication
    session = request.session
    if "user_id" in session:
        # fetch user from DB once and cache
        user = await auth_service.user_service.get_user_by_id(session["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session user",
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.current_user = user
        return user

    # If neither method works, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id(
    current_user=Depends(get_current_user),
) -> str:
    """Get current user id by reusing the cached user object from get_current_user.

    This function intentionally depends on `get_current_user` (resolved by FastAPI)
    so that the user lookup is performed once per request and cached on
    `request.state.current_user`.
    """
    # FastAPI will inject the result of get_current_user here. If something
    # else depends on get_current_user_id directly, get_current_user will run
    # first and cache the user on request.state.
    # We accept either a full user object or a dict-like with an 'id' key.
    user = current_user
    if not user:
        # Defensive fallback: raise unauthorized if dependency didn't provide user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # user may be a pydantic model with attribute 'id' or a dict
    try:
        return user.id
    except Exception:
        return user.get("id") if isinstance(user, dict) else None


# Convenience functions for getting services
def get_plaid_service():
    """Get Plaid service instance."""
    from .services.plaid_service import PlaidService

    return PlaidService()
