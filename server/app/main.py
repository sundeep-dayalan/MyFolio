"""
FastAPI application for Sage.
Version: 2.0.0 - Production Ready

A streamlined financial management API focused on:
- Google OAuth 2.0 authentication
- Plaid financial data integration
- Real-time account balances and transactions
- Secure token management

Removed unused endpoints:
- JWT-based authentication (replaced with OAuth)
- User management APIs
- Wealth/portfolio management APIs
- Unused Plaid utility endpoints
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import cosmos_client
from .middleware import (
    add_cors_middleware,
    add_exception_handlers,
    add_logging_middleware,
    RateLimitMiddleware,
)
from .routers import plaid_router
from .routers.oauth import router as oauth_router
from .routers.firestore import router as cosmosdb_router, firestore_router
from .utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Sage API...")

    # Skip CosmosDB connection in test environment
    if settings.environment != "test":
        try:
            await cosmos_client.connect()
            logger.info("Application startup complete")

        except Exception as e:
            logger.warning(f"CosmosDB connection failed: {e}")
            logger.info(
                "Starting application in offline mode - some features may not work"
            )
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

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description="A comprehensive financial management API with portfolio tracking, transaction management, and financial analytics.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add middleware
    add_cors_middleware(app)
    add_logging_middleware(app)
    add_exception_handlers(app)

    # Add rate limiting middleware
    rate_limiter = RateLimitMiddleware()
    app.middleware("http")(rate_limiter)

    # Add session middleware for OAuth state management
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=3600,  # 1 hour session timeout
        same_site="lax",
        https_only=not settings.debug,  # Use secure cookies in production
    )

    # Add routers
    app.include_router(oauth_router, prefix=settings.api_v1_prefix)
    # Plaid integration endpoints
    app.include_router(plaid_router, prefix=settings.api_v1_prefix)
    # CosmosDB direct access endpoints
    app.include_router(cosmosdb_router, prefix=settings.api_v1_prefix)
    # Firestore compatibility endpoints (redirect to CosmosDB)
    app.include_router(firestore_router, prefix=settings.api_v1_prefix)

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


# Create the app instance
app = create_app()

# --- Azure Functions support ---
try:
    import azure.functions as func

    async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
        """
        Azure Functions entry point for HTTP requests.
        Wraps the FastAPI app with ASGI middleware.
        """
        # Ensure CosmosDB connection is established for Azure Functions
        logger.info(f"Azure Function called - Environment: {settings.environment}")
        logger.info(f"CosmosDB is_connected: {cosmos_client.is_connected}")
        
        if not cosmos_client.is_connected and settings.environment != "test":
            try:
                logger.info("Attempting to establish CosmosDB connection in Azure Function")
                await cosmos_client.connect()
                logger.info("CosmosDB connection established in Azure Function")
            except Exception as e:
                logger.error(f"CosmosDB connection failed in Azure Function: {e}")
                logger.error(f"CosmosDB settings - Endpoint: {settings.cosmos_db_endpoint}")
                logger.error(f"CosmosDB settings - DB Name: {settings.cosmos_db_name}")
        else:
            if cosmos_client.is_connected:
                logger.info("CosmosDB already connected")
            elif settings.environment == "test":
                logger.info("Skipping CosmosDB connection in test environment")
        
        return await func.AsgiMiddleware(app).handle_async(req, context)

except ImportError:
    # Not running in Azure Functions, ignore
    pass
