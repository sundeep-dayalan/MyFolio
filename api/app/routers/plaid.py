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
        result = plaid_service.exchange_public_token(request.public_token, user_id)

        # Add the long-running sync as a background task
        # This will run after the response has been sent to the user.
        if result.get("success") and result.get("access_token"):
            logger.info(
                f"Scheduling background task for initial transaction sync for item {result['item_id']}"
            )
            background_tasks.add_task(
                plaid_service.sync_all_transactions_for_item,
                user_id=user_id,
                item_id=result["item_id"],
                access_token=result["access_token"],
            )

        # We don't want to return the sensitive access token to the client
        del result["access_token"]
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts")
def get_accounts(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Fetch all account balances for the current user from stored data (fast, no API cost)."""
    try:
        result = plaid_service.get_stored_accounts_balance(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/refresh")
def refresh_accounts(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Force refresh account balances from Plaid API and update stored data."""
    try:
        result = plaid_service.refresh_accounts_balance(user_id)
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
        result = plaid_service.get_data_info(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/balance")
def get_balance_legacy(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Legacy endpoint - redirects to /accounts for backward compatibility."""
    try:
        result = plaid_service.get_accounts_balance(user_id)
        return {"accounts": result["accounts"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/items")
def get_plaid_items(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get summary of user's connected Plaid items (institutions)."""
    try:
        result = plaid_service.get_user_plaid_items(user_id)
        return {"items": result}
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
        success = plaid_service.revoke_user_token(user_id, item_id)
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
        count = plaid_service.revoke_all_user_tokens(user_id)
        return {
            "message": f"Revoked {count} tokens successfully",
            "revoked_count": count,
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


@router.post("/transactions/refresh/{item_id}")
def refresh_transactions(
    item_id: str,
    days: int = 30,
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Refresh transactions for a specific item/bank."""
    try:
        result = plaid_service.refresh_transactions(user_id, item_id, days=days)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
