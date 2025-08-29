"""
Plaid configuration models for on-demand credential management.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class PlaidConfigurationCreate(BaseModel):
    """Request model for creating Plaid configuration."""

    plaid_client_id: str = Field(..., min_length=1, description="Plaid client ID")
    plaid_secret: str = Field(..., min_length=1, description="Plaid secret")
    environment: str = Field(
        ...,
        pattern="^(sandbox|production)$",
        description="Plaid environment (sandbox or production)",
    )


class PlaidConfigurationResponse(BaseModel):
    """Response model for Plaid configuration status."""

    is_configured: bool = Field(..., description="Whether Plaid is configured")
    plaid_client_id: Optional[str] = Field(None, description="Plaid client ID (masked)")
    environment: str = Field(..., description="Plaid environment (sandbox/production)")
    last_updated: Optional[datetime] = Field(
        None, description="Last configuration update"
    )
    updated_by: Optional[str] = Field(None, description="Admin who last updated")


class PlaidConfigurationValidate(BaseModel):
    """Request model for validating Plaid credentials."""

    plaid_client_id: str = Field(..., min_length=1, description="Plaid client ID")
    plaid_secret: str = Field(..., min_length=1, description="Plaid secret")
    environment: str = Field(
        ...,
        pattern="^(sandbox|production)$",
        description="Plaid environment (sandbox or production)",
    )


class PlaidValidationResult(BaseModel):
    """Response model for Plaid credential validation."""

    is_valid: bool = Field(..., description="Whether credentials are valid")
    message: str = Field(..., description="Validation message")
    environment: Optional[str] = Field(None, description="Detected environment")


class PlaidConfigurationStatus(BaseModel):
    """Simple status response for checking configuration."""

    is_configured: bool = Field(..., description="Whether Plaid is configured")
