from typing import List, Dict, Any, Optional

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
    PlaidAccountWithBalance,
    PlaidBalance,
    BankDocument,
)
from .account_storage_service import account_storage_service
from .transaction_storage_service import transaction_storage_service
from .plaid_config_service import plaid_config_service
from datetime import datetime, timezone
import json
from plaid.model.accounts_balance_get_request_options import (
    AccountsBalanceGetRequestOptions,
)
from ..constants import (
    Containers,
    PlaidEnvironments,
    PlaidProducts,
    TransactionSyncStatus,
    PlaidLinkConfig,
    Currency,
    ConfigMessages,
    ErrorMessages,
    PlaidResponseFields,
    Status,
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
            return token  # For now removing encrpytion and decrypt
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
            return encrypted_token  # For now removing encrpytion and decrypt
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise Exception("Token decryption failed")


class PlaidService:
    """Production-ready service for interacting with the Plaid API with dynamic credentials."""

    def __init__(self):
        # Environment will be determined dynamically from stored configuration
        self._client = None
        self._client_initialized = False

    async def _get_client(self, user_id: str) -> plaid_api.PlaidApi:
        """Get Plaid client with dynamic credentials (Just-In-Time initialization)."""
        if self._client and self._client_initialized:
            return self._client

        # Get credentials and environment from secure storage
        credentials = await plaid_config_service.get_decrypted_credentials(user_id)

        if not credentials:
            raise ValueError(ConfigMessages.CREDENTIALS_NOT_CONFIGURED)

        client_id, secret, environment = credentials

        self.environment = environment

        # Configure Plaid client with user-provided credentials
        from plaid.configuration import Configuration, Environment

        # Map environment string to Plaid Environment enum
        environment_map = {
            PlaidEnvironments.SANDBOX: Environment.Sandbox,
            PlaidEnvironments.DEVELOPMENT: Environment.Sandbox,  # Use sandbox for development
            PlaidEnvironments.PRODUCTION: Environment.Production,
        }

        plaid_environment = environment_map.get(
            environment.lower(), Environment.Sandbox
        )

        config = Configuration(
            host=plaid_environment,
            api_key={
                "clientId": client_id,
                "secret": secret,
            },
        )
        api_client = ApiClient(config)
        self._client = plaid_api.PlaidApi(api_client)
        self._client_initialized = True

        logger.info(
            f"Plaid client initialized with dynamic credentials for {environment} environment"
        )
        return self._client

    def _reset_client(self):
        """Reset client to force re-initialization with fresh credentials."""
        self._client = None
        self._client_initialized = False

    async def create_link_token(
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
            client = await self._get_client(user_id)
            logger.info(
                f"Creating link token for user {user_id} in {self.environment} environment"
            )

            # Build request params dynamically
            request_params = {
                "products": [
                    Products(p) for p in (products or [PlaidProducts.TRANSACTIONS])
                ],
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
            if PlaidProducts.TRANSACTIONS in (products or []):
                request_params["transactions"] = {
                    "days_requested": transactions_days_requested
                }

            request = LinkTokenCreateRequest(**request_params)

            response = client.link_token_create(request)
            link_token = response["link_token"]

            logger.info(f"Link token created successfully for user {user_id}")
            return link_token

        except ValueError as ve:
            # Re-raise credential configuration errors
            raise ve
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

    async def exchange_public_token(
        self, user_id: str, public_token: str
    ) -> BankDocument:
        """Exchange public token for access token and store it securely."""
        try:
            client = await self._get_client(user_id)
            logger.info(f"Exchanging public token for user {user_id}")

            # Exchange public token for access token
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = client.item_public_token_exchange(request)

            access_token = response["access_token"]
            item_id = response["item_id"]

            # Get institution info
            institution_info = await self._get_institution_info_by_item(
                user_id, access_token
            )

            # Store the access token
            stored_token = self._store_access_token(
                user_id, access_token, item_id, institution_info
            )

            # Immediately sync account data so accounts are available right away
            try:
                logger.info(f"🔄 Syncing account data immediately for item {item_id}")
                await self.get_accounts_with_balances(user_id, use_cached_balance=False)
                logger.info(f"✅ Account data synced successfully for item {item_id}")
            except Exception as e:
                logger.error(f"❌ Failed to sync account data for item {item_id}: {e}")
                # Don't fail the entire exchange if account sync fails

            # Start transaction sync in the background (non-blocking)
            try:
                logger.info(f"🚀 Starting transaction sync for item {item_id}")
                await self._sync_transactions_for_stored_item(user_id, item_id)
                logger.info(f"✅ Transaction sync completed for item {item_id}")
            except Exception as e:
                logger.error(f"❌ Background transaction sync failed for item {item_id}: {e}")
                # Don't fail the exchange if transaction sync fails

            logger.info(
                f"Successfully exchanged and stored token for user {user_id}, item_id: {item_id}"
            )
            return stored_token

        except ValueError as ve:
            # Re-raise credential configuration errors
            raise ve
        except Exception as e:
            logger.error(f"Failed to exchange public token for user {user_id}: {e}")
            raise Exception(f"Failed to exchange public token: {e}")

    async def _get_institution_info_by_item(
        self, user_id: str, access_token: str
    ) -> Dict[str, Any]:
        """Get institution information using item access token."""
        try:
            client = await self._get_client(user_id)
            # Get item info first
            request = ItemGetRequest(access_token=access_token)
            item_response = client.item_get(request)
            plaid_institution_data = item_response["item"]
            institution_id = plaid_institution_data["institution_id"]

            logger.info(f"Got institution_id: {institution_id}")

            # Get institution details
            inst_request = InstitutionsGetByIdRequest(
                institution_id=institution_id, country_codes=[CountryCode("US")]
            )
            inst_response = client.institutions_get_by_id(inst_request)
            institution = inst_response["institution"]

            institution_info = {
                "institution_id": institution_id,
                "name": institution["name"],
                "products": institution["products"],
                "country_codes": institution["country_codes"],
                "plaid_institution_data": plaid_institution_data,
            }

            logger.info(f"Retrieved institution info: {institution['name']}")
            logger.debug(f"Full institution_info: {institution_info}")
            return institution_info

        except Exception as e:
            logger.error(f"Failed to get institution info: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            # Return minimal info as fallback but still try to get plaid_institution_data
            try:
                request = ItemGetRequest(access_token=access_token)
                client = await self._get_client(user_id)
                item_response = client.item_get(request)
                plaid_institution_data = item_response["item"]
                institution_id = plaid_institution_data["institution_id"]
                fallback_info = {
                    "institution_id": institution_id,
                    "name": f"Bank {institution_id}",
                    "products": [],
                    "country_codes": ["US"],
                    "plaid_institution_data": plaid_institution_data,
                }
                logger.info(
                    f"Using fallback institution info with plaid_institution_data: {bool(plaid_institution_data)}"
                )
                logger.debug(
                    f"Fallback plaid_institution_data: {plaid_institution_data}"
                )
                return fallback_info
            except Exception as e2:
                logger.error(f"Failed to get even basic institution info: {e2}")
                return {
                    "institution_id": None,
                    "name": "Unknown Bank",
                    "products": [],
                    "country_codes": ["US"],
                    "plaid_institution_data": {},
                }

    def _convert_plaid_object(self, obj) -> Dict[str, Any]:
        """Convert Plaid API objects to JSON-serializable dictionaries."""
        try:
            if obj is None:
                return None
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, "value"):  # Enum objects
                return obj.value
            elif isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, (list, tuple)):
                return [self._convert_plaid_object(item) for item in obj]
            elif isinstance(obj, dict):
                # Process dict recursively to handle nested datetime objects
                result = {}
                for key, value in obj.items():
                    result[key] = self._convert_plaid_object(value)
                return result
            elif hasattr(obj, "to_dict"):
                # For Plaid objects with to_dict method
                return self._convert_plaid_object(obj.to_dict())
            elif hasattr(obj, "__dict__"):
                # Convert object attributes to dict, handling nested objects
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith("_"):  # Skip private attributes
                        result[key] = self._convert_plaid_object(value)
                return result
            else:
                # For any other type, convert to string
                return str(obj)
        except Exception as e:
            logger.error(f"Failed to convert Plaid object {type(obj)}: {e}")
            # Return string representation as fallback
            return str(obj)

    def _store_access_token(
        self,
        user_id: str,
        access_token: str,
        item_id: str,
        institution_info: Dict[str, Any] = None,
    ) -> BankDocument:
        """Store bank data using optimized BankDocument structure."""
        try:
            logger.info(f"Storing bank data for user {user_id}, item_id: {item_id}")

            # Check if CosmosDB is connected
            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot store bank data")
                raise Exception("CosmosDB connection required for bank data storage")

            # Encrypt the access token
            encrypted_token = TokenEncryption.encrypt_token(access_token)

            # Prepare timestamps
            now = datetime.now(timezone.utc)
            iso_timestamp = now.isoformat()

            # Clean and prepare Plaid data
            institution_info = institution_info or {}
            logger.debug(f"Institution info before storage: {institution_info}")

            def ensure_serializable(data):
                """Convert Plaid objects to JSON-serializable format."""
                if data is None:
                    return None
                elif hasattr(data, "value"):  # Enum objects
                    return data.value
                elif isinstance(data, datetime):
                    return data.isoformat()
                elif isinstance(data, (str, int, float, bool)):
                    return data
                elif isinstance(data, list):
                    return [ensure_serializable(item) for item in data]
                elif isinstance(data, dict):
                    return {k: ensure_serializable(v) for k, v in data.items()}
                elif hasattr(data, "__dict__"):  # Complex Plaid objects
                    try:
                        # Try to extract attributes safely
                        obj_dict = {}
                        for k, v in data.__dict__.items():
                            if not k.startswith("_"):  # Skip private attributes
                                obj_dict[k] = ensure_serializable(v)
                        return obj_dict
                    except Exception:
                        # If extraction fails, try to convert to string
                        return str(data)
                else:
                    # For any other type, convert to string
                    return str(data)

            # Create optimized BankDocument
            bank_document = BankDocument(
                id=item_id,
                userId=user_id,
                schemaVersion="2.0",
                institutionId=institution_info.get("institution_id", "unknown"),
                institutionName=institution_info.get("name", "Unknown Bank"),
                status="active",
                createdAt=iso_timestamp,
                updatedAt=iso_timestamp,
                lastUsedAt=iso_timestamp,
                environment=self.environment,
                summary={
                    "accountCount": 0,
                    "totalBalance": 0.0,
                    "lastSync": {"status": "pending", "timestamp": None, "error": None},
                },
                plaidData={
                    "accessToken": encrypted_token,
                    "itemId": item_id,
                    "institutionId": institution_info.get("institution_id"),
                    "institutionName": institution_info.get("name"),
                    "products": ensure_serializable(
                        institution_info.get("products", [])
                    ),
                    "countryCodes": ensure_serializable(
                        institution_info.get("country_codes", [])
                    ),
                    "plaidInstitutionData": self._convert_plaid_object(
                        institution_info.get("plaid_institution_data", {})
                    ),
                },
            )
            logger.debug(f"Final plaidData before storage: {bank_document.plaidData}")

            # Store document
            document_dict = bank_document.model_dump()
            try:
                cosmos_client.create_item(Containers.BANKS, document_dict, user_id)
            except CosmosHttpResponseError as e:
                if e.status_code == 409:  # Document exists, update it
                    cosmos_client.update_item(
                        Containers.BANKS, item_id, user_id, document_dict
                    )
                else:
                    raise

            logger.info(
                f"Successfully stored bank data for user {user_id}, item_id: {item_id}"
            )
            return bank_document

        except Exception as e:
            logger.error(f"Failed to store bank data for user {user_id}: {e}")
            raise Exception(f"Failed to store bank data: {e}")

    def get_user_access_tokens(self, user_id: str) -> List[BankDocument]:
        """Retrieve all active bank documents for a user."""
        try:
            logger.info(f"Retrieving bank documents for user {user_id}")

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot retrieve bank documents")
                raise Exception("CosmosDB connection required for bank data retrieval")

            # Query all active banks for the user
            query = "SELECT * FROM c WHERE c.userId = @userId AND c.status = @status"
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@status", "value": "active"},
            ]

            bank_documents = cosmos_client.query_items(
                Containers.BANKS, query, parameters, user_id
            )

            parsed_documents = []
            for bank_doc in bank_documents:
                try:
                    # Parse as BankDocument
                    document = BankDocument.model_validate(bank_doc)
                    parsed_documents.append(document)
                except Exception as e:
                    logger.error(
                        f"Failed to parse bank document {bank_doc.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(
                f"Found {len(parsed_documents)} active bank documents for user {user_id}"
            )
            return parsed_documents

        except Exception as e:
            logger.error(f"Failed to retrieve bank documents for user {user_id}: {e}")
            raise Exception(f"Failed to retrieve bank documents: {e}")

    async def get_accounts_with_balances(
        self,
        user_id: str,
        account_ids: Optional[List[str]] = None,
        use_cached_balance: bool = True,
    ) -> Dict[str, Any]:
        """
        If use_cached_balance is True, fetch account data from bank documents.
        If use_cached_balance is False, fetch from Plaid API and update bank documents.
        """
        try:
            logger.info(
                f"Getting accounts with balances for user {user_id}, use_cached_balance={use_cached_balance}"
            )

            if use_cached_balance:
                # Fetch from bank documents
                cached_data = self._get_cached_accounts_from_banks(user_id)
                if cached_data and cached_data["accounts"]:
                    logger.info(f"Returning cached account data for user {user_id}")
                    return cached_data
                else:
                    logger.warning(f"No cached account data found for user {user_id}")
                    return {
                        "accounts": [],
                        "total_balance": 0.0,
                        "account_count": 0,
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                        "message": "No cached account data found. Please refresh.",
                    }

            # If not using cached balance, fetch from Plaid and update bank documents
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
                    decrypted_token = TokenEncryption.decrypt_token(
                        token.plaidData["accessToken"]
                    )
                    if account_ids:
                        options = AccountsBalanceGetRequestOptions(
                            account_ids=account_ids
                        )
                        request = AccountsBalanceGetRequest(
                            access_token=decrypted_token, options=options
                        )
                    else:
                        request = AccountsBalanceGetRequest(
                            access_token=decrypted_token
                        )
                    client = await self._get_client(user_id)
                    response = client.accounts_balance_get(request)
                    accounts_data = response["accounts"]

                    bank_accounts = []
                    bank_total_balance = 0.0

                    for account in accounts_data:
                        balance_info = account["balances"]
                        balance = PlaidBalance(
                            available=balance_info.get("available"),
                            current=balance_info.get("current", 0),
                            limit=balance_info.get("limit"),
                            iso_currency_code=balance_info.get(
                                "iso_currency_code", "USD"
                            ),
                            unofficial_currency_code=balance_info.get(
                                "unofficial_currency_code"
                            ),
                        )
                        account_type = (
                            account["type"].value
                            if hasattr(account["type"], "value")
                            else account["type"]
                        )
                        account_subtype = account.get("subtype")
                        if account_subtype and hasattr(account_subtype, "value"):
                            account_subtype = account_subtype.value
                        account_with_balance = PlaidAccountWithBalance(
                            account_id=account["account_id"],
                            name=account["name"],
                            official_name=account.get("official_name"),
                            type=account_type,
                            subtype=account_subtype,
                            mask=account.get("mask"),
                            balances=balance,
                            item_id=token.id,
                            institution_name=token.institutionName,
                            institution_id=token.institutionId,
                        )
                        account_dict = account_with_balance.model_dump()
                        bank_accounts.append(account_dict)
                        all_accounts.append(account_dict)
                        if balance.current is not None:
                            current_balance = float(balance.current)
                            bank_total_balance += current_balance
                            total_balance += current_balance

                    # Update this bank's document with accounts
                    self._update_bank_accounts(
                        user_id, token.id, bank_accounts, bank_total_balance
                    )
                    self._update_token_last_used(user_id, token.id)

                except Exception as e:
                    logger.error(f"Failed to get balances for token {token.id}: {e}")
                    continue

            all_accounts.sort(key=lambda x: x["balances"]["current"] or 0, reverse=True)
            result = {
                "accounts": all_accounts,
                "total_balance": round(total_balance, 2),
                "account_count": len(all_accounts),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(
                f"Retrieved {len(all_accounts)} accounts with total balance ${total_balance:.2f} for user {user_id}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to get accounts with balances for user {user_id}: {e}"
            )
            raise Exception(f"Failed to get account balances: {e}")

    def _get_cached_accounts_from_banks(self, user_id: str) -> Dict[str, Any]:
        """Get cached account data from all bank documents for a user."""
        try:
            query = "SELECT * FROM c WHERE c.userId = @userId"
            parameters = [{"name": "@userId", "value": user_id}]

            bank_documents = cosmos_client.query_items(
                Containers.BANKS, query, parameters, user_id
            )
            all_accounts = []
            total_balance = 0.0

            logger.info(
                f"Found {len(bank_documents)} bank documents for user {user_id}"
            )

            for bank_doc in bank_documents:
                bank_accounts = bank_doc.get("accounts", [])
                all_accounts.extend(bank_accounts)

                # Calculate balance from individual accounts instead of relying on stored metadata
                bank_balance = 0.0
                for account in bank_accounts:
                    balances = account.get("balances", {})
                    current_balance = balances.get("current")
                    if current_balance is not None:
                        bank_balance += float(current_balance)

                logger.info(
                    f"Bank {bank_doc.get('id', 'unknown')}: {len(bank_accounts)} accounts, balance: ${bank_balance:.2f}"
                )
                total_balance += bank_balance

            logger.info(
                f"Total cached balance for user {user_id}: ${total_balance:.2f}"
            )

            return {
                "accounts": all_accounts,
                "total_balance": round(total_balance, 2),
                "account_count": len(all_accounts),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get cached accounts from banks: {e}")
            return {"accounts": [], "total_balance": 0.0, "account_count": 0}

    def _update_bank_accounts(
        self, user_id: str, item_id: str, accounts: List[Dict], total_balance: float
    ) -> bool:
        """Update accounts and summary data for a specific bank document using new schema."""
        try:
            iso_timestamp = datetime.now(timezone.utc).isoformat()

            # Use the new optimized schema fields
            update_data = {
                # Store accounts directly (no nested structure needed)
                "accounts": accounts,
                # Update summary object with new structure
                "summary.accountCount": len(accounts),
                "summary.totalBalance": round(total_balance, 2),
                "summary.lastSync.status": "completed",
                "summary.lastSync.timestamp": iso_timestamp,
                "summary.lastSync.error": None,
                # Update document timestamps
                "updatedAt": iso_timestamp,
                "lastUsedAt": iso_timestamp,
            }

            cosmos_client.update_item(Containers.BANKS, item_id, user_id, update_data)
            logger.info(
                f"Updated bank {item_id} with {len(accounts)} accounts, balance: ${total_balance:.2f}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update bank accounts for {item_id}: {e}")
            return False

    def _update_token_last_used(self, user_id: str, item_id: str) -> bool:
        """Update the lastUsedAt timestamp for a bank document using new schema."""
        try:
            iso_timestamp = datetime.now(timezone.utc).isoformat()
            update_data = {
                "lastUsedAt": iso_timestamp,
                "updatedAt": iso_timestamp,
            }

            cosmos_client.update_item(Containers.BANKS, item_id, user_id, update_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update token last_used for {item_id}: {e}")
            return False

    async def revoke_item_access(self, user_id: str, item_id: str) -> bool:
        """Revoke access to a Plaid item and remove from database."""
        try:
            logger.info(f"Revoking access for user {user_id}, item {item_id}")

            # Get the token first
            tokens = self.get_user_access_tokens(user_id)
            token_to_revoke = None

            for token in tokens:
                if token.id == item_id:
                    token_to_revoke = token
                    break

            if not token_to_revoke:
                logger.warning(f"Token not found for item {item_id}")
                return False

            # Revoke with Plaid API
            decrypted_token = TokenEncryption.decrypt_token(
                token_to_revoke.plaidData["accessToken"]
            )
            request = ItemRemoveRequest(access_token=decrypted_token)

            try:
                client = await self._get_client(user_id)
                client.item_remove(request)
                logger.info(f"Successfully revoked Plaid access for item {item_id}")
            except ValueError as ve:
                logger.warning(
                    f"Plaid credentials not configured, skipping API revocation: {ve}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to revoke with Plaid API: {e}, continuing with local cleanup"
                )

            # Remove bank document from CosmosDB
            cosmos_client.delete_item(Containers.BANKS, item_id, user_id)

            # Clean up transaction data
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
                    if self.revoke_item_access(user_id, token.id):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to revoke item {token.id}: {e}")

            # Clean up transaction data
            transaction_storage_service.delete_all_user_transactions(user_id)

            # Also clean up any remaining banks that might not have been caught
            self._delete_all_user_banks(user_id)

            logger.info(
                f"Removed {success_count}/{len(tokens)} items for user {user_id}"
            )
            return success_count == len(tokens)

        except Exception as e:
            logger.error(f"Failed to remove all user data for {user_id}: {e}")
            return False

    def _delete_all_user_banks(self, user_id: str) -> bool:
        """Delete all bank documents for a user from CosmosDB."""
        try:
            logger.info(f"Deleting all banks for user {user_id}")

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot delete banks")
                return False

            # Query all banks for the user
            query = "SELECT c.id FROM c WHERE c.userId = @userId"
            parameters = [{"name": "@userId", "value": user_id}]

            bank_docs = cosmos_client.query_items("banks", query, parameters, user_id)

            deleted_count = 0
            for bank_doc in bank_docs:
                try:
                    cosmos_client.delete_item(Containers.BANKS, bank_doc["id"], user_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to delete bank document {bank_doc['id']}: {e}"
                    )

            logger.info(
                f"Successfully deleted {deleted_count} banks for user {user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to delete all banks for user {user_id}: {e}")
            return False

    def update_transaction_sync_status(
        self, user_id: str, item_id: str, status: str
    ) -> bool:
        """Update transaction sync status for an item."""
        try:
            update_data = {
                "metadata.transactionSyncStatus": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            cosmos_client.update_item(Containers.BANKS, item_id, user_id, update_data)
            logger.info(f"Updated sync status to '{status}' for item {item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update sync status for {item_id}: {e}")
            return False

    async def sync_all_transactions_for_item(
        self, user_id: str, item_id: str, access_token: str
    ) -> Dict[str, Any]:
        """Initial full sync of transactions for a newly connected item."""
        try:
            logger.info(f"Starting initial transaction sync for item {item_id}")

            # Update status to in progress
            self.update_transaction_sync_status(
                user_id, item_id, TransactionSyncStatus.SYNCING
            )

            # Use transactions/sync for initial historical data
            cursor = None
            added_count = 0
            modified_count = 0
            removed_count = 0

            # Safety counter to prevent infinite loops
            max_iterations = 50
            iteration_count = 0

            while True:
                iteration_count += 1
                if iteration_count > max_iterations:
                    logger.error(
                        f"Transaction sync exceeded {max_iterations} iterations for item {item_id}. Breaking loop."
                    )
                    break

                logger.info(
                    f"Transaction sync iteration {iteration_count} for item {item_id}"
                )

                # Create request - omit cursor for initial sync when None
                if cursor is not None:
                    request = TransactionsSyncRequest(
                        access_token=access_token, cursor=cursor
                    )
                else:
                    request = TransactionsSyncRequest(access_token=access_token)

                client = await self._get_client(user_id)
                response = client.transactions_sync(request)

                # Process transactions
                added = response.get("added", [])
                modified = response.get("modified", [])
                removed = response.get("removed", [])

                logger.info(
                    f"Sync iteration {iteration_count}: added={len(added)}, modified={len(modified)}, removed={len(removed)}"
                )

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

                cursor = response.get("next_cursor")
                has_more = response.get("has_more", False)

                logger.info(
                    f"Sync iteration {iteration_count}: cursor={cursor}, has_more={has_more}"
                )

                if not has_more:
                    logger.info(
                        f"Transaction sync completed for item {item_id} after {iteration_count} iterations"
                    )
                    break

            # Update sync status to complete
            self.update_transaction_sync_status(
                user_id, item_id, TransactionSyncStatus.COMPLETED
            )

            result = {
                "success": True,
                "item_id": item_id,
                "added": added_count,
                "modified": modified_count,
                "removed": removed_count,
                "total": added_count + modified_count + removed_count,
            }

            logger.info(f"Completed initial sync for {item_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to sync transactions for {item_id}: {e}")
            self.update_transaction_sync_status(
                user_id, item_id, TransactionSyncStatus.ERROR
            )
            raise Exception(f"Transaction sync failed: {e}")

    async def refresh_transactions(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Refresh transactions for a specific item using sync API."""
        try:
            logger.info(f"Refreshing transactions for item {item_id}")

            # Get token for this item
            tokens = self.get_user_access_tokens(user_id)
            target_token = None

            for token in tokens:
                if token.id == item_id:
                    target_token = token
                    break

            if not target_token:
                raise Exception(f"No token found for item {item_id}")

            # Decrypt token
            access_token = TokenEncryption.decrypt_token(
                target_token.plaidData["accessToken"]
            )

            # Get cursor from last sync
            cursor = transaction_storage_service.get_last_sync_cursor(user_id, item_id)

            # Create request - omit cursor if None
            if cursor is not None:
                request = TransactionsSyncRequest(
                    access_token=access_token, cursor=cursor
                )
            else:
                request = TransactionsSyncRequest(access_token=access_token)

            client = await self._get_client(user_id)
            response = client.transactions_sync(request)

            # Process new transactions
            added = response.get("added", [])
            modified = response.get("modified", [])
            removed = response.get("removed", [])

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
            new_cursor = response.get("next_cursor")
            if new_cursor:
                transaction_storage_service.update_sync_cursor(
                    user_id, item_id, new_cursor
                )

            result = {
                "success": True,
                "transactions_added": added_count,
                "transactions_modified": modified_count,
                "transactions_removed": removed_count,
                "total_processed": added_count + modified_count + removed_count,
                "item_id": item_id,
                "institution_name": target_token.institutionName or "Unknown",
                "message": f"Refreshed {added_count + modified_count + removed_count} transactions",
            }

            logger.info(f"Transaction refresh completed for {item_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to refresh transactions for {item_id}: {e}")
            raise Exception(f"Transaction refresh failed: {e}")

    async def force_refresh_transactions(
        self, user_id: str, item_id: str
    ) -> Dict[str, Any]:
        """Force refresh by clearing all data and performing complete resync."""
        try:
            logger.info(f"Force refreshing transactions for item {item_id}")

            # Get token for this item
            tokens = self.get_user_access_tokens(user_id)
            target_token = None

            for token in tokens:
                if token.id == item_id:
                    target_token = token
                    break

            if not target_token:
                raise Exception(f"No token found for item {item_id}")

            # Clear existing transaction data
            transaction_storage_service.clear_item_transactions(user_id, item_id)

            # Decrypt token
            access_token = TokenEncryption.decrypt_token(
                target_token.plaidData["accessToken"]
            )

            # Perform complete resync
            sync_result = await self.sync_all_transactions_for_item(
                user_id, item_id, access_token
            )

            result = {
                "success": True,
                "message": f"Force refresh completed - synced {sync_result['total']} transactions",
                "item_id": item_id,
                "institution_name": target_token.institutionName or "Unknown",
                PlaidResponseFields.STATUS: Status.COMPLETED,
                "async_operation": False,
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
                PlaidResponseFields.TRANSACTIONS: transactions,
                "total_count": len(transactions),
                "days_requested": days,
            }

            logger.info(
                f"Retrieved {len(transactions)} transactions for user {user_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get transactions for user {user_id}: {e}")
            raise Exception(f"Failed to get transactions: {e}")

    def get_transactions_by_account(
        self, user_id: str, account_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get transactions for a specific account."""
        try:
            logger.info(
                f"Getting transactions for account {account_id} - last {days} days"
            )

            # Get transactions from storage for specific account
            transactions = transaction_storage_service.get_account_transactions(
                user_id, account_id, days=days
            )

            result = {
                PlaidResponseFields.TRANSACTIONS: transactions,
                "account_id": account_id,
                "total_count": len(transactions),
                "days_requested": days,
            }

            logger.info(
                f"Retrieved {len(transactions)} transactions for account {account_id}"
            )
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
                item_accounts = [
                    acc for acc in accounts if acc.get("item_id") == token.id
                ]

                items.append(
                    {
                        "item_id": token.id,
                        "institution_id": token.institutionId,
                        "institution_name": token.institutionName or "Unknown",
                        "status": token.status,
                        "accounts_count": len(item_accounts),
                        "created_at": token.createdAt,
                        "last_used_at": token.lastUsedAt,
                    }
                )

            logger.info(f"Retrieved {len(items)} Plaid items for user {user_id}")
            return items

        except Exception as e:
            logger.error(f"Failed to get Plaid items for user {user_id}: {e}")
            raise Exception(f"Failed to get Plaid items: {e}")

    async def _sync_transactions_for_stored_item(
        self, user_id: str, item_id: str
    ) -> None:
        """Background task to sync transactions for a newly stored item."""
        try:
            logger.info(
                f"🚀 BACKGROUND TASK STARTED: Transaction sync for user {user_id}, item {item_id}"
            )

            # Get the token from storage
            tokens = self.get_user_access_tokens(user_id)
            logger.info(f"Retrieved {len(tokens)} tokens for user {user_id}")

            target_token = None
            for token in tokens:
                if token.id == item_id:
                    target_token = token
                    break

            if not target_token:
                logger.error(f"❌ No stored token found for item {item_id}")
                return

            logger.info(f"✅ Found target token for item {item_id}")

            # Decrypt the access token
            access_token = TokenEncryption.decrypt_token(
                target_token.plaidData["accessToken"]
            )
            logger.info(f"✅ Successfully decrypted access token for item {item_id}")

            # Perform transaction sync
            result = await self.sync_all_transactions_for_item(
                user_id, item_id, access_token
            )
            logger.info(
                f"🎉 Background transaction sync completed for item {item_id}: {result}"
            )

        except Exception as e:
            logger.error(
                f"❌ Background transaction sync failed for item {item_id}: {e}",
                exc_info=True,
            )
            self.update_transaction_sync_status(
                user_id, item_id, TransactionSyncStatus.ERROR
            )
