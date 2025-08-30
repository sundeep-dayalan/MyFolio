"""
Azure Key Vault cryptographic service for encryption and decryption operations.
Provides reusable utilities for secure data handling using Azure Key Vault.
"""

from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm, SignatureAlgorithm
from azure.identity import DefaultAzureCredential
from typing import Optional
from datetime import datetime, timedelta
import base64
import json
import hashlib

from ..constants.security import Security
from ..exceptions import AzureKeyVaultError
from ..settings import settings
from ..utils.logger import get_logger
from azure.keyvault.secrets import SecretClient

logger = get_logger(__name__)


class AzureKeyVaultService:
    """Service for Azure Key Vault-based encryption and decryption operations."""

    def __init__(self):
        """
        Initialize the Azure Key Vault crypto client.

        """
        self.key_vault_url = settings.key_vault_url
        self.crypto_client = None
        self.secret_manager_client = None

        if self.key_vault_url:
            try:
                credential = DefaultAzureCredential()
                self.crypto_client = CryptographyClient(
                    f"{self.key_vault_url}/keys/{Security.SECRETS_ENCRYPTION_KEY}",
                    credential,
                )
                logger.info(f"Azure Key Vault crypto client initialized successfully.")
                self.secret_manager_client = SecretClient(
                    vault_url=self.key_vault_url, credential=credential
                )
                logger.info(
                    f"Azure Key Vault secret manager client initialized successfully."
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Key Vault client for key {Security.SECRETS_ENCRYPTION_KEY}: {e}. Using development mode."
                )
                raise AzureKeyVaultError(
                    "Failed to initialize Key Vault client for cryptography"
                )

        else:
            logger.warning("Key Vault url is not configured.")
            raise AzureKeyVaultError("Key Vault URL is not configured")

    @staticmethod
    async def encrypt_secret(secret: str) -> str:
        """Encrypt secret using Azure Key Vault."""
        # Use the global instance for static method
        instance = get_azure_key_vault_service()
        if not instance.crypto_client:
            raise AzureKeyVaultError("Key Vault crypto client not available for encryption")

        try:
            # Encrypt using Key Vault cryptographic operation
            result = instance.crypto_client.encrypt(
                EncryptionAlgorithm.rsa_oaep, secret.encode()
            )
            # Return base64 encoded ciphertext
            return base64.b64encode(result.ciphertext).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt secret: {e}")
            raise AzureKeyVaultError(f"Failed to encrypt secret: {e}")

    @staticmethod
    async def decrypt_secret(encrypted_secret: str) -> str:
        """Decrypt secret using Azure Key Vault."""
        # Use the global instance for static method
        instance = get_azure_key_vault_service()
        if not instance.crypto_client:
            raise AzureKeyVaultError("Key Vault crypto client not available for decryption")

        try:
            # Decode base64 and decrypt using Key Vault
            ciphertext = base64.b64decode(encrypted_secret.encode())
            result = instance.crypto_client.decrypt(
                EncryptionAlgorithm.rsa_oaep, ciphertext
            )
            return result.plaintext.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt secret: {e}")
            raise AzureKeyVaultError(f"Failed to decrypt secret: {e}")

    @staticmethod
    async def get_secret(secret_name: str) -> Optional[str]:
        instance = get_azure_key_vault_service()
        if not instance.secret_manager_client:
            raise AzureKeyVaultError("Key Vault secret manager client not available")
            
        try:
            secret = instance.secret_manager_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            raise AzureKeyVaultError(f"Failed to retrieve secret '{secret_name}' from Key Vault: {e}")

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token using Key Vault."""
        instance = get_azure_key_vault_service()
        if not instance.crypto_client:
            raise AzureKeyVaultError(
                "Key Vault crypto client not available for JWT token creation"
            )

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        try:
            return instance._create_token_with_keyvault(to_encode)
        except Exception as e:
            raise AzureKeyVaultError(f"Failed to create JWT token: {e}")

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token using Key Vault only."""
        instance = get_azure_key_vault_service()
        if not instance.crypto_client:
            raise AzureKeyVaultError(
                "Key Vault crypto client not available for token verification"
            )

        try:
            logger.debug(f"Verifying token: {token[:50]}...")
            # Only accept RS256 tokens signed by Key Vault
            parts = token.split(".")
            if len(parts) == 3:
                header_b64 = parts[0]
                header_b64 += "=" * (4 - len(header_b64) % 4)
                header_json = base64.urlsafe_b64decode(header_b64).decode()
                header = json.loads(header_json)

                logger.debug(f"Token header: {header}")

                if header.get("alg") != "RS256":
                    logger.error(
                        f"Invalid token algorithm: {header.get('alg')}. Only RS256 tokens are accepted."
                    )
                    return None

                result = instance._verify_token_with_keyvault(token)
                logger.debug(
                    f"Token verification result: {'SUCCESS' if result else 'FAILED'}"
                )
                return result
            else:
                logger.error(
                    f"Invalid token format: expected 3 parts, got {len(parts)}"
                )
                return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise AzureKeyVaultError(f"JWT token verification failed: {e}")

    def _create_token_with_keyvault(self, payload: dict) -> str:
        """Create JWT token using Key Vault RSA signing."""
        header = {"alg": "RS256", "typ": "JWT"}

        # Convert datetime objects to timestamps for JSON serialization
        serializable_payload = {}
        for key, value in payload.items():
            if isinstance(value, datetime):
                serializable_payload[key] = int(value.timestamp())
            else:
                serializable_payload[key] = value

        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )

        payload_b64 = (
            base64.urlsafe_b64encode(
                json.dumps(serializable_payload, separators=(",", ":")).encode()
            )
            .decode()
            .rstrip("=")
        )

        message = f"{header_b64}.{payload_b64}"

        # Hash the message with SHA256 for RS256 algorithm
        message_hash = hashlib.sha256(message.encode()).digest()

        signature_result = self.crypto_client.sign(
            SignatureAlgorithm.rs256, message_hash
        )

        signature_b64 = (
            base64.urlsafe_b64encode(signature_result.signature).decode().rstrip("=")
        )

        return f"{message}.{signature_b64}"

    def _verify_token_with_keyvault(self, token: str) -> Optional[dict]:
        """Verify JWT token using Key Vault RSA verification."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts
            message = f"{header_b64}.{payload_b64}"

            # Hash the message with SHA256 for RS256 algorithm
            message_hash = hashlib.sha256(message.encode()).digest()

            signature_b64 += "=" * (4 - len(signature_b64) % 4)
            signature = base64.urlsafe_b64decode(signature_b64)

            verification_result = self.crypto_client.verify(
                SignatureAlgorithm.rs256, message_hash, signature
            )

            if verification_result.is_valid:
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload_json = base64.urlsafe_b64decode(payload_b64).decode()
                payload = json.loads(payload_json)

                # Check token expiration
                if payload.get("exp"):
                    current_time = datetime.utcnow().timestamp()
                    token_exp = payload["exp"]
                    logger.debug(
                        f"Token exp: {token_exp}, Current time: {current_time}, Valid: {current_time < token_exp}"
                    )

                    if current_time > token_exp:
                        logger.info("Token has expired")
                        return None

                return payload
            else:
                logger.warning("Token signature verification failed")
                return None

        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            raise AzureKeyVaultError(f"JWT token verification error: {e}")


# Global service instance - lazy initialization
azure_key_vault_crypto_service = None


def get_azure_key_vault_service():
    """Get or create the global Azure Key Vault service instance."""
    global azure_key_vault_crypto_service
    if azure_key_vault_crypto_service is None:
        azure_key_vault_crypto_service = AzureKeyVaultService()
    return azure_key_vault_crypto_service
