from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Literal, Dict, Any

from .plaid import (
    PlaidAccount,
    PlaidAccountWithBalance,
    PlaidInstitution,
    PlaidItem,
    PlaidItemGetResponse,
    PlaidItemStatus,
)

from .sync import SyncInfo, SyncState


class BankSummary(BaseModel):
    """Represents the aggregated summary for a single bank connection."""

    account_count: int = 0


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
    accounts: List[PlaidAccountWithBalance]

    class Config:
        extra = "ignore"
        from_attributes = True


class BankStatus(str, Enum):
    """Plaid token status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class GetAccountsResponse(BaseModel):
    """
    Defines the successful response structure, grouped by institution.
    """

    institutions: List[InstitutionDetail]
    accounts_count: int = Field(description="The grand total number of accounts.")
    banks_count: int = Field(description="The grand total number of banks.")


class PartialItem(BaseModel):
    item_id: str
    institution_id: str
    institution_name: str
    accounts: List[PartialAccountInfo] = []


class PartialAccountInfo(BaseModel):
    account_id: str
    name: Optional[str] = None
    official_name: Optional[str] = None
    type: Optional[str] = None
    subtype: Optional[str] = None
    mask: Optional[str] = None
    logo: Optional[str] = None


class PartialBankInfo(BaseModel):
    item: PartialItem


class PartialBankDocument(BaseModel):
    """Model to safely parse the data fetched by our optimized query."""

    id: str
    bankInfo: PartialBankInfo
    status: str
    accounts: Optional[List[PlaidAccountWithBalance]] = []
    updatedAt: Optional[str] = None
    syncs: SyncState = Field(default_factory=SyncState)


class GetBanksResponse(BaseModel):
    banks: List[PartialBankInfo]
    banks_count: int = Field(description="The grand total number of banks.")


class InstitutionDetail(BaseModel):
    """Represents a single financial institution and its associated accounts."""

    name: str
    logo: Optional[str] = None
    status: str = Field(description="Connection status for this specific institution.")
    account_count: int = Field(description="Number of accounts at this institution.")
    accounts: List[PlaidAccountWithBalance]
    last_account_sync: SyncInfo = Field(default_factory=SyncInfo)
