"""
Cloud-specific configuration utilities for GCP deployment.
"""
import os
from typing import Optional

try:
    from google.cloud import secretmanager

    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False


class GCPSecretManager:
    """Helper class to manage GCP Secret Manager integration."""

    def __init__(self, project_id: Optional[str] = None):
        # For Cloud Run, explicitly use the project ID since GOOGLE_CLOUD_PROJECT might not be set
        self.project_id = (
            project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or "fit-guide-465001-p3"
        )
        self.client = None

        if GOOGLE_CLOUD_AVAILABLE and self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
            except Exception:
                # Fallback to environment variables if Secret Manager is not available
                self.client = None

    def get_secret(
        self, secret_id: str, default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get secret from GCP Secret Manager or fallback to environment variable.

        Args:
            secret_id: The secret ID in Secret Manager
            default: Default value if secret is not found

        Returns:
            Secret value or default
        """
        # First try environment variable (for local development)
        env_value = os.getenv(secret_id)
        if env_value:
            return env_value

        # Then try Secret Manager (for production)
        if self.client and self.project_id:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
                response = self.client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode("UTF-8")
                return secret_value
            except Exception:
                pass

        return default



# Global instance
_secret_manager = None


def get_secret_manager() -> GCPSecretManager:
    """Get global Secret Manager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = GCPSecretManager()
    return _secret_manager
