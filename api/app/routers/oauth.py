"""
OAuth authentication routes for Google OAuth 2.0 flow.
"""
import urllib.parse
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from ..models.user import UserResponse, Token
from ..services.auth_service import AuthService
from ..services.user_service import UserService
from ..exceptions import AuthenticationError, ValidationError
from ..utils.logger import get_logger
from ..database import firebase_client
from ..config import settings

logger = get_logger(__name__)
router = APIRouter(prefix="/auth/oauth", tags=["OAuth Authentication"])


@router.get("/google")
async def google_oauth_login(
    request: Request,
    state: Optional[str] = Query(None, description="Optional state parameter for security")
):
    """
    Initiate Google OAuth 2.0 authentication flow.
    Redirects user to Google's authorization server.
    """
    try:
        # Initialize services
        user_service = UserService(firebase_client.db)
        auth_service = AuthService(user_service)
        
        # Generate authorization URL
        auth_url, oauth_state = auth_service.generate_google_auth_url(state)
        
        # Log the OAuth state for debugging (remove in production)
        logger.info(f"Generated OAuth state: {oauth_state}")
        logger.info(f"Redirecting to Google OAuth URL: {auth_url}")
        
        # Redirect to Google's authorization server
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth initiation failed")


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter for security"),
    error: Optional[str] = Query(None, description="Error from Google OAuth")
):
    """
    Handle Google OAuth 2.0 callback.
    Exchanges authorization code for tokens and authenticates user.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.warning(f"OAuth error received: {error}")
            react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote(f'OAuth error: {error}')}"
            return RedirectResponse(url=react_error_url, status_code=302)
        
        # Validate required parameters
        if not code:
            logger.error("Authorization code is missing")
            react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote('Authorization code is required')}"
            return RedirectResponse(url=react_error_url, status_code=302)
        
        if not state:
            logger.warning("State parameter is missing - continuing anyway")
        
        logger.info(f"Processing OAuth callback - code: {code[:10]}..., state: {state}")
        logger.info(f"Frontend URL for redirect: {settings.frontend_url}")
        
        # Initialize services
        user_service = UserService(firebase_client.db)
        auth_service = AuthService(user_service)
        
        # Process OAuth callback
        user, token = await auth_service.process_google_oauth_callback(code, state)
        
        # Redirect back to React app with success parameters
        user_data = urllib.parse.quote(user.json())
        react_callback_url = f"{settings.frontend_url}/auth/callback?success=true&token={token.access_token}&user={user_data}"
        
        logger.info(f"OAuth callback successful for user: {user.id}")
        logger.info(f"Redirecting to: {react_callback_url}")
        return RedirectResponse(url=react_callback_url, status_code=302)
        
    except AuthenticationError as e:
        logger.error(f"Authentication error in OAuth callback: {str(e)}")
        # Redirect to React app with error
        react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote(str(e))}"
        return RedirectResponse(url=react_error_url, status_code=302)
    except ValidationError as e:
        logger.error(f"Validation error in OAuth callback: {str(e)}")
        # Redirect to React app with error
        react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote(str(e))}"
        return RedirectResponse(url=react_error_url, status_code=302)
    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")
        # Redirect to React app with error
        react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote('OAuth callback failed')}"
        return RedirectResponse(url=react_error_url, status_code=302)


@router.post("/google/revoke")
async def revoke_google_token(
    request: Request,
    token: str
):
    """
    Revoke Google OAuth token.
    """
    try:
        # Initialize services
        user_service = UserService(firebase_client.db)
        auth_service = AuthService(user_service)
        
        # Revoke the token
        success = await auth_service.google_oauth.revoke_token(token)
        
        if success:
            return {"message": "Token revoked successfully"}
        else:
            return {"message": "Token revocation may have failed", "warning": True}
            
    except Exception as e:
        logger.error(f"Error revoking token: {str(e)}")
        raise HTTPException(status_code=500, detail="Token revocation failed")


@router.get("/status")
async def oauth_status():
    """
    Get OAuth configuration status.
    """
    return {
        "google_oauth_enabled": bool(settings.google_client_id and settings.google_client_secret),
        "redirect_uri": settings.google_redirect_uri,
        "frontend_url": settings.frontend_url,
        "available_flows": ["authorization_code"]
    }
