"""
Setup and configuration routes for initial app setup.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..dependencies import get_current_user_id
from ..utils.logger import get_logger
from ..services.firestore_service import FirestoreService
from ..config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/setup", tags=["setup"])


class PlaidConfigRequest(BaseModel):
    client_id: str = Field(..., description="Plaid client ID")
    secret: str = Field(..., description="Plaid secret key")
    env: str = Field(default="sandbox", description="Plaid environment (sandbox/production)")


class PlaidConfigResponse(BaseModel):
    success: bool
    message: str


class SetupStatusResponse(BaseModel):
    plaid_configured: bool
    oauth_configured: bool
    app_ready: bool


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(user_id: str = Depends(get_current_user_id)):
    """
    Get the current setup status of the application.
    """
    try:
        # Check if Plaid is configured
        plaid_configured = (
            settings.PLAID_CLIENT_ID and 
            settings.PLAID_SECRET and 
            settings.PLAID_CLIENT_ID != "SETUP_LATER" and
            settings.PLAID_SECRET != "SETUP_LATER"
        )
        
        # Check if OAuth is configured
        oauth_configured = (
            settings.GOOGLE_CLIENT_ID and 
            settings.GOOGLE_CLIENT_SECRET
        )
        
        app_ready = plaid_configured and oauth_configured
        
        return SetupStatusResponse(
            plaid_configured=plaid_configured,
            oauth_configured=oauth_configured,
            app_ready=app_ready
        )
        
    except Exception as e:
        logger.error(f"Error getting setup status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get setup status")


@router.post("/plaid", response_model=PlaidConfigResponse)
async def configure_plaid(
    config: PlaidConfigRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Configure Plaid credentials for the application.
    Note: In a production environment, this would need additional security measures.
    """
    try:
        # In a real production app, you'd want to:
        # 1. Validate the user has admin permissions
        # 2. Store credentials securely in Secret Manager
        # 3. Restart the application to pick up new credentials
        
        # For now, we'll store in user's profile for per-user configuration
        firestore_service = FirestoreService()
        
        user_config = {
            "plaid_client_id": config.client_id,
            "plaid_env": config.env,
            "configured_at": firestore_service.server_timestamp(),
            "configured_by": user_id
        }
        
        # Store in user's configuration (without the secret in logs)
        await firestore_service.store_user_plaid_config(user_id, user_config)
        
        logger.info(f"Plaid configuration updated for user {user_id}")
        
        return PlaidConfigResponse(
            success=True,
            message="Plaid configuration updated successfully. Please restart the application to apply changes."
        )
        
    except Exception as e:
        logger.error(f"Error configuring Plaid: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to configure Plaid credentials")


@router.get("/instructions")
async def get_setup_instructions():
    """
    Get setup instructions for configuring the application.
    """
    return {
        "plaid_setup": {
            "title": "Set up Plaid Integration",
            "steps": [
                "Go to https://dashboard.plaid.com/",
                "Sign up or log in to your account",
                "Create a new application",
                "Copy your Client ID and Secret",
                "Use the /setup/plaid endpoint to configure"
            ],
            "sandbox_credentials": {
                "note": "For testing, you can use Plaid's sandbox environment",
                "test_bank": "First Platypus Bank",
                "test_username": "user_good",
                "test_password": "pass_good"
            }
        },
        "oauth_setup": {
            "title": "Google OAuth Configuration",
            "steps": [
                "Go to https://console.cloud.google.com/apis/credentials",
                "Create OAuth 2.0 Client ID",
                "Set application type to 'Web application'",
                "Add your domain to authorized origins",
                "Add redirect URIs for your application"
            ],
            "redirect_uris": [
                f"{settings.FRONTEND_URL}/auth/callback" if hasattr(settings, 'FRONTEND_URL') else "https://your-app-domain.com/auth/callback",
                "http://localhost:5173/auth/callback"  # For local development
            ]
        }
    }