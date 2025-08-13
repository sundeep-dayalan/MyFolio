"""
Cloud-specific configuration utilities for GCP deployment.
"""
import json
import os
import tempfile
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
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or "fit-guide-465001-p3"
        self.client = None
        
        if GOOGLE_CLOUD_AVAILABLE and self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
            except Exception:
                # Fallback to environment variables if Secret Manager is not available
                self.client = None

    def get_secret(self, secret_id: str, default: Optional[str] = None) -> Optional[str]:
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

    def setup_firebase_credentials(self) -> Optional[str]:
        """
        Setup Firebase credentials for Cloud Run environment.
        
        Returns:
            Path to Firebase credentials file
        """
        # Check if we're in Cloud Run environment
        if os.getenv("K_SERVICE"):
            # In Cloud Run, Firebase credentials are stored as a secret
            firebase_credentials = self.get_secret("FIREBASE_CREDENTIALS")
            if firebase_credentials:
                # Create temporary file with credentials
                temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
                temp_file.write(firebase_credentials)
                temp_file.close()
                return temp_file.name
        
        # For local development, use the service account file
        local_path = os.path.join(os.path.dirname(__file__), "..", "service-account.json")
        if os.path.exists(local_path):
            return local_path
            
        return None


# Global instance
_secret_manager = None

def get_secret_manager() -> GCPSecretManager:
    """Get global Secret Manager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = GCPSecretManager()
    return _secret_manager
