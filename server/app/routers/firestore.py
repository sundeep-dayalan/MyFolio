"""
CosmosDB-based transaction routes for direct database access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any
from pydantic import BaseModel
from ..services.transaction_storage_service import transaction_storage_service
from ..dependencies import get_current_user_id
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/cosmosdb", tags=["cosmosdb"])

# Create a compatibility router for old firestore endpoints
firestore_router = APIRouter(prefix="/firestore", tags=["firestore-compatibility"])


class PaginatedTransactionsResponse(BaseModel):
    transactions: list[Dict[str, Any]]
    totalCount: int
    page: int
    pageSize: int
    totalPages: int
    hasNextPage: bool
    hasPreviousPage: bool
    transactionType: str  # Added to show which type was queried


@router.get("/transactions/paginated", response_model=PaginatedTransactionsResponse)
def get_transactions_paginated(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(
        20, ge=1, le=100, description="Number of transactions per page"
    ),
    sortBy: str = Query("date", description="Field to sort by"),
    sortOrder: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    transactionType: str = Query(
        "added",
        regex="^(added|modified|removed|all)$",
        description="Type of transactions to fetch",
    ),
    accountId: Optional[str] = Query(None, description="Filter by account ID"),
    itemId: Optional[str] = Query(None, description="Filter by item ID (bank)"),
    institutionName: Optional[str] = Query(
        None, description="Filter by institution name"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    dateFrom: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    dateTo: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    searchTerm: Optional[str] = Query(
        None, description="Search term for name/merchant"
    ),
    user_id: str = Depends(get_current_user_id),
):
    """Get paginated transactions from Firestore with filtering and sorting."""
    try:
        logger.info(
            f"Getting paginated {transactionType} transactions for user {user_id}, page {page}"
        )

        # Build filters dictionary
        filters = {}
        if accountId:
            filters["account_id"] = accountId
        if itemId:
            filters["item_id"] = itemId
        if institutionName:
            filters["institution_name"] = institutionName
        if category:
            filters["category"] = category
        if dateFrom:
            filters["date_from"] = dateFrom
        if dateTo:
            filters["date_to"] = dateTo
        if searchTerm:
            filters["search_term"] = searchTerm

        # Get paginated transactions with transaction type
        (
            transactions,
            total_count,
            total_pages,
            has_next,
            has_previous,
        ) = transaction_storage_service.get_transactions_paginated(
            user_id=user_id,
            page=page,
            page_size=pageSize,
            sort_by=sortBy,
            sort_order=sortOrder,
            filters=filters if filters else None,
            transaction_type=transactionType,
        )

        return PaginatedTransactionsResponse(
            transactions=transactions,
            totalCount=total_count,
            page=page,
            pageSize=pageSize,
            totalPages=total_pages,
            hasNextPage=has_next,
            hasPreviousPage=has_previous,
            transactionType=transactionType,
        )

    except Exception as e:
        logger.error(
            f"Failed to get paginated transactions for user {user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/count")
def get_transactions_count(
    user_id: str = Depends(get_current_user_id),
):
    """Get total count of transactions for the current user."""
    try:
        count = transaction_storage_service.get_user_transactions_count(user_id)
        return {"count": count}

    except Exception as e:
        logger.error(
            f"Failed to get transaction count for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# Firestore compatibility endpoints - redirect to CosmosDB endpoints
@firestore_router.get("/transactions/paginated", response_model=PaginatedTransactionsResponse)
def get_transactions_paginated_firestore_compat(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(
        20, ge=1, le=100, description="Number of transactions per page"
    ),
    sortBy: str = Query("date", description="Field to sort by"),
    sortOrder: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    transactionType: str = Query(
        "added",
        regex="^(added|modified|removed|all)$",
        description="Type of transactions to fetch",
    ),
    accountId: Optional[str] = Query(None, description="Filter by account ID"),
    itemId: Optional[str] = Query(None, description="Filter by item ID (bank)"),
    institutionName: Optional[str] = Query(
        None, description="Filter by institution name"
    ),
    category: Optional[str] = Query(None, description="Filter by category"),
    dateFrom: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    dateTo: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    searchTerm: Optional[str] = Query(
        None, description="Search term for name/merchant"
    ),
    user_id: str = Depends(get_current_user_id),
):
    """Firestore compatibility endpoint - redirects to CosmosDB."""
    # Call the same logic as the CosmosDB endpoint
    return get_transactions_paginated(
        page=page, pageSize=pageSize, sortBy=sortBy, sortOrder=sortOrder,
        transactionType=transactionType, accountId=accountId, itemId=itemId,
        institutionName=institutionName, category=category, dateFrom=dateFrom,
        dateTo=dateTo, searchTerm=searchTerm, user_id=user_id
    )


@firestore_router.get("/transactions/count")
def get_transactions_count_firestore_compat(
    user_id: str = Depends(get_current_user_id),
):
    """Firestore compatibility endpoint - redirects to CosmosDB."""
    return get_transactions_count(user_id=user_id)
