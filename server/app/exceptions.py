"""
Custom exception classes.
"""

import json
from fastapi import HTTPException
from typing import Any, Dict, Optional

from .models.plaid import PlaidError
from plaid.exceptions import ApiException


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


class PlaidApiException(BaseCustomException):
    """
    Custom exception for Plaid API errors.

    It intelligently parses the error body from Plaid's ApiException.
    It handles two cases:
    1. The body is a clean JSON string.
    2. The body is a descriptive HTTP error message that CONTAINS a JSON string.
    """

    def __init__(self, original_exception: ApiException):
        self.original_exception = original_exception
        raw_body_string = original_exception.body
        json_to_parse = None

        # Define the marker that precedes the actual JSON body in descriptive errors.
        marker = "HTTP response body: "

        if marker in raw_body_string:
            # If the marker is found, split the string and take the JSON part after it.
            try:
                json_to_parse = raw_body_string.split(marker, 1)[1]
            except IndexError:
                # This is a fallback in case the split fails unexpectedly.
                json_to_parse = None
        else:
            # If the marker isn't found, assume the entire body is the JSON (the original behavior).
            json_to_parse = raw_body_string

        try:
            # We must have a string to parse.
            if not json_to_parse:
                raise ValueError(
                    "Could not find a JSON payload in the API exception body."
                )

            # Parse the extracted JSON string into our Pydantic model.
            self.plaid_error: PlaidError = PlaidError.model_validate_json(json_to_parse)

            # Create a detailed and informative error message for the exception detail.
            detail_message = (
                f"Plaid Error: {self.plaid_error.error_code} - "
                f"{self.plaid_error.error_message} "
                f"(Request ID: {self.plaid_error.request_id})"
            )
        except (ValueError, json.JSONDecodeError) as parse_error:
            # Fallback if the extracted string is still not valid JSON.
            self.plaid_error = None
            detail_message = (
                f"Failed to parse Plaid API error. Raw response: {raw_body_string}"
            )

        # Determine a more appropriate status code based on the error type
        status_code = 500  # Default to Internal Server Error
        if self.plaid_error and self.plaid_error.error_type in [
            "INVALID_REQUEST",
            "INVALID_INPUT",
            "ITEM_ERROR",
        ]:
            status_code = 500  # Internal Server Error for client-side errors

        super().__init__(status_code=status_code, detail=detail_message)


class BankNotFoundError(BaseCustomException):
    """Bank not found error."""

    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class AccountNotFoundError(BaseCustomException):
    """Account not found error."""

    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class AccountFetchError(BaseCustomException):
    """Account fetch error."""

    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)


class BankDeleteError(BaseCustomException):
    """Bank deletion error."""

    def __init__(self, detail: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=detail)
