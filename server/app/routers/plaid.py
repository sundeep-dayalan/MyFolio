"""
Plaid integration routes.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from ..exceptions import BankDeleteError, ValidationError
from ..services.plaid_service import PlaidService
from ..dependencies import get_current_user, get_plaid_service
from ..utils.logger import get_logger
from ..constants import ApiRoutes, ApiTags
from ..services.transaction_storage_service import transaction_storage_service
from ..database import cosmos_client

logger = get_logger(__name__)

router = APIRouter(prefix=ApiRoutes.PLAID_PREFIX, tags=[ApiTags.PLAID])


class ExchangeTokenRequest(BaseModel):
    public_token: str


class RefreshTransactionsResponse(BaseModel):
    success: bool
    transactions_added: int
    transactions_modified: int
    transactions_removed: int
    total_processed: int
    item_id: str
    institution_name: str
    message: str


class ForceRefreshTransactionsResponse(BaseModel):
    success: bool
    message: str
    item_id: str
    institution_name: str
    status: str
    async_operation: bool


class PaginatedTransactionsResponse(BaseModel):
    transactions: list[Dict[str, Any]]
    totalCount: int
    page: int
    pageSize: int
    totalPages: int
    hasNextPage: bool
    hasPreviousPage: bool
    transactionType: str  # Added to show which type was queried


@router.post("/create_link_token")
async def create_link_token(
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Create a Plaid link token for the current user."""
    try:
        link_token = await plaid_service.create_link_token(user_id)
        logger.debug(f"Created link token for user {user_id} link token: {link_token}")
        return {"link_token": link_token}
    except Exception as e:
        logger.error(f"Failed to create link token for user {user_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/exchange_public_token")
async def exchange_public_token(
    request: ExchangeTokenRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Exchange public token for an access token and store securely."""
    try:
        result = await plaid_service.exchange_public_token(
            user_id, request.public_token, background_tasks
        )

        # Convert to dict for response
        result_dict = result.model_dump() if hasattr(result, "model_dump") else result

        # Remove sensitive data from response
        if "access_token" in result_dict:
            del result_dict["access_token"]
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account")
async def get_accounts(
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Fetch all account balances for the current user from Cosmos DB only."""
    try:
        result = await plaid_service.get_accounts(user_id)
        return result
    except Exception as e:
        return {
            "accounts": [],
            "message": f"No connected accounts: {str(e)}",
        }


@router.post("/account/refresh")
async def refresh_accounts(
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Force refresh account balances from Plaid API, update DB, and return latest."""
    try:
        result = await plaid_service.get_accounts_with_balances(
            user_id, use_cached_db_data=False
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/account/data-info")
def get_accounts_data_info(
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get information about stored account data (last updated, age, etc.)."""
    try:
        # Return basic info about user's tokens
        tokens = plaid_service.get_user_access_tokens(user_id)
        return {"tokens_count": len(tokens), "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bank")
async def get_plaid_items(
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get summary of user's connected Plaid items (institutions)."""
    try:
        return await plaid_service.get_banks(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/bank")
async def delete_bank(
    bank_ids: List[str] = Query(None, description="Additional bank IDs to delete"),
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Revoke access to one or multiple Plaid items."""
    all_bank_ids = []
    if bank_ids:
        all_bank_ids = bank_ids

    if not all_bank_ids:
        raise ValidationError("No bank IDs provided for deletion")

    try:
        logger.info(f"Deleting banks: {all_bank_ids} for user {user_id}")
        success_count = 0
        failed_banks = []

        for current_bank_id in all_bank_ids:
            try:
                success = await plaid_service.delete_bank(user_id, current_bank_id)
                if success:
                    success_count += 1
                else:
                    failed_banks.append(current_bank_id)
            except Exception as e:
                logger.error(f"Failed to delete bank {current_bank_id}: {str(e)}")
                failed_banks.append(current_bank_id)

        if failed_banks:
            return {
                "message": (
                    f"Partially completed: {success_count} items revoked, "
                    f"{len(failed_banks)} failed"
                ),
                "success_count": success_count,
                "failed_count": len(failed_banks),
                "failed_banks": failed_banks,
            }
        else:
            return {
                "message": f"All {success_count} items revoked successfully",
                "success_count": success_count,
            }
    except Exception as e:
        raise BankDeleteError(detail=str(e))


@router.get("/transactions")
def get_transactions(
    days: int = 30,
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Fetch transactions for the current user across all accounts."""
    try:
        result = plaid_service.get_transactions(user_id, days=days)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions/account/{account_id}")
def get_transactions_by_account(
    account_id: str,
    days: int = 30,
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Fetch transactions for a specific account."""
    try:
        result = plaid_service.get_transactions_by_account(
            user_id, account_id, days=days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/transactions/refresh/{item_id}", response_model=RefreshTransactionsResponse
)
async def refresh_transactions(
    item_id: str,
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """
    Refresh transactions for a specific item/bank using sync API.
    Fetches only new transactions since the last sync.
    """
    try:
        result = await plaid_service.refresh_transactions(user_id, item_id)
        return RefreshTransactionsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/transactions/force-refresh/{item_id}",
    response_model=ForceRefreshTransactionsResponse,
)
async def force_refresh_transactions(
    item_id: str,
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """
    Force refresh transactions for a specific item/bank by clearing all data
    and performing a complete resync. This is an async operation.
    """
    try:
        result = await plaid_service.force_refresh_transactions(user_id, item_id)
        return ForceRefreshTransactionsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions/paginated", response_model=PaginatedTransactionsResponse)
async def get_transactions_paginated(
    user_id: str = Depends(get_current_user),
    # Pagination & Sorting Parameters
    page: int = Query(1, ge=1, description="Page number, defaults to 1"),
    pageSize: int = Query(
        20, ge=1, le=100, description="Number of items per page, defaults to 20"
    ),
    sortBy: str = Query("date", description="Field to sort by: date, amount"),
    sortOrder: str = Query("desc", description="Sort order: asc or desc"),
    # Core Identity Filters
    accountId: Optional[str] = Query(None, description="Filter by specific account ID"),
    itemId: Optional[str] = Query(
        None, description="Filter by specific item ID (bank connection)"
    ),
    # State & Type Filters
    status: Optional[str] = Query(
        None, description="Filter by status: posted, pending, removed"
    ),
    isPending: Optional[bool] = Query(
        None,
        description="Filter by pending status (true for pending, false for posted)",
    ),
    paymentChannel: Optional[str] = Query(
        None, description="Filter by payment channel: online, in store, other"
    ),
    # Date & Financial Filters
    dateFrom: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    dateTo: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    minAmount: Optional[float] = Query(None, description="Minimum transaction amount"),
    maxAmount: Optional[float] = Query(None, description="Maximum transaction amount"),
    currency: Optional[str] = Query(
        None, description="Filter by currency code (e.g., USD)"
    ),
    # Content & Category Filters
    searchTerm: Optional[str] = Query(
        None, description="Search term for description and counterparty names"
    ),
    category: Optional[str] = Query(
        None, description="Filter by primary personal finance category"
    ),
):
    """Get paginated transactions from Cosmos DB with filtering and sorting."""
    try:
        await cosmos_client.ensure_connected()
        # Get paginated transactions with all filters
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
            account_id=accountId,
            item_id=itemId,
            status=status,
            is_pending=isPending,
            payment_channel=paymentChannel,
            date_from=dateFrom,
            date_to=dateTo,
            min_amount=minAmount,
            max_amount=maxAmount,
            currency=currency,
            search_term=searchTerm,
            category=category,
        )

        return PaginatedTransactionsResponse(
            transactions=transactions,
            totalCount=total_count,
            page=page,
            pageSize=pageSize,
            totalPages=total_pages,
            hasNextPage=has_next,
            hasPreviousPage=has_previous,
            # Use status as transaction type for backward compatibility
            transactionType=status or "all",
        )

    except Exception as e:
        logger.error(
            f"Failed to get paginated transactions for user {user_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/count")
def get_transactions_count(
    user_id: str = Depends(get_current_user),
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


@router.get("/transactions/test")
async def test_transactions(
    user_id: str = Depends(get_current_user),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get total count of transactions for the current user."""
    try:
        await cosmos_client.ensure_connected()
        # count = await plaid_service.sync_transactions(
        #     "J8aRXNqzQzt3nBxDdkzvhJvGEyqm6kcdQEKva", user_id
        # )
        # return {"count": count}

        await transaction_storage_service.delete_item_transactions(
            user_id, "qLJQGxdEqbukrbpyQvlxS1K3vPQ5ZBTdByg4p"
        )

    except Exception as e:
        logger.error(
            f"Failed to get transaction count for user {user_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
