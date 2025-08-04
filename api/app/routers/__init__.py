"""
API routers for the application.
"""

from .users import router as users_router
from .auth import router as auth_router
from .wealth import router as wealth_router

__all__ = [
    "users_router",
    "auth_router", 
    "wealth_router",
]
