"""
Security utilities for token encryption and data protection.
"""

import base64
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
from azure.identity import DefaultAzureCredential
from typing import Union
import logging

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenEncryption:
    """Token encryption utility for securing sensitive data using Key Vault."""

    def __init__(self):
        self.key_vault_url = settings.key_vault_url
        self.crypto_client = None
        self._initialize_encryption()

    def _initialize_encryption(self):
        """Initialize encryption with Key Vault or fallback."""
        try:
            if self.key_vault_url:
                credential = DefaultAzureCredential()
                self.crypto_client = CryptographyClient(
                    f"{self.key_vault_url}/keys/secrets-encryption-key", credential
                )
                logger.info("Token encryption initialized with Key Vault")
            else:
                logger.warning("Key Vault not configured. Using development mode for token encryption.")
        except Exception as e:
            logger.warning(f"Failed to initialize Key Vault for token encryption: {e}. Using development mode.")
            self.crypto_client = None

    def encrypt_token(self, token: str) -> str:
        """Encrypt a token string using Key Vault or fallback."""
        try:
            if not token:
                return ""

            if self.crypto_client:
                logger.info("Encrypting token using Key Vault RSA encryption")
                result = self.crypto_client.encrypt(
                    EncryptionAlgorithm.rsa_oaep, token.encode()
                )
                encrypted = base64.b64encode(result.ciphertext).decode()
                logger.info(f"Token encrypted successfully, length: {len(encrypted)}")
                return encrypted
            else:
                logger.warning("Using development mode token encryption (NOT SECURE)")
                return base64.b64encode(token.encode()).decode()

        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt an encrypted token string using Key Vault or fallback."""
        try:
            if not encrypted_token:
                return ""

            if self.crypto_client:
                ciphertext = base64.b64decode(encrypted_token.encode())
                result = self.crypto_client.decrypt(
                    EncryptionAlgorithm.rsa_oaep, ciphertext
                )
                return result.plaintext.decode()
            else:
                logger.warning("Using development mode token decryption")
                return base64.b64decode(encrypted_token.encode()).decode()

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
