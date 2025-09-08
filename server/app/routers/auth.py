"""
Microsoft Entra ID OAuth authentication routes.
"""

import urllib.parse
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..services.auth_service import AuthService
from ..services.user_service import UserService
from ..exceptions import AuthenticationError, ValidationError
from ..utils.logger import get_logger
from ..constants import ApiRoutes, ApiTags
from ..settings import settings

logger = get_logger(__name__)
router = APIRouter(prefix=ApiRoutes.AUTH_PREFIX, tags=[ApiTags.MICROSOFT_OAUTH])


@router.get("")
async def microsoft_oauth_login(
    state: Optional[str] = Query(
        None, description="Optional state parameter for security"
    ),
):
    """
    Initiate Microsoft Entra ID OAuth 2.0 authentication flow.
    Redirects user to Microsoft's authorization server.
    """
    try:
        # Initialize services
        user_service = UserService()
        auth_service = AuthService(user_service)

        # Generate authorization URL
        auth_url, oauth_state = auth_service.generate_microsoft_auth_url(state)

        logger.info(f"Generated Microsoft OAuth state: {oauth_state}")
        logger.info(f"Redirecting to Microsoft OAuth URL: {auth_url}")

        # Create redirect response
        response = RedirectResponse(url=auth_url, status_code=302)

        # Store state in secure HTTP-only cookie for CSRF protection
        response.set_cookie(
            key="oauth_state",
            value=oauth_state,
            max_age=600,  # 10 minutes - enough for OAuth flow
            httponly=True,
            secure=True,  # Only over HTTPS
            samesite="none",  # Allow cross-domain for production
            path="/",
        )

        return response

    except Exception as e:
        logger.error(f"Error initiating Microsoft OAuth: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth initiation failed")


@router.get("/callback")
async def microsoft_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Authorization code from Microsoft"),
    state: Optional[str] = Query(None, description="State parameter for security"),
    error: Optional[str] = Query(None, description="Error from Microsoft OAuth"),
    error_description: Optional[str] = Query(
        None, description="Error description from Microsoft"
    ),
):
    """
    Handle Microsoft Entra ID OAuth 2.0 callback.
    Exchanges authorization code for tokens and authenticates user.
    """
    try:
        # Check for OAuth errors
        if error:
            error_msg = f"OAuth error: {error}"
            if error_description:
                error_msg += f" - {error_description}"
            logger.warning(f"Microsoft OAuth error received: {error_msg}")
            react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote(error_msg)}"
            return RedirectResponse(url=react_error_url, status_code=302)

        # Validate required parameters
        if not code:
            logger.error("Authorization code is missing")
            react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote('Authorization code is required')}"
            return RedirectResponse(url=react_error_url, status_code=302)

        # Critical: Validate state parameter for CSRF protection
        oauth_state_cookie = request.cookies.get("oauth_state")
        if not state or not oauth_state_cookie:
            logger.error("State parameter or oauth_state cookie is missing")
            react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote('Invalid OAuth state - possible CSRF attack')}"
            return RedirectResponse(url=react_error_url, status_code=302)

        if state != oauth_state_cookie:
            logger.error(
                f"State parameter mismatch: received {state}, expected {oauth_state_cookie}"
            )
            react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote('Invalid OAuth state - possible CSRF attack')}"
            return RedirectResponse(url=react_error_url, status_code=302)

        logger.info(
            f"Processing Microsoft OAuth callback - code: {code[:10]}..., state: {state}"
        )
        logger.info(f"Frontend URL for redirect: '{settings.frontend_url}'")

        # Initialize services
        user_service = UserService()
        auth_service = AuthService(user_service)

        # Process OAuth callback
        user, token = await auth_service.process_microsoft_oauth_callback(code, state)

        # Create secure session response
        response = RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?success=true", status_code=302
        )

        # Set secure HTTP-only session cookie (only token needed)
        response.set_cookie(
            key="session",
            value=token.access_token,
            max_age=token.expires_in,
            httponly=True,
            secure=True,  # Only over HTTPS
            samesite="none",  # Allow cross-domain for production
            path="/",
        )

        # Clear the oauth_state cookie after successful validation
        response.set_cookie(
            key="oauth_state",
            value="",
            max_age=0,  # Expire immediately
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
        )

        logger.info(f"Microsoft OAuth callback successful for user: {user.id}")
        logger.info(
            f"Session cookies set, redirecting to: {settings.frontend_url}/auth/callback?success=true"
        )
        return response

    except AuthenticationError as e:
        logger.error(f"Authentication error in Microsoft OAuth callback: {str(e)}")
        # Redirect to React app with error
        react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote(str(e))}"
        return RedirectResponse(url=react_error_url, status_code=302)
    except ValidationError as e:
        logger.error(f"Validation error in Microsoft OAuth callback: {str(e)}")
        # Redirect to React app with error
        react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote(str(e))}"
        return RedirectResponse(url=react_error_url, status_code=302)
    except Exception as e:
        logger.error(f"Unexpected error in Microsoft OAuth callback: {str(e)}")
        # Redirect to React app with error
        react_error_url = f"{settings.frontend_url}/auth/callback?success=false&error={urllib.parse.quote('OAuth callback failed')}"
        return RedirectResponse(url=react_error_url, status_code=302)


@router.get("/session/me")
async def get_current_user(request: Request):
    """
    Get current authenticated user details.
    This endpoint is optimized for frequent calls (app initialization, etc.)
    """
    try:
        session_token = request.cookies.get("session")

        if not session_token:
            raise HTTPException(status_code=401, detail="No active session")

        # Decode JWT token to get user data
        try:
            from ..services.az_key_vault_service import AzureKeyVaultService

            # Decode and validate the JWT token
            payload = AzureKeyVaultService.verify_token(session_token)

            if not payload:
                raise Exception("Token verification failed - invalid or expired token")

            # Return only user data (no token for security)
            user_data = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
            }

            return user_data

        except Exception as token_error:
            logger.error(f"Token validation failed in /me endpoint: {str(token_error)}")
            raise HTTPException(status_code=401, detail="Invalid or expired session")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session /me validation error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid session")


@router.post("/logout")
async def logout():
    """
    Logout user by clearing session cookies and optionally ending Microsoft session.
    """
    try:
        # Create logout response
        logout_data = {"message": "Logged out successfully"}

        from fastapi.responses import JSONResponse

        json_response = JSONResponse(content=logout_data)

        # Clear session cookie
        json_response.set_cookie(
            key="session",
            value="",
            max_age=0,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
        )

        # Also clear any remaining oauth_state cookie
        json_response.set_cookie(
            key="oauth_state",
            value="",
            max_age=0,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
        )

        logger.info("User logged out, session cookies cleared")
        return json_response

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/status")
async def microsoft_oauth_status():
    """
    Get Microsoft OAuth configuration status.
    """
    return {
        "microsoft_oauth_enabled": bool(
            settings.azure_client_id
            and settings.azure_client_secret
            and settings.azure_tenant_id
        ),
        "redirect_uri": settings.azure_redirect_uri,
        "frontend_url": settings.frontend_url,
        "tenant_id": settings.azure_tenant_id,
        "available_flows": ["authorization_code"],
    }
