"""
Plaid integration routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from ..services.plaid_service import PlaidService
from ..dependencies import get_current_user_id

router = APIRouter(prefix="/plaid", tags=["plaid"])


class ExchangeTokenRequest(BaseModel):
    public_token: str


def get_plaid_service() -> PlaidService:
    return PlaidService()


@router.get("/test")
def test_plaid_connection():
    """Test endpoint to verify Plaid service is working."""
    try:
        plaid_service = PlaidService()
        return {"status": "ok", "message": "Plaid service initialized successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Plaid service error: {e}"}


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
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Exchange public token for an access token and store securely."""
    try:
        result = plaid_service.exchange_public_token(request.public_token, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts")
def get_accounts(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Fetch all account balances for the current user."""
    try:
        result = plaid_service.get_accounts_balance(user_id)
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


# ===== TOKEN LIFECYCLE MANAGEMENT ENDPOINTS =====


@router.delete("/tokens/cleanup")
def cleanup_expired_tokens(
    days_threshold: int = 90,
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Clean up expired and stale tokens. Requires authentication."""
    try:
        # Note: This is a system-wide cleanup, but we require authentication for security
        stats = plaid_service.cleanup_expired_tokens(days_threshold)
        return {"message": "Token cleanup completed", "statistics": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/tokens/analytics")
def get_token_analytics(
    user_id: str = Depends(get_current_user_id),
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Get token analytics and health information. Requires authentication."""
    try:
        analytics = plaid_service.get_token_analytics()
        return {"analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
