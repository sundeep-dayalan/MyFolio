"""
Application configuration settings.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from .cloud_config import get_secret_manager


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    project_name: str = Field(default="Sage API", env="PROJECT_NAME")
    version: str = Field(default="2.0.2", env="VERSION")
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    debug: bool = Field(default=False, env="DEBUG")

    # Security
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # CORS
    frontend_url: str = Field(default="http://localhost:5173", env="FRONTEND_URL")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", env="ALLOWED_HOSTS")
    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000", env="ALLOWED_ORIGINS"
    )

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Get allowed hosts as a list."""
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        """Get allowed origins as a list."""
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    # Azure Key Vault Configuration
    key_vault_url: Optional[str] = Field(default=None, env="KEY_VAULT_URL")

    # CosmosDB Configuration
    cosmos_db_endpoint: str = Field(..., env="COSMOS_DB_ENDPOINT")
    cosmos_db_key: str = Field(..., env="COSMOS_DB_KEY")
    cosmos_db_name: str = Field(default="sage-db", env="COSMOS_DB_NAME")

    # Microsoft Entra ID OAuth Configuration
    azure_client_id: str = Field(default="test-client-id", env="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(
        default="test-client-secret", env="AZURE_CLIENT_SECRET"
    )
    azure_tenant_id: str = Field(default="common", env="AZURE_TENANT_ID")
    azure_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/oauth/microsoft/callback",
        env="AZURE_REDIRECT_URI",
    )

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
