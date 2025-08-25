"""
Plaid configuration service for managing user-provided credentials.
Implements Azure Key Vault cryptographic operations for secure storage.
"""

from typing import Optional, Tuple
from datetime import datetime, timezone
import logging
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
from azure.identity import DefaultAzureCredential
from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)

from ..config import settings
from ..database import cosmos_client
from ..models.plaid_config import (
    PlaidConfigurationCreate,
    PlaidConfigurationResponse,
    PlaidValidationResult,
    PlaidConfigurationStatus,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PlaidConfigurationService:
    """Service for managing Plaid configuration with Azure Key Vault encryption."""

    def __init__(self):
        self.container_name = "plaid_configuration"
        self.key_vault_url = settings.key_vault_url
        self.crypto_client = None

        # Initialize Key Vault crypto client for encryption/decryption
        if self.key_vault_url:
            try:
                credential = DefaultAzureCredential()
                # Use a dedicated key for Plaid encryption (not the JWT secret)
                self.crypto_client = CryptographyClient(
                    f"{self.key_vault_url}/keys/secrets-encryption-key", credential
                )
                logger.info("Azure Key Vault crypto client initialized successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Key Vault client: {e}. Using development mode."
                )
                self.crypto_client = None
        else:
            logger.warning(
                "Key Vault not configured or Azure libraries not available. Using development mode."
            )

    async def _get_container(self):
        """Get or create Cosmos DB container for Plaid configuration."""
        try:
            # Ensure CosmosDB is connected
            await cosmos_client.ensure_connected()

            database = cosmos_client.database

            # Try to create the container (will succeed if it doesn't exist)
            try:
                container = database.create_container(
                    id=self.container_name,
                    partition_key={"paths": ["/id"], "kind": "Hash"},
                )
                logger.info(f"Created new container: {self.container_name}")
                return container
            except Exception as create_error:
                # Container might already exist, try to get it
                if (
                    "Conflict" in str(create_error)
                    or "already exists" in str(create_error).lower()
                ):
                    container = database.get_container_client(self.container_name)
                    logger.debug(f"Using existing container: {self.container_name}")
                    return container
                else:
                    logger.error(
                        f"Failed to create or get container {self.container_name}: {create_error}"
                    )
                    raise
        except Exception as e:
            logger.error(f"Failed to get/create container {self.container_name}: {e}")
            raise

    def _mask_client_id(self, client_id: str) -> str:
        """Mask client ID for display (show first 4 and last 4 characters)."""
        if len(client_id) <= 8:
            return "*" * len(client_id)
        return client_id[:4] + "*" * (len(client_id) - 8) + client_id[-4:]

    async def _encrypt_secret(self, secret: str) -> str:
        """Encrypt secret using Azure Key Vault."""
        if not self.crypto_client:
            logger.warning(
                "Key Vault not configured, storing secret in plain text (DEV ONLY)"
            )
            return secret

        try:
            if self.crypto_client:
                # Encrypt using Key Vault cryptographic operation
                result = self.crypto_client.encrypt(
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

    async def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt secret using Azure Key Vault."""
        if not self.crypto_client:
            logger.warning("Key Vault not configured, returning plain text (DEV ONLY)")
            return encrypted_secret

        try:
            if self.crypto_client:
                # Decode base64 and decrypt using Key Vault
                import base64

                ciphertext = base64.b64decode(encrypted_secret.encode())
                result = self.crypto_client.decrypt(
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

    async def validate_credentials(
        self, client_id: str, secret: str, environment: str
    ) -> PlaidValidationResult:
        """Validate Plaid credentials by basic format checking and environment setup."""
        try:
            # Basic format validation first
            if not client_id or not secret:
                return PlaidValidationResult(
                    is_valid=False,
                    message="Client ID and secret are required",
                    environment=None,
                )

            if len(client_id) < 20 or len(secret) < 20:
                return PlaidValidationResult(
                    is_valid=False,
                    message="Client ID and secret appear to be too short",
                    environment=None,
                )

            # Require explicit environment value
            from plaid.configuration import Environment

            environment_map = {
                "sandbox": Environment.Sandbox,
                "production": Environment.Production,
            }
            if not environment or environment.lower() not in environment_map:
                return PlaidValidationResult(
                    is_valid=False,
                    message="Environment must be either 'sandbox' or 'production'",
                    environment=None,
                )

            plaid_environment = environment_map[environment.lower()]

            try:
                configuration = Configuration(
                    host=plaid_environment,
                    api_key={"clientId": client_id, "secret": secret},
                )

                # If we can create the configuration successfully, credentials format is valid
                logger.info(
                    f"Plaid configuration created successfully for environment: {environment}"
                )

                return PlaidValidationResult(
                    is_valid=True,
                    message="Credentials format is valid. Actual credentials will be validated with Plaid once stored.",
                    environment=environment,
                )

            except Exception as config_error:
                logger.error(f"Plaid configuration error: {config_error}")
                return PlaidValidationResult(
                    is_valid=False,
                    message=f"Invalid credential format: {str(config_error)}",
                    environment=None,
                )

        except Exception as e:
            logger.error(f"Error validating Plaid credentials: {e}")
            return PlaidValidationResult(
                is_valid=False, message=f"Validation error: {str(e)}", environment=None
            )

    async def store_configuration(
        self, config: PlaidConfigurationCreate, admin_user_id: str
    ) -> PlaidConfigurationResponse:
        """Store Plaid configuration with encrypted secret. Throws error if config already exists."""
        try:
            container = await self._get_container()

            # Check if configuration already exists
            try:
                existing_config = container.read_item("plaid_config", "plaid_config")
                if existing_config:
                    logger.error(
                        "Plaid configuration already exists. Cannot update via POST."
                    )
                    raise ValueError(
                        "Plaid configuration already exists. Delete before creating a new one."
                    )
            except CosmosResourceNotFoundError:
                pass  # Not found, safe to create

            # Encrypt the secret using Key Vault
            encrypted_secret = await self._encrypt_secret(config.plaid_secret)

            # Store configuration
            config_doc = {
                "id": "plaid_config",  # Single configuration document
                "plaid_client_id": config.plaid_client_id,
                "encrypted_plaid_secret": encrypted_secret,
                "is_active": True,
                "environment": config.environment,
                "updated_by": admin_user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Create the configuration (not upsert)
            container.create_item(config_doc)

            logger.info(f"Plaid configuration stored by admin: {admin_user_id}")

            return PlaidConfigurationResponse(
                is_configured=True,
                plaid_client_id=self._mask_client_id(config.plaid_client_id),
                environment=config.environment,
                last_updated=datetime.now(timezone.utc),
                updated_by=admin_user_id,
            )

        except Exception as e:
            logger.error(f"Error storing Plaid configuration: {e}")
            raise ValueError(str(e) or "Failed to store Plaid configuration")

    async def get_configuration_status(self) -> PlaidConfigurationStatus:
        """Get Plaid configuration status."""
        try:
            container = await self._get_container()

            try:
                config_doc = container.read_item("plaid_config", "plaid_config")
                return PlaidConfigurationStatus(
                    is_configured=config_doc.get("is_active", False)
                )
            except CosmosResourceNotFoundError:
                return PlaidConfigurationStatus(is_configured=False)

        except Exception as e:
            logger.error(f"Error getting Plaid configuration status: {e}")
            return PlaidConfigurationStatus(is_configured=False, environment="sandbox")

    async def get_configuration(self) -> Optional[PlaidConfigurationResponse]:
        """Get Plaid configuration details (admin only)."""
        try:
            container = await self._get_container()

            try:
                config_doc = container.read_item("plaid_config", "plaid_config")

                return PlaidConfigurationResponse(
                    is_configured=config_doc.get("is_active", False),
                    plaid_client_id=self._mask_client_id(
                        config_doc.get("plaid_client_id", "")
                    ),
                    environment=config_doc.get("environment", "sandbox"),
                    last_updated=datetime.fromisoformat(config_doc.get("updated_at")),
                    updated_by=config_doc.get("updated_by"),
                )
            except CosmosResourceNotFoundError:
                return None

        except Exception as e:
            logger.error(f"Error getting Plaid configuration: {e}")
            return None

    async def get_decrypted_credentials(self) -> Optional[Tuple[str, str, str]]:
        """Get decrypted credentials for Plaid API calls (internal use only)."""
        try:
            container = await self._get_container()

            try:
                config_doc = container.read_item("plaid_config", "plaid_config")

                if not config_doc.get("is_active", False):
                    return None

                client_id = config_doc.get("plaid_client_id")
                encrypted_secret = config_doc.get("encrypted_plaid_secret")
                environment = config_doc.get("environment", "sandbox")

                if not client_id or not encrypted_secret:
                    return None

                # Decrypt secret using Key Vault
                decrypted_secret = await self._decrypt_secret(encrypted_secret)

                return client_id, decrypted_secret, environment

            except CosmosResourceNotFoundError:
                return None

        except Exception as e:
            logger.error(f"Error getting decrypted credentials: {e}")
            return None

    async def delete_configuration(self, admin_user_id: str) -> bool:
        """Delete Plaid configuration."""
        try:
            container = await self._get_container()

            try:
                container.delete_item("plaid_config", "plaid_config")
                logger.info(f"Plaid configuration deleted by admin: {admin_user_id}")
                return True
            except CosmosResourceNotFoundError:
                return True  # Already deleted

        except Exception as e:
            logger.error(f"Error deleting Plaid configuration: {e}")
            return False


# Global service instance
plaid_config_service = PlaidConfigurationService()
