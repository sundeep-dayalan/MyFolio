"""
FastAPI application for Sage.
Version: 2.0.3 - Production Ready with Microsoft Entra ID Only

A streamlined financial management API focused on:
- Microsoft Entra ID OAuth 2.0 authentication
- Plaid financial data integration
- Real-time account balances and transactions
- Secure token management

Clean Microsoft Entra ID implementation supporting both personal and organizational Microsoft accounts.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .constants import Security

from .exceptions import AzureKeyVaultError

from .services.az_key_vault_service import AzureKeyVaultService

from .settings import settings
from .database import cosmos_client
from .middleware import (
    add_cors_middleware,
    add_exception_handlers,
    add_logging_middleware,
    RateLimitMiddleware,
)
from .routers import plaid_router
from .routers.auth import router as microsoft_oauth_router
from .utils.logger import setup_logging, get_logger
from .routers.config import router as plaid_config_router
import os

# Setup logging
setup_logging()
logger = get_logger(__name__)


def get_session_secret() -> str:
    """
    Get session secret for middleware initialization.
    """
    try:
        # Try environment variable first (for Azure Functions configuration)
        session_secret = os.getenv("SESSION_SECRET_KEY")
        if session_secret:
            logger.info("Using session secret from environment variable")
            return session_secret

        # If no environment variable, must use Key Vault
        kv_service = AzureKeyVaultService()
        if kv_service.secret_manager_client:
            secret = kv_service.secret_manager_client.get_secret(
                Security.SESSION_SECRET_KEY
            )
            logger.info("Session secret retrieved from Azure Key Vault")
            return secret.value
        else:
            logger.error(
                "Key Vault client not initialized and no SESSION_SECRET_KEY environment variable"
            )
            raise AzureKeyVaultError("Key Vault client not initialized")

    except Exception as e:
        logger.error(f"Failed to retrieve session secret: {e}")
        raise AzureKeyVaultError(
            "Failed to retrieve session secret - no fallbacks allowed for security"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Sage API...")

    # Skip CosmosDB connection in test environment
    if settings.environment != "test":
        try:
            await cosmos_client.connect()
            logger.info("CosmosDB connected successfully at startup")
            logger.info("Application startup complete")
        except Exception as e:
            logger.error(f"Failed to connect to CosmosDB at startup: {e}")
            raise e  # Fail fast - prevent app from starting if DB unavailable
    else:
        logger.info("Skipping CosmosDB connection in test environment")

    yield

    # Shutdown
    logger.info("Shutting down Sage API...")

    if settings.environment != "test":
        try:
            await cosmos_client.disconnect()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.warning(f"Error during CosmosDB disconnection: {e}")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    # For Azure Functions, disable lifespan to avoid startup issues
    app_kwargs = {
        "title": settings.project_name,
        "version": settings.version,
        "description": "....",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "lifespan": None,  # For Azure Functions
    }
    app = FastAPI(**app_kwargs)

    # Add middleware
    add_cors_middleware(app)
    add_logging_middleware(app)
    add_exception_handlers(app)

    # Add rate limiting middleware
    rate_limiter = RateLimitMiddleware()
    app.middleware("http")(rate_limiter)

    # Add session middleware for OAuth state management
    session_secret = get_session_secret()
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        max_age=3600,  # 1 hour session timeout
        same_site="lax",
        https_only=not settings.debug,  # Use secure cookies in production
    )

    # Add routers
    app.include_router(
        microsoft_oauth_router, prefix=settings.api_v1_prefix
    )  # Microsoft OAuth
    # Plaid integration endpoints
    app.include_router(plaid_router, prefix=settings.api_v1_prefix)
    # Plaid configuration endpoints
    app.include_router(plaid_config_router, prefix=settings.api_v1_prefix)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Cloud Run."""
        try:
            # Test CosmosDB connection
            cosmos_status = (
                "connected" if cosmos_client.is_connected else "disconnected"
            )

            return {
                "status": "healthy",
                "service": settings.project_name,
                "version": settings.version,
                "environment": settings.environment,
                "cosmos_db": cosmos_status,
                "cosmos_connected": cosmos_client.is_connected,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.project_name}!",
            "version": settings.version,
            "docs_url": "/docs",
        }

    return app


# Create the app instance (with lifespan for local development)
app = create_app()

# --- Azure Functions support ---
try:
    import azure.functions as func

    async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
        """
        Azure Functions entry point for HTTP requests.
        Wraps the FastAPI app with ASGI middleware.
        """
        try:
            # Ensure CosmosDB connection is established for Azure Functions
            logger.info(f"Azure Function called - Environment: {settings.environment}")
            logger.info(f"Request path: {req.url}")
            logger.info(f"CosmosDB is_connected: {cosmos_client.is_connected}")

            if not cosmos_client.is_connected:
                try:
                    logger.info(
                        "Attempting to establish CosmosDB connection in Azure Function"
                    )
                    await cosmos_client.connect()
                    logger.info("CosmosDB connection established in Azure Function")
                except Exception as e:
                    logger.error(f"CosmosDB connection failed in Azure Function: {e}")
                    logger.error(
                        f"CosmosDB settings - Endpoint: {settings.cosmos_db_endpoint}"
                    )
                    logger.error(
                        f"CosmosDB settings - DB Name: {settings.cosmos_db_name}"
                    )
                    # Continue even if DB connection fails - some endpoints might still work
            else:
                if cosmos_client.is_connected:
                    logger.info("CosmosDB already connected")
                elif settings.environment == "test":
                    logger.info("Skipping CosmosDB connection in test environment")

            # Import azure_app from __init__.py to use the Azure Function specific app
            from . import azure_app

            return await func.AsgiMiddleware(azure_app).handle_async(req, context)

        except Exception as e:
            logger.error(f"Critical error in Azure Function main handler: {e}")
            # Return a proper HTTP error response instead of letting the function fail
            return func.HttpResponse(
                body=f"Internal server error: {str(e)}",
                status_code=500,
                headers={"Content-Type": "text/plain"},
            )

except ImportError:
    # Not running in Azure Functions, ignore
    pass
