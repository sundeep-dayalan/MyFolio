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
from datetime import datetime, timezone
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
import json

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
            f = Fernet(TokenEncryption._get_key())
            encrypted_token = f.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_token).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise Exception("Token encryption failed")

    @staticmethod
    def decrypt_token(encrypted_token: str) -> str:
        """Decrypt a token for use."""
        try:
            f = Fernet(TokenEncryption._get_key())
            decoded_token = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_token = f.decrypt(decoded_token)
            return decrypted_token.decode()
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

            # Create the basic request without webhook for now
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

            # Store the access token securely in Firestore
            stored_token = self._store_access_token(user_id, access_token, item_id)

            logger.info(
                f"Successfully exchanged and stored token for user {user_id}, item_id: {item_id}"
            )
            return {
                "success": True,
                "item_id": item_id,
                "token_id": stored_token.item_id,
            }

        except Exception as e:
            logger.error(f"Failed to exchange public token for user {user_id}: {e}")
            raise Exception(f"Failed to exchange public token: {e}")

    def _store_access_token(
        self, user_id: str, access_token: str, item_id: str
    ) -> PlaidAccessToken:
        """Securely store access token in Firestore."""
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
            plaid_token = PlaidAccessToken(
                user_id=user_id,
                access_token=encrypted_token,
                item_id=item_id,
                status=PlaidTokenStatus.ACTIVE,
                environment=PlaidEnvironment(self.environment),
                created_at=now,
                updated_at=now,
                last_used_at=now,
            )

            # Store in Firestore
            doc_ref = firebase_client.db.collection("plaid_tokens").document(item_id)
            doc_ref.set(plaid_token.model_dump())

            logger.info(f"Successfully stored encrypted token for user {user_id}")
            return plaid_token

        except Exception as e:
            logger.error(f"Failed to store access token for user {user_id}: {e}")
            raise Exception(f"Failed to store access token: {e}")

    def get_user_access_tokens(self, user_id: str) -> List[PlaidAccessToken]:
        """Retrieve all access tokens for a user."""
        try:
            logger.info(f"Retrieving access tokens for user {user_id}")

            # Check if Firebase is connected
            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot retrieve tokens")
                raise Exception("Firebase connection required for token retrieval")

            # Query Firestore for user's tokens
            query = (
                firebase_client.db.collection("plaid_tokens")
                .where("user_id", "==", user_id)
                .where("status", "==", PlaidTokenStatus.ACTIVE.value)
            )

            docs = query.stream()
            tokens = []

            for doc in docs:
                try:
                    data = doc.to_dict()
                    # Convert Firestore timestamps to datetime objects
                    if data.get("created_at"):
                        data["created_at"] = data["created_at"].replace(
                            tzinfo=timezone.utc
                        )
                    if data.get("updated_at"):
                        data["updated_at"] = data["updated_at"].replace(
                            tzinfo=timezone.utc
                        )
                    if data.get("last_used_at"):
                        data["last_used_at"] = data["last_used_at"].replace(
                            tzinfo=timezone.utc
                        )

                    token = PlaidAccessToken.model_validate(data)
                    tokens.append(token)
                except Exception as e:
                    logger.error(f"Failed to parse token document {doc.id}: {e}")
                    continue

            logger.info(
                f"Found {len(tokens)} active tokens from Firestore for user {user_id}"
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

                    # Get accounts for this token
                    accounts = self._get_balance_for_token(decrypted_token)
                    logger.info(f"Token {i+1} returned {len(accounts)} accounts")

                    # Update last used timestamp
                    self._update_token_last_used(token.item_id)

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

            return {
                "accounts": [account.model_dump() for account in all_accounts],
                "total_balance": float(total_balance),
                "account_count": int(len(all_accounts)),
            }

        except Exception as e:
            logger.error(f"Failed to get accounts balance for user {user_id}: {e}")
            raise Exception(f"Failed to retrieve account balances: {e}")

    def _get_balance_for_token(
        self, access_token: str
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
                items.append(
                    {
                        "item_id": token.item_id,
                        "institution_name": token.institution_name,
                        "status": token.status.value,
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
