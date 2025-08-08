"""
Security utilities for token encryption and data protection.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Union
import logging

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenEncryption:
    """Token encryption utility for securing sensitive data."""

    def __init__(self):
        self._key = None
        self._fernet = None
        self._initialize_encryption()

    def _initialize_encryption(self):
        """Initialize encryption with app secret key."""
        try:
            # Use app secret key as the base for encryption
            secret_key = settings.SECRET_KEY.encode()

            # Generate a salt (in production, this could be stored separately)
            salt = b"plaid_token_salt"

            # Derive a key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key))
            self._key = key
            self._fernet = Fernet(key)

        except Exception as e:
            logger.error(f"Failed to initialize token encryption: {e}")
            raise

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token string.

        Args:
            token: The token string to encrypt

        Returns:
            Encrypted token as base64 string
        """
        try:
            if not token:
                return ""

            encrypted_bytes = self._fernet.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()

        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt an encrypted token string.

        Args:
            encrypted_token: The encrypted token as base64 string

        Returns:
            Decrypted token string
        """
        try:
            if not encrypted_token:
                return ""

            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()

        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise


# Global encryption instance
_token_encryption = None


def get_token_encryption() -> TokenEncryption:
    """Get the global token encryption instance."""
    global _token_encryption
    if _token_encryption is None:
        _token_encryption = TokenEncryption()
    return _token_encryption


def encrypt_access_token(token: str) -> str:
    """Encrypt a Plaid access token."""
    encryption = get_token_encryption()
    return encryption.encrypt_token(token)


def decrypt_access_token(encrypted_token: str) -> str:
    """Decrypt a Plaid access token."""
    encryption = get_token_encryption()
    return encryption.decrypt_token(encrypted_token)


def mask_token_for_logging(token: str) -> str:
    """
    Mask a token for safe logging.

    Args:
        token: The token to mask

    Returns:
        Masked token showing only first 8 and last 4 characters
    """
    if not token or len(token) < 12:
        return "***"

    return f"{token[:8]}***{token[-4:]}"
