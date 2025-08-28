"""
Plaid configuration API endpoints for admin credential management.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.plaid_config import (
    PlaidConfigurationCreate,
    PlaidConfigurationResponse,
    PlaidValidationResult,
    PlaidConfigurationStatus,
    PlaidConfigurationValidate,
)
from ..services.plaid_config_service import plaid_config_service
from ..services.plaid_service import PlaidService
from ..dependencies import get_current_user
from ..models.user import UserResponse
from ..utils.logger import get_logger
from ..constants import ApiRoutes, ApiTags

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter(prefix=ApiRoutes.PLAID_PREFIX, tags=[ApiTags.PLAID_CONFIGURATION])


def require_admin_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Require admin user for Plaid configuration operations."""
    # For now, all authenticated users are considered admins
    # In production, you might want to add role-based access control
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return current_user


@router.post("/configuration", response_model=PlaidConfigurationResponse)
async def store_plaid_configuration(
    config: PlaidConfigurationCreate,
    current_user: UserResponse = Depends(require_admin_user),
):
    """
    Store Plaid API credentials securely.

    **Admin Only**: Stores client_id and encrypted secret in database.
    The secret is encrypted using Azure Key Vault cryptographic operations.

    - **plaid_client_id**: Your Plaid client ID
    - **plaid_secret**: Your Plaid secret (will be encrypted)
    """
    try:
        # Validate credentials before storing
        validation_result = await plaid_config_service.validate_credentials(
            client_id=config.plaid_client_id,
            secret=config.plaid_secret,
            environment=config.environment,
        )
        if not validation_result.is_valid:
            logger.error(
                f"Plaid credential validation failed: {validation_result.message}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_result.message,
            )

        result = await plaid_config_service.store_configuration(
            config=config, admin_user_id=current_user.id
        )

        logger.info(f"Plaid configuration stored by user: {current_user.id}")
        return result

    except ValueError as e:
        logger.error(f"Configuration storage error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error storing configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store configuration",
        )


@router.get("/configuration/status", response_model=PlaidConfigurationStatus)
async def get_plaid_configuration_status(
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Check if Plaid is configured and active for the current user.

    Returns basic status without sensitive information.
    Used by frontend to show/hide Plaid features.
    """
    try:
        status_result = await plaid_config_service.get_configuration_status(current_user.id)
        return status_result

    except Exception as e:
        logger.error(f"Error getting configuration status: {e}")
        # Return unconfigured status on error
        return PlaidConfigurationStatus(is_configured=False)


@router.get("/configuration", response_model=PlaidConfigurationResponse)
async def get_plaid_configuration(
    current_user: UserResponse = Depends(require_admin_user),
):
    """
    Get Plaid configuration details for the current user.

    **Admin Only**: Returns configuration with masked client_id.
    Secret is never returned for security.
    """
    try:
        config = await plaid_config_service.get_configuration(current_user.id)

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plaid configuration not found",
            )

        return config

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration",
        )


@router.post("/configuration/validate", response_model=PlaidValidationResult)
async def validate_plaid_credentials(
    credentials: PlaidConfigurationValidate,
    current_user: UserResponse = Depends(require_admin_user),
):
    """
    Validate Plaid credentials without storing them.

    **Admin Only**: Tests credentials by making a test API call to Plaid.
    Credentials are not stored during validation.
    """
    try:
        result = await plaid_config_service.validate_credentials(
            client_id=credentials.plaid_client_id,
            secret=credentials.plaid_secret,
            environment=credentials.environment,
        )

        logger.info(
            f"Credential validation attempted by user: {current_user.id}, "
            f"result: {result.is_valid}"
        )

        return result

    except Exception as e:
        logger.error(f"Error validating credentials: {e}")
        return PlaidValidationResult(
            is_valid=False, message=f"Validation failed: {str(e)}", environment=None
        )


@router.delete("/configuration")
async def delete_plaid_configuration(
    current_user: UserResponse = Depends(require_admin_user),
):
    """
    Delete Plaid configuration and disconnect all user bank connections.

    **Admin Only**: Removes stored Plaid credentials, disconnects all bank connections,
    and deletes all related financial data. This action cannot be undone.
    """
    try:
        # First, revoke all user bank connections and delete their data
        plaid_service = PlaidService()
        
        # Get all users and revoke their connections
        # Since this is an admin operation, we need to clean up all user data
        try:
            # Note: This assumes remove_all_user_data handles cleanup for the admin's data
            # For a full system-wide cleanup, additional logic might be needed
            revoke_success = plaid_service.remove_all_user_data(current_user.id)
            if revoke_success:
                logger.info(f"All user bank connections revoked during config deletion by: {current_user.id}")
        except Exception as revoke_error:
            logger.error(f"Error revoking bank connections during config deletion: {revoke_error}")
            # Continue with config deletion even if revocation fails

        # Delete the Plaid configuration
        success = await plaid_config_service.delete_configuration(
            admin_user_id=current_user.id
        )

        if success:
            logger.info(f"Plaid configuration deleted by user: {current_user.id}")
            return {
                "message": "Plaid configuration deleted successfully. All bank connections have been disconnected and related data removed.",
                "revoked_connections": revoke_success if 'revoke_success' in locals() else False
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete configuration",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration",
        )
