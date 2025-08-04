"""
Wealth management related Pydantic models.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class AssetType(str, Enum):
    """Asset types enum."""
    STOCK = "stock"
    BOND = "bond"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    CASH = "cash"
    COMMODITY = "commodity"
    OTHER = "other"


class TransactionType(str, Enum):
    """Transaction types enum."""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class AssetBase(BaseModel):
    """Base asset model."""
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    asset_type: AssetType
    description: Optional[str] = Field(None, max_length=500)


class AssetCreate(AssetBase):
    """Asset creation model."""
    pass


class AssetUpdate(BaseModel):
    """Asset update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class AssetResponse(AssetBase):
    """Asset response model."""
    id: str
    current_price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PortfolioBase(BaseModel):
    """Base portfolio model."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = False


class PortfolioCreate(PortfolioBase):
    """Portfolio creation model."""
    pass


class PortfolioUpdate(BaseModel):
    """Portfolio update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: Optional[bool] = None


class PortfolioResponse(PortfolioBase):
    """Portfolio response model."""
    id: str
    user_id: str
    total_value: Decimal = Decimal('0')
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class HoldingBase(BaseModel):
    """Base holding model."""
    asset_id: str
    quantity: Decimal = Field(..., gt=0)
    average_cost: Decimal = Field(..., ge=0)


class HoldingCreate(HoldingBase):
    """Holding creation model."""
    portfolio_id: str


class HoldingUpdate(BaseModel):
    """Holding update model."""
    quantity: Optional[Decimal] = Field(None, gt=0)
    average_cost: Optional[Decimal] = Field(None, ge=0)


class HoldingResponse(HoldingBase):
    """Holding response model."""
    id: str
    portfolio_id: str
    current_value: Decimal
    gain_loss: Decimal
    gain_loss_percentage: Decimal
    created_at: datetime
    updated_at: datetime
    asset: AssetResponse
    
    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    """Base transaction model."""
    asset_id: str
    transaction_type: TransactionType
    quantity: Decimal = Field(..., gt=0)
    price_per_unit: Decimal = Field(..., ge=0)
    total_amount: Decimal = Field(..., ge=0)
    transaction_date: datetime
    notes: Optional[str] = Field(None, max_length=500)


class TransactionCreate(TransactionBase):
    """Transaction creation model."""
    portfolio_id: str


class TransactionUpdate(BaseModel):
    """Transaction update model."""
    quantity: Optional[Decimal] = Field(None, gt=0)
    price_per_unit: Optional[Decimal] = Field(None, ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=500)


class TransactionResponse(TransactionBase):
    """Transaction response model."""
    id: str
    portfolio_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    asset: AssetResponse
    
    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    """Portfolio summary model."""
    portfolio: PortfolioResponse
    holdings: List[HoldingResponse]
    recent_transactions: List[TransactionResponse]
    total_invested: Decimal
    total_current_value: Decimal
    total_gain_loss: Decimal
    total_gain_loss_percentage: Decimal
