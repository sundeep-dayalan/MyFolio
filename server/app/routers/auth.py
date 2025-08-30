"""
Microsoft Entra ID OAuth authentication routes.
"""

import urllib.parse
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..models.user import UserResponse
from ..services.auth_service import AuthService
from ..services.user_service import UserService
from ..exceptions import AuthenticationError, ValidationError
from ..utils.logger import get_logger
from ..constants import ApiRoutes, ApiTags
from ..database import cosmos_client
from ..settings import settings

logger = get_logger(__name__)
router = APIRouter(prefix=ApiRoutes.AUTH_PREFIX, tags=[ApiTags.MICROSOFT_OAUTH])


async def ensure_cosmos_connected():
    """Ensure CosmosDB is connected, initializing if necessary."""
    if not cosmos_client.is_connected:
        logger.info("CosmosDB not connected, initializing...")
        try:
            await cosmos_client.connect()
        except Exception as e:
            logger.warning(
                f"CosmosDB connection failed, continuing in offline mode: {str(e)}"
            )
            # Continue in offline mode - OAuth can still work without CosmosDB


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
        # Ensure CosmosDB is connected
        await ensure_cosmos_connected()

        # Initialize services
        user_service = UserService()
        auth_service = AuthService(user_service)

        # Generate authorization URL
        auth_url, oauth_state = auth_service.generate_microsoft_auth_url(state)

        logger.info(f"Generated Microsoft OAuth state: {oauth_state}")
        logger.info(f"Redirecting to Microsoft OAuth URL: {auth_url}")

        # Redirect to Microsoft's authorization server
        return RedirectResponse(url=auth_url, status_code=302)

    except Exception as e:
        logger.error(f"Error initiating Microsoft OAuth: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth initiation failed")


@router.get("/callback")
async def microsoft_oauth_callback(
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

        if not state:
            logger.warning("State parameter is missing - continuing anyway")

        logger.info(
            f"Processing Microsoft OAuth callback - code: {code[:10]}..., state: {state}"
        )
        logger.info(f"Frontend URL for redirect: '{settings.frontend_url}'")

        # Ensure CosmosDB is connected
        await ensure_cosmos_connected()

        # Initialize services
        user_service = UserService()
        auth_service = AuthService(user_service)

        # Process OAuth callback
        user, token = await auth_service.process_microsoft_oauth_callback(code, state)

        # Redirect back to React app with success parameters
        user_data = urllib.parse.quote(user.model_dump_json())
        react_callback_url = f"{settings.frontend_url}/auth/callback?success=true&token={token.access_token}&user={user_data}"

        logger.info(f"Microsoft OAuth callback successful for user: {user.id}")
        logger.info(f"Redirecting to: {react_callback_url}")
        return RedirectResponse(url=react_callback_url, status_code=302)

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
