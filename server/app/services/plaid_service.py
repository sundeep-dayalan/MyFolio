from typing import Tuple, List, Dict, Any, Optional
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_refresh_request import TransactionsRefreshRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.account_subtype import AccountSubtype
from plaid.model.credit_account_subtypes import CreditAccountSubtypes
from plaid.model.credit_account_subtype import CreditAccountSubtype
from plaid.model.link_token_account_filters import LinkTokenAccountFilters
from plaid.model.depository_filter import DepositoryFilter
from plaid.model.credit_filter import CreditFilter
from plaid.model.depository_account_subtype import DepositoryAccountSubtype
from plaid.model.depository_account_subtypes import DepositoryAccountSubtypes
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from datetime import datetime, timezone, timedelta
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config import settings
from ..database import cosmos_client
from ..utils.logger import get_logger
from ..models.plaid import (
    PlaidAccessToken,
    PlaidTokenStatus,
    PlaidEnvironment,
    PlaidAccountWithBalance,
    PlaidBalance,
)
from .account_storage_service import account_storage_service
from .transaction_storage_service import transaction_storage_service
import json
from datetime import date, datetime, timezone
from plaid.model.accounts_balance_get_request_options import (
    AccountsBalanceGetRequestOptions,
)

logger = get_logger(__name__)


class TokenEncryption:
    """Utility class for encrypting/decrypting sensitive tokens."""

    @staticmethod
    def _get_key() -> bytes:
        """Generate or retrieve encryption key from settings."""
        # In production, this should be from environment variable or key management service
        password = getattr(
            settings, "token_encryption_key", "default-key-change-in-production"
        ).encode()
        salt = b"plaid_tokens_salt"  # In production, use a random salt per token
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    @staticmethod
    def encrypt_token(token: str) -> str:
        """Encrypt a token for secure storage."""
        try:
            # f = Fernet(TokenEncryption._get_key())
            # encrypted_token = f.encrypt(token.encode())
            # return base64.urlsafe_b64encode(encrypted_token).decode()
            return token  # For now removing  encrpytion and decrypt
        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise Exception("Token encryption failed")

    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """Decrypt a token for use."""
        try:
            # f = Fernet(TokenEncryption._get_key())
            # decoded_token = base64.urlsafe_b64decode(encrypted_token.encode())
            # decrypted_token = f.decrypt(decoded_token)
            # return decrypted_token.decode()
            return encrypted_token  # For now removing  encrpytion and decrypt
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise Exception("Token decryption failed")


class PlaidService:
    """Production-ready service for interacting with the Plaid API."""

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
        self.environment = plaid_env

    def create_link_token(
        self,
        user_id: str,
        products: list = None,
        optional_products: list = None,
        required_if_supported_products: list = None,
        account_filters: dict = None,
        transactions_days_requested: int = 730,
    ) -> str:
        """Create a Plaid Link token for a user, supporting any Plaid product."""
        try:
            logger.info(
                f"Creating link token for user {user_id} in {self.environment} environment"
            )

            # Build request params dynamically
            request_params = {
                "products": [Products(p) for p in (products or ["transactions"])],
                "client_name": settings.project_name,
                "country_codes": [CountryCode("US")],
                "language": "en",
                "user": LinkTokenCreateRequestUser(client_user_id=user_id),
            }

            # Add optional products if provided
            if optional_products:
                request_params["optional_products"] = [
                    Products(p) for p in optional_products
                ]

            # Add required_if_supported_products if provided
            if required_if_supported_products:
                request_params["required_if_supported_products"] = [
                    Products(p) for p in required_if_supported_products
                ]

            # Add account filters if provided
            if account_filters:
                request_params["account_filters"] = self._build_account_filters(
                    account_filters
                )

            # Add transactions-specific configuration
            if "transactions" in (products or []):
                request_params["transactions"] = {
                    "days_requested": transactions_days_requested
                }

            request = LinkTokenCreateRequest(**request_params)

            response = self.client.link_token_create(request)
            link_token = response["link_token"]

            logger.info(f"Link token created successfully for user {user_id}")
            return link_token

        except Exception as e:
            logger.error(f"Failed to create link token for user {user_id}: {e}")
            raise Exception(f"Failed to create link token: {e}")

    def _build_account_filters(self, filters: dict) -> LinkTokenAccountFilters:
        """Build account filters for link token creation."""
        filter_params = {}

        # Build depository filters
        if "depository" in filters:
            depository_subtypes = [
                DepositoryAccountSubtype(subtype) for subtype in filters["depository"]
            ]
            filter_params["depository"] = DepositoryFilter(
                account_subtypes=DepositoryAccountSubtypes(depository_subtypes)
            )

        # Build credit filters
        if "credit" in filters:
            credit_subtypes = [
                CreditAccountSubtype(subtype) for subtype in filters["credit"]
            ]
            filter_params["credit"] = CreditFilter(
                account_subtypes=CreditAccountSubtypes(credit_subtypes)
            )

        return LinkTokenAccountFilters(**filter_params)

    def exchange_public_token(
        self, user_id: str, public_token: str
    ) -> PlaidAccessToken:
        """Exchange public token for access token and store it securely."""
        try:
            logger.info(f"Exchanging public token for user {user_id}")

            # Exchange public token for access token
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)

            access_token = response["access_token"]
            item_id = response["item_id"]

            # Get institution info
            institution_info = self._get_institution_info_by_item(access_token)

            # Store the access token
            stored_token = self._store_access_token(
                user_id, access_token, item_id, institution_info
            )

            logger.info(
                f"Successfully exchanged and stored token for user {user_id}, item_id: {item_id}"
            )
            return stored_token

        except Exception as e:
            logger.error(f"Failed to exchange public token for user {user_id}: {e}")
            raise Exception(f"Failed to exchange public token: {e}")

    def _get_institution_info_by_item(self, access_token: str) -> Dict[str, Any]:
        """Get institution information using item access token."""
        try:
            # Get item info first
            request = ItemGetRequest(access_token=access_token)
            item_response = self.client.item_get(request)
            institution_id = item_response["item"]["institution_id"]

            logger.info(f"Got institution_id: {institution_id}")

            # Get institution details
            inst_request = InstitutionsGetByIdRequest(
                institution_id=institution_id, country_codes=[CountryCode("US")]
            )
            inst_response = self.client.institutions_get_by_id(inst_request)
            institution = inst_response["institution"]

            institution_info = {
                "institution_id": institution_id,
                "name": institution["name"],
                "products": institution["products"],
                "country_codes": institution["country_codes"],
            }

            logger.info(f"Retrieved institution info: {institution['name']}")
            return institution_info

        except Exception as e:
            logger.error(f"Failed to get institution info: {e}")
            # Return minimal info as fallback
            try:
                request = ItemGetRequest(access_token=access_token)
                item_response = self.client.item_get(request)
                institution_id = item_response["item"]["institution_id"]
                return {
                    "institution_id": institution_id,
                    "name": f"Bank {institution_id}",
                }
            except Exception as e2:
                logger.error(f"Failed to get even basic institution info: {e2}")
                return {"institution_id": None, "name": "Unknown Bank"}

    def _store_access_token(
        self,
        user_id: str,
        access_token: str,
        item_id: str,
        institution_info: Dict[str, Any] = None,
    ) -> PlaidAccessToken:
        """Store access token in CosmosDB."""
        try:
            logger.info(f"Storing access token for user {user_id}, item_id: {item_id}")

            # Check if CosmosDB is connected
            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot store tokens")
                raise Exception("CosmosDB connection required for token storage")

            # Encrypt the access token for production storage
            encrypted_token = TokenEncryption.encrypt_token(access_token)

            # Create PlaidAccessToken model
            now = datetime.now(timezone.utc)
            institution_info = institution_info or {}
            
            # Clean metadata - convert any enum objects to strings
            clean_metadata = {}
            for key, value in institution_info.items():
                if hasattr(value, 'value'):  # Enum object
                    clean_metadata[key] = value.value
                elif isinstance(value, list):
                    clean_metadata[key] = [item.value if hasattr(item, 'value') else item for item in value]
                else:
                    clean_metadata[key] = value

            plaid_token = PlaidAccessToken(
                user_id=user_id,
                access_token=encrypted_token,
                item_id=item_id,
                institution_id=institution_info.get("institution_id"),
                institution_name=institution_info.get("name"),
                status=PlaidTokenStatus.ACTIVE,
                environment=PlaidEnvironment(self.environment),
                created_at=now,
                updated_at=now,
                last_used_at=now,
                metadata=clean_metadata,  # Store cleaned institution info in metadata
            )

            # Store the plaid token as individual document in CosmosDB
            # Use model_dump with mode='json' to properly serialize all types including enums and datetime
            token_data = plaid_token.model_dump(mode='json')
                
            token_data.update(
                {
                    "id": f"{user_id}_{item_id}",  # Unique document ID
                    "userId": user_id,  # Partition key
                    "item_id": item_id,
                    "transactions": {"transaction_sync_status": "inprogress"},
                }
            )

            # Try to store the token document, update if exists
            try:
                cosmos_client.create_item("plaid_tokens", token_data, user_id)
            except CosmosHttpResponseError as e:
                if e.status_code == 409:  # Conflict - document exists, update it
                    cosmos_client.update_item(
                        "plaid_tokens", token_data["id"], user_id, token_data
                    )
                else:
                    raise

            logger.info(
                f"Successfully stored token for user {user_id}, item_id: {item_id}"
            )
            return plaid_token

        except Exception as e:
            logger.error(f"Failed to store access token for user {user_id}: {e}")
            raise Exception(f"Failed to store access token: {e}")

    def get_user_access_tokens(self, user_id: str) -> List[PlaidAccessToken]:
        """Retrieve all active access tokens for a user from CosmosDB."""
        try:
            logger.info(f"Retrieving access tokens for user {user_id}")

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot retrieve tokens")
                raise Exception("CosmosDB connection required for token retrieval")

            # Query all plaid tokens for the user
            query = "SELECT * FROM c WHERE c.userId = @userId AND c.status = @status"
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@status", "value": PlaidTokenStatus.ACTIVE.value},
            ]

            token_documents = cosmos_client.query_items(
                "plaid_tokens", query, parameters, user_id
            )
            tokens = []

            for token_doc in token_documents:
                try:
                    # Convert datetime strings back to datetime objects if needed
                    for field in ["created_at", "updated_at", "last_used_at"]:
                        if token_doc.get(field) and isinstance(token_doc[field], str):
                            token_doc[field] = datetime.fromisoformat(
                                token_doc[field].replace("Z", "+00:00")
                            )

                    token = PlaidAccessToken.model_validate(token_doc)
                    tokens.append(token)
                except Exception as e:
                    logger.error(
                        f"Failed to parse token data for document {token_doc.get('id', 'unknown')}: {e}"
                    )
                    continue  # Skip to the next item if one is corrupted

            logger.info(f"Found {len(tokens)} active tokens for user {user_id}")
            return tokens

        except Exception as e:
            logger.error(f"Failed to retrieve access tokens for user {user_id}: {e}")
            raise Exception(f"Failed to retrieve access tokens: {e}")

    def get_accounts_with_balances(
        self,
        user_id: str,
        account_ids: Optional[List[str]] = None,
        use_cached_balance: bool = True,
        max_cache_age_hours: int = 4,
    ) -> Dict[str, Any]:
        """
        If use_cached_balance is True, fetch account data from Cosmos DB only.
        If use_cached_balance is False, fetch from Plaid API, update Cosmos DB, and return latest.
        """
        try:
            logger.info(f"Getting accounts with balances for user {user_id}, use_cached_balance={use_cached_balance}")

            if use_cached_balance:
                # Only fetch from Cosmos DB
                cached_data = account_storage_service.get_stored_account_data(user_id)
                if cached_data:
                    logger.info(f"Returning cached account data for user {user_id}")
                    return cached_data
                else:
                    logger.warning(f"No cached account data found for user {user_id}")
                    return {
                        "accounts": [],
                        "total_balance": 0.0,
                        "account_count": 0,
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "message": "No cached account data found. Please refresh."
                    }

            # If not using cached balance, fetch from Plaid and update Cosmos DB
            tokens = self.get_user_access_tokens(user_id)
            if not tokens:
                logger.warning(f"No active tokens found for user {user_id}")
                return {
                    "accounts": [],
                    "total_balance": 0.0,
                    "account_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

            all_accounts = []
            total_balance = 0.0

            for token in tokens:
                try:
                    decrypted_token = TokenEncryption.decrypt_token(token.access_token)
                    if account_ids:
                        options = AccountsBalanceGetRequestOptions(account_ids=account_ids)
                        request = AccountsBalanceGetRequest(access_token=decrypted_token, options=options)
                    else:
                        request = AccountsBalanceGetRequest(access_token=decrypted_token)
                    response = self.client.accounts_balance_get(request)
                    accounts_data = response["accounts"]
                    for account in accounts_data:
                        balance_info = account["balances"]
                        balance = PlaidBalance(
                            available=balance_info.get("available"),
                            current=balance_info.get("current", 0),
                            limit=balance_info.get("limit"),
                            iso_currency_code=balance_info.get("iso_currency_code", "USD"),
                            unofficial_currency_code=balance_info.get("unofficial_currency_code"),
                        )
                        account_type = account["type"].value if hasattr(account["type"], 'value') else account["type"]
                        account_subtype = account.get("subtype")
                        if account_subtype and hasattr(account_subtype, 'value'):
                            account_subtype = account_subtype.value
                        account_with_balance = PlaidAccountWithBalance(
                            account_id=account["account_id"],
                            name=account["name"],
                            official_name=account.get("official_name"),
                            type=account_type,
                            subtype=account_subtype,
                            mask=account.get("mask"),
                            balances=balance,
                            item_id=token.item_id,
                            institution_name=token.institution_name,
                            institution_id=token.institution_id,
                        )
                        all_accounts.append(account_with_balance.model_dump())
                        if balance.current:
                            total_balance += float(balance.current)
                    self._update_token_last_used(user_id, token.item_id)
                except Exception as e:
                    logger.error(f"Failed to get balances for token {token.item_id}: {e}")
                    continue
            all_accounts.sort(key=lambda x: x["balances"]["current"] or 0, reverse=True)
            result = {
                "accounts": all_accounts,
                "total_balance": round(total_balance, 2),
                "account_count": len(all_accounts),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            # Store the result in Cosmos DB
            account_storage_service.store_account_data(user_id, result)
            logger.info(f"Retrieved {len(all_accounts)} accounts with total balance ${total_balance:.2f} for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get accounts with balances for user {user_id}: {e}")
            raise Exception(f"Failed to get account balances: {e}")

    def _update_token_last_used(self, user_id: str, item_id: str) -> bool:
        """Update the last_used_at timestamp for a token."""
        try:
            doc_id = f"{user_id}_{item_id}"
            update_data = {
                "last_used_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            cosmos_client.update_item("plaid_tokens", doc_id, user_id, update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update token last_used for {item_id}: {e}")
            return False

    def revoke_item_access(self, user_id: str, item_id: str) -> bool:
        """Revoke access to a Plaid item and remove from database."""
        try:
            logger.info(f"Revoking access for user {user_id}, item {item_id}")

            # Get the token first
            tokens = self.get_user_access_tokens(user_id)
            token_to_revoke = None

            for token in tokens:
                if token.item_id == item_id:
                    token_to_revoke = token
                    break

            if not token_to_revoke:
                logger.warning(f"Token not found for item {item_id}")
                return False

            # Revoke with Plaid API
            decrypted_token = TokenEncryption.decrypt_token(
                token_to_revoke.access_token
            )
            request = ItemRemoveRequest(access_token=decrypted_token)

            try:
                self.client.item_remove(request)
                logger.info(f"Successfully revoked Plaid access for item {item_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to revoke with Plaid API: {e}, continuing with local cleanup"
                )

            # Remove token from CosmosDB
            doc_id = f"{user_id}_{item_id}"
            cosmos_client.delete_item("plaid_tokens", doc_id, user_id)

            # Clean up related data
            account_storage_service.clear_data(user_id)
            transaction_storage_service.delete_item_transactions(user_id, item_id)

            logger.info(f"Successfully cleaned up all data for item {item_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke item access for {item_id}: {e}")
            return False

    def remove_all_user_data(self, user_id: str) -> bool:
        """Remove all Plaid data for a user from both Plaid API and local storage."""
        try:
            logger.info(f"Removing all Plaid data for user {user_id}")

            # Get all user tokens
            tokens = self.get_user_access_tokens(user_id)

            if not tokens:
                logger.info(f"No tokens found for user {user_id}")
                return True

            success_count = 0
            for token in tokens:
                try:
                    # Revoke each item
                    if self.revoke_item_access(user_id, token.item_id):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to revoke item {token.item_id}: {e}")

            # Clean up any remaining data
            account_storage_service.clear_data(user_id)
            transaction_storage_service.delete_all_user_transactions(user_id)

            logger.info(
                f"Removed {success_count}/{len(tokens)} items for user {user_id}"
            )
            return success_count == len(tokens)

        except Exception as e:
            logger.error(f"Failed to remove all user data for {user_id}: {e}")
            return False

    def update_transaction_sync_status(
        self, user_id: str, item_id: str, status: str
    ) -> bool:
        """Update transaction sync status for an item."""
        try:
            doc_id = f"{user_id}_{item_id}"
            update_data = {
                "transactions.transaction_sync_status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            cosmos_client.update_item("plaid_tokens", doc_id, user_id, update_data)
            logger.info(f"Updated sync status to '{status}' for item {item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update sync status for {item_id}: {e}")
            return False

    def sync_all_transactions_for_item(
        self, user_id: str, item_id: str, access_token: str
    ) -> Dict[str, Any]:
        """Initial full sync of transactions for a newly connected item."""
        try:
            logger.info(f"Starting initial transaction sync for item {item_id}")
            
            # Update status to in progress
            self.update_transaction_sync_status(user_id, item_id, "syncing")

            # Use transactions/sync for initial historical data
            cursor = None
            added_count = 0
            modified_count = 0
            removed_count = 0
            
            while True:
                # Create request - omit cursor for initial sync when None
                if cursor is not None:
                    request = TransactionsSyncRequest(
                        access_token=access_token,
                        cursor=cursor
                    )
                else:
                    request = TransactionsSyncRequest(
                        access_token=access_token
                    )
                
                response = self.client.transactions_sync(request)
                
                # Process transactions
                added = response.get('added', [])
                modified = response.get('modified', [])
                removed = response.get('removed', [])
                
                if added:
                    # Store added transactions
                    transaction_storage_service.store_transactions(
                        user_id, item_id, added, "added"
                    )
                    added_count += len(added)
                
                if modified:
                    # Store modified transactions
                    transaction_storage_service.store_transactions(
                        user_id, item_id, modified, "modified"
                    )
                    modified_count += len(modified)
                
                if removed:
                    # Handle removed transactions
                    transaction_storage_service.handle_removed_transactions(
                        user_id, item_id, removed
                    )
                    removed_count += len(removed)
                
                cursor = response.get('next_cursor')
                has_more = response.get('has_more', False)
                
                if not has_more:
                    break
            
            # Update sync status to complete
            self.update_transaction_sync_status(user_id, item_id, "completed")
            
            result = {
                "success": True,
                "item_id": item_id,
                "added": added_count,
                "modified": modified_count,
                "removed": removed_count,
                "total": added_count + modified_count + removed_count
            }
            
            logger.info(f"Completed initial sync for {item_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync transactions for {item_id}: {e}")
            self.update_transaction_sync_status(user_id, item_id, "error")
            raise Exception(f"Transaction sync failed: {e}")

    def refresh_transactions(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Refresh transactions for a specific item using sync API."""
        try:
            logger.info(f"Refreshing transactions for item {item_id}")
            
            # Get token for this item
            tokens = self.get_user_access_tokens(user_id)
            target_token = None
            
            for token in tokens:
                if token.item_id == item_id:
                    target_token = token
                    break
            
            if not target_token:
                raise Exception(f"No token found for item {item_id}")
            
            # Decrypt token
            access_token = TokenEncryption.decrypt_token(target_token.access_token)
            
            # Get cursor from last sync
            cursor = transaction_storage_service.get_last_sync_cursor(user_id, item_id)
            
            # Create request - omit cursor if None
            if cursor is not None:
                request = TransactionsSyncRequest(
                    access_token=access_token,
                    cursor=cursor
                )
            else:
                request = TransactionsSyncRequest(
                    access_token=access_token
                )
            
            response = self.client.transactions_sync(request)
            
            # Process new transactions
            added = response.get('added', [])
            modified = response.get('modified', [])
            removed = response.get('removed', [])
            
            added_count = 0
            modified_count = 0
            removed_count = 0
            
            if added:
                transaction_storage_service.store_transactions(
                    user_id, item_id, added, "added"
                )
                added_count = len(added)
            
            if modified:
                transaction_storage_service.store_transactions(
                    user_id, item_id, modified, "modified"
                )
                modified_count = len(modified)
            
            if removed:
                transaction_storage_service.handle_removed_transactions(
                    user_id, item_id, removed
                )
                removed_count = len(removed)
            
            # Update cursor for next sync
            new_cursor = response.get('next_cursor')
            if new_cursor:
                transaction_storage_service.update_sync_cursor(user_id, item_id, new_cursor)
            
            result = {
                "success": True,
                "transactions_added": added_count,
                "transactions_modified": modified_count,
                "transactions_removed": removed_count,
                "total_processed": added_count + modified_count + removed_count,
                "item_id": item_id,
                "institution_name": target_token.institution_name or "Unknown",
                "message": f"Refreshed {added_count + modified_count + removed_count} transactions"
            }
            
            logger.info(f"Transaction refresh completed for {item_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to refresh transactions for {item_id}: {e}")
            raise Exception(f"Transaction refresh failed: {e}")

    def force_refresh_transactions(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Force refresh by clearing all data and performing complete resync."""
        try:
            logger.info(f"Force refreshing transactions for item {item_id}")
            
            # Get token for this item
            tokens = self.get_user_access_tokens(user_id)
            target_token = None
            
            for token in tokens:
                if token.item_id == item_id:
                    target_token = token
                    break
            
            if not target_token:
                raise Exception(f"No token found for item {item_id}")
            
            # Clear existing transaction data
            transaction_storage_service.clear_item_transactions(user_id, item_id)
            
            # Decrypt token
            access_token = TokenEncryption.decrypt_token(target_token.access_token)
            
            # Perform complete resync
            sync_result = self.sync_all_transactions_for_item(user_id, item_id, access_token)
            
            result = {
                "success": True,
                "message": f"Force refresh completed - synced {sync_result['total']} transactions",
                "item_id": item_id,
                "institution_name": target_token.institution_name or "Unknown",
                "status": "completed",
                "async_operation": False
            }
            
            logger.info(f"Force refresh completed for {item_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to force refresh transactions for {item_id}: {e}")
            raise Exception(f"Force refresh failed: {e}")

    def get_transactions(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get transactions for user across all accounts."""
        try:
            logger.info(f"Getting transactions for user {user_id} - last {days} days")
            
            # Get transactions from storage
            transactions = transaction_storage_service.get_user_transactions(
                user_id, days=days
            )
            
            result = {
                "transactions": transactions,
                "total_count": len(transactions),
                "days_requested": days
            }
            
            logger.info(f"Retrieved {len(transactions)} transactions for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get transactions for user {user_id}: {e}")
            raise Exception(f"Failed to get transactions: {e}")

    def get_transactions_by_account(
        self, user_id: str, account_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get transactions for a specific account."""
        try:
            logger.info(f"Getting transactions for account {account_id} - last {days} days")
            
            # Get transactions from storage for specific account
            transactions = transaction_storage_service.get_account_transactions(
                user_id, account_id, days=days
            )
            
            result = {
                "transactions": transactions,
                "account_id": account_id,
                "total_count": len(transactions),
                "days_requested": days
            }
            
            logger.info(f"Retrieved {len(transactions)} transactions for account {account_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get transactions for account {account_id}: {e}")
            raise Exception(f"Failed to get account transactions: {e}")

    def get_user_plaid_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get summary of user's connected Plaid items."""
        try:
            tokens = self.get_user_access_tokens(user_id)
            items = []
            
            for token in tokens:
                # Get account count for this item
                accounts = account_storage_service.get_user_accounts(user_id)
                item_accounts = [acc for acc in accounts if acc.get('item_id') == token.item_id]
                
                items.append({
                    "item_id": token.item_id,
                    "institution_id": token.institution_id,
                    "institution_name": token.institution_name or "Unknown",
                    "status": token.status,
                    "accounts_count": len(item_accounts),
                    "created_at": token.created_at,
                    "last_used_at": token.last_used_at
                })
            
            logger.info(f"Retrieved {len(items)} Plaid items for user {user_id}")
            return items
            
        except Exception as e:
            logger.error(f"Failed to get Plaid items for user {user_id}: {e}")
            raise Exception(f"Failed to get Plaid items: {e}")

    def _sync_transactions_for_stored_item(self, user_id: str, item_id: str) -> None:
        """Background task to sync transactions for a newly stored item."""
        try:
            logger.info(f"🚀 BACKGROUND TASK STARTED: Transaction sync for user {user_id}, item {item_id}")
            
            # Get the token from storage
            tokens = self.get_user_access_tokens(user_id)
            logger.info(f"Retrieved {len(tokens)} tokens for user {user_id}")
            
            target_token = None
            for token in tokens:
                if token.item_id == item_id:
                    target_token = token
                    break
            
            if not target_token:
                logger.error(f"❌ No stored token found for item {item_id}")
                return
            
            logger.info(f"✅ Found target token for item {item_id}")
            
            # Decrypt the access token
            access_token = TokenEncryption.decrypt_token(target_token.access_token)
            logger.info(f"✅ Successfully decrypted access token for item {item_id}")
            
            # Perform the sync
            result = self.sync_all_transactions_for_item(user_id, item_id, access_token)
            logger.info(f"🎉 Background transaction sync completed for item {item_id}: {result}")
            
        except Exception as e:
            logger.error(f"❌ Background transaction sync failed for item {item_id}: {e}", exc_info=True)
            self.update_transaction_sync_status(user_id, item_id, "error")
