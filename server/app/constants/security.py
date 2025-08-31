"""
Security-related constants.
"""


# Encryption and Security
class Security:
    # Key Vault
    SECRETS_ENCRYPTION_KEY = "secrets-encryption-key"
    SESSION_SECRET_KEY = "session-secret-key"


# Configuration Messages
class ConfigMessages:
    CREDENTIALS_NOT_CONFIGURED = (
        "Plaid credentials not configured. Admin must provide credentials via "
        "/api/v1/plaid/configuration endpoint."
    )
    CONFIG_ALREADY_EXISTS = (
        "Plaid configuration already exists. Delete before creating a new one."
    )
    CREDENTIALS_REQUIRED = "Client ID and secret are required"
    CREDENTIALS_TOO_SHORT = "Client ID and secret appear to be too short"
    ENVIRONMENT_REQUIRED = "Environment must be either 'sandbox' or 'production'"
    CREDENTIALS_FORMAT_VALID = "Credentials format is valid. Actual credentials will be validated with Plaid once stored."
    CREDENTIALS_VALIDATED = "Credentials validated successfully with Plaid API"


# Error Messages
class ErrorMessages:
    FAILED_TO_ENCRYPT = "Failed to encrypt secret"
    FAILED_TO_DECRYPT = "Failed to decrypt secret"
    FAILED_TO_STORE_CONFIG = "Failed to store Plaid configuration"
    FAILED_TO_GET_CONFIG = "Failed to get Plaid configuration"
    FAILED_TO_DELETE_CONFIG = "Failed to delete Plaid configuration"
    TOKEN_ENCRYPTION_FAILED = "Token encryption failed"
    TOKEN_DECRYPTION_FAILED = "Token decryption failed"
    COSMOSDB_CONNECTION_REQUIRED = "CosmosDB connection required for bank data storage"
    COSMOSDB_NOT_CONNECTED = "CosmosDB not connected"
