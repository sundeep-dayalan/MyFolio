"""
Plaid integration routes.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from ..services.plaid_service import PlaidService
from ..dependencies import get_current_user_id
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/plaid", tags=["plaid"])


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


def get_plaid_service() -> PlaidService:
    return PlaidService()


@router.post("/create_link_token")
def create_link_token(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Create a Plaid link token for the current user."""
    try:
        link_token = plaid_service.create_link_token(user_id)
        return {"link_token": link_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/exchange_public_token")
def exchange_public_token(
    request: ExchangeTokenRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Exchange public token for an access token and store securely."""
    try:
        result = plaid_service.exchange_public_token(user_id, request.public_token)

        # Convert to dict for response
        result_dict = result.dict() if hasattr(result, 'dict') else result

        # Add the long-running sync as a background task
        # The sync method will get the encrypted token from CosmosDB storage
        if result_dict.get("item_id"):
            logger.info(
                f"Scheduling background task for initial transaction sync for item {result_dict['item_id']}"
            )
            background_tasks.add_task(
                plaid_service._sync_transactions_for_stored_item,
                user_id=user_id,
                item_id=result_dict["item_id"]
            )

        # Remove sensitive data from response
        if "access_token" in result_dict:
            del result_dict["access_token"]
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts")
def get_accounts(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Fetch all account balances for the current user from stored data (fast, no API cost)."""
    try:
        result = plaid_service.get_accounts_with_balances(user_id)
        return result
    except Exception as e:
        # Return empty accounts if no tokens found
        return {"accounts": [], "total_balance": 0, "message": f"No connected accounts: {str(e)}"}


@router.post("/accounts/refresh")
def refresh_accounts(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Force refresh account balances from Plaid API and update stored data."""
    try:
        result = plaid_service.get_accounts_with_balances(user_id, use_cached_balance=False)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/data-info")
def get_accounts_data_info(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get information about stored account data (last updated, age, etc.)."""
    try:
        # Return basic info about user's tokens
        tokens = plaid_service.get_user_access_tokens(user_id)
        return {"tokens_count": len(tokens), "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/balance")
def get_balance_legacy(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Legacy endpoint - redirects to /accounts for backward compatibility."""
    try:
        result = plaid_service.get_accounts_with_balances(user_id)
        return {"accounts": result.get("accounts", [])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/items")
def get_plaid_items(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get summary of user's connected Plaid items (institutions)."""
    try:
        items = plaid_service.get_user_plaid_items(user_id)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/items/{item_id}")
def revoke_plaid_item(
    item_id: str,
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Revoke access to a specific Plaid item."""
    try:
        success = plaid_service.revoke_item_access(user_id, item_id)
        if success:
            return {"message": "Item revoked successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to revoke item")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tokens/revoke-all")
def revoke_all_tokens(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Revoke all tokens for the current user."""
    try:
        success = plaid_service.remove_all_user_data(user_id)
        return {
            "message": "All user data removed successfully" if success else "Failed to remove user data",
            "success": success,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
def get_transactions(
    days: int = 30,
    user_id: str = Depends(get_current_user_id),
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
    user_id: str = Depends(get_current_user_id),
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
def refresh_transactions(
    item_id: str,
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """
    Refresh transactions for a specific item/bank using sync API.
    Fetches only new transactions since the last sync.
    """
    try:
        result = plaid_service.refresh_transactions(user_id, item_id)
        return RefreshTransactionsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/transactions/force-refresh/{item_id}",
    response_model=ForceRefreshTransactionsResponse,
)
def force_refresh_transactions(
    item_id: str,
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """
    Force refresh transactions for a specific item/bank by clearing all existing data
    and performing a complete resync. This is an async operation that returns immediately.
    """
    try:
        result = plaid_service.force_refresh_transactions(user_id, item_id)
        return ForceRefreshTransactionsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
