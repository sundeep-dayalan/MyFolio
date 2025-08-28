"""
Plaid-related constants.
"""

# Plaid Environments
class PlaidEnvironments:
    SANDBOX = "sandbox"
    DEVELOPMENT = "development" 
    PRODUCTION = "production"


# Plaid Products
class PlaidProducts:
    TRANSACTIONS = "transactions"
    ACCOUNTS = "accounts"
    IDENTITY = "identity"
    ASSETS = "assets"
    INVESTMENTS = "investments"
    LIABILITIES = "liabilities"
    PAYMENT_INITIATION = "payment_initiation"


# Plaid Configuration Fields
class PlaidConfigFields:
    PLAID_CLIENT_ID = "plaid_client_id"
    ENCRYPTED_PLAID_SECRET = "encrypted_plaid_secret"
    ENVIRONMENT = "environment"
    INSTITUTION_ID = "institution_id"
    INSTITUTION_NAME = "institution_name"
    ACCESS_TOKEN = "access_token"


# Plaid Transaction Sync Status
class TransactionSyncStatus:
    IN_PROGRESS = "inprogress"
    SYNCING = "syncing"
    COMPLETED = "completed"
    ERROR = "error"


# Plaid Link Token Configuration
class PlaidLinkConfig:
    CLIENT_NAME_VALIDATION = "Sage - Credential Validation"
    COUNTRY_CODE_US = "US"
    LANGUAGE_EN = "en"
    VALIDATION_TEST_USER_ID = "validation_test_user"
    DEFAULT_DAYS_REQUESTED = 730


# Plaid API Error Messages
class PlaidApiErrors:
    INVALID_CLIENT_ID = "INVALID_CLIENT_ID"
    INVALID_API_KEYS = "INVALID_API_KEYS"
    INVALID_SECRET = "INVALID_SECRET"
    UNAUTHORIZED = "UNAUTHORIZED"
    API_ERROR = "API_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    BAD_REQUEST = "Bad Request"


# Plaid Error User-Friendly Messages
class PlaidErrorMessages:
    INVALID_CLIENT_ID_MSG = "Invalid Plaid Client ID. Please check your credentials."
    INVALID_SECRET_MSG = "Invalid Plaid Secret. Please check your credentials."
    UNAUTHORIZED_MSG = "Invalid credentials. Please verify your Plaid Client ID and Secret."
    INVALID_CREDENTIALS_MSG = "Invalid Plaid credentials. Please verify your Client ID and Secret are correct."
    API_ERROR_MSG = "Unable to validate credentials with Plaid API. Please try again."
    BAD_REQUEST_MSG = "Invalid Plaid credentials. Please check your Client ID and Secret."
    GENERIC_ERROR_MSG = "Credential validation failed. Please verify your Plaid credentials."
    
    
# Default Currency
class Currency:
    USD = "USD"


# Plaid Response Fields
class PlaidResponseFields:
    TRANSACTIONS = "transactions"
    STATUS = "status"
    SUCCESS = "success" 
    COMPLETED = "completed"