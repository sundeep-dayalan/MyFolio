"""
Status and state-related constants.
"""

# General Status Values
class Status:
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"
    SUCCESS = "success"
    FAILED = "failed"


# Operation Types
class OperationTypes:
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


# Response Messages
class ResponseMessages:
    SUCCESS = "Success"
    OPERATION_COMPLETED = "Operation completed successfully"
    DATA_NOT_FOUND = "Data not found"
    INVALID_REQUEST = "Invalid request"
    UNAUTHORIZED_ACCESS = "Unauthorized access"
    INTERNAL_ERROR = "Internal server error"


# Processing Status
class ProcessingStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"