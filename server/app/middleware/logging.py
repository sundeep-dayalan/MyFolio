"""
Logging middleware.
"""
import time
import uuid
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            f"Request started - ID: {request_id} | "
            f"Method: {request.method} | "
            f"URL: {request.url} | "
            f"Client IP: {client_ip}"
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed - ID: {request_id} | "
                f"Error: {str(e)} | "
                f"Duration: {process_time:.4f}s"
            )
            raise

        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Request completed - ID: {request_id} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time:.4f}s"
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def add_logging_middleware(app: FastAPI) -> None:
    """Add logging middleware to the application."""
    app.add_middleware(LoggingMiddleware)
