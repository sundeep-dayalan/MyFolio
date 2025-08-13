"""
Application dependencies.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import firestore

from .database import firebase_client
from .exceptions import DatabaseConnectionError, AuthenticationError
from .services.user_service import UserService
from .services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_firestore_client() -> firestore.Client:
    """Get Firestore client dependency."""
    if not firebase_client.is_connected:
        raise DatabaseConnectionError("Firestore client not initialized")
    return firebase_client.db


def get_user_service(
    db: firestore.Client = Depends(get_firestore_client),
) -> UserService:
    """Get user service dependency."""
    return UserService(db)


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    """Get auth service dependency."""
    return AuthService(user_service)


async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> str:
    """
    Get current user ID from authentication token or session.
    """
    # First try to get from Authorization header (Bearer token)
    if credentials:
        user = await auth_service.verify_access_token(credentials.credentials)
        if user:
            return user.id

    # Fallback to session-based authentication
    session = request.session
    if "user_id" in session:
        return session["user_id"]

    # If neither method works, raise authentication error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get current user from authentication token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.verify_access_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
