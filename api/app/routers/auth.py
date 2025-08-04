"""
Authentication routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import firestore

from ..models.user import GoogleTokenData, Token, UserResponse
from ..services.user_service import UserService
from ..services.auth_service import AuthService
from ..dependencies import get_firestore_client
from ..exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


def get_user_service(db: firestore.Client = Depends(get_firestore_client)) -> UserService:
    """Get user service dependency."""
    return UserService(db)


def get_auth_service(user_service: UserService = Depends(get_user_service)) -> AuthService:
    """Get auth service dependency."""
    return AuthService(user_service)


@router.post("/google", response_model=dict)
async def authenticate_with_google(
    token_data: GoogleTokenData,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user with Google OAuth token."""
    try:
        user, token = await auth_service.authenticate_google_user(token_data.credential)
        
        return {
            "user": user,
            "token": token,
            "message": "Authentication successful"
        }
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required"
        )
    
    # Verify current token
    current_user = await auth_service.verify_access_token(credentials.credentials)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Generate new token
    new_token = await auth_service.refresh_token(current_user)
    return new_token


@router.get("/me", response_model=UserResponse)
async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current authenticated user information."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required"
        )
    
    user = await auth_service.verify_access_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user


@router.post("/logout", status_code=204)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user (client-side token invalidation)."""
    # In a stateless JWT system, logout is typically handled client-side
    # by removing the token from client storage
    # Here we just verify the token is valid and return success
    
    if credentials:
        user = await auth_service.verify_access_token(credentials.credentials)
        if user:
            # Token is valid, logout successful
            return
    
    # Even if token is invalid, we return success for logout
    return
