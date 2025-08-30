"""
Custom exception classes.
"""

from fastapi import HTTPException
from typing import Any, Dict, Optional


class BaseCustomException(HTTPException):
    """Base custom exception."""

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code, detail, headers)


class DatabaseConnectionError(BaseCustomException):
    """Database connection error."""

    def __init__(self, detail: str = "Database connection failed"):
        super().__init__(status_code=500, detail=detail)


class UserNotFoundError(BaseCustomException):
    """User not found error."""

    def __init__(self, user_id: str):
        super().__init__(status_code=404, detail=f"User '{user_id}' not found")


class UserAlreadyExistsError(BaseCustomException):
    """User already exists error."""

    def __init__(self, identifier: str):
        super().__init__(
            status_code=409,
            detail=f"User with identifier '{identifier}' already exists",
        )


class ValidationError(BaseCustomException):
    """Validation error."""

    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)


class AuthenticationError(BaseCustomException):
    """Authentication error."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class DatabaseError(BaseCustomException):
    """Database-specific error."""

    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)


class AzureKeyVaultError(BaseCustomException):
    """Azure Key Vault error."""

    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)
