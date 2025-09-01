from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Represents the standardized status of a synchronization task."""

    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    ERROR = "error"


class SyncInitiatorType(str, Enum):
    """Represents who or what triggered a synchronization task."""

    USER = (
        "user"  # Triggered by a direct user action (e.g., clicking a 'refresh' button)
    )
    SYSTEM = "system"  # Triggered by an automated background job
    WEBHOOK = "webhook"  # Triggered by an incoming Plaid webhook


class SyncInfo(BaseModel):
    """A generic model to track the status and metadata of any sync operation."""

    status: SyncStatus = SyncStatus.PENDING

    # Timestamps for tracking duration
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    initiator_type: Optional[SyncInitiatorType] = None
    initiator_id: Optional[str] = None  # Can be a user_id, system process name, etc.

    # Error details
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = (
        None  # For storing extra context, like a Plaid request_id
    )


class SyncType(str, Enum):
    ACCOUNTS = "accounts"
    TRANSACTIONS = "transactions"


class SyncState(BaseModel):
    """Tracks the state of various data synchronization processes for a bank item."""

    accounts: SyncInfo = Field(default_factory=SyncInfo, alias="last_account_sync")
    transactions: SyncInfo = Field(
        default_factory=SyncInfo, alias="last_transaction_sync"
    )

    class Config:
        populate_by_name = True
