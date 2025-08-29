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
from ..constants import (
    Containers,
    PartitionKeys,
    DocumentFields,
    PlaidEnvironments,
    PlaidConfigFields,
    ConfigMessages,
    ErrorMessages,
    Security,
)

from ..services.azure_key_vault_crypto_service import AzureKeyVaultCryptoService

logger = get_logger(__name__)


class PlaidConfigurationService:
    """Service for managing Plaid configuration with Azure Key Vault encryption."""

    def __init__(self):
        self.container_name = Containers.CONFIGURATION

    #     self.key_vault_url = settings.key_vault_url
    #     self.crypto_client = None

    #     # Initialize Key Vault crypto client for encryption/decryption
    #     if self.key_vault_url:
    #         try:
    #             credential = DefaultAzureCredential()
    #             # Use a dedicated key for Plaid encryption (not the JWT secret)
    #             self.crypto_client = CryptographyClient(
    #                 f"{self.key_vault_url}/keys/secrets-encryption-key", credential
    #             )
    #             logger.info("Azure Key Vault crypto client initialized successfully")
    #         except Exception as e:
    #             logger.warning(
    #                 f"Failed to initialize Key Vault client: {e}. Using development mode."
    #             )
    #             self.crypto_client = None
    #     else:
    #         logger.warning(
    #             "Key Vault not configured or Azure libraries not available. Using development mode."
    #         )

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
                    partition_key={
                        "paths": [PartitionKeys.USER_ID_PATH],
                        "kind": PartitionKeys.HASH_KIND,
                    },
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

    # async def _encrypt_secret(self, secret: str) -> str:
    #     """Encrypt secret using Azure Key Vault."""
    #     if not self.crypto_client:
    #         logger.warning(
    #             "Key Vault not configured, storing secret in plain text (DEV ONLY)"
    #         )
    #         return secret

    #     try:
    #         if self.crypto_client:
    #             # Encrypt using Key Vault cryptographic operation
    #             result = self.crypto_client.encrypt(
    #                 EncryptionAlgorithm.rsa_oaep, secret.encode()
    #             )
    #             # Return base64 encoded ciphertext
    #             import base64

    #             return base64.b64encode(result.ciphertext).decode()
    #         else:
    #             # Development mode: use base64 encoding (NOT SECURE - for dev only)
    #             import base64

    #             logger.warning(
    #                 "Using development mode encryption (base64) - NOT SECURE for production"
    #             )
    #             return base64.b64encode(secret.encode()).decode()
    #     except Exception as e:
    #         logger.error(f"Failed to encrypt secret: {e}")
    #         raise ValueError("Failed to encrypt secret")

    # async def _decrypt_secret(self, encrypted_secret: str) -> str:
    #     """Decrypt secret using Azure Key Vault."""
    #     if not self.crypto_client:
    #         logger.warning("Key Vault not configured, returning plain text (DEV ONLY)")
    #         return encrypted_secret

    #     try:
    #         if self.crypto_client:
    #             # Decode base64 and decrypt using Key Vault
    #             import base64

    #             ciphertext = base64.b64decode(encrypted_secret.encode())
    #             result = self.crypto_client.decrypt(
    #                 EncryptionAlgorithm.rsa_oaep, ciphertext
    #             )
    #             return result.plaintext.decode()
    #         else:
    #             # Development mode: decode base64 (NOT SECURE - for dev only)
    #             import base64

    #             logger.warning(
    #                 "Using development mode decryption (base64) - NOT SECURE for production"
    #             )
    #             return base64.b64decode(encrypted_secret.encode()).decode()
    #     except Exception as e:
    #         logger.error(f"Failed to decrypt secret: {e}")
    #         raise ValueError("Failed to decrypt secret")

    async def validate_credentials(
        self, client_id: str, secret: str, environment: str
    ) -> PlaidValidationResult:
        """Validate Plaid credentials by creating a link token."""
        try:
            # Basic format validation first
            if not client_id or not secret:
                return PlaidValidationResult(
                    is_valid=False,
                    message=ConfigMessages.CREDENTIALS_REQUIRED,
                    environment=None,
                )

            if len(client_id) < 20 or len(secret) < 20:
                return PlaidValidationResult(
                    is_valid=False,
                    message=ConfigMessages.CREDENTIALS_TOO_SHORT,
                    environment=None,
                )

            # Require explicit environment value
            from plaid.configuration import Environment

            environment_map = {
                PlaidEnvironments.SANDBOX: Environment.Sandbox,
                PlaidEnvironments.PRODUCTION: Environment.Production,
            }
            if not environment or environment.lower() not in environment_map:
                return PlaidValidationResult(
                    is_valid=False,
                    message=ConfigMessages.ENVIRONMENT_REQUIRED,
                    environment=None,
                )

            plaid_environment = environment_map[environment.lower()]

            try:
                # Create Plaid configuration and API client
                configuration = Configuration(
                    host=plaid_environment,
                    api_key={"clientId": client_id, "secret": secret},
                )

                # Test credentials by creating a link token
                with ApiClient(configuration) as api_client:
                    api = plaid_api.PlaidApi(api_client)

                    # Import required models for link token creation
                    from plaid.model.link_token_create_request import (
                        LinkTokenCreateRequest,
                    )
                    from plaid.model.link_token_create_request_user import (
                        LinkTokenCreateRequestUser,
                    )
                    from plaid.model.country_code import CountryCode
                    from plaid.model.products import Products

                    # Create a test link token request
                    request = LinkTokenCreateRequest(
                        products=[Products("transactions")],
                        client_name="Sage - Credential Validation",
                        country_codes=[CountryCode("US")],
                        language="en",
                        user=LinkTokenCreateRequestUser(
                            client_user_id="validation_test_user"
                        ),
                    )

                    # Make the API call to create link token
                    response = api.link_token_create(request)

                    # If we get here without exception, credentials are valid
                    logger.info(
                        f"Plaid credentials validated successfully for environment: {environment}"
                    )

                    return PlaidValidationResult(
                        is_valid=True,
                        message="Credentials validated successfully with Plaid API",
                        environment=environment,
                    )

            except Exception as api_error:
                logger.error(f"Plaid API validation error: {api_error}")
                error_message = str(api_error)

                # Parse common Plaid errors to provide better user feedback
                if (
                    "INVALID_CLIENT_ID" in error_message
                    or "INVALID_API_KEYS" in error_message
                ):
                    friendly_message = (
                        "Invalid Plaid Client ID. Please check your credentials."
                    )
                elif (
                    "INVALID_SECRET" in error_message
                    or "invalid client_id or secret provided" in error_message
                ):
                    friendly_message = (
                        "Invalid Plaid Secret. Please check your credentials."
                    )
                elif "UNAUTHORIZED" in error_message or "401" in error_message:
                    friendly_message = "Invalid credentials. Please verify your Plaid Client ID and Secret."
                elif "400" in error_message and (
                    "INVALID_API_KEYS" in error_message
                    or "INVALID_INPUT" in error_message
                ):
                    friendly_message = "Invalid Plaid credentials. Please verify your Client ID and Secret are correct."
                elif "API_ERROR" in error_message:
                    friendly_message = "Unable to validate credentials with Plaid API. Please try again."
                elif "Bad Request" in error_message:
                    friendly_message = "Invalid Plaid credentials. Please check your Client ID and Secret."
                else:
                    friendly_message = "Credential validation failed. Please verify your Plaid credentials."

                return PlaidValidationResult(
                    is_valid=False,
                    message=friendly_message,
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

            # Check if configuration already exists for this user
            try:
                existing_config = container.read_item(admin_user_id, admin_user_id)
                if existing_config and existing_config.get(DocumentFields.PLAID):
                    logger.error(
                        f"Plaid configuration already exists for user {admin_user_id}. Cannot update via POST."
                    )
                    raise ValueError(ConfigMessages.CONFIG_ALREADY_EXISTS)
            except CosmosResourceNotFoundError:
                pass  # Not found, safe to create

            # Encrypt the secret using Key Vault
            encrypted_secret = await AzureKeyVaultCryptoService.encrypt_secret(
                config.plaid_secret
            )

            # Store configuration partitioned by userId
            config_doc = {
                DocumentFields.ID: admin_user_id,  # User ID as document ID
                DocumentFields.USER_ID: admin_user_id,  # Partition key
                DocumentFields.PLAID: {
                    PlaidConfigFields.PLAID_CLIENT_ID: config.plaid_client_id,
                    PlaidConfigFields.ENCRYPTED_PLAID_SECRET: encrypted_secret,
                    "is_active": True,
                    PlaidConfigFields.ENVIRONMENT: config.environment,
                    "updated_by": admin_user_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            }

            # Create or update the configuration
            container.upsert_item(config_doc)

            logger.info(f"Plaid configuration stored for user: {admin_user_id}")

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

    async def get_configuration_status(self, user_id: str) -> PlaidConfigurationStatus:
        """Get Plaid configuration status for a specific user."""
        try:
            container = await self._get_container()

            try:
                config_doc = container.read_item(user_id, user_id)
                plaid_config = config_doc.get(DocumentFields.PLAID, {})
                return PlaidConfigurationStatus(
                    is_configured=plaid_config.get("is_active", False),
                    environment=plaid_config.get(
                        PlaidConfigFields.ENVIRONMENT, PlaidEnvironments.SANDBOX
                    ),
                )
            except CosmosResourceNotFoundError:
                return PlaidConfigurationStatus(is_configured=False)

        except Exception as e:
            logger.error(f"Error getting Plaid configuration status: {e}")
            return PlaidConfigurationStatus(
                is_configured=False, environment=PlaidEnvironments.SANDBOX
            )

    async def get_configuration(
        self, user_id: str
    ) -> Optional[PlaidConfigurationResponse]:
        """Get Plaid configuration details for a specific user."""
        try:
            container = await self._get_container()

            try:
                config_doc = container.read_item(user_id, user_id)
                plaid_config = config_doc.get(DocumentFields.PLAID, {})

                if not plaid_config:
                    return None

                return PlaidConfigurationResponse(
                    is_configured=plaid_config.get("is_active", False),
                    plaid_client_id=self._mask_client_id(
                        plaid_config.get("plaid_client_id", "")
                    ),
                    environment=plaid_config.get(
                        PlaidConfigFields.ENVIRONMENT, PlaidEnvironments.SANDBOX
                    ),
                    last_updated=datetime.fromisoformat(plaid_config.get("updated_at")),
                    updated_by=plaid_config.get("updated_by"),
                )
            except CosmosResourceNotFoundError:
                return None

        except Exception as e:
            logger.error(f"Error getting Plaid configuration: {e}")
            return None

    async def get_decrypted_credentials(
        self, user_id: str
    ) -> Optional[Tuple[str, str, str]]:
        """Get decrypted credentials for Plaid API calls (internal use only)."""
        try:
            container = await self._get_container()

            try:
                config_doc = container.read_item(user_id, user_id)
                plaid_config = config_doc.get(DocumentFields.PLAID, {})

                if not plaid_config.get("is_active", False):
                    return None

                client_id = plaid_config.get(PlaidConfigFields.PLAID_CLIENT_ID)
                encrypted_secret = plaid_config.get(
                    PlaidConfigFields.ENCRYPTED_PLAID_SECRET
                )
                environment = plaid_config.get(
                    PlaidConfigFields.ENVIRONMENT, PlaidEnvironments.SANDBOX
                )

                if not client_id or not encrypted_secret:
                    return None

                # Decrypt secret using Key Vault
                decrypted_secret = await AzureKeyVaultCryptoService.decrypt_secret(
                    encrypted_secret
                )

                return client_id, decrypted_secret, environment

            except CosmosResourceNotFoundError:
                return None

        except Exception as e:
            logger.error(f"Error getting decrypted credentials: {e}")
            return None

    async def delete_configuration(self, admin_user_id: str) -> bool:
        """Delete Plaid configuration for a specific user."""
        try:
            container = await self._get_container()

            try:
                # Get existing document
                config_doc = container.read_item(admin_user_id, admin_user_id)

                # Remove plaid configuration but keep other configs
                if DocumentFields.PLAID in config_doc:
                    del config_doc[DocumentFields.PLAID]

                # If no other configs remain, delete the entire document
                if (
                    len([k for k in config_doc.keys() if k not in ["id", "userId"]])
                    == 0
                ):
                    container.delete_item(admin_user_id, admin_user_id)
                    logger.info(
                        f"User configuration document deleted for user: {admin_user_id}"
                    )
                else:
                    # Update document without plaid config
                    container.upsert_item(config_doc)
                    logger.info(
                        f"Plaid configuration removed for user: {admin_user_id}"
                    )

                return True
            except CosmosResourceNotFoundError:
                return True  # Already deleted

        except Exception as e:
            logger.error(f"Error deleting Plaid configuration: {e}")
            return False


# Global service instance
plaid_config_service = PlaidConfigurationService()
