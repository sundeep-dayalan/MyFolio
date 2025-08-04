"""
Pydantic models for the application.
"""

from .user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserInDB,
    TokenData,
    Token,
    GoogleTokenData,
    GoogleUserInfo,
)

from .wealth import (
    AssetType,
    TransactionType,
    AssetBase,
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    PortfolioBase,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    HoldingBase,
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    TransactionBase,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    PortfolioSummary,
)

__all__ = [
    # User models
    "UserBase",
    "UserCreate", 
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    "TokenData",
    "Token",
    "GoogleTokenData",
    "GoogleUserInfo",
    # Wealth models
    "AssetType",
    "TransactionType",
    "AssetBase",
    "AssetCreate",
    "AssetUpdate", 
    "AssetResponse",
    "PortfolioBase",
    "PortfolioCreate",
    "PortfolioUpdate",
    "PortfolioResponse",
    "HoldingBase",
    "HoldingCreate",
    "HoldingUpdate",
    "HoldingResponse",
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "PortfolioSummary",
]
