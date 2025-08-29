"""
Azure Key Vault cryptographic service for encryption and decryption operations.
Provides reusable utilities for secure data handling using Azure Key Vault.
"""

from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
from azure.identity import DefaultAzureCredential

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AzureKeyVaultCryptoService:
    """Service for Azure Key Vault-based encryption and decryption operations."""

    def __init__(self, key_name: str = "secrets-encryption-key"):
        """
        Initialize the Azure Key Vault crypto client.

        Args:
            key_name: Name of the key in Key Vault to use for operations.
        """
        self.key_vault_url = settings.key_vault_url
        self.key_name = key_name
        self.crypto_client = None

        if self.key_vault_url:
            try:
                credential = DefaultAzureCredential()
                self.crypto_client = CryptographyClient(
                    f"{self.key_vault_url}/keys/{self.key_name}", credential
                )
                logger.info(
                    f"Azure Key Vault crypto client initialized successfully for key: {self.key_name}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Key Vault client for key {self.key_name}: {e}. Using development mode."
                )
                self.crypto_client = None
        else:
            logger.warning(
                "Key Vault not configured or Azure libraries not available. Using development mode."
            )

    @staticmethod
    async def encrypt_secret(secret: str) -> str:
        """Encrypt secret using Azure Key Vault."""
        # Use the global instance for static method
        instance = azure_key_vault_crypto_service
        if not instance.crypto_client:
            logger.warning(
                "Key Vault not configured, storing secret in plain text (DEV ONLY)"
            )
            return secret

        try:
            if instance.crypto_client:
                # Encrypt using Key Vault cryptographic operation
                result = instance.crypto_client.encrypt(
                    EncryptionAlgorithm.rsa_oaep, secret.encode()
                )
                # Return base64 encoded ciphertext
                import base64

                return base64.b64encode(result.ciphertext).decode()
            else:
                # Development mode: use base64 encoding (NOT SECURE - for dev only)
                import base64

                logger.warning(
                    "Using development mode encryption (base64) - NOT SECURE for production"
                )
                return base64.b64encode(secret.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt secret: {e}")
            raise ValueError("Failed to encrypt secret")

    @staticmethod
    async def decrypt_secret(encrypted_secret: str) -> str:
        """Decrypt secret using Azure Key Vault."""
        # Use the global instance for static method
        instance = azure_key_vault_crypto_service
        if not instance.crypto_client:
            logger.warning("Key Vault not configured, returning plain text (DEV ONLY)")
            return encrypted_secret

        try:
            if instance.crypto_client:
                # Decode base64 and decrypt using Key Vault
                import base64

                ciphertext = base64.b64decode(encrypted_secret.encode())
                result = instance.crypto_client.decrypt(
                    EncryptionAlgorithm.rsa_oaep, ciphertext
                )
                return result.plaintext.decode()
            else:
                # Development mode: decode base64 (NOT SECURE - for dev only)
                import base64

                logger.warning(
                    "Using development mode decryption (base64) - NOT SECURE for production"
                )
                return base64.b64decode(encrypted_secret.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt secret: {e}")
            raise ValueError("Failed to decrypt secret")


# Global service instance
azure_key_vault_crypto_service = AzureKeyVaultCryptoService()
