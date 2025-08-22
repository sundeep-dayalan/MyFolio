"""
Configuration management for Azure-based backend
Handles environment variables and Azure Key Vault integration
"""

import os
import logging
from typing import Optional, Dict, Any
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseSettings, Field

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings with Azure Key Vault integration"""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # JWT Configuration
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 24 hours
    
    # Azure Cosmos DB
    cosmos_db_endpoint: str = Field(default="", env="COSMOS_DB_ENDPOINT")
    cosmos_db_key: str = Field(default="", env="COSMOS_DB_KEY")
    cosmos_db_name: str = Field(default="sage-db", env="COSMOS_DB_NAME")
    
    # Azure Key Vault
    key_vault_url: str = Field(default="", env="KEY_VAULT_URL")
    
    # Google OAuth (will be retrieved from Key Vault in production)
    google_client_id: str = Field(default="", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", env="GOOGLE_CLIENT_SECRET")
    
    # Plaid Configuration (will be retrieved from Key Vault in production)
    plaid_client_id: str = Field(default="", env="PLAID_CLIENT_ID")
    plaid_secret: str = Field(default="", env="PLAID_SECRET")
    plaid_env: str = Field(default="sandbox", env="PLAID_ENV")
    
    # CORS settings
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class AzureKeyVaultManager:
    """Manages secrets from Azure Key Vault"""
    
    def __init__(self, key_vault_url: str):
        self.key_vault_url = key_vault_url
        self.secret_client: Optional[SecretClient] = None
        self._secrets_cache: Dict[str, str] = {}
        
        if key_vault_url:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Key Vault client"""
        try:
            credential = DefaultAzureCredential()
            self.secret_client = SecretClient(
                vault_url=self.key_vault_url,
                credential=credential
            )
            logger.info("Azure Key Vault client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Key Vault client: {str(e)}")
            self.secret_client = None
    
    async def get_secret(self, secret_name: str, default_value: str = "") -> str:
        """Get secret from Key Vault with caching"""
        # Return cached value if available
        if secret_name in self._secrets_cache:
            return self._secrets_cache[secret_name]
        
        # Try to get from Key Vault
        if self.secret_client:
            try:
                secret = self.secret_client.get_secret(secret_name)
                self._secrets_cache[secret_name] = secret.value
                logger.info(f"Secret '{secret_name}' retrieved from Key Vault")
                return secret.value
            except Exception as e:
                logger.warning(f"Failed to get secret '{secret_name}' from Key Vault: {str(e)}")
        
        # Return default value if Key Vault is not available
        if default_value:
            self._secrets_cache[secret_name] = default_value
            return default_value
        
        logger.warning(f"Secret '{secret_name}' not found and no default provided")
        return ""
    
    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Key Vault"""
        if not self.secret_client:
            logger.error("Key Vault client not initialized")
            return False
        
        try:
            self.secret_client.set_secret(secret_name, secret_value)
            self._secrets_cache[secret_name] = secret_value
            logger.info(f"Secret '{secret_name}' set in Key Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to set secret '{secret_name}' in Key Vault: {str(e)}")
            return False
    
    def clear_cache(self):
        """Clear secrets cache"""
        self._secrets_cache.clear()


class ConfigManager:
    """Enhanced configuration manager with Azure Key Vault support"""
    
    def __init__(self):
        self.settings = Settings()
        self.key_vault_manager = AzureKeyVaultManager(self.settings.key_vault_url)
        self._initialized = False
    
    async def initialize(self):
        """Initialize configuration with Key Vault secrets"""
        if self._initialized:
            return
        
        try:
            # Load secrets from Key Vault if available
            if self.key_vault_manager.secret_client:
                await self._load_secrets_from_key_vault()
            
            self._initialized = True
            logger.info("Configuration initialized successfully")
            
        except Exception as e:
            logger.error(f"Configuration initialization failed: {str(e)}")
            raise
    
    async def _load_secrets_from_key_vault(self):
        """Load secrets from Azure Key Vault"""
        secret_mappings = {
            'jwt-secret': 'secret_key',
            'google-client-id': 'google_client_id',
            'google-client-secret': 'google_client_secret',
            'plaid-client-id': 'plaid_client_id',
            'plaid-secret': 'plaid_secret',
        }
        
        for key_vault_name, settings_attr in secret_mappings.items():
            current_value = getattr(self.settings, settings_attr)
            secret_value = await self.key_vault_manager.get_secret(
                key_vault_name,
                current_value
            )
            
            if secret_value:
                setattr(self.settings, settings_attr, secret_value)
                logger.debug(f"Updated {settings_attr} from Key Vault")
    
    async def get_secret(self, secret_name: str, default_value: str = "") -> str:
        """Get secret from Key Vault"""
        return await self.key_vault_manager.get_secret(secret_name, default_value)
    
    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Key Vault"""
        return await self.key_vault_manager.set_secret(secret_name, secret_value)
    
    def get_cors_origins(self) -> list:
        """Get CORS origins as a list"""
        if isinstance(self.settings.cors_origins, str):
            return [origin.strip() for origin in self.settings.cors_origins.split(',')]
        return self.settings.cors_origins
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.settings.environment.lower() in ['development', 'dev', 'local']
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.settings.environment.lower() in ['production', 'prod']


# Global configuration instance
config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global configuration manager instance"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager


async def initialize_config():
    """Initialize the global configuration"""
    config = get_config()
    await config.initialize()
    return config


# Environment-specific logging setup
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Reduce Azure SDK logging
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    
    logger.info(f"Logging initialized with level: {log_level}")


# Configuration validation
def validate_config(config: ConfigManager) -> bool:
    """Validate required configuration"""
    required_settings = []
    
    if not config.settings.cosmos_db_endpoint:
        required_settings.append("COSMOS_DB_ENDPOINT")
    
    if not config.settings.secret_key or config.settings.secret_key == "dev-secret-key":
        if config.is_production():
            required_settings.append("SECRET_KEY or jwt-secret in Key Vault")
    
    if required_settings:
        logger.error(f"Missing required configuration: {', '.join(required_settings)}")
        return False
    
    return True