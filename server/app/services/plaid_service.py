import asyncio
from inspect import _void
from typing import List, Dict, Any, Optional, Tuple

from fastapi import BackgroundTasks, Depends
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
from datetime import date as DateType
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..dependencies import get_current_user

from ..exceptions import (
    AccountFetchError,
    BankNotFoundError,
    DatabaseError,
    PlaidApiException,
)
from .az_key_vault_service import (
    AzureKeyVaultService,
)
from ..services.sync_update_service import sync_update_service

from ..settings import settings
from ..database import cosmos_client
from ..utils.logger import get_logger
from ..models.plaid import (
    Counterparty,
    Location,
    PersonalFinanceCategory,
    PlaidAccount,
    PlaidAccountWithBalance,
    PlaidAccountsGetResponse,
    PlaidBalance,
    Account,
    PlaidInstitution,
    PlaidItemGetResponse,
    RemovedTransaction,
    SystemMetadata,
    Transaction,
    TransactionDocument,
    TransactionsUpdateResponse,
)

from ..models.bank import (
    BankStatus,
    BankSummary,
    BankDocument,
    GetAccountsResponse,
    GetBanksResponse,
    InstitutionDetail,
    PartialAccountInfo,
    PartialBankDocument,
    PartialBankInfo,
    PartialItem,
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
        self, user_id: str, public_token: str, background_tasks: BackgroundTasks
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

            item_request = ItemGetRequest(access_token=access_token)
            # Use .to_dict() for reliable Pydantic validation
            item_response_dict = client.item_get(item_request).to_dict()
            bank_info = PlaidItemGetResponse.model_validate(item_response_dict)

            # Store the access token
            stored_token = await self._store_access_token(
                user_id, access_token, item_id, bank_info
            )
            # Chain the sync operations: accounts first, then transactions
            background_tasks.add_task(
                self.sync_accounts_in_background, item_id, user_id, True
            )
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
                accounts=[],
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

    async def sync_accounts_for_item(
        self,
        item_id: str,
        user_id: str,
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

    def sync_accounts_in_background(
        self, item_id: str, user_id: str, chain_transactions: bool = False
    ) -> None:
        """
        Synchronous wrapper for sync_accounts_for_item to be used with background tasks.
        FastAPI's background_tasks.add_task() expects synchronous functions.

        Args:
            item_id: The bank item ID
            user_id: The user ID
            chain_transactions: If True, will also sync transactions after accounts sync completes
        """
        try:

            # Create a new event loop for the background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run accounts sync
            loop.run_until_complete(self.sync_accounts_for_item(item_id, user_id))

            # If chaining is requested, run transactions sync after accounts sync succeeds
            if chain_transactions:
                logger.info(
                    f"Accounts sync completed, starting transactions sync for user {user_id}, item {item_id}"
                )
                loop.run_until_complete(self.sync_transactions(item_id, user_id))

        except Exception as e:
            logger.error(
                f"Background sync failed for user {user_id}, item {item_id}: {e}"
            )
        finally:
            loop.close()

    def sync_transactions_in_background(self, item_id: str, user_id: str) -> None:
        """
        Synchronous wrapper for sync_transactions to be used with background tasks.
        FastAPI's background_tasks.add_task() expects synchronous functions.
        """
        try:
            # Create a new event loop for the background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.sync_transactions(item_id, user_id))
        except Exception as e:
            logger.error(
                f"Background transaction sync failed for user {user_id}, item {item_id}: {e}"
            )
        finally:
            loop.close()

    async def get_accounts(self, user_id: str) -> GetAccountsResponse:
        """
        Get cached account data, grouped by institution.
        This implementation is optimized for performance and concurrency.
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Valid user_id is required")

        try:
            # Optimized connection check with timeout to prevent blocking
            await cosmos_client.ensure_connected()

            # Updated query to fetch institution details
            query = """
                SELECT c.id, c.accounts, c.updatedAt, c.status, c.bankInfo, c.syncs
                FROM c 
                WHERE c.userId = @userId 
                AND c.status = @status
                """
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@status", "value": BankStatus.ACTIVE},
            ]

            bank_documents_raw = cosmos_client.query_items(
                Containers.BANKS, query, parameters, user_id
            )

            if not bank_documents_raw:
                logger.info(f"No active bank documents found for user {user_id}")
                return GetAccountsResponse(
                    institutions=[],
                    banks_count=0,
                    accounts_count=0,
                )

            bank_documents: List[PartialBankDocument] = []
            for bank_doc_raw in bank_documents_raw:
                try:
                    parsed_doc = PartialBankDocument.model_validate(bank_doc_raw)
                    bank_documents.append(parsed_doc)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse bank document {bank_doc_raw.get('id', 'unknown')}: {e}"
                    )
                    raise e

            # Process all valid bank documents concurrently
            tasks = [self._process_bank_document(doc) for doc in bank_documents]
            results: List[Optional[InstitutionDetail]] = await asyncio.gather(*tasks)

            # Aggregate successful results into the final response structure
            institutions = [res for res in results if res is not None]
            overall_account_count = sum(inst.account_count for inst in institutions)

            logger.info(
                f"Account aggregation complete for user {user_id}: "
                f"Institutions processed: {len(institutions)}/{len(bank_documents)}, "
                f"Total accounts: {overall_account_count}, "
            )

            response_data = {
                "institutions": institutions,
                "accounts_count": overall_account_count,
                "banks_count": len(institutions),
            }

            return GetAccountsResponse.model_validate(response_data)

        except Exception as e:
            logger.error(
                f"Unexpected error getting accounts for user {user_id}: {e}",
                exc_info=True,
            )
            raise AccountFetchError(f"Failed to get accounts: {e}")

    @staticmethod
    async def _process_bank_document(
        bank_doc: PartialBankDocument,
    ) -> Optional[InstitutionDetail]:
        """
        Processes a single bank document and transforms it into a structured InstitutionDetail object.
        Returns None if processing fails.
        """
        item_id = bank_doc.id
        try:
            valid_accounts: List[PlaidAccountWithBalance] = []
            bank_balance = 0.0

            for account in bank_doc.accounts or []:
                if account.balances.current is not None:
                    try:
                        balance_value = float(account.balances.current)
                        bank_balance += balance_value
                        valid_accounts.append(account)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Invalid balance for account {account.account_id} in item {item_id}: {e}"
                        )

            # Find the first available logo from any account
            logo = next((acc.logo for acc in valid_accounts if acc.logo), None)
            return InstitutionDetail(
                name=bank_doc.bankInfo.item.institution_name,
                logo=logo,
                status=bank_doc.status,
                account_count=len(valid_accounts),
                accounts=valid_accounts,
                last_account_sync=bank_doc.syncs.accounts,
            )
        except Exception as e:
            logger.error(
                f"Error processing bank document for item {item_id}: {e}", exc_info=True
            )
            return None

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

            # 4. Prepare the final, properly nested update payload.
            # IMPROVED: Create a BankSummary instance for a more robust update.
            new_summary = BankSummary(account_count=account_count)

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
                f"Count={account_count}."
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

    async def delete_bank(self, user_id: str, bank_id: str) -> bool:
        """Delete a Plaid item and remove from database."""
        try:
            logger.info(f"Deleting bank for user {user_id}, item {bank_id}")
            await cosmos_client.ensure_connected()

            access_token = await self.get_bank_access_token(user_id, bank_id)
            request = ItemRemoveRequest(access_token=access_token)

            try:
                client = await self._get_client(user_id)
                client.item_remove(request)
                logger.info(f"Successfully revoked Plaid access for item {bank_id}")
            except ValueError as ve:
                logger.warning(
                    f"Plaid credentials not configured, skipping API revocation: {ve}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to revoke with Plaid API: {e}, continuing with local cleanup"
                )

            # Remove bank document from CosmosDB
            cosmos_client.delete_item(Containers.BANKS, bank_id, user_id)

            # Clean up transaction data
            await transaction_storage_service.delete_item_transactions(user_id, bank_id)

            logger.info(f"Successfully cleaned up all data for item {bank_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke item access for {bank_id}: {e}")
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
                    if self.delete_bank(user_id, token.id):
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

    async def get_banks(self, user_id: str) -> GetBanksResponse:
        """Get summary of user's connected Plaid items."""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Valid user_id is required")

        try:
            await cosmos_client.ensure_connected()

            query = """
                SELECT c.id, c.bankInfo, c.status, c.updatedAt, c.accounts
                FROM c 
                WHERE c.userId = @userId 
                AND c.status = @status
                """
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@status", "value": BankStatus.ACTIVE},
            ]

            bank_documents_raw = cosmos_client.query_items(
                Containers.BANKS, query, parameters, user_id
            )

            if not bank_documents_raw:
                logger.info(f"No active bank documents found for user {user_id}")
                return GetBanksResponse(
                    banks=[],
                    banks_count=0,
                )

            banks = []
            for bank_doc_raw in bank_documents_raw:
                try:
                    # Extract accounts and convert to PartialAccountInfo
                    accounts = []
                    if "accounts" in bank_doc_raw and bank_doc_raw["accounts"]:
                        for account_data in bank_doc_raw["accounts"]:
                            partial_account = PartialAccountInfo(
                                account_id=account_data.get("account_id", ""),
                                name=account_data.get("name", ""),
                                official_name=account_data.get("official_name", ""),
                                type=account_data.get("type", ""),
                                subtype=account_data.get("subtype", ""),
                                mask=account_data.get("mask"),
                                logo=account_data.get("logo"),
                            )
                            accounts.append(partial_account)

                    partial_item = PartialItem(
                        item_id=bank_doc_raw["bankInfo"]["item"]["item_id"],
                        institution_id=bank_doc_raw["bankInfo"]["item"][
                            "institution_id"
                        ],
                        institution_name=bank_doc_raw["bankInfo"]["item"][
                            "institution_name"
                        ],
                        accounts=accounts,
                    )
                    partial_bank_info = PartialBankInfo(item=partial_item)
                    banks.append(partial_bank_info)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse bank document {bank_doc_raw.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(
                f"Banks retrieval complete for user {user_id}: "
                f"Banks count: {len(banks)}"
            )

            return GetBanksResponse(
                banks=banks,
                banks_count=len(banks),
            )

        except Exception as e:
            logger.error(
                f"Unexpected error getting banks for user {user_id}: {e}",
                exc_info=True,
            )
            raise AccountFetchError(f"Failed to get banks: {e}")

    async def sync_transactions(self, item_id: str, user_id: str) -> None:
        """
        Fetches incremental transaction updates for a Plaid item and stores them
        in the 'transactions' container.

        This process is idempotent and uses a cursor to only fetch new changes.
        It handles added, modified, and removed (soft delete) transactions.
        """
        logger.info(
            f"Starting transaction sync for user_id='{user_id}', item_id='{item_id}'"
        )
        await cosmos_client.ensure_connected()
        current_cursor = None
        try:
            # 1. SETUP: Fetch current state and set status to SYNCING
            bank_doc_raw = cosmos_client.get_item(Containers.BANKS, item_id, user_id)
            if not bank_doc_raw:
                raise BankNotFoundError(
                    f"Bank connection with item ID '{item_id}' not found."
                )

            bank_doc = BankDocument.model_validate(bank_doc_raw)
            current_cursor = bank_doc.syncs.transactions.next_cursor

            await sync_update_service.update_sync_status(
                user_id=user_id,
                item_id=item_id,
                sync_type=SyncType.TRANSACTIONS,
                status=SyncStatus.SYNCING,
                initiator_type=SyncInitiatorType.SYSTEM,
                initiator_id="PlaidService",
            )

            access_token = await self.get_bank_access_token(user_id, item_id)
            client = await self._get_client(user_id)

            # 2. PAGINATION LOOP: Fetch all available updates from Plaid
            has_more = True
            while has_more:
                request = None
                if current_cursor:
                    logger.info(
                        f"Fetching transaction sync page for item '{item_id}' with cursor '{current_cursor}'"
                    )
                    request = TransactionsSyncRequest(
                        access_token=access_token,
                        cursor=current_cursor,
                        count=500,
                    )
                else:
                    logger.info(
                        f"Fetching initial transaction sync page for item '{item_id}'"
                    )
                    request = TransactionsSyncRequest(
                        access_token=access_token,
                        count=500,
                    )

                response = client.transactions_sync(request).to_dict()

                added = response.get("added", [])
                modified = response.get("modified", [])
                removed = response.get("removed", [])

                logger.info(
                    f"Sync page for item '{item_id}': "
                    f"{len(added)} added, {len(modified)} modified, {len(removed)} removed."
                )
                next_page_cursor = response.get("next_cursor")

                # 3. PROCESS CHANGES: Transform and save to the database
                if added or modified:
                    docs_to_upsert = await self._transform_transactions(
                        user_id=user_id,
                        item_id=item_id,
                        plaid_transactions=added + modified,
                        sync_cursor=next_page_cursor,
                    )
                    if docs_to_upsert:
                        await transaction_storage_service.upsert_transactions(
                            docs_to_upsert
                        )

                if removed:
                    transaction_ids_to_remove = [tx["transaction_id"] for tx in removed]
                    if transaction_ids_to_remove:
                        await transaction_storage_service.soft_delete_transactions(
                            user_id=user_id,
                            transaction_ids=transaction_ids_to_remove,
                            sync_cursor=next_page_cursor,
                        )

                has_more = response["has_more"]
                current_cursor = next_page_cursor

            # 4. FINALIZE: Update sync status to COMPLETED
            await sync_update_service.update_sync_status(
                user_id=user_id,
                item_id=item_id,
                sync_type=SyncType.TRANSACTIONS,
                status=SyncStatus.COMPLETED,
                next_cursor=current_cursor,
            )
            logger.info(
                f"Successfully completed transaction sync for item_id='{item_id}'"
            )

        except Exception as e:
            # 5. ERROR HANDLING: Log error and update sync status
            error_message = str(e)
            if isinstance(e, ApiException):
                error_body = json.loads(e.body)
                error_message = error_body.get("error_message", "Plaid API Error")
                logger.error(
                    f"Plaid API error during transaction sync for item '{item_id}': {e.body}",
                    exc_info=True,
                )
            else:
                logger.error(
                    f"Error during transaction sync for item '{item_id}': {e}",
                    exc_info=True,
                )

            await sync_update_service.update_sync_status(
                user_id=user_id,
                item_id=item_id,
                sync_type=SyncType.TRANSACTIONS,
                status=SyncStatus.ERROR,
                error=error_message,
                next_cursor=current_cursor,
            )
            raise

    async def _transform_transactions(
        self,
        user_id: str,
        item_id: str,
        plaid_transactions: List[
            Transaction | TransactionsUpdateResponse | RemovedTransaction
        ],
        sync_cursor: str,
    ) -> List[TransactionDocument]:
        """
        Transforms raw Plaid transaction objects into the TransactionDocument model.
        This version is resilient to validation errors and uses a robust instantiation pattern.
        """
        transformed_docs = []

        for tx_data in plaid_transactions:
            tx_id = tx_data.get("transaction_id")
            if not tx_id:
                logger.warning("Skipping transaction with no ID.")
                continue

            try:
                # --- Resilient Date Handling ---
                raw_trans_date = tx_data["date"]
                if isinstance(raw_trans_date, DateType):
                    trans_date = raw_trans_date
                elif isinstance(raw_trans_date, str):
                    trans_date = DateType.fromisoformat(raw_trans_date)
                else:
                    raise TypeError(
                        f"Unsupported type for 'date': {type(raw_trans_date)}"
                    )

                raw_auth_date = tx_data.get("authorized_date")
                auth_date = None
                if isinstance(raw_auth_date, DateType):
                    auth_date = raw_auth_date
                elif isinstance(raw_auth_date, str):
                    auth_date = DateType.fromisoformat(raw_auth_date)

                # --- Prepare a dictionary using the model's ALIASES (camelCase) ---
                # This directly addresses the validation error by providing the keys Pydantic expects.
                now_utc = datetime.now(timezone.utc)
                doc_data = {
                    "id": f"user-{user_id}-transaction-{tx_id}",
                    "userId": user_id,
                    "type": "transaction",
                    "plaidTransactionId": tx_id,
                    "plaidAccountId": tx_data["account_id"],
                    "plaidItemId": item_id,
                    "_meta": SystemMetadata(
                        created_at=now_utc,
                        updated_at=now_utc,
                        is_removed=False,
                        source_sync_cursor=sync_cursor,
                    ),
                    "description": tx_data.get("merchant_name") or tx_data.get("name"),
                    "amount": tx_data["amount"],
                    "currency": tx_data.get("iso_currency_code"),
                    "date": trans_date,
                    "authorizedDate": auth_date,
                    "isPending": tx_data["pending"],
                    "category": PersonalFinanceCategory.model_validate(
                        tx_data.get("personal_finance_category") or {}
                    ),
                    "paymentChannel": tx_data["payment_channel"],
                    "location": Location.model_validate(tx_data.get("location") or {}),
                    "counterparties": [
                        Counterparty.model_validate(c)
                        for c in tx_data.get("counterparties", [])
                    ],
                    "pendingTransactionId": tx_data.get("pending_transaction_id"),
                    "originalDescription": tx_data.get("original_description"),
                    "_rawPlaidData": self._validate_transaction_data(tx_data),
                }

                # --- Instantiate the model using the standard constructor ---
                # Pydantic will use the aliases to populate the correct fields.
                doc = TransactionDocument(**doc_data)
                transformed_docs.append(doc)

            except (ValueError, TypeError, KeyError) as e:
                logger.error(
                    f"Skipping transaction {tx_id} due to data parsing/missing key error: {e}"
                )
                continue
            except Exception as e:
                logger.error(f"Pydantic validation failed for transaction {tx_id}: {e}")
                continue

        return transformed_docs

    def _validate_transaction_data(
        self, tx_data: Dict[str, Any]
    ) -> Transaction | TransactionsUpdateResponse | RemovedTransaction:
        """
        Validates transaction data and returns the appropriate model type.
        Tries Transaction first, then falls back to RemovedTransaction if needed.
        """
        try:
            # First, try to validate as a full Transaction
            return Transaction.model_validate(tx_data)
        except Exception as transaction_error:
            logger.debug(f"Failed to validate as Transaction: {transaction_error}")

            try:
                # If that fails, try as TransactionsUpdateResponse
                return TransactionsUpdateResponse.model_validate(tx_data)
            except Exception as update_error:
                logger.debug(
                    f"Failed to validate as TransactionsUpdateResponse: {update_error}"
                )

                try:
                    # If that fails too, try as RemovedTransaction
                    return RemovedTransaction.model_validate(tx_data)
                except Exception as removed_error:
                    logger.warning(
                        f"Failed to validate transaction data as any known type. "
                        f"Transaction: {transaction_error}, Update: {update_error}, Removed: {removed_error}. "
                        f"Falling back to RemovedTransaction with available data."
                    )

                    # As a last resort, create a minimal RemovedTransaction
                    return RemovedTransaction(
                        transaction_id=tx_data.get("transaction_id", "unknown"),
                        account_id=tx_data.get("account_id", "unknown"),
                    )
