"""
User-related Pydantic models.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator


class UserBase(BaseModel):
    """Base user model."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    given_name: Optional[str] = Field(None, max_length=50)
    family_name: Optional[str] = Field(None, max_length=50)
    picture: Optional[str] = None


class UserCreate(UserBase):
    """User creation model."""

    id: str = Field(..., min_length=1, max_length=100)

    @validator("id")
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v.strip()


class UserUpdate(BaseModel):
    """User update model."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    given_name: Optional[str] = Field(None, max_length=50)
    family_name: Optional[str] = Field(None, max_length=50)
    picture: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    """User response model."""

    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Auth-related models
class TokenData(BaseModel):
    """Token data model."""

    user_id: Optional[str] = None


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MicrosoftUserInfo(BaseModel):
    """Microsoft Entra ID user information from JWT."""

    oid: Optional[str] = None  # Object ID (unique user identifier)
    sub: str  # Subject (unique user identifier, alternative to oid)
    tid: Optional[str] = None  # Tenant ID
    email: EmailStr
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    exp: Optional[int] = None  # Expiration time
    iat: Optional[int] = None  # Issued at time
