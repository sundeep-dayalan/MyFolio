from typing import Tuple, List, Dict, Any, Optional
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from firebase_admin import firestore
from ..config import settings
from ..database import firebase_client
from ..utils.logger import get_logger
import json

logger = get_logger(__name__)


class PlaidService:
    """Service for interacting with the Plaid API using the official Python SDK."""
    
    # Class-level variable to store tokens across instances
    _dev_tokens_storage = {}

    def __init__(self):
        # Configure Plaid client
        from plaid.configuration import Configuration, Environment

        # Map environment string to Plaid Environment enum
        environment_map = {
            "sandbox": Environment.Sandbox,
            "development": Environment.Sandbox,  # Use sandbox for development
            "production": Environment.Production,
        }

        plaid_env = getattr(settings, "plaid_env", "sandbox").lower()
        environment = environment_map.get(plaid_env, Environment.Sandbox)

        config = Configuration(
            host=environment,
            api_key={
                "clientId": settings.plaid_client_id,
                "secret": settings.plaid_secret,
            },
        )
        api_client = ApiClient(config)
        self.client = plaid_api.PlaidApi(api_client)

    def create_link_token(self, user_id: str) -> str:
        """Create a Plaid Link token for a user."""
        try:
            # Create the basic request without webhook for now
            request_params = {
                "products": [Products("auth"), Products("transactions")],
                "client_name": settings.project_name,
                "country_codes": [CountryCode("US")],
                "language": "en",
                "user": LinkTokenCreateRequestUser(client_user_id=user_id),
            }
            
            # Only add webhook if it's explicitly set in settings
            if hasattr(settings, 'plaid_webhook') and settings.plaid_webhook:
                request_params["webhook"] = settings.plaid_webhook
            
            request = LinkTokenCreateRequest(**request_params)
            response = self.client.link_token_create(request)
            logger.info(f"Created link token for user {user_id}")
            return response["link_token"]

        except Exception as e:
            logger.error(f"Failed to create link token: {e}")
            raise Exception(f"Failed to create Plaid link token: {e}")

    def exchange_public_token(self, public_token: str, user_id: str) -> Dict[str, Any]:
        """Exchange a public token for an access token and item ID, then store securely."""
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)

            access_token = response["access_token"]
            item_id = response["item_id"]

            # Store the access token securely in Firestore
            self._store_access_token(user_id, access_token, item_id)

            logger.info(f"Successfully exchanged token and stored for user {user_id}")
            return {"success": True, "item_id": item_id}

        except Exception as e:
            logger.error(f"Failed to exchange public token: {e}")
            raise Exception(f"Failed to exchange public token: {e}")

    def _store_access_token(self, user_id: str, access_token: str, item_id: str):
        """Securely store access token in Firestore or development storage."""
        try:
            logger.info(f"Storing access token for user {user_id}, item_id: {item_id}")

            # Check if Firebase is connected
            if not firebase_client.is_connected:
                logger.warning(
                    "Firebase not connected, storing in memory for development"
                )
                # For development, store in class-level dict
                if user_id not in PlaidService._dev_tokens_storage:
                    PlaidService._dev_tokens_storage[user_id] = []
                
                PlaidService._dev_tokens_storage[user_id].append({
                    "access_token": access_token,
                    "item_id": item_id,
                    "user_id": user_id,
                })
                logger.info(f"Stored token in class-level memory for user {user_id}, total tokens: {len(PlaidService._dev_tokens_storage[user_id])}")
                return

            # Store in a secure collection
            plaid_data = {
                "access_token": access_token,
                "item_id": item_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "user_id": user_id,
            }

            # Use item_id as document ID for easy retrieval
            doc_ref = firebase_client.db.collection("plaid_tokens").document(item_id)
            doc_ref.set(plaid_data)

            logger.info(f"Stored Plaid token for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to store access token: {e}")
            # Fallback to development storage if Firestore fails
            logger.warning("Firestore failed, falling back to development storage")
            if user_id not in PlaidService._dev_tokens_storage:
                PlaidService._dev_tokens_storage[user_id] = []
            
            PlaidService._dev_tokens_storage[user_id].append({
                "access_token": access_token,
                "item_id": item_id,
                "user_id": user_id,
            })
            logger.info(f"Stored token in class-level development storage for user {user_id}, total tokens: {len(PlaidService._dev_tokens_storage[user_id])}")

    def get_user_access_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all access tokens for a user."""
        try:
            logger.info(f"Retrieving access tokens for user {user_id}")

            # Check for development storage first
            if user_id in PlaidService._dev_tokens_storage:
                logger.info(
                    f"Found {len(PlaidService._dev_tokens_storage[user_id])} tokens in class-level development storage"
                )
                return PlaidService._dev_tokens_storage[user_id]

            # Check if Firebase is connected
            if not firebase_client.is_connected:
                logger.warning(
                    "Firebase not connected and no dev tokens, returning empty token list"
                )
                return []

            # Try to get from Firestore
            query = firebase_client.db.collection("plaid_tokens").where(
                "user_id", "==", user_id
            )
            docs = query.stream()

            tokens = []
            for doc in docs:
                data = doc.to_dict()
                tokens.append(
                    {
                        "item_id": doc.id,
                        "access_token": data.get("access_token"),
                        "created_at": data.get("created_at"),
                        "user_id": user_id,
                    }
                )

            logger.info(f"Found {len(tokens)} tokens in Firestore for user {user_id}")
            return tokens

        except Exception as e:
            logger.error(f"Failed to retrieve access tokens for user {user_id}: {e}")

            # If Firestore fails, check for development storage as fallback
            if user_id in PlaidService._dev_tokens_storage:
                logger.info(
                    f"Firestore failed, but found {len(PlaidService._dev_tokens_storage[user_id])} tokens in class-level development storage"
                )
                return PlaidService._dev_tokens_storage[user_id]

            logger.warning("No access tokens found anywhere for user")
            return []

    def get_accounts_balance(self, user_id: str) -> Dict[str, Any]:
        """Retrieve account balances for all user's connected accounts."""
        try:
            logger.info(f"Getting accounts balance for user: {user_id}")
            tokens = self.get_user_access_tokens(user_id)

            if not tokens:
                logger.info(f"No tokens found for user {user_id}")
                return {"accounts": [], "total_balance": 0.0}

            logger.info(f"Found {len(tokens)} tokens for user {user_id}")
            all_accounts = []
            total_balance = 0.0

            for i, token_data in enumerate(tokens):
                logger.info(f"Processing token {i+1}/{len(tokens)} for user {user_id}")
                access_token = token_data["access_token"]
                accounts = self._get_balance_for_token(access_token)
                logger.info(f"Token {i+1} returned {len(accounts)} accounts")

                for account in accounts:
                    # Calculate total balance
                    balance = account.get("balances", {}).get("current", 0) or 0
                    total_balance += balance
                    all_accounts.append(account)
                    logger.info(
                        f"Account: {account.get('name', 'Unknown')} - Balance: ${balance}"
                    )

            logger.info(
                f"Total: {len(all_accounts)} accounts, ${total_balance} total balance for user {user_id}"
            )

            return {
                "accounts": all_accounts,
                "total_balance": float(total_balance),
                "account_count": int(len(all_accounts)),
            }

        except Exception as e:
            logger.error(f"Failed to get accounts balance: {e}")
            raise Exception(f"Failed to retrieve account balances: {e}")

    def _get_balance_for_token(self, access_token: str) -> List[Dict[str, Any]]:
        """Retrieve account balances for a specific access token."""
        try:
            request = AccountsBalanceGetRequest(access_token=access_token)
            response = self.client.accounts_balance_get(request)
            
            # Convert Plaid response to serializable format
            accounts = []
            raw_accounts = response["accounts"]
            
            for account in raw_accounts:
                # Extract all data as basic Python types to ensure JSON serializability
                balances = account.get("balances", {})
                
                clean_account = {
                    "account_id": str(account.get("account_id", "")),
                    "name": str(account.get("name", "")),
                    "type": str(account.get("type", "")),
                    "subtype": str(account.get("subtype", "")) if account.get("subtype") else None,
                    "balances": {
                        "available": float(balances.get("available")) if balances.get("available") is not None else None,
                        "current": float(balances.get("current")) if balances.get("current") is not None else None,
                        "limit": float(balances.get("limit")) if balances.get("limit") is not None else None,
                        "iso_currency_code": str(balances.get("iso_currency_code", "")) if balances.get("iso_currency_code") else None,
                        "unofficial_currency_code": str(balances.get("unofficial_currency_code", "")) if balances.get("unofficial_currency_code") else None,
                    },
                    "mask": str(account.get("mask", "")) if account.get("mask") else None,
                    "official_name": str(account.get("official_name", "")) if account.get("official_name") else None,
                }
                accounts.append(clean_account)
            
            return accounts

        except Exception as e:
            logger.error(f"Failed to get balance for token: {e}")
            # Don't raise here, just return empty list to continue with other tokens
            return []
