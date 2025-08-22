"""
Plaid service for Azure-based backend
Handles Plaid API integration with Azure Cosmos DB storage
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

from ..database import get_document_service
from ..utils.security import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)


class PlaidService:
    """Service for handling Plaid API operations"""
    
    def __init__(self):
        self.document_service = get_document_service()
        self.secret_client = self._initialize_secret_client()
        self._plaid_client: Optional[plaid_api.PlaidApi] = None
        self._plaid_client_id: Optional[str] = None
        self._plaid_secret: Optional[str] = None
        self._plaid_env: str = os.getenv('PLAID_ENV', 'sandbox')
    
    def _initialize_secret_client(self) -> Optional[SecretClient]:
        """Initialize Azure Key Vault secret client"""
        try:
            key_vault_url = os.getenv('KEY_VAULT_URL')
            if not key_vault_url:
                logger.warning("KEY_VAULT_URL not configured, using environment variables")
                return None
            
            credential = DefaultAzureCredential()
            return SecretClient(vault_url=key_vault_url, credential=credential)
        except Exception as e:
            logger.error(f"Failed to initialize Key Vault client: {str(e)}")
            return None
    
    async def _get_secret(self, secret_name: str, env_var_name: str) -> Optional[str]:
        """Get secret from Key Vault or environment variable"""
        try:
            if self.secret_client:
                secret = self.secret_client.get_secret(secret_name)
                return secret.value
        except Exception as e:
            logger.warning(f"Failed to get secret '{secret_name}' from Key Vault: {str(e)}")
        
        # Fallback to environment variable
        return os.getenv(env_var_name)
    
    async def get_plaid_credentials(self) -> tuple[str, str]:
        """Get Plaid API credentials"""
        if not self._plaid_client_id:
            self._plaid_client_id = await self._get_secret('plaid-client-id', 'PLAID_CLIENT_ID')
        if not self._plaid_secret:
            self._plaid_secret = await self._get_secret('plaid-secret', 'PLAID_SECRET')
        
        if not self._plaid_client_id or not self._plaid_secret:
            raise ValueError("Plaid credentials not configured")
        
        return self._plaid_client_id, self._plaid_secret
    
    async def get_plaid_client(self) -> plaid_api.PlaidApi:
        """Get Plaid API client"""
        if self._plaid_client is None:
            client_id, secret = await self.get_plaid_credentials()
            
            # Configure Plaid client
            configuration = Configuration(
                host=self._get_plaid_host(),
                api_key={
                    'clientId': client_id,
                    'secret': secret
                }
            )
            api_client = ApiClient(configuration)
            self._plaid_client = plaid_api.PlaidApi(api_client)
        
        return self._plaid_client
    
    def _get_plaid_host(self):
        """Get Plaid host URL based on environment"""
        from plaid.configuration import Environment
        
        env_mapping = {
            'sandbox': Environment.sandbox,
            'development': Environment.development,
            'production': Environment.production
        }
        
        return env_mapping.get(self._plaid_env, Environment.sandbox)
    
    async def create_link_token(self, user_id: str, products: List[str]) -> str:
        """Create Plaid Link token"""
        try:
            client = await self.get_plaid_client()
            
            # Convert string products to Plaid Products enum
            plaid_products = []
            product_mapping = {
                'transactions': Products('transactions'),
                'accounts': Products('accounts'),
                'identity': Products('identity'),
                'investments': Products('investments'),
                'assets': Products('assets'),
                'liabilities': Products('liabilities')
            }
            
            for product in products:
                if product in product_mapping:
                    plaid_products.append(product_mapping[product])
            
            request = LinkTokenCreateRequest(
                products=plaid_products,
                client_name="Sage Financial Management",
                country_codes=[CountryCode('US')],
                language='en',
                user=LinkTokenCreateRequestUser(client_user_id=user_id)
            )
            
            response = client.link_token_create(request)
            logger.info(f"Link token created for user: {user_id}")
            return response['link_token']
            
        except Exception as e:
            logger.error(f"Error creating Plaid link token: {str(e)}")
            raise
    
    async def exchange_public_token(self, public_token: str, user_id: str) -> Dict[str, Any]:
        """Exchange public token for access token"""
        try:
            client = await self.get_plaid_client()
            
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = client.item_public_token_exchange(request)
            
            access_token = response['access_token']
            item_id = response['item_id']
            
            # Store encrypted access token
            await self._store_access_token(user_id, access_token, item_id)
            
            # Get account information
            accounts = await self._fetch_and_store_accounts(access_token, user_id)
            
            logger.info(f"Public token exchanged for user: {user_id}")
            return {
                'item_id': item_id,
                'accounts': accounts
            }
            
        except Exception as e:
            logger.error(f"Error exchanging Plaid public token: {str(e)}")
            raise
    
    async def _store_access_token(self, user_id: str, access_token: str, item_id: str):
        """Store encrypted access token in database"""
        try:
            # Check if token already exists
            existing_token = await self.document_service.get_document(
                'plaid_tokens',
                f"{user_id}_{item_id}",
                user_id
            )
            
            token_data = {
                'id': f"{user_id}_{item_id}",
                'userId': user_id,
                'item_id': item_id,
                'access_token': encrypt_token(access_token),
                'created_at': existing_token['created_at'] if existing_token else datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing_token:
                await self.document_service.update_document('plaid_tokens', token_data)
            else:
                await self.document_service.create_document('plaid_tokens', token_data)
            
            logger.info(f"Access token stored for user: {user_id}, item: {item_id}")
            
        except Exception as e:
            logger.error(f"Error storing access token: {str(e)}")
            raise
    
    async def _get_access_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all access tokens for a user"""
        try:
            tokens = await self.document_service.get_user_documents('plaid_tokens', user_id)
            
            # Decrypt access tokens
            for token in tokens:
                token['access_token'] = decrypt_token(token['access_token'])
            
            return tokens
            
        except Exception as e:
            logger.error(f"Error getting access tokens for user {user_id}: {str(e)}")
            raise
    
    async def _fetch_and_store_accounts(self, access_token: str, user_id: str) -> List[Dict[str, Any]]:
        """Fetch and store account information"""
        try:
            client = await self.get_plaid_client()
            
            request = AccountsGetRequest(access_token=access_token)
            response = client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                account_data = {
                    'id': account['account_id'],
                    'userId': user_id,
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'official_name': account.get('official_name'),
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'balances': {
                        'available': account['balances'].get('available'),
                        'current': account['balances'].get('current'),
                        'limit': account['balances'].get('limit'),
                        'iso_currency_code': account['balances'].get('iso_currency_code')
                    },
                    'mask': account.get('mask'),
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                # Store or update account
                existing_account = await self.document_service.get_document(
                    'accounts',
                    account['account_id'],
                    user_id
                )
                
                if existing_account:
                    account_data['created_at'] = existing_account['created_at']
                    await self.document_service.update_document('accounts', account_data)
                else:
                    account_data['created_at'] = datetime.utcnow().isoformat()
                    await self.document_service.create_document('accounts', account_data)
                
                accounts.append(account_data)
            
            logger.info(f"Stored {len(accounts)} accounts for user: {user_id}")
            return accounts
            
        except Exception as e:
            logger.error(f"Error fetching and storing accounts: {str(e)}")
            raise
    
    async def get_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get accounts for a user"""
        try:
            # First try to get from database
            accounts = await self.document_service.get_user_documents('accounts', user_id)
            
            if not accounts:
                # If no accounts in database, fetch from Plaid
                tokens = await self._get_access_tokens(user_id)
                all_accounts = []
                
                for token in tokens:
                    token_accounts = await self._fetch_and_store_accounts(
                        token['access_token'],
                        user_id
                    )
                    all_accounts.extend(token_accounts)
                
                return all_accounts
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting accounts for user {user_id}: {str(e)}")
            raise
    
    async def get_transactions(self, user_id: str, start_date: Optional[str] = None, 
                             end_date: Optional[str] = None, count: int = 500, 
                             offset: int = 0) -> List[Dict[str, Any]]:
        """Get transactions for a user"""
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now().date()
            else:
                end_date = datetime.fromisoformat(end_date).date()
            
            if not start_date:
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime.fromisoformat(start_date).date()
            
            tokens = await self._get_access_tokens(user_id)
            all_transactions = []
            
            client = await self.get_plaid_client()
            
            for token in tokens:
                try:
                    request = TransactionsGetRequest(
                        access_token=token['access_token'],
                        start_date=start_date,
                        end_date=end_date,
                        count=count,
                        offset=offset
                    )
                    
                    response = client.transactions_get(request)
                    
                    for transaction in response['transactions']:
                        transaction_data = {
                            'id': transaction['transaction_id'],
                            'userId': user_id,
                            'transaction_id': transaction['transaction_id'],
                            'account_id': transaction['account_id'],
                            'amount': transaction['amount'],
                            'iso_currency_code': transaction.get('iso_currency_code'),
                            'unofficial_currency_code': transaction.get('unofficial_currency_code'),
                            'category': transaction.get('category', []),
                            'category_id': transaction.get('category_id'),
                            'date': transaction['date'].isoformat(),
                            'datetime': transaction.get('datetime'),
                            'authorized_date': transaction.get('authorized_date'),
                            'authorized_datetime': transaction.get('authorized_datetime'),
                            'location': transaction.get('location', {}),
                            'name': transaction['name'],
                            'merchant_name': transaction.get('merchant_name'),
                            'payment_channel': transaction['payment_channel'],
                            'pending': transaction['pending'],
                            'pending_transaction_id': transaction.get('pending_transaction_id'),
                            'account_owner': transaction.get('account_owner'),
                            'transaction_type': transaction.get('transaction_type'),
                            'transaction_code': transaction.get('transaction_code'),
                            'updated_at': datetime.utcnow().isoformat()
                        }
                        
                        # Store transaction (upsert)
                        existing_transaction = await self.document_service.get_document(
                            'transactions',
                            transaction['transaction_id'],
                            user_id
                        )
                        
                        if existing_transaction:
                            transaction_data['created_at'] = existing_transaction['created_at']
                            await self.document_service.update_document('transactions', transaction_data)
                        else:
                            transaction_data['created_at'] = datetime.utcnow().isoformat()
                            await self.document_service.create_document('transactions', transaction_data)
                        
                        all_transactions.append(transaction_data)
                
                except Exception as e:
                    logger.error(f"Error fetching transactions for token {token['item_id']}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved {len(all_transactions)} transactions for user: {user_id}")
            return all_transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {str(e)}")
            raise


# Global service instance
plaid_service: Optional[PlaidService] = None


def get_plaid_service() -> PlaidService:
    """Get the global Plaid service instance"""
    global plaid_service
    if plaid_service is None:
        plaid_service = PlaidService()
    return plaid_service