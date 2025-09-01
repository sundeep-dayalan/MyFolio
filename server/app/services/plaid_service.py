from inspect import _void
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

from ..exceptions import BankNotFoundError, DatabaseError, PlaidApiException
from .az_key_vault_service import (
    AzureKeyVaultService,
)
from ..services.sync_update_service import sync_update_service

from ..settings import settings
from ..database import cosmos_client
from ..utils.logger import get_logger
from ..models.plaid import (
    PlaidAccountWithBalance,
    PlaidAccountsGetResponse,
    PlaidBalance,
    Account,
    PlaidInstitution,
    PlaidItemGetResponse,
)

from ..models.bank import (
    BankStatus,
    BankSummary,
    BankDocument,
)
from ..models.sync import (
    SyncInfo,
    SyncInitiatorType,
    SyncStatus,
    SyncType,
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
from plaid.exceptions import ApiException

logger = get_logger(__name__)


class PlaidService:
    """Production-ready service for interacting with the Plaid API with dynamic credentials."""

    def __init__(self):
        # Environment will be determined dynamically from stored configuration
        self._clients = {}  # user_id -> client
        self._clients_initialized = {}  # user_id -> bool

    async def _get_client(self, user_id: str) -> plaid_api.PlaidApi:
        """Get Plaid client with dynamic credentials (Just-In-Time initialization)."""
        if user_id in self._clients and self._clients_initialized.get(user_id, False):
            return self._clients[user_id]

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
        client = plaid_api.PlaidApi(api_client)
        self._clients[user_id] = client
        self._clients_initialized[user_id] = True

        logger.info(
            f"Plaid client initialized with dynamic credentials for {environment} environment for user {user_id}"
        )
        return client

    def reset_client(self, user_id: str):
        """Reset client for specific user to force re-initialization with fresh credentials."""
        if user_id in self._clients:
            del self._clients[user_id]
        if user_id in self._clients_initialized:
            del self._clients_initialized[user_id]
        logger.info(
            f"Plaid client reset for user {user_id} - will reinitialize on next use"
        )

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

            # # Get institution info
            # institution_info = await self._get_institution_info_by_item(
            #     user_id, access_token
            # )

            item_request = ItemGetRequest(access_token=access_token)
            # Use .to_dict() for reliable Pydantic validation
            item_response_dict = client.item_get(item_request).to_dict()
            bank_info = PlaidItemGetResponse.model_validate(item_response_dict)

            # Store the access token
            stored_token = await self._store_access_token(
                user_id, access_token, item_id, bank_info
            )

            # Immediately sync account data so accounts are available right away
            # try:
            #     logger.info(f"🔄 Syncing account data immediately for item {item_id}")
            #     await self.get_accounts_with_balances(user_id, use_cached_db_data=False)
            #     logger.info(f"✅ Account data synced successfully for item {item_id}")
            # except Exception as e:
            #     logger.error(f"❌ Failed to sync account data for item {item_id}: {e}")
            #     # Re-raise the exception so connection fails if we can't get account data
            #     raise Exception(
            #         f"Bank connection failed - unable to fetch account data: {str(e)}"
            #     )

            # # Start transaction sync in the background (non-blocking)
            # try:
            #     logger.info(f"🚀 Starting transaction sync for item {item_id}")
            #     await self._sync_transactions_for_stored_item(user_id, item_id)
            #     logger.info(f"✅ Transaction sync completed for item {item_id}")
            # except Exception as e:
            #     logger.error(
            #         f"❌ Background transaction sync failed for item {item_id}: {e}"
            #     )
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
        """
        Get institution information using item access token and return Pydantic models.
        """
        client = await self._get_client(user_id)
        item_response_data = None
        inst_response_data = None

        try:
            # 1. Get Item data from Plaid
            item_request = ItemGetRequest(access_token=access_token)
            # Use .to_dict() for reliable Pydantic validation
            item_response_dict = client.item_get(item_request).to_dict()
            item_response_data = PlaidItemGetResponse.model_validate(item_response_dict)
            institution_id = item_response_data.item.institution_id

            if not institution_id:
                raise ValueError("Institution ID not found in item response.")

            logger.info(f"Got institution_id: {institution_id}")

            # 2. Get Institution data from Plaid
            inst_request = InstitutionsGetByIdRequest(
                institution_id=institution_id, country_codes=[CountryCode("US")]
            )
            inst_response_dict = client.institutions_get_by_id(inst_request).to_dict()
            inst_response_data = PlaidInstitution.model_validate(
                inst_response_dict["institution"]
            )

            logger.info(f"Retrieved institution info: {inst_response_data.name}")

            return {
                "item": item_response_data.item,
                "institution": inst_response_data,
            }

        except ApiException as e:
            logger.error(f"Failed to get full institution info, creating fallback: {e}")

            raise PlaidApiException(e)

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

    async def _store_access_token(
        self,
        user_id: str,
        access_token: str,
        item_id: str,
        bank_info: Dict[str, Any],
    ) -> BankDocument:
        """Store bank data using the corrected BankDocument structure."""
        try:
            logger.info(f"Storing bank data for user {user_id}, item_id: {item_id}")

            if not cosmos_client.is_connected:
                raise DatabaseError("CosmosDB not connected - cannot store bank data")

            # Encrypt the access token
            encrypted_token = await AzureKeyVaultService.encrypt_secret(access_token)

            # Prepare timestamp
            now_iso = datetime.now(timezone.utc).isoformat()

            # Create BankDocument instance directly from validated data
            # This will now pass validation because institution_info is guaranteed
            # to have the correct structure.
            bank_document = BankDocument(
                id=item_id,
                userId=user_id,
                bankInfo=bank_info,
                encryptedAccessToken=encrypted_token,
                status=BankStatus.ACTIVE,
                createdAt=now_iso,
                environment=self.environment,
            )

            # Store document
            document_dict = bank_document.model_dump(mode="json")
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

        except (PlaidApiException, DatabaseError) as e:
            logger.error(f"Specific error storing bank data for user {user_id}: {e}")
            raise e  # Re-raise known exceptions
        except Exception as e:
            logger.error(f"Generic error storing bank data for user {user_id}: {e}")
            # Re-package as a DatabaseError to be handled upstream
            raise DatabaseError(f"Failed to store bank data: {e}")

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

    async def get_bank_access_token(self, user_id: str, item_id: str) -> Optional[str]:
        """
        Retrieve and decrypt the access token for a single, active bank document.
        """
        logger.info(f"Retrieving bank document for user {user_id}, item {item_id}")

        # CHANGE: The generic try...except block is removed. We only handle
        # the "not found" case specifically. Other errors will propagate.

        query = "SELECT * FROM c WHERE c.id = @itemId AND c.userId = @userId AND c.status = @status"
        parameters = [
            {"name": "@itemId", "value": item_id},
            {"name": "@userId", "value": user_id},
            {"name": "@status", "value": "active"},
        ]

        bank_documents = cosmos_client.query_items(
            Containers.BANKS, query, parameters, user_id
        )

        if not bank_documents:
            # This is a specific, expected error, so we handle it.
            raise BankNotFoundError(
                f"Bank connection with item ID '{item_id}' not found."
            )

        bank_doc = bank_documents[0]
        document = BankDocument.model_validate(bank_doc)

        logger.info(f"Successfully retrieved access token for item {item_id}")

        # Let any decryption errors propagate up naturally.
        return await AzureKeyVaultService.decrypt_secret(document.encryptedAccessToken)

    async def get_accounts_with_balances(
        self,
        user_id: str,
        account_ids: Optional[List[str]] = None,
        use_cached_db_data: bool = True,
    ) -> Dict[str, Any]:
        """
        If use_cached_db_data is True, fetch account data from bank documents.
        If use_cached_db_data is False, fetch from Plaid API and update bank documents.
        """
        try:
            logger.info(
                f"Getting accounts with balances for user {user_id}, use_cached_db_data={use_cached_db_data}"
            )

            if use_cached_db_data:
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
                    decrypted_token = await AzureKeyVaultService.decrypt_secret(
                        token.plaidData["encryptedAccessToken"]
                    )

                    # Set it to 90 days ago to ensure we get acceptable balance data (Only applicable for Capital One)
                    min_last_updated = datetime.now(timezone.utc) - timedelta(days=90)

                    if account_ids:
                        options = AccountsBalanceGetRequestOptions(
                            account_ids=account_ids,
                            min_last_updated_datetime=min_last_updated,
                        )
                        request = AccountsBalanceGetRequest(
                            access_token=decrypted_token, options=options
                        )
                    else:
                        options = AccountsBalanceGetRequestOptions(
                            min_last_updated_datetime=min_last_updated
                        )
                        request = AccountsBalanceGetRequest(
                            access_token=decrypted_token, options=options
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
                    # self._update_bank_accounts(
                    #     user_id, token.id, bank_accounts, bank_total_balance
                    # )
                    self._update_token_last_used(user_id, token.id)

                except Exception as e:
                    logger.error(f"Failed to get balances for token {token.id}: {e}")
                    raise Exception(
                        f"Failed to fetch account balances from Plaid: {str(e)}"
                    )

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

    async def sync_accounts_for_item(
        self,
        user_id: str,
        item_id: str,
        account_ids: Optional[List[str]] = None,
    ) -> None:
        """
        Fetches the latest account and balance data from Plaid for a specific item
        and updates the database with the new information.
        """
        logger.info(f"Starting account sync for user {user_id}, item {item_id}")

        try:
            await sync_update_service.update_sync_status(
                user_id=user_id,
                item_id=item_id,
                sync_type=SyncType.ACCOUNTS,
                status=SyncStatus.SYNCING,
                initiator_type=SyncInitiatorType.USER,
                initiator_id=user_id,
            )
            await cosmos_client.ensure_connected()
            # 1. Preparation
            access_token = await self.get_bank_access_token(user_id, item_id)

            min_last_updated = datetime.now(timezone.utc) - timedelta(days=90)
            options_args = {"min_last_updated_datetime": min_last_updated}
            if account_ids:
                options_args["account_ids"] = account_ids

            options = AccountsBalanceGetRequestOptions(**options_args)
            request = AccountsBalanceGetRequest(
                access_token=access_token, options=options
            )

            # 2. Plaid API Call and Pydantic Parsing
            client = await self._get_client(user_id)
            api_response = client.accounts_balance_get(request)
            response_data = api_response.to_dict()
            plaid_data = PlaidAccountsGetResponse.model_validate(response_data)

            # 3. Update Database
            await self._update_bank_accounts(user_id, item_id, plaid_data.accounts)

            await sync_update_service.update_sync_status(
                user_id=user_id,
                item_id=item_id,
                sync_type=SyncType.ACCOUNTS,
                status=SyncStatus.COMPLETED,
                initiator_type=SyncInitiatorType.USER,
                initiator_id=user_id,
            )

            sync_update_service

            logger.info(
                f"Successfully synced accounts for user {user_id}, item {item_id}"
            )

        except Exception as e:
            await sync_update_service.update_sync_status(
                user_id=user_id,
                item_id=item_id,
                sync_type=SyncType.ACCOUNTS,
                status=SyncStatus.ERROR,
                initiator_type=SyncInitiatorType.USER,
                initiator_id=user_id,
                error=e,
            )
            # Re-raise the exception to be handled by the main middleware
            if isinstance(e, ApiException):
                raise PlaidApiException(e)
            raise e

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

    # def _update_bank_accounts(
    #     self, user_id: str, item_id: str, accounts: List[Dict], total_balance: float
    # ) -> bool:
    #     """Update accounts and summary data for a specific bank document using new schema."""
    #     try:
    #         iso_timestamp = datetime.now(timezone.utc).isoformat()

    #         # Use the new optimized schema fields
    #         update_data = {
    #             # Store accounts directly (no nested structure needed)
    #             "accounts": accounts,
    #             # Update summary object with new structure
    #             "summary.accountCount": len(accounts),
    #             "summary.totalBalance": round(total_balance, 2),
    #             "summary.lastSync.status": "completed",
    #             "summary.lastSync.timestamp": iso_timestamp,
    #             "summary.lastSync.error": None,
    #             # Update document timestamps
    #             "updatedAt": iso_timestamp,
    #             "lastUsedAt": iso_timestamp,
    #         }

    #         cosmos_client.update_item(Containers.BANKS, item_id, user_id, update_data)
    #         logger.info(
    #             f"Updated bank {item_id} with {len(accounts)} accounts, balance: ${total_balance:.2f}"
    #         )
    #         return True
    #     except Exception as e:
    #         logger.error(f"Failed to update bank accounts for {item_id}: {e}")
    #         return False

    async def _update_bank_accounts(
        self,
        user_id: str,
        item_id: str,
        new_accounts: List[Account],
    ) -> bool:
        """
        Intelligently merges new account data into the bank document and updates
        the summary fields for data consistency using the new Pydantic models.
        """
        try:
            # 1. Fetch the existing bank document.
            bank_document = cosmos_client.get_item(Containers.BANKS, item_id, user_id)
            if not bank_document:
                raise BankNotFoundError(
                    f"Bank document not found for item_id: {item_id}"
                )

            # 2. Merge new accounts with existing ones.
            existing_accounts = bank_document.get("accounts", [])
            accounts_map = {acc["account_id"]: acc for acc in existing_accounts}

            for account_model in new_accounts:
                new_account_dict = account_model.model_dump(mode="json")
                accounts_map[account_model.account_id] = new_account_dict

            final_accounts_list = list(accounts_map.values())

            # 3. Calculate summary metrics from the final list.
            account_count = len(final_accounts_list)
            total_balance = sum(
                acc.get("balances", {}).get("current") or 0.0
                for acc in final_accounts_list
            )

            # 4. Prepare the final, properly nested update payload.
            # IMPROVED: Create a BankSummary instance for a more robust update.
            new_summary = BankSummary(
                account_count=account_count, total_balance=round(total_balance, 2)
            )

            update_data = {
                "accounts": final_accounts_list,
                "summary": new_summary.model_dump(
                    mode="json"
                ),  # Update the whole summary object
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }

            cosmos_client.update_item(Containers.BANKS, item_id, user_id, update_data)

            logger.info(
                f"Successfully updated bank accounts and summary for item {item_id}: "
                f"Count={account_count}, Balance=${total_balance:.2f}."
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to intelligently update bank accounts for {item_id}: {e}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to update account data in the database: {e}")

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
            decrypted_token = await AzureKeyVaultService.decrypt_secret(
                token_to_revoke.plaidData["encryptedAccessToken"]
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
            access_token = await AzureKeyVaultService.decrypt_secret(
                target_token.plaidData["encryptedAccessToken"]
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
            access_token = await AzureKeyVaultService.decrypt_secret(
                target_token.plaidData["encryptedAccessToken"]
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
            access_token = await AzureKeyVaultService.decrypt_secret(
                target_token.plaidData["encryptedAccessToken"]
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
