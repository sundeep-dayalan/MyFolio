"""
Production-ready Plaid integration service with Firebase storage,
user authentication, and comprehensive security features.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from plaid.exceptions import ApiException

from firebase_admin import firestore

from ..config import get_settings
from ..utils.logger import get_logger
from ..utils.token_security import (
    encrypt_access_token,
    decrypt_access_token,
    mask_token_for_logging,
)
from ..models.plaid import (
    PlaidAccessToken,
    PlaidTokenStatus,
    PlaidEnvironment,
    PlaidAccountWithBalance,
    PlaidBalance,
    PlaidAccount,
)
from ..exceptions import PlaidServiceError

settings = get_settings()
logger = get_logger(__name__)


class PlaidService:
    """
    Production-ready Plaid service with Firebase storage and security features.
    """

    # Firestore collection names
    PLAID_TOKENS_COLLECTION = "plaid_access_tokens"

    def __init__(self, firestore_client: firestore.Client):
        """Initialize Plaid service with Firebase client."""
        self.db = firestore_client
        self._setup_plaid_client()

    def _setup_plaid_client(self):
        """Setup Plaid API client with configuration."""
        try:
            configuration = Configuration(
                host=getattr(settings, "PLAID_HOST"),
                api_key={
                    "clientId": settings.PLAID_CLIENT_ID,
                    "secret": settings.PLAID_SECRET_KEY,
                },
            )
            api_client = ApiClient(configuration)
            self.client = plaid_api.PlaidApi(api_client)

            logger.info(
                f"Plaid client initialized for environment: {settings.PLAID_HOST}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Plaid client: {e}")
            raise PlaidServiceError(f"Plaid initialization failed: {str(e)}")

    def _clean_plaid_response(self, obj: Any) -> Any:
        """
        Recursively clean Plaid API response objects for JSON serialization.
        Converts Plaid SDK objects to basic Python types.
        """
        if hasattr(obj, "to_dict"):
            try:
                cleaned = obj.to_dict()
                return self._clean_plaid_response(cleaned)
            except Exception:
                pass

        if isinstance(obj, dict):
            cleaned_dict = {}
            for key, value in obj.items():
                if not str(key).startswith("_") and not callable(value):
                    try:
                        cleaned_dict[key] = self._clean_plaid_response(value)
                    except Exception as e:
                        logger.debug(
                            f"Skipping key {key} due to serialization error: {e}"
                        )
                        continue
            return cleaned_dict

        if isinstance(obj, (list, tuple)):
            cleaned_list = []
            for item in obj:
                try:
                    cleaned_list.append(self._clean_plaid_response(item))
                except Exception as e:
                    logger.debug(f"Skipping list item due to serialization error: {e}")
                    continue
            return cleaned_list

        # Handle basic types
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        # Convert other objects to string representation
        try:
            return str(obj)
        except Exception:
            logger.debug(f"Could not convert object of type {type(obj)} to string")
            return None

    async def get_stored_access_token(self, user_id: str) -> Optional[PlaidAccessToken]:
        """
        Retrieve stored access token for a user from Firebase.

        Args:
            user_id: The authenticated user ID

        Returns:
            PlaidAccessToken model if found, None otherwise
        """
        try:
            # Query for active tokens for this user
            tokens_ref = self.db.collection(self.PLAID_TOKENS_COLLECTION)
            query = tokens_ref.where("user_id", "==", user_id).where(
                "status", "==", PlaidTokenStatus.ACTIVE.value
            )

            docs = query.get()

            if not docs:
                logger.info(f"No active Plaid tokens found for user: {user_id}")
                return None

            # Get the most recent token (in case there are multiple)
            latest_doc = max(
                docs,
                key=lambda d: d.get(
                    "created_at", datetime.min.replace(tzinfo=timezone.utc)
                ),
            )
            token_data = latest_doc.to_dict()

            # Decrypt the access token
            encrypted_token = token_data.get("access_token")
            if encrypted_token:
                token_data["access_token"] = decrypt_access_token(encrypted_token)

            # Convert Firestore timestamp to datetime
            if "created_at" in token_data:
                token_data["created_at"] = token_data["created_at"]
            if "updated_at" in token_data:
                token_data["updated_at"] = token_data["updated_at"]

            plaid_token = PlaidAccessToken(**token_data)

            logger.info(
                f"Retrieved Plaid token for user {user_id}, item: {plaid_token.item_id}"
            )
            return plaid_token

        except Exception as e:
            logger.error(f"Error retrieving access token for user {user_id}: {e}")
            return None

    async def store_access_token(
        self,
        user_id: str,
        access_token: str,
        item_id: str,
        institution_id: Optional[str] = None,
        institution_name: Optional[str] = None,
    ) -> PlaidAccessToken:
        """
        Store access token in Firebase with encryption.

        Args:
            user_id: The authenticated user ID
            access_token: The Plaid access token to store
            item_id: The Plaid item ID
            institution_id: Optional institution ID
            institution_name: Optional institution name

        Returns:
            PlaidAccessToken model of the stored token
        """
        try:
            # Encrypt the access token
            encrypted_token = encrypt_access_token(access_token)

            # Create token model
            token_model = PlaidAccessToken(
                user_id=user_id,
                access_token=encrypted_token,
                item_id=item_id,
                institution_id=institution_id,
                institution_name=institution_name,
                environment=PlaidEnvironment.SANDBOX,  # Always sandbox as requested
                status=PlaidTokenStatus.ACTIVE,
            )

            # Store in Firestore
            doc_ref = self.db.collection(self.PLAID_TOKENS_COLLECTION).document()
            doc_ref.set(token_model.dict())

            logger.info(
                f"Stored encrypted Plaid token for user {user_id}, item: {item_id}"
            )

            # Return model with decrypted token for immediate use
            token_model.access_token = access_token
            return token_model

        except Exception as e:
            logger.error(f"Error storing access token for user {user_id}: {e}")
            raise PlaidServiceError(f"Failed to store access token: {str(e)}")

    async def update_token_last_used(self, user_id: str, item_id: str):
        """Update the last_used_at timestamp for a token."""
        try:
            tokens_ref = self.db.collection(self.PLAID_TOKENS_COLLECTION)
            query = tokens_ref.where("user_id", "==", user_id).where(
                "item_id", "==", item_id
            )

            docs = query.get()
            for doc in docs:
                doc.reference.update(
                    {"last_used_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
                )

        except Exception as e:
            logger.warning(f"Failed to update token last_used timestamp: {e}")

    async def revoke_token(self, user_id: str, item_id: str):
        """Mark a token as revoked in the database."""
        try:
            tokens_ref = self.db.collection(self.PLAID_TOKENS_COLLECTION)
            query = tokens_ref.where("user_id", "==", user_id).where(
                "item_id", "==", item_id
            )

            docs = query.get()
            for doc in docs:
                doc.reference.update(
                    {
                        "status": PlaidTokenStatus.REVOKED.value,
                        "updated_at": datetime.utcnow(),
                    }
                )

            logger.info(f"Revoked Plaid token for user {user_id}, item: {item_id}")

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            raise PlaidServiceError(f"Failed to revoke token: {str(e)}")

    async def create_link_token(self, user_id: str) -> Dict[str, Any]:
        """
        Create a Plaid Link token for the authenticated user.

        Args:
            user_id: The authenticated user ID from Google SSO

        Returns:
            Dictionary containing the link token response
        """
        try:
            # Create link token request with authenticated user ID
            request = LinkTokenCreateRequest(
                products=[
                    Products("transactions"),
                    Products("assets"),
                    Products("accounts"),
                ],
                client_name="Personal Wealth Management",
                country_codes=[CountryCode("US")],
                language="en",
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                webhook=(
                    settings.PLAID_WEBHOOK_URL
                    if hasattr(settings, "PLAID_WEBHOOK_URL")
                    else None
                ),
            )

            # Create the link token
            response = self.client.link_token_create(request)
            cleaned_response = self._clean_plaid_response(response)

            logger.info(f"Created link token for authenticated user: {user_id}")
            return cleaned_response

        except ApiException as e:
            error_response = json.loads(e.body) if e.body else {}
            logger.error(f"Plaid API error creating link token: {error_response}")
            raise PlaidServiceError(
                f"Failed to create link token: {error_response.get('error_message', str(e))}"
            )
        except Exception as e:
            logger.error(f"Unexpected error creating link token: {e}")
            raise PlaidServiceError(f"Unexpected error: {str(e)}")

    async def exchange_public_token(
        self, user_id: str, public_token: str
    ) -> Dict[str, Any]:
        """
        Exchange public token for access token and store it securely.

        Args:
            user_id: The authenticated user ID
            public_token: The public token from Plaid Link

        Returns:
            Dictionary containing exchange response and storage confirmation
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            cleaned_response = self._clean_plaid_response(response)

            access_token = cleaned_response.get("access_token")
            item_id = cleaned_response.get("item_id")

            if not access_token or not item_id:
                raise PlaidServiceError("Invalid response from token exchange")

            # Store the token securely in Firebase
            stored_token = await self.store_access_token(
                user_id=user_id, access_token=access_token, item_id=item_id
            )

            logger.info(
                f"Successfully exchanged and stored token for user: {user_id}, item: {item_id}"
            )

            # Return response without sensitive data
            safe_response = {
                "item_id": item_id,
                "stored": True,
                "user_id": user_id,
                "environment": "sandbox",
            }

            return safe_response

        except ApiException as e:
            error_response = json.loads(e.body) if e.body else {}
            logger.error(f"Plaid API error exchanging token: {error_response}")
            raise PlaidServiceError(
                f"Token exchange failed: {error_response.get('error_message', str(e))}"
            )
        except Exception as e:
            logger.error(f"Unexpected error exchanging token: {e}")
            raise PlaidServiceError(f"Unexpected error: {str(e)}")

    async def get_accounts(self, user_id: str) -> List[PlaidAccountWithBalance]:
        """
        Get account information for the authenticated user.

        Args:
            user_id: The authenticated user ID

        Returns:
            List of PlaidAccountWithBalance objects
        """
        try:
            # Retrieve stored access token
            stored_token = await self.get_stored_access_token(user_id)
            if not stored_token:
                raise PlaidServiceError(
                    "No active Plaid connection found. Please reconnect your bank account."
                )

            # Make API request
            request = AccountsGetRequest(access_token=stored_token.access_token)
            response = self.client.accounts_get(request)
            cleaned_response = self._clean_plaid_response(response)

            # Update last used timestamp
            await self.update_token_last_used(user_id, stored_token.item_id)

            # Convert to our models
            accounts = []
            for account_data in cleaned_response.get("accounts", []):
                # Extract balance information
                balance_data = account_data.get("balances", {})
                balance = PlaidBalance(**balance_data)

                # Create account with balance
                account = PlaidAccountWithBalance(
                    account_id=account_data["account_id"],
                    name=account_data["name"],
                    official_name=account_data.get("official_name"),
                    type=account_data["type"],
                    subtype=account_data.get("subtype"),
                    mask=account_data.get("mask"),
                    balances=balance,
                )
                accounts.append(account)

            logger.info(f"Retrieved {len(accounts)} accounts for user: {user_id}")
            return accounts

        except ApiException as e:
            error_response = json.loads(e.body) if e.body else {}
            logger.error(f"Plaid API error getting accounts: {error_response}")

            # Handle token revocation
            if error_response.get("error_code") == "ITEM_LOGIN_REQUIRED":
                if stored_token:
                    await self.revoke_token(user_id, stored_token.item_id)
                raise PlaidServiceError(
                    "Bank connection expired. Please reconnect your account."
                )

            raise PlaidServiceError(
                f"Failed to get accounts: {error_response.get('error_message', str(e))}"
            )
        except PlaidServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting accounts for user {user_id}: {e}")
            raise PlaidServiceError(f"Unexpected error: {str(e)}")

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Plaid webhook events.

        Args:
            webhook_data: The webhook payload from Plaid

        Returns:
            Dictionary containing processing result
        """
        try:
            webhook_type = webhook_data.get("webhook_type")
            webhook_code = webhook_data.get("webhook_code")
            item_id = webhook_data.get("item_id")

            logger.info(
                f"Processing Plaid webhook: {webhook_type}.{webhook_code} for item {item_id}"
            )

            # Handle different webhook types
            if webhook_type == "ITEM" and webhook_code == "ERROR":
                # Handle item errors (e.g., login required)
                error = webhook_data.get("error", {})
                logger.warning(f"Item error for {item_id}: {error}")

                # You could update token status here
                # await self.update_token_status_by_item(item_id, PlaidTokenStatus.ERROR)

            elif webhook_type == "TRANSACTIONS":
                # Handle transaction updates
                logger.info(f"Transaction update for item {item_id}: {webhook_code}")

            # Return acknowledgment
            return {
                "status": "processed",
                "webhook_type": webhook_type,
                "webhook_code": webhook_code,
                "item_id": item_id,
            }

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise PlaidServiceError(f"Webhook processing failed: {str(e)}")

    async def get_user_plaid_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive Plaid connection status for a user.

        Args:
            user_id: The authenticated user ID

        Returns:
            Dictionary containing user's Plaid status
        """
        try:
            stored_token = await self.get_stored_access_token(user_id)

            if not stored_token:
                return {
                    "connected": False,
                    "status": "no_connection",
                    "message": "No bank accounts connected",
                }

            # Try to fetch accounts to verify token is still valid
            try:
                accounts = await self.get_accounts(user_id)
                return {
                    "connected": True,
                    "status": "active",
                    "item_id": stored_token.item_id,
                    "institution_name": stored_token.institution_name,
                    "account_count": len(accounts),
                    "last_used": stored_token.last_used_at,
                    "environment": stored_token.environment,
                }
            except PlaidServiceError as e:
                # Token might be invalid
                return {
                    "connected": False,
                    "status": "connection_error",
                    "message": str(e),
                    "item_id": stored_token.item_id,
                }

        except Exception as e:
            logger.error(f"Error getting Plaid status for user {user_id}: {e}")
            return {
                "connected": False,
                "status": "error",
                "message": f"Unable to check status: {str(e)}",
            }
