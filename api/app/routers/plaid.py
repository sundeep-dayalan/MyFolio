"""
Plaid integration routes.
"""

from fastapi import APIRouter, Depends, HTTPException
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


# ===== TRANSACTIONS ENDPOINTS =====


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


# ===== TEST ENDPOINTS (Remove in production) =====


@router.get("/transactions/test")
def test_get_transactions(
    days: int = 30,
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Test endpoint to check transactions without authentication - REMOVE IN PRODUCTION."""
    try:
        from ..database import firebase_client

        # Get any user with plaid tokens from CORRECT collection
        tokens_ref = firebase_client.db.collection(
            "plaid_tokens"
        )  # Fixed: was 'plaid_access_tokens'
        docs = list(tokens_ref.limit(1).get())

        if not docs:
            return {
                "error": "No users with Plaid tokens found",
                "message": "Connect a bank account first through the frontend",
                "transactions": [],
                "transaction_count": 0,
                "account_count": 0,
                "items": [],
            }

        # Use the first user we find
        user_id = docs[0].to_dict().get("user_id")
        if not user_id:
            return {"error": "Invalid user_id found in token"}

        result = plaid_service.get_transactions(user_id, days=days)
        return {**result, "debug_info": {"user_id": user_id, "found_tokens": len(docs)}}
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch transactions"}


@router.get("/transactions/test-user/{user_id}")
def test_get_transactions_for_user(
    user_id: str,
    days: int = 30,
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Test endpoint to check transactions for a specific user - REMOVE IN PRODUCTION."""
    try:
        result = plaid_service.get_transactions(user_id, days=days)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/test/simple-transactions")
def simple_transactions_test():
    """Simple test endpoint that returns mock transactions - REMOVE IN PRODUCTION."""
    return {
        "transactions": [
            {
                "transaction_id": "test_1",
                "name": "Test Transaction 1",
                "amount": -25.50,
                "date": "2025-08-07",
                "account_id": "test_account_1",
                "category": ["Food", "Restaurants"],
                "merchant_name": "Test Restaurant",
            },
            {
                "transaction_id": "test_2",
                "name": "Test Transaction 2",
                "amount": -75.00,
                "date": "2025-08-06",
                "account_id": "test_account_2",
                "category": ["Shops", "Supermarkets"],
                "merchant_name": "Test Store",
            },
        ],
        "transaction_count": 2,
        "account_count": 2,
        "items": [
            {
                "item_id": "test_item",
                "institution_name": "Test Bank",
                "transaction_count": 2,
            }
        ],
        "sync_api": True,
    }


@router.get("/test/debug-transactions")
def debug_transactions_data(plaid_service: PlaidService = Depends(get_plaid_service)):
    """Debug endpoint to test transactions sync API - REMOVE IN PRODUCTION."""
    try:
        # Test with the known user ID
        user_id = "106251072616484621570"
        logger.info(f"Debug: Testing transactions for user {user_id}")

        result = plaid_service.get_transactions(user_id, days=30)

        return {"debug": True, "user_id": user_id, "result": result}

    except Exception as e:
        logger.error(f"Debug transactions error: {e}")
        return {"debug": True, "error": str(e), "error_type": type(e).__name__}


@router.get("/test/debug-accounts")
def debug_accounts_data(plaid_service: PlaidService = Depends(get_plaid_service)):
    """Debug endpoint to check what accounts endpoint returns - REMOVE IN PRODUCTION."""
    try:
        from ..database import firebase_client

        # Get any user with plaid tokens from CORRECT collection
        tokens_ref = firebase_client.db.collection(
            "plaid_tokens"
        )  # Fixed: was 'plaid_access_tokens'
        docs = list(tokens_ref.get())

        debug_info = {"total_tokens_in_db": len(docs), "sample_tokens": []}

        for i, doc in enumerate(docs[:3]):  # Show first 3
            token_data = doc.to_dict()
            debug_info["sample_tokens"].append(
                {
                    "user_id": token_data.get("user_id"),
                    "institution_name": token_data.get("institution_name"),
                    "status": token_data.get("status"),
                    "created_at": str(token_data.get("created_at")),
                }
            )

            # If we find a user, test their accounts and transactions
            if i == 0 and token_data.get("user_id"):
                user_id = token_data.get("user_id")
                try:
                    accounts_result = plaid_service.get_accounts_balance(user_id)
                    debug_info["sample_accounts"] = accounts_result
                except Exception as e:
                    debug_info["accounts_error"] = str(e)

                try:
                    transactions_result = plaid_service.get_transactions(
                        user_id, days=365
                    )
                    debug_info["sample_transactions"] = {
                        "transaction_count": transactions_result.get(
                            "transaction_count", 0
                        ),
                        "date_range": transactions_result.get("date_range"),
                        "first_few_transactions": transactions_result.get(
                            "transactions", []
                        )[:3],
                    }
                except Exception as e:
                    debug_info["transactions_error"] = str(e)

        return debug_info
    except Exception as e:
        return {"error": str(e)}


@router.get("/test/plaid-sandbox-info")
def test_plaid_sandbox_info():
    """Test endpoint to check Plaid environment and setup - REMOVE IN PRODUCTION."""
    try:
        from ..services.plaid_service import PlaidService

        plaid_service = PlaidService()

        return {
            "plaid_environment": plaid_service.environment,
            "message": f"Using Plaid {plaid_service.environment} environment",
            "next_steps": [
                "1. Make sure you're logged in to the React app",
                "2. Go to /accounts page",
                "3. Click 'Connect Bank Account'",
                "4. Use Plaid sandbox credentials if in sandbox mode:",
                "   - Username: user_good",
                "   - Password: pass_good",
                "5. After connecting, transactions should be available",
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/test/debug-token-storage")
def debug_token_storage():
    """Debug what's in the plaid_tokens collection - REMOVE IN PRODUCTION."""
    try:
        from ..database import firebase_client

        tokens_ref = firebase_client.db.collection("plaid_tokens")
        docs = list(tokens_ref.limit(2).get())

        debug_info = []
        for doc in docs:
            data = doc.to_dict()
            debug_info.append(
                {
                    "doc_id": doc.id,
                    "all_fields": data,
                    "encrypted_token_present": (
                        "encrypted_token" in data if data else False
                    ),
                    "encrypted_token_length": (
                        len(data.get("encrypted_token", ""))
                        if data and data.get("encrypted_token")
                        else 0
                    ),
                }
            )

        return {"total_docs": len(docs), "documents": debug_info}
    except Exception as e:
        return {"error": str(e)}


@router.get("/test/direct-plaid-test")
def test_direct_plaid_call():
    """Test direct Plaid API call with known access token - REMOVE IN PRODUCTION."""
    try:
        from ..services.plaid_service import PlaidService
        from plaid.model.transactions_get_request import TransactionsGetRequest
        from datetime import datetime, timezone, timedelta

        plaid_service = PlaidService()
        access_token = "access-sandbox-c257efd3-db6a-4905-a239-c379d6871dd2"

        # Calculate date range
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=730)  # 2 years back

        # Make direct call to Plaid
        transactions_request = TransactionsGetRequest(
            access_token=access_token, start_date=start_date, end_date=end_date
        )

        response = plaid_service.client.transactions_get(transactions_request)

        transactions = response.get("transactions", [])

        return {
            "access_token": access_token,
            "date_range": f"{start_date} to {end_date}",
            "total_transactions": len(transactions),
            "first_5_transactions": transactions[:5] if transactions else [],
            "accounts_found": len(response.get("accounts", [])),
            "warning": "Direct Plaid API test - remove in production!",
        }
    except Exception as e:
        return {
            "error": str(e),
            "access_token": "access-sandbox-c257efd3-db6a-4905-a239-c379d6871dd2",
            "message": "Direct Plaid API call failed",
        }


@router.get("/test/decrypt-token")
def test_decrypt_token(encrypted_token: str):
    """Test endpoint to decrypt a token - REMOVE IN PRODUCTION."""
    try:
        from ..services.plaid_service import TokenEncryption

        decrypted_token = TokenEncryption.decrypt_token(encrypted_token)

        return {
            "encrypted_token": encrypted_token,
            "decrypted_token": decrypted_token,
            "warning": "This is a test endpoint - remove in production!",
        }
    except Exception as e:
        return {
            "error": str(e),
            "encrypted_token": encrypted_token,
            "message": "Failed to decrypt token",
        }


@router.get("/test/get-real-tokens")
def test_get_real_encrypted_tokens():
    """Test endpoint to get actual encrypted tokens from database - REMOVE IN PRODUCTION."""
    try:
        from ..database import firebase_client
        from ..services.plaid_service import TokenEncryption

        # Get active tokens from database
        tokens_ref = firebase_client.db.collection("plaid_tokens").limit(
            3
        )  # Get any tokens, not just active
        docs = list(tokens_ref.get())

        results = []
        for doc in docs:
            data = doc.to_dict()
            encrypted_token = data.get("encrypted_token")
            user_id = data.get("user_id")
            institution = data.get("institution_name")

            if encrypted_token:
                try:
                    decrypted_token = TokenEncryption.decrypt_token(encrypted_token)
                    results.append(
                        {
                            "user_id": user_id,
                            "institution": institution,
                            "encrypted_token": encrypted_token,
                            "decrypted_token": decrypted_token,
                            "decrypt_success": True,
                        }
                    )
                except Exception as decrypt_error:
                    results.append(
                        {
                            "user_id": user_id,
                            "institution": institution,
                            "encrypted_token": encrypted_token,
                            "decrypt_error": str(decrypt_error),
                            "decrypt_success": False,
                        }
                    )

        return {
            "results": results,
            "warning": "This exposes real access tokens - remove in production!",
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/test/users-with-tokens")
def test_list_users_with_tokens(
    plaid_service: PlaidService = Depends(get_plaid_service),
):
    """Test endpoint to list users who have Plaid access tokens - REMOVE IN PRODUCTION."""
    try:
        from ..database import firebase_client

        # Get all plaid tokens from the CORRECT collection
        tokens_ref = firebase_client.db.collection(
            "plaid_tokens"
        )  # Fixed: was 'plaid_access_tokens'
        docs = tokens_ref.get()

        user_tokens = {}
        for doc in docs:
            data = doc.to_dict()
            user_id = data.get("user_id")
            if user_id:
                if user_id not in user_tokens:
                    user_tokens[user_id] = []
                user_tokens[user_id].append(
                    {
                        "item_id": data.get("item_id"),
                        "institution_name": data.get("institution_name"),
                        "status": data.get("status"),
                    }
                )

        return {"users_with_tokens": user_tokens, "total_tokens": len(docs)}
    except Exception as e:
        return {"error": str(e)}
