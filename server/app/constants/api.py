"""
API-related constants.
"""

# API Route Prefixes
class ApiRoutes:
    PLAID_PREFIX = "/plaid"
    CONFIGURATION_PREFIX = "/configuration"
    AUTH_PREFIX = "/auth/oauth/microsoft"


# API Route Tags  
class ApiTags:
    PLAID = "plaid"
    PLAID_CONFIGURATION = "plaid-configuration"
    MICROSOFT_OAUTH = "Microsoft OAuth Authentication"


# API Endpoints
class ApiEndpoints:
    # Plaid Configuration
    PLAID_CONFIG = "/configuration"
    PLAID_CONFIG_STATUS = "/configuration/status"
    PLAID_CONFIG_VALIDATE = "/configuration/validate"
    
    # Plaid Operations
    PLAID_LINK_TOKEN = "/link_token"
    PLAID_EXCHANGE_TOKEN = "/exchange_token"
    PLAID_ACCOUNTS = "/accounts"
    PLAID_TRANSACTIONS = "/transactions"


# HTTP Status Messages
class HttpMessages:
    AUTHENTICATION_REQUIRED = "Authentication required"
    FAILED_TO_STORE_CONFIG = "Failed to store configuration"
    FAILED_TO_GET_CONFIG = "Failed to get configuration"
    FAILED_TO_DELETE_CONFIG = "Failed to delete configuration"
    CONFIG_NOT_FOUND = "Plaid configuration not found"
    

# Content Types
class ContentTypes:
    APPLICATION_JSON = "application/json"
    

# Authentication
class AuthHeaders:
    AUTHORIZATION = "Authorization"
    BEARER_PREFIX = "Bearer"