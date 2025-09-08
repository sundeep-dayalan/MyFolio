"""
Error handling middleware.
"""

import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..exceptions import BaseCustomException, PlaidApiException
from ..utils.logger import get_logger
from ..settings import settings

logger = get_logger(__name__)


async def plaid_api_exception_handler(
    request: Request, exc: PlaidApiException
) -> JSONResponse:
    """Handle Plaid API specific exceptions."""
    # This handler will now be used exclusively for PlaidApiException.
    # We can access the structured `plaid_error` object for more detailed logging.
    if exc.plaid_error:
        log_message = (
            f"Plaid API error at {request.url}: "
            f"Code='{exc.plaid_error.error_code}', "
            f"RequestID='{exc.plaid_error.request_id}'"
        )
    else:
        log_message = f"Plaid API error at {request.url}: {exc.detail}"

    logger.warning(log_message)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "plaid_api_error",  # A specific type for the frontend
            }
        },
    )


async def custom_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP {exc.status_code} error at {request.url}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error",
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    logger.warning(f"Validation error at {request.url}: {exc.errors()}")

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "type": "validation_error",
                "details": exc.errors(),
            }
        },
    )


async def custom_exception_handler(
    request: Request, exc: BaseCustomException
) -> JSONResponse:
    """Handle custom exceptions."""
    logger.warning(f"Custom error at {request.url}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "application_error",
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unhandled error at {request.url}: {str(exc)}")

    if settings.debug:
        logger.error(f"Traceback: {traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error",
                **({"details": str(exc)} if settings.debug else {}),
            }
        },
    )


def add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to the application."""
    app.add_exception_handler(PlaidApiException, plaid_api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BaseCustomException, custom_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
