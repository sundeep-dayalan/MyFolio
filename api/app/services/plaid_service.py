from typing import Tuple, List, Dict, Any, Optional
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from firebase_admin import firestore
from datetime import datetime, timezone, timedelta
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config import settings
from ..database import firebase_client
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

    def create_link_token(self, user_id: str) -> str:
        """Create a Plaid Link token for a user."""
        try:
            logger.info(
                f"Creating link token for user {user_id} in {self.environment} environment"
            )

            # Create the basic request
            request_params = {
                "products": [Products("auth"), Products("transactions")],
                "client_name": settings.project_name,
                "country_codes": [CountryCode("US")],
                "language": "en",
                "user": LinkTokenCreateRequestUser(client_user_id=user_id),
            }

            # Only add webhook if it's explicitly set in settings
            if hasattr(settings, "plaid_webhook") and settings.plaid_webhook:
                request_params["webhook"] = settings.plaid_webhook

            request = LinkTokenCreateRequest(**request_params)
            response = self.client.link_token_create(request)

            logger.info(f"Successfully created link token for user {user_id}")
            return response["link_token"]

        except Exception as e:
            logger.error(f"Failed to create link token for user {user_id}: {e}")
            raise Exception(f"Failed to create Plaid link token: {e}")

    def exchange_public_token(self, public_token: str, user_id: str) -> Dict[str, Any]:
        """Exchange a public token for an access token and item ID, then store securely."""
        try:
            logger.info(f"Exchanging public token for user {user_id}")

            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)

            access_token = response["access_token"]
            item_id = response["item_id"]

            # Get institution information
            institution_info = self._get_institution_info(access_token)

            # Store the access token securely in Firestore with institution info
            stored_token = self._store_access_token(
                user_id, access_token, item_id, institution_info
            )

            logger.info(
                f"Successfully exchanged and stored token for user {user_id}, item_id: {item_id}, institution: {institution_info.get('name', 'Unknown')}"
            )

            # Automatically fetch and store account data after successful token exchange
            try:
                logger.info(
                    f"Fetching initial account data after token exchange for user {user_id}"
                )
                account_data = self.get_accounts_balance(user_id)
                logger.info(
                    f"Successfully fetched and stored {account_data.get('account_count', 0)} accounts after token exchange"
                )
            except Exception as account_error:
                logger.error(
                    f"Failed to fetch account data after token exchange for user {user_id}: {account_error}"
                )
                # Don't fail the entire exchange if account fetch fails

            return {
                "success": True,
                "item_id": item_id,
                "token_id": stored_token.item_id,
                "institution_name": institution_info.get("name"),
                "access_token": access_token,  # Return for background task use
            }

        except Exception as e:
            logger.error(f"Failed to exchange public token for user {user_id}: {e}")
            raise Exception(f"Failed to exchange public token: {e}")

    def _get_institution_info(self, access_token: str) -> Dict[str, Any]:
        """Get institution information for an access token."""
        try:
            # First get the item to get institution_id
            item_request = ItemGetRequest(access_token=access_token)
            item_response = self.client.item_get(item_request)
            institution_id = item_response["item"]["institution_id"]

            logger.info(f"Got institution_id: {institution_id}")

            # Then get institution details
            institution_request = InstitutionsGetByIdRequest(
                institution_id=institution_id, country_codes=[CountryCode("US")]
            )
            institution_response = self.client.institutions_get_by_id(
                institution_request
            )
            institution = institution_response["institution"]

            institution_info = {
                "institution_id": institution_id,
                "name": institution.get("name", "Unknown Bank"),
                "url": institution.get("url"),
                "primary_color": institution.get("primary_color"),
                "logo": institution.get("logo"),
            }

            logger.info(f"Retrieved institution info: {institution_info['name']}")
            return institution_info

        except Exception as e:
            logger.warning(f"Failed to get institution info: {e}")
            # Return minimal info if we can't get details
            try:
                # Try to at least get the institution_id from item
                item_request = ItemGetRequest(access_token=access_token)
                item_response = self.client.item_get(item_request)
                institution_id = item_response["item"]["institution_id"]
                logger.info(f"At least got institution_id: {institution_id}")
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
        try:
            logger.info(f"Storing access token for user {user_id}, item_id: {item_id}")

            # Check if Firebase is connected
            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot store tokens")
                raise Exception("Firebase connection required for token storage")

            # Encrypt the access token for production storage
            encrypted_token = TokenEncryption.encrypt_token(access_token)

            # Create PlaidAccessToken model
            now = datetime.now(timezone.utc)
            institution_info = institution_info or {}

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
                metadata=institution_info,  # Store full institution info in metadata
            )

            # Get the document reference for the user
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)

            # This data structure will be merged with the existing document.
            # It contains an 'items' map with the new item to add.
            update_data = {"items": {item_id: plaid_token.model_dump()}}

            # For long-running sync, we can set a placeholder for transaction sync status
            update_data["items"][item_id]["transaction_sync_status"] = "inprogress"

            # Use merge=True to add the new item to the existing items map
            # without deleting previously stored bank tokens
            doc_ref.set(update_data, merge=True)

            logger.info(
                f"Successfully stored token for user {user_id}, item_id: {item_id}, preserving existing tokens"
            )
            return plaid_token

        except Exception as e:
            logger.error(f"Failed to store access token for user {user_id}: {e}")
            raise Exception(f"Failed to store access token: {e}")

    def get_user_access_tokens(self, user_id: str) -> List[PlaidAccessToken]:
        """Retrieve all active access tokens for a user from their document."""
        try:
            logger.info(f"Retrieving access tokens for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot retrieve tokens")
                raise Exception("Firebase connection required for token retrieval")

            # 1. Get the specific document for the user
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(f"No token document found for user {user_id}")
                return []

            # 2. Extract the 'items' map from the document
            user_data = doc.to_dict()
            items_map = user_data.get("items", {})  # Get the map, default to empty dict
            tokens = []

            # 3. Iterate through the items in the map
            for item_id, item_data in items_map.items():
                try:
                    # 4. Filter for active tokens inside the loop
                    if item_data.get("status") != PlaidTokenStatus.ACTIVE.value:
                        continue

                    # Convert Firestore timestamps to datetime objects
                    # (This is good practice, assuming these fields exist)
                    if item_data.get("created_at"):
                        item_data["created_at"] = item_data["created_at"].replace(
                            tzinfo=timezone.utc
                        )
                    if item_data.get("updated_at"):
                        item_data["updated_at"] = item_data["updated_at"].replace(
                            tzinfo=timezone.utc
                        )
                    if item_data.get("last_used_at"):
                        item_data["last_used_at"] = item_data["last_used_at"].replace(
                            tzinfo=timezone.utc
                        )

                    token = PlaidAccessToken.model_validate(item_data)
                    tokens.append(token)
                except Exception as e:
                    logger.error(
                        f"Failed to parse token data for item_id {item_id}: {e}"
                    )
                    continue  # Skip to the next item if one is corrupted

            logger.info(
                f"Found {len(tokens)} active tokens in document for user {user_id}"
            )
            return tokens

        except Exception as e:
            logger.error(f"Failed to retrieve access tokens for user {user_id}: {e}")
            raise Exception(f"Failed to retrieve access tokens: {e}")

    def get_accounts_balance(self, user_id: str) -> Dict[str, Any]:
        """Retrieve account balances for all user's connected accounts."""
        try:
            logger.info(f"Getting accounts balance for user {user_id}")
            tokens = self.get_user_access_tokens(user_id)

            if not tokens:
                logger.info(f"No active tokens found for user {user_id}")
                return {"accounts": [], "total_balance": 0.0, "account_count": 0}

            logger.info(f"Found {len(tokens)} active tokens for user {user_id}")
            all_accounts = []
            total_balance = 0.0

            for i, token in enumerate(tokens):
                try:
                    logger.info(
                        f"Processing token {i+1}/{len(tokens)} for user {user_id}"
                    )

                    # Decrypt the access token (tokens are always encrypted in Firestore)
                    decrypted_token = TokenEncryption.decrypt_token(token.access_token)

                    # If token doesn't have institution info, fetch it now
                    institution_name = token.institution_name
                    institution_id = token.institution_id

                    if not institution_name or not institution_id:
                        logger.info(
                            f"Fetching missing institution info for token {token.item_id}"
                        )
                        institution_info = self._get_institution_info(decrypted_token)
                        institution_name = institution_info.get("name")
                        institution_id = institution_info.get("institution_id")

                        # Update the token in database with institution info
                        if institution_name:
                            self._update_token_institution_info(
                                token.item_id, institution_info
                            )

                    # Get accounts for this token
                    accounts = self._get_balance_for_token(
                        decrypted_token, institution_name, institution_id
                    )
                    logger.info(f"Token {i+1} returned {len(accounts)} accounts")

                    # Mark token as used
                    self.mark_token_as_used(user_id, token.item_id)

                    for account in accounts:
                        # Calculate total balance
                        balance = account.balances.current or 0
                        total_balance += balance
                        all_accounts.append(account)
                        logger.info(f"Account: {account.name} - Balance: ${balance}")

                except Exception as e:
                    logger.error(f"Failed to process token {token.item_id}: {e}")
                    # Continue with other tokens
                    continue

            logger.info(
                f"Total: {len(all_accounts)} accounts, ${total_balance} total balance for user {user_id}"
            )

            account_data = {
                "accounts": [account.model_dump() for account in all_accounts],
                "total_balance": float(total_balance),
                "account_count": int(len(all_accounts)),
            }

            # Cache the account data in Firestore
            account_storage_service.store_account_data(user_id, account_data)

            return account_data

        except Exception as e:
            logger.error(f"Failed to get accounts balance for user {user_id}: {e}")
            raise Exception(f"Failed to retrieve account balances: {e}")

    def get_stored_accounts_balance(
        self,
        user_id: str,
        max_age_hours: int = None,  # No age limit - show any data that exists
    ) -> Dict[str, Any]:
        """Retrieve cached account balances from Firestore without calling Plaid API."""
        try:
            logger.info(f"Getting cached accounts balance for user {user_id}")

            # Get any cached data regardless of age
            cached_data = account_storage_service.get_stored_account_data(
                user_id, max_age_hours=24 * 365 * 10  # Allow up to 10 years old data
            )

            if cached_data:
                logger.info(
                    f"Found cached data for user {user_id} - {cached_data.get('account_count', 0)} accounts"
                )

                # Determine if data should be considered "expired" for UI purposes (older than 7 days)
                is_old = False
                last_updated = cached_data.get("last_updated")
                if last_updated:
                    try:
                        from datetime import datetime, timezone

                        if isinstance(last_updated, str):
                            update_time = datetime.fromisoformat(
                                last_updated.replace("Z", "+00:00")
                            )
                        else:
                            update_time = last_updated

                        age_hours = (
                            datetime.now(timezone.utc) - update_time
                        ).total_seconds() / 3600
                        is_old = age_hours > 168  # Consider old if older than 7 days
                    except:
                        is_old = True  # If we can't parse the date, assume it's old

                return {
                    "accounts": cached_data.get("accounts", []),
                    "total_balance": cached_data.get("total_balance", 0.0),
                    "account_count": cached_data.get("account_count", 0),
                    "last_updated": cached_data.get("last_updated"),
                    "from_cache": True,
                    "is_expired": is_old,
                    "message": (
                        "Data may be outdated. Consider refreshing for latest balances."
                        if is_old
                        else None
                    ),
                }

            # If absolutely no cached data exists
            logger.info(f"No cached data found for user {user_id}")
            return {
                "accounts": [],
                "total_balance": 0.0,
                "account_count": 0,
                "last_updated": None,
                "from_cache": False,
                "message": "No cached data available. Please refresh to get latest data.",
            }

        except Exception as e:
            logger.error(
                f"Failed to get cached accounts balance for user {user_id}: {e}"
            )
            raise Exception(f"Failed to retrieve cached account balances: {e}")

    def refresh_accounts_balance(self, user_id: str) -> Dict[str, Any]:
        """Force refresh of account balances from Plaid API and update cache."""
        try:
            logger.info(f"Force refreshing accounts balance for user {user_id}")

            # Call the original method which will fetch from Plaid and cache the results
            account_data = self.get_accounts_balance(user_id)

            # Add refresh indicator
            account_data["refreshed"] = True
            account_data["from_cache"] = False

            logger.info(
                f"Successfully refreshed and cached account data for user {user_id}"
            )
            return account_data

        except Exception as e:
            logger.error(f"Failed to refresh accounts balance for user {user_id}: {e}")
            raise Exception(f"Failed to refresh account balances: {e}")

    def get_data_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about cached account data."""
        try:
            # Get any data regardless of age
            cache_info = account_storage_service.get_data_info(
                user_id, max_age_hours=24 * 365 * 10
            )  # 10 years

            if cache_info:
                return {
                    "has_data": True,
                    "last_updated": cache_info["last_updated"],
                    "age_hours": cache_info["age_hours"],
                    "account_count": cache_info["account_count"],
                    "total_balance": cache_info["total_balance"],
                    "is_expired": cache_info["age_hours"]
                    > 168,  # Mark as expired if older than 7 days, but still show it
                }

            return {"has_data": False}

        except Exception as e:
            logger.error(f"Failed to get cache info for user {user_id}: {e}")
            return {"has_data": False, "error": str(e)}

    def _get_balance_for_token(
        self,
        access_token: str,
        institution_name: str = None,
        institution_id: str = None,
    ) -> List[PlaidAccountWithBalance]:
        """Retrieve account balances for a specific access token."""
        try:
            request = AccountsBalanceGetRequest(access_token=access_token)
            response = self.client.accounts_balance_get(request)

            accounts = []
            raw_accounts = response["accounts"]

            for account in raw_accounts:
                # Extract balance information
                balances = account.get("balances", {})

                # Create PlaidBalance model
                balance = PlaidBalance(
                    available=(
                        float(balances.get("available"))
                        if balances.get("available") is not None
                        else None
                    ),
                    current=(
                        float(balances.get("current"))
                        if balances.get("current") is not None
                        else None
                    ),
                    iso_currency_code=balances.get("iso_currency_code"),
                    unofficial_currency_code=balances.get("unofficial_currency_code"),
                )

                # Create PlaidAccountWithBalance model
                account_with_balance = PlaidAccountWithBalance(
                    account_id=str(account.get("account_id", "")),
                    name=str(account.get("name", "")),
                    official_name=(
                        str(account.get("official_name", ""))
                        if account.get("official_name")
                        else None
                    ),
                    type=str(account.get("type", "")),
                    subtype=(
                        str(account.get("subtype", ""))
                        if account.get("subtype")
                        else None
                    ),
                    mask=str(account.get("mask", "")) if account.get("mask") else None,
                    balances=balance,
                    institution_name=institution_name,
                    institution_id=institution_id,
                )

                accounts.append(account_with_balance)

            return accounts

        except Exception as e:
            logger.error(f"Failed to get balance for token: {e}")
            # Don't raise here, just return empty list to continue with other tokens
            return []

    def _update_token_last_used(self, item_id: str):
        """Update the last_used_at timestamp for a token."""
        try:
            doc_ref = firebase_client.db.collection("plaid_tokens").document(item_id)
            doc_ref.update(
                {
                    "last_used_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update last_used_at for token {item_id}: {e}")

    def _update_token_institution_info(
        self, item_id: str, institution_info: Dict[str, Any]
    ):
        """Update institution information for a token."""
        try:
            doc_ref = firebase_client.db.collection("plaid_tokens").document(item_id)
            doc_ref.update(
                {
                    "institution_id": institution_info.get("institution_id"),
                    "institution_name": institution_info.get("name"),
                    "metadata": institution_info,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
            )
            logger.info(
                f"Updated institution info for token {item_id}: {institution_info.get('name')}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to update institution info for token {item_id}: {e}"
            )

    def revoke_token(self, user_id: str, item_id: str) -> bool:
        """Revoke a Plaid access token."""
        try:
            logger.info(f"Revoking token {item_id} for user {user_id}")

            # Update token status in Firestore
            doc_ref = firebase_client.db.collection("plaid_tokens").document(item_id)
            doc_ref.update(
                {
                    "status": PlaidTokenStatus.REVOKED.value,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
            )

            logger.info(f"Successfully revoked token {item_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke token {item_id}: {e}")
            return False

    def get_user_plaid_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get summary of user's Plaid items (institutions)."""
        try:
            tokens = self.get_user_access_tokens(user_id)

            items = []
            for token in tokens:
                # Handle status field - it might be string or enum
                status_value = token.status
                if hasattr(status_value, "value"):
                    status_str = status_value.value
                else:
                    status_str = str(status_value)

                items.append(
                    {
                        "item_id": token.item_id,
                        "institution_name": token.institution_name,
                        "status": status_str,
                        "created_at": token.created_at.isoformat(),
                        "last_used_at": (
                            token.last_used_at.isoformat()
                            if token.last_used_at
                            else None
                        ),
                    }
                )

            return items

        except Exception as e:
            logger.error(f"Failed to get Plaid items for user {user_id}: {e}")
            raise Exception(f"Failed to retrieve Plaid items: {e}")

    # ===== TOKEN LIFECYCLE MANAGEMENT METHODS =====

    def cleanup_expired_tokens(self, days_threshold: int = 90) -> Dict[str, int]:
        """
        Clean up expired and stale tokens from Firebase.

        Args:
            days_threshold: Number of days of inactivity before considering a token stale

        Returns:
            Dict with cleanup statistics
        """
        try:
            logger.info(f"Starting token cleanup with {days_threshold} days threshold")

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

            # Get all tokens for analysis
            all_tokens = firebase_client.db.collection("plaid_tokens").stream()

            expired_count = 0
            stale_count = 0
            invalid_count = 0
            revoked_count = 0
            total_checked = 0

            for doc in all_tokens:
                try:
                    total_checked += 1
                    token_data = doc.to_dict()

                    # Convert timestamps
                    last_used_at = token_data.get("last_used_at")
                    if last_used_at:
                        last_used_at = last_used_at.replace(tzinfo=timezone.utc)

                    status = token_data.get("status", "unknown")
                    item_id = token_data.get("item_id")
                    user_id = token_data.get("user_id")

                    logger.info(
                        f"Checking token for user {user_id}, item_id: {item_id}, status: {status}"
                    )

                    # Check if token is already marked as expired/revoked
                    if status in [
                        PlaidTokenStatus.EXPIRED.value,
                        PlaidTokenStatus.REVOKED.value,
                    ]:
                        logger.info(
                            f"Removing already expired/revoked token: {item_id}"
                        )
                        doc.reference.delete()
                        if status == PlaidTokenStatus.EXPIRED.value:
                            expired_count += 1
                        else:
                            revoked_count += 1
                        continue

                    # Check if token hasn't been used for too long (stale)
                    if last_used_at and last_used_at < cutoff_date:
                        logger.info(
                            f"Removing stale token (last used: {last_used_at}): {item_id}"
                        )
                        doc.reference.delete()
                        stale_count += 1
                        continue

                    # Verify token is still valid with Plaid
                    if status == PlaidTokenStatus.ACTIVE.value and token_data.get(
                        "access_token"
                    ):
                        is_valid = self._verify_token_with_plaid(
                            token_data.get("access_token")
                        )
                        if not is_valid:
                            logger.info(f"Removing invalid token: {item_id}")
                            # Mark as expired instead of deleting immediately
                            doc.reference.update(
                                {
                                    "status": PlaidTokenStatus.EXPIRED.value,
                                    "updated_at": datetime.now(timezone.utc),
                                }
                            )
                            invalid_count += 1

                except Exception as e:
                    logger.error(f"Error processing token document {doc.id}: {e}")
                    continue

            cleanup_stats = {
                "total_checked": total_checked,
                "expired_removed": expired_count,
                "stale_removed": stale_count,
                "invalid_marked": invalid_count,
                "revoked_removed": revoked_count,
                "total_cleaned": expired_count + stale_count + revoked_count,
            }

            logger.info(f"Token cleanup completed: {cleanup_stats}")
            return cleanup_stats

        except Exception as e:
            logger.error(f"Token cleanup failed: {e}")
            raise Exception(f"Token cleanup failed: {e}")

    def _verify_token_with_plaid(self, encrypted_token: str) -> bool:
        """
        Verify if a token is still valid with Plaid API.

        Args:
            encrypted_token: The encrypted access token to verify

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Decrypt the token
            access_token = TokenEncryption.decrypt_token(encrypted_token)

            # Try to get item info to verify token is still valid
            request = ItemGetRequest(access_token=access_token)
            self.client.item_get(request)
            return True

        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False

    def mark_token_as_used(self, user_id: str, item_id: str) -> None:
        """
        Update the last_used_at timestamp for a token.

        Args:
            user_id: The user ID who owns the token
            item_id: The Plaid item ID to update
        """
        try:
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)
            now = datetime.now(timezone.utc)
            doc_ref.update(
                {
                    f"items.{item_id}.last_used_at": now,
                    f"items.{item_id}.updated_at": now,
                }
            )
            logger.info(f"Updated token usage for user {user_id}, item {item_id}")
        except Exception as e:
            logger.error(
                f"Failed to update token usage for user {user_id}, item {item_id}: {e}"
            )

    def revoke_user_token(self, user_id: str, item_id: str) -> bool:
        """
        Revoke a specific token for a user.

        Args:
            user_id: The user ID
            item_id: The item ID to revoke

        Returns:
            True if successfully revoked
        """
        try:
            logger.info(f"Revoking token for user {user_id}, item_id: {item_id}")

            # Get the user's token document (tokens stored as items map inside user document)
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(f"No token document found for user {user_id}")
                return False

            user_data = doc.to_dict()
            items_map = user_data.get("items", {})

            if item_id not in items_map:
                logger.warning(
                    f"Token not found for item_id: {item_id} in user {user_id} document"
                )
                return False

            token_data = items_map[item_id]

            # Get the encrypted access token
            encrypted_token = token_data.get("access_token")
            if encrypted_token:
                try:
                    # Decrypt the access token
                    access_token = TokenEncryption.decrypt_token(encrypted_token)

                    # Call Plaid API to remove the item
                    request = ItemRemoveRequest(access_token=access_token)
                    response = self.client.item_remove(request)

                    logger.info(f"Successfully removed item from Plaid: {item_id}")

                except Exception as plaid_error:
                    logger.error(f"Failed to remove item from Plaid API: {plaid_error}")
                    # Continue to mark as revoked locally even if Plaid API fails
                    # This ensures the user can still "disconnect" items that may be invalid
            else:
                logger.warning(f"No access token found for item_id: {item_id}")

            # Mark as revoked in our database by updating the specific item in the map
            items_map[item_id]["status"] = PlaidTokenStatus.REVOKED.value
            items_map[item_id]["updated_at"] = datetime.now(timezone.utc)

            # Check if this was the last active token - if so, we'll delete the entire document
            remaining_active_items = [
                item
                for item in items_map.values()
                if item.get("status") == PlaidTokenStatus.ACTIVE.value
            ]

            if len(remaining_active_items) == 0:
                # This was the last active token - delete the entire plaid_tokens document
                logger.info(
                    f"No active tokens remaining for user {user_id}, deleting entire plaid_tokens document"
                )
                doc_ref.delete()
            else:
                # Still have active tokens - remove only this specific item from the map
                logger.info(
                    f"Removing revoked item {item_id} from plaid_tokens document, {len(remaining_active_items)} active tokens remaining"
                )
                del items_map[item_id]  # Remove the revoked item completely
                doc_ref.update(
                    {"items": items_map, "updated_at": datetime.now(timezone.utc)}
                )

            # Clean up cached account data for this item
            try:
                from .account_storage_service import account_storage_service

                # Use the remaining_active_items we calculated above
                if len(remaining_active_items) == 0:
                    logger.info(
                        f"No active tokens remaining for user {user_id}, clearing all account data"
                    )
                    account_storage_service.clear_data(user_id)
                else:
                    logger.info(
                        f"User {user_id} still has {len(remaining_active_items)} active tokens, refreshing account data to remove unlinked accounts"
                    )
                    # Refresh account data to immediately reflect the removal of accounts from the unlinked bank
                    try:
                        updated_accounts = self.refresh_accounts_balance(user_id)
                        logger.info(
                            f"Successfully refreshed account data after unlinking - now showing {len(updated_accounts.get('accounts', []))} accounts"
                        )
                    except Exception as refresh_error:
                        logger.error(
                            f"Failed to refresh account data after unlinking: {refresh_error}"
                        )
                        # Continue anyway - the data will be refreshed on next API call

            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup account data after revoking item {item_id}: {cleanup_error}"
                )
                # Don't fail the entire operation if cleanup fails

            # Clean up transaction data for this specific item
            try:
                logger.info(
                    f"Cleaning up transaction data for unlinked item {item_id}"
                )
                transaction_cleanup_success = transaction_storage_service.delete_item_transactions(user_id, item_id)
                if transaction_cleanup_success:
                    logger.info(
                        f"Successfully cleaned up transaction data for item {item_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to clean up transaction data for item {item_id}, but continuing"
                    )
            except Exception as transaction_cleanup_error:
                logger.error(
                    f"Failed to cleanup transaction data for item {item_id}: {transaction_cleanup_error}"
                )
                # Don't fail the entire operation if transaction cleanup fails

            logger.info(f"Successfully revoked token {item_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke token {item_id} for user {user_id}: {e}")
            return False

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of tokens revoked
        """
        try:
            logger.info(f"Revoking all tokens for user {user_id}")

            # Get the user's token document (tokens stored as items map inside user document)
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning(f"No token document found for user {user_id}")
                return 0

            user_data = doc.to_dict()
            items_map = user_data.get("items", {})
            revoked_count = 0

            # Process each active token in the items map
            for item_id, token_data in items_map.items():
                try:
                    # Skip already revoked tokens
                    if token_data.get("status") != PlaidTokenStatus.ACTIVE.value:
                        continue

                    # Get the encrypted access token
                    encrypted_token = token_data.get("access_token")
                    if encrypted_token:
                        try:
                            # Decrypt the access token
                            access_token = TokenEncryption.decrypt_token(
                                encrypted_token
                            )

                            # Call Plaid API to remove the item
                            request = ItemRemoveRequest(access_token=access_token)
                            response = self.client.item_remove(request)

                            logger.info(
                                f"Successfully removed item from Plaid: {item_id}"
                            )

                        except Exception as plaid_error:
                            logger.error(
                                f"Failed to remove item {item_id} from Plaid API: {plaid_error}"
                            )
                            # Continue to mark as revoked locally even if Plaid API fails

                    # Mark as revoked in the items map
                    items_map[item_id]["status"] = PlaidTokenStatus.REVOKED.value
                    items_map[item_id]["updated_at"] = datetime.now(timezone.utc)
                    revoked_count += 1

                except Exception as e:
                    logger.error(f"Failed to revoke token {item_id}: {e}")
                    continue

            # Delete the entire plaid_tokens document since all tokens are being revoked
            if revoked_count > 0:
                logger.info(
                    f"Deleting entire plaid_tokens document for user {user_id} after revoking all {revoked_count} tokens"
                )
                doc_ref.delete()

                # Clean up all cached account data since all tokens are being revoked
                try:
                    from .account_storage_service import account_storage_service

                    logger.info(
                        f"Clearing all account data for user {user_id} after revoking all tokens"
                    )
                    account_storage_service.clear_data(user_id)
                    transaction_storage_service.delete_all_user_transactions(user_id)

                except Exception as cleanup_error:
                    logger.error(
                        f"Failed to cleanup account data after revoking all tokens for user {user_id}: {cleanup_error}"
                    )
                    # Don't fail the entire operation if cleanup fails

            logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
            return revoked_count

        except Exception as e:
            logger.error(f"Failed to revoke all tokens for user {user_id}: {e}")
            return 0

        except Exception as e:
            logger.error(f"Failed to revoke tokens for user {user_id}: {e}")
            return 0

    def get_token_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about token usage and health.

        Returns:
            Dict with token analytics
        """
        try:
            logger.info("Generating token analytics")

            # Get all tokens
            all_tokens = firebase_client.db.collection("plaid_tokens").stream()

            analytics = {
                "total_tokens": 0,
                "active_tokens": 0,
                "expired_tokens": 0,
                "revoked_tokens": 0,
                "error_tokens": 0,
                "users_with_tokens": set(),
                "institutions": {},
                "environments": {},
                "stale_tokens_30_days": 0,
                "stale_tokens_90_days": 0,
            }

            cutoff_30_days = datetime.now(timezone.utc) - timedelta(days=30)
            cutoff_90_days = datetime.now(timezone.utc) - timedelta(days=90)

            for doc in all_tokens:
                try:
                    token_data = doc.to_dict()
                    analytics["total_tokens"] += 1

                    status = token_data.get("status", "unknown")
                    user_id = token_data.get("user_id")
                    institution_name = token_data.get("institution_name", "Unknown")
                    environment = token_data.get("environment", "unknown")

                    # Count by status
                    if status == PlaidTokenStatus.ACTIVE.value:
                        analytics["active_tokens"] += 1
                    elif status == PlaidTokenStatus.EXPIRED.value:
                        analytics["expired_tokens"] += 1
                    elif status == PlaidTokenStatus.REVOKED.value:
                        analytics["revoked_tokens"] += 1
                    else:
                        analytics["error_tokens"] += 1

                    # Track users
                    if user_id:
                        analytics["users_with_tokens"].add(user_id)

                    # Track institutions
                    analytics["institutions"][institution_name] = (
                        analytics["institutions"].get(institution_name, 0) + 1
                    )

                    # Track environments
                    analytics["environments"][environment] = (
                        analytics["environments"].get(environment, 0) + 1
                    )

                    # Check for stale tokens
                    last_used_at = token_data.get("last_used_at")
                    if last_used_at:
                        last_used_at = last_used_at.replace(tzinfo=timezone.utc)
                        if last_used_at < cutoff_30_days:
                            analytics["stale_tokens_30_days"] += 1
                        if last_used_at < cutoff_90_days:
                            analytics["stale_tokens_90_days"] += 1

                except Exception as e:
                    logger.error(f"Error processing token for analytics {doc.id}: {e}")
                    continue

            # Convert set to count
            analytics["unique_users"] = len(analytics["users_with_tokens"])
            del analytics["users_with_tokens"]

            logger.info(f"Token analytics generated: {analytics}")
            return analytics

        except Exception as e:
            logger.error(f"Failed to generate token analytics: {e}")
            raise Exception(f"Token analytics failed: {e}")

    def get_transactions(
        self, user_id: str, days: int = 30, account_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fetch transactions for a user with simple, robust serialization."""
        try:
            logger.info(f"Fetching transactions for user {user_id}")

            access_tokens = self.get_user_access_tokens(user_id)

            if not access_tokens:
                logger.warning(f"No access tokens found for user {user_id}")
                return {
                    "transactions": [],
                    "account_count": 0,
                    "transaction_count": 0,
                    "items": [],
                }

            all_transactions = []
            items_data = []

            for token_obj in access_tokens:
                if token_obj.status != PlaidTokenStatus.ACTIVE:
                    continue

                try:
                    decrypted_token = TokenEncryption.decrypt_token(
                        token_obj.access_token
                    )

                    # Use traditional API for better sandbox compatibility
                    end_date = datetime.now(timezone.utc).date()
                    start_date = end_date - timedelta(days=days)

                    from plaid.model.transactions_get_request import (
                        TransactionsGetRequest,
                    )

                    traditional_request = TransactionsGetRequest(
                        access_token=decrypted_token,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    traditional_response = self.client.transactions_get(
                        traditional_request
                    )

                    # Extract transactions with manual field extraction to avoid serialization issues
                    transactions = []
                    for tx in traditional_response.transactions:
                        try:
                            # Manually extract only essential fields to ensure JSON compatibility
                            simple_tx = {
                                "transaction_id": (
                                    str(tx.transaction_id) if tx.transaction_id else ""
                                ),
                                "account_id": (
                                    str(tx.account_id) if tx.account_id else ""
                                ),
                                "amount": float(tx.amount) if tx.amount else 0.0,
                                "date": str(tx.date) if tx.date else "",
                                "name": (
                                    str(tx.name) if tx.name else "Unknown Transaction"
                                ),
                                "merchant_name": (
                                    str(tx.merchant_name) if tx.merchant_name else ""
                                ),
                                "category": (
                                    list(tx.category) if tx.category else ["Other"]
                                ),
                                "account_owner": (
                                    str(tx.account_owner) if tx.account_owner else ""
                                ),
                                "transaction_type": (
                                    str(tx.transaction_type)
                                    if hasattr(tx, "transaction_type")
                                    else "other"
                                ),
                                "iso_currency_code": (
                                    str(tx.iso_currency_code)
                                    if tx.iso_currency_code
                                    else "USD"
                                ),
                                "institution_name": token_obj.institution_name,
                                "institution_id": token_obj.institution_id,
                            }
                            transactions.append(simple_tx)
                        except Exception as e:
                            logger.warning(
                                f"Failed to process transaction {tx.transaction_id}: {e}"
                            )
                            # Add a minimal transaction record even if there's an error
                            transactions.append(
                                {
                                    "transaction_id": f"error_{len(transactions)}",
                                    "account_id": "",
                                    "amount": 0.0,
                                    "date": str(end_date),
                                    "name": "Transaction Processing Error",
                                    "merchant_name": "",
                                    "category": ["Error"],
                                    "account_owner": "",
                                    "transaction_type": "other",
                                    "iso_currency_code": "USD",
                                    "institution_name": token_obj.institution_name,
                                    "institution_id": token_obj.institution_id,
                                }
                            )

                    all_transactions.extend(transactions)

                    # Track item data
                    items_data.append(
                        {
                            "item_id": token_obj.item_id,
                            "institution_name": token_obj.institution_name,
                            "transaction_count": len(transactions),
                        }
                    )

                    self._update_token_last_used(token_obj.item_id)

                    logger.info(
                        f"Successfully fetched {len(transactions)} transactions for institution {token_obj.institution_name}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to fetch transactions for token {token_obj.item_id}: {e}"
                    )
                    continue

            # Sort transactions by date (most recent first)
            all_transactions.sort(key=lambda x: x.get("date", ""), reverse=True)

            result = {
                "transactions": all_transactions,
                "transaction_count": len(all_transactions),
                "account_count": len(
                    set(t.get("account_id") for t in all_transactions)
                ),
                "items": items_data,
            }

            logger.info(
                f"Successfully fetched {len(all_transactions)} total transactions for user {user_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to fetch transactions for user {user_id}: {e}")
            raise Exception(f"Failed to fetch transactions: {e}")

    def get_transactions_by_account(
        self, user_id: str, account_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Fetch transactions for a specific account."""
        try:
            return self.get_transactions(user_id, days=days, account_ids=[account_id])
        except Exception as e:
            logger.error(f"Failed to fetch transactions for account {account_id}: {e}")
            raise Exception(f"Failed to fetch account transactions: {e}")

    def refresh_transactions(
        self, user_id: str, item_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Refresh transactions for a specific item/bank using traditional API for compatibility."""
        try:
            logger.info(f"Refreshing transactions for user {user_id}, item {item_id}")

            # Get the specific access token
            access_tokens = self.get_user_access_tokens(user_id)
            target_token = next(
                (token for token in access_tokens if token.item_id == item_id), None
            )

            if not target_token:
                raise Exception(f"Access token not found for item {item_id}")

            if target_token.status != PlaidTokenStatus.ACTIVE:
                raise Exception(f"Access token for item {item_id} is not active")

            decrypted_token = TokenEncryption.decrypt_token(target_token.access_token)

            # Use traditional API for better sandbox compatibility
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)

            from plaid.model.transactions_get_request import TransactionsGetRequest

            traditional_request = TransactionsGetRequest(
                access_token=decrypted_token,
                start_date=start_date,
                end_date=end_date,
            )
            traditional_response = self.client.transactions_get(traditional_request)

            # Extract transactions with manual field extraction to avoid serialization issues
            transactions = []
            for tx in traditional_response.transactions:
                try:
                    # Manually extract only essential fields to ensure JSON compatibility
                    simple_tx = {
                        "transaction_id": (
                            str(tx.transaction_id) if tx.transaction_id else ""
                        ),
                        "account_id": str(tx.account_id) if tx.account_id else "",
                        "amount": float(tx.amount) if tx.amount else 0.0,
                        "date": str(tx.date) if tx.date else "",
                        "name": str(tx.name) if tx.name else "Unknown Transaction",
                        "merchant_name": (
                            str(tx.merchant_name) if tx.merchant_name else ""
                        ),
                        "category": list(tx.category) if tx.category else ["Other"],
                        "account_owner": (
                            str(tx.account_owner) if tx.account_owner else ""
                        ),
                        "transaction_type": (
                            str(tx.transaction_type)
                            if hasattr(tx, "transaction_type")
                            else "other"
                        ),
                        "iso_currency_code": (
                            str(tx.iso_currency_code) if tx.iso_currency_code else "USD"
                        ),
                        "institution_name": target_token.institution_name,
                        "institution_id": target_token.institution_id,
                    }
                    transactions.append(simple_tx)
                except Exception as e:
                    logger.warning(
                        f"Failed to process transaction {tx.transaction_id}: {e}"
                    )
                    # Add a minimal transaction record even if there's an error
                    transactions.append(
                        {
                            "transaction_id": f"error_{len(transactions)}",
                            "account_id": "",
                            "amount": 0.0,
                            "date": str(end_date),
                            "name": "Transaction Processing Error",
                            "merchant_name": "",
                            "category": ["Error"],
                            "account_owner": "",
                            "transaction_type": "other",
                            "iso_currency_code": "USD",
                            "institution_name": target_token.institution_name,
                            "institution_id": target_token.institution_id,
                        }
                    )

            # Sort transactions by date (most recent first)
            transactions.sort(key=lambda x: x.get("date", ""), reverse=True)

            # Update token last used
            self._update_token_last_used(item_id)

            result = {
                "transactions": transactions,
                "transaction_count": len(transactions),
                "institution_name": target_token.institution_name,
                "item_id": item_id,
            }

            logger.info(
                f"Successfully refreshed {len(transactions)} transactions for item {item_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to refresh transactions for item {item_id}: {e}")
            raise Exception(f"Failed to refresh transactions: {e}")
            raise Exception(f"Failed to refresh transactions: {e}")

    def _clean_and_normalize_for_firestore(self, data: Any) -> Any:
        """
        Recursively cleans and normalizes data to be compatible with Firestore.
        This version corrects the order of type checks to prevent RecursionError.
        """
        if data is None:
            return None

        # --- Recursive Cleaning for Collections (Do this FIRST) ---
        if isinstance(data, dict):
            return {
                k: self._clean_and_normalize_for_firestore(v) for k, v in data.items()
            }
        if isinstance(data, list):
            return [self._clean_and_normalize_for_firestore(item) for item in data]

        # --- Data Type Conversion (Do this AFTER recursion) ---
        # Check for the MOST specific type (datetime) BEFORE the less specific type (date).
        if isinstance(data, datetime):
            return (
                data.astimezone(timezone.utc)
                if data.tzinfo
                else data.replace(tzinfo=timezone.utc)
            )
        if isinstance(data, date):
            # This clause will only be reached if the object is a 'date' but not a 'datetime'.
            return datetime.combine(data, datetime.min.time(), tzinfo=timezone.utc)

        # Return all other compatible types (str, int, float, bool)
        return data

    # The main sync function
    def sync_all_transactions_for_item(
        self, user_id: str, item_id: str, access_token: str
    ):
        """
        Fetch all available transactions for a new item and store them in Firestore.
        This method is designed to be run in the background.
        """
        try:
            logger.info(
                f"Starting initial transaction sync for user {user_id}, item {item_id}"
            )

            decrypted_token = TokenEncryption.decrypt_token(access_token)
            has_more = True
            cursor = None
            total_transactions_fetched = 0

            while has_more:
                request_args = {"access_token": decrypted_token, "count": 500}
                if cursor:
                    request_args["cursor"] = cursor

                request = TransactionsSyncRequest(**request_args)
                response = self.client.transactions_sync(request)

                added_transactions = response.get("added", [])
                if added_transactions:
                    logger.info(
                        f"Fetched {len(added_transactions)} new transactions for item {item_id}"
                    )

                    # 1. Clean and normalize all transactions in the batch
                    cleaned_transactions = [
                        self._clean_and_normalize_for_firestore(tx.to_dict())
                        for tx in added_transactions
                    ]

                    # 2. Delegate the database write operation to the storage service
                    success = transaction_storage_service.store_transactions_batch(
                        user_id, item_id, cleaned_transactions
                    )

                    # 3. Handle the result
                    if success:
                        total_transactions_fetched += len(added_transactions)
                    else:
                        # If storage fails, stop the sync to avoid inconsistent data
                        raise Exception(
                            "Failed to store transaction batch in Firestore."
                        )

                has_more = response["has_more"]
                cursor = response["next_cursor"]
                logger.info(f"has_more is now {has_more} for item {item_id}")

            # Update the token metadata (cursor, status, etc.)
            # This logic correctly remains in the PlaidService
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)
            doc_ref.update(
                {
                    f"items.{item_id}.transactions_cursor": cursor,
                    f"items.{item_id}.last_sync_completed_at": firestore.SERVER_TIMESTAMP,
                    f"items.{item_id}.total_transactions_synced": total_transactions_fetched,
                    f"items.{item_id}.transaction_sync_status": "completed",
                }
            )

            logger.info(
                f"Successfully completed initial sync for item {item_id}. "
                f"Fetched {total_transactions_fetched} transactions. Final cursor stored."
            )

        except Exception as e:
            logger.error(
                f"Background transaction sync failed for user {user_id}, item {item_id}: {e}",
                exc_info=True,
            )
            doc_ref = firebase_client.db.collection("plaid_tokens").document(user_id)
            doc_ref.update(
                {
                    f"items.{item_id}.transaction_sync_status": "failed",
                    f"items.{item_id}.sync_error": str(e),
                    f"items.{item_id}.last_sync_completed_at": firestore.SERVER_TIMESTAMP,
                }
            )
