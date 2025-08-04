"""
CORS middleware configuration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import settings


def add_cors_middleware(app: FastAPI) -> None:
    """Add CORS middleware to the application."""
    
    # Development CORS settings
    if settings.environment == "development":
        origins = [
            settings.frontend_url,
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    else:
        # Production CORS settings - be more restrictive
        origins = [settings.frontend_url] + settings.allowed_hosts_list
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
