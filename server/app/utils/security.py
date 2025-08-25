"""
Security utilities.
"""

from datetime import timedelta
from typing import Optional
from passlib.context import CryptContext


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    from ..services.jwt_key_service import jwt_key_service
    return jwt_key_service.create_access_token(data, expires_delta)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    from ..services.jwt_key_service import jwt_key_service
    return jwt_key_service.verify_token(token)


def sanitize_input(input_string: str) -> str:
    """Basic input sanitization."""
    if not isinstance(input_string, str):
        return ""

    # Remove potential dangerous characters
    dangerous_chars = ["<", ">", "&", '"', "'", "/", "\\"]
    sanitized = input_string
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    return sanitized.strip()
