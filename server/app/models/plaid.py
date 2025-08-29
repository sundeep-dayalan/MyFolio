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
    item_id: Optional[str] = None  # Bank identifier
    institution_name: Optional[str] = None
    institution_id: Optional[str] = None
    logo: Optional[str] = None  # Institution logo URL

    class Config:
        from_attributes = True


class BankDocument(BaseModel):

    # Core identifiers
    id: str = Field(..., description="Plaid Item ID as document ID")
    userId: str = Field(..., description="User ID (partition key)")
    schemaVersion: str = Field(
        default="2.0", description="Schema version for migrations"
    )

    # Institution information
    institutionId: str = Field(..., description="Plaid institution ID")
    institutionName: str = Field(..., description="Institution name")

    # Item status & timestamps
    status: str = Field(
        default="active", description="Item status: active, error, disconnected"
    )
    createdAt: str = Field(..., description="ISO 8601 timestamp")
    updatedAt: str = Field(..., description="ISO 8601 timestamp")
    lastUsedAt: Optional[str] = Field(None, description="ISO 8601 timestamp")

    # Environment
    environment: str = Field(default="sandbox", description="Plaid environment")

    # Summarized & computed data
    summary: Dict[str, Any] = Field(
        default_factory=lambda: {
            "accountCount": 0,
            "totalBalance": 0.0,
            "lastSync": {"status": "pending", "timestamp": None, "error": None},
        },
        description="Computed summary data",
    )

    # Raw Plaid API data
    plaidData: Dict[str, Any] = Field(
        default_factory=dict, description="Raw Plaid API response data"
    )

    # Optional error tracking
    lastError: Optional[Dict[str, Any]] = Field(
        None, description="Last error information if any"
    )

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
