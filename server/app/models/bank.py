from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Literal, Dict, Any

from .plaid import PlaidInstitution, PlaidItem, PlaidItemGetResponse, PlaidItemStatus

from .sync import SyncInfo, SyncState


class BankSummary(BaseModel):
    """Represents the aggregated summary for a single bank connection."""

    account_count: int = 0
    total_balance: float = 0.0


class BankDocument(BaseModel):

    schemaVersion: str = Field(
        default="1.0", description="Schema version for migrations"
    )
    id: str = Field(..., description="Plaid Item ID as document ID")
    userId: str = Field(..., description="User ID (partition key)")
    bankInfo: PlaidItemGetResponse
    status: BankStatus
    createdAt: str = Field(..., description="ISO 8601 timestamp")
    environment: str = Field(default="sandbox", description="Plaid environment")
    summary: BankSummary = Field(default_factory=BankSummary)
    syncs: SyncState = Field(default_factory=SyncState)
    encryptedAccessToken: str = Field(
        ..., description="The encrypted Plaid access token"
    )

    class Config:
        from_attributes = True


class BankStatus(str, Enum):
    """Plaid token status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"
