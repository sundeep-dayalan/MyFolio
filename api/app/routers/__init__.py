"""
API routers for the application.
"""

from .plaid import router as plaid_router

__all__ = [
    "plaid_router",
]
