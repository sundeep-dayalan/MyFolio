"""
Database-related constants.
"""


# Container Names
class Containers:
    USERS = "users"
    TRANSACTIONS = "transactions"
    BANKS = "banks"
    CONFIGURATION = "configuration"


# Document Keys and Field Names
class DocumentFields:
    ID = "id"
    USER_ID = "userId"
    ITEM_ID = "itemId"
    PLAID = "plaid"
    ACCOUNTS = "accounts"
    TRANSACTIONS = "transactions"
    METADATA = "metadata"


# Partition Key Configurations
class PartitionKeys:
    USER_ID_PATH = "/userId"
    ID_PATH = "/id"
    HASH_KIND = "Hash"
    RANGE_KIND = "Range"


# Database Query Fields
class QueryFields:
    # Common query parameter names
    USER_ID_PARAM = "@userId"
    STATUS_PARAM = "@status"
    ITEM_ID_PARAM = "@itemId"

    # Metadata fields
    ACCOUNT_COUNT = "metadata.accountCount"
    TOTAL_BALANCE = "metadata.totalBalance"
    LAST_UPDATED = "metadata.lastUpdated"
    TRANSACTION_SYNC_STATUS = "metadata.transactionSyncStatus"


# Standard document fields that appear across collections
class StandardFields:
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    UPDATED_BY = "updated_by"
    LAST_USED_AT = "last_used_at"
    IS_ACTIVE = "is_active"
    STATUS = "status"
    NAME = "name"
    VALUE = "value"
