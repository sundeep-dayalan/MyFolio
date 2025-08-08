"""
Plaid-related Pydantic models for data validation and serialization.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PlaidEnvironment(str, Enum):
    """Plaid environment enumeration."""

    SANDBOX = "sandbox"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class PlaidTokenStatus(str, Enum):
    """Plaid token status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class PlaidAccessToken(BaseModel):
    """Plaid access token model for database storage."""

    user_id: str = Field(..., description="User ID from authentication")
    access_token: str = Field(..., description="Encrypted Plaid access token")
    item_id: str = Field(..., description="Plaid item ID")
    institution_id: Optional[str] = Field(None, description="Institution ID")
    institution_name: Optional[str] = Field(None, description="Institution name")
    status: PlaidTokenStatus = Field(default=PlaidTokenStatus.ACTIVE)
    environment: PlaidEnvironment = Field(default=PlaidEnvironment.SANDBOX)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class PlaidAccount(BaseModel):
    """Plaid account model."""

    account_id: str
    name: str
    official_name: Optional[str] = None
    type: str
    subtype: Optional[str] = None
    mask: Optional[str] = None

    class Config:
        from_attributes = True


class PlaidBalance(BaseModel):
    """Plaid balance model."""

    available: Optional[float] = None
    current: Optional[float] = None
    iso_currency_code: Optional[str] = None
    unofficial_currency_code: Optional[str] = None

    class Config:
        from_attributes = True


class PlaidAccountWithBalance(BaseModel):
    """Plaid account with balance information."""

    account_id: str
    name: str
    official_name: Optional[str] = None
    type: str
    subtype: Optional[str] = None
    mask: Optional[str] = None
    balances: PlaidBalance

    class Config:
        from_attributes = True


class LinkTokenRequest(BaseModel):
    """Link token creation request."""

    user_id: Optional[str] = Field(None, description="Will be set from authentication")

    class Config:
        from_attributes = True


class PublicTokenExchangeRequest(BaseModel):
    """Public token exchange request."""

    public_token: str = Field(..., description="Plaid public token from Link")

    class Config:
        from_attributes = True


class PlaidWebhookRequest(BaseModel):
    """Plaid webhook request model."""

    webhook_type: str
    webhook_code: str
    item_id: str
    error: Optional[Dict[str, Any]] = None
    new_transactions: Optional[int] = None
    removed_transactions: Optional[List[str]] = None

    class Config:
        from_attributes = True
