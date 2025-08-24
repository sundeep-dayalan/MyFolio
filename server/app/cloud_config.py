"""
Azure Key Vault configuration utilities for Azure deployment.
"""
import os
from typing import Optional

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
    AZURE_KEYVAULT_AVAILABLE = True
except ImportError:
    AZURE_KEYVAULT_AVAILABLE = False


class AzureKeyVaultManager:
    """Helper class to manage Azure Key Vault integration."""

    def __init__(self, key_vault_url: Optional[str] = None):
        # Get Key Vault URL from environment or parameter
        self.key_vault_url = (
            key_vault_url or os.getenv("KEY_VAULT_URL")
        )
        self.client = None

        if AZURE_KEYVAULT_AVAILABLE and self.key_vault_url:
            try:
                # Use DefaultAzureCredential for authentication
                # This works with Managed Identity in Azure Functions
                credential = DefaultAzureCredential()
                self.client = SecretClient(vault_url=self.key_vault_url, credential=credential)
            except Exception:
                # Fallback to environment variables if Key Vault is not available
                self.client = None

    def get_secret(
        self, secret_name: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get secret from Azure Key Vault or fallback to environment variable.

        Args:
            secret_name: The secret name in Key Vault
            default: Default value if secret is not found

        Returns:
            Secret value or default
        """
        # First try environment variable (for local development)
        env_value = os.getenv(secret_name.upper().replace("-", "_"))
        if env_value:
            return env_value

        # Then try Key Vault (for production)
        if self.client and self.key_vault_url:
            try:
                secret = self.client.get_secret(secret_name)
                return secret.value
            except Exception:
                pass

        return default


# Global instance
_key_vault_manager = None


def get_secret_manager() -> AzureKeyVaultManager:
    """Get global Key Vault Manager instance."""
    global _key_vault_manager
    if _key_vault_manager is None:
        _key_vault_manager = AzureKeyVaultManager()
    return _key_vault_manager