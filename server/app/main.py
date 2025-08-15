"""
FastAPI application for Personal Wealth Management.
Version: 2.0.0 - Production Ready

A streamlined personal wealth management API focused on:
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
from .database import firebase_client
from .middleware import (
    add_cors_middleware,
    add_exception_handlers,
    add_logging_middleware,
    RateLimitMiddleware,
)
from .routers import plaid_router
from .routers.oauth import router as oauth_router
from .routers.firestore import router as firestore_router
from .utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Personal Wealth Management API...")

    # Skip Firebase connection in test environment
    if settings.environment != "test":
        try:
            await firebase_client.connect()
            logger.info("Application startup complete")

        except Exception as e:
            logger.warning(f"Firebase connection failed: {e}")
            logger.info(
                "Starting application in offline mode - some features may not work"
            )
    else:
        logger.info("Skipping Firebase connection in test environment")

    yield

    # Shutdown
    logger.info("Shutting down Personal Wealth Management API...")

    if settings.environment != "test":
        try:
            await firebase_client.disconnect()

        except Exception as e:
            logger.warning(f"Error during Firebase disconnection: {e}")
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description="A comprehensive personal wealth management API with portfolio tracking, transaction management, and financial analytics.",
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
    # Firestore direct access endpoints
    app.include_router(firestore_router, prefix=settings.api_v1_prefix)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for Cloud Run."""
        try:
            # Test Firebase connection
            firebase_status = (
                "connected" if firebase_client.is_connected else "disconnected"
            )

            return {
                "status": "healthy",
                "service": settings.project_name,
                "version": settings.version,
                "environment": settings.environment,
                "firebase": firebase_status,
                "firebase_connected": firebase_client.is_connected,
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
