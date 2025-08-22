"""
Authentication service for Azure-based backend
Handles user authentication, JWT tokens, and OAuth integration
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import httpx

from ..database import get_document_service
from ..utils.security import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self):
        self.document_service = get_document_service()
        self.secret_client = self._initialize_secret_client()
        self._jwt_secret: Optional[str] = None
        self._google_client_id: Optional[str] = None
        self._google_client_secret: Optional[str] = None
    
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
    
    async def get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        if not self._jwt_secret:
            self._jwt_secret = await self._get_secret('jwt-secret', 'SECRET_KEY')
            if not self._jwt_secret:
                raise ValueError("JWT secret not configured")
        return self._jwt_secret
    
    async def get_google_credentials(self) -> tuple[str, str]:
        """Get Google OAuth credentials"""
        if not self._google_client_id:
            self._google_client_id = await self._get_secret('google-client-id', 'GOOGLE_CLIENT_ID')
        if not self._google_client_secret:
            self._google_client_secret = await self._get_secret('google-client-secret', 'GOOGLE_CLIENT_SECRET')
        
        if not self._google_client_id or not self._google_client_secret:
            raise ValueError("Google OAuth credentials not configured")
        
        return self._google_client_id, self._google_client_secret
    
    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT token for user"""
        try:
            # Token payload
            payload = {
                'user_id': user_data['userId'],
                'email': user_data['email'],
                'exp': datetime.utcnow() + timedelta(hours=24),  # 24 hour expiration
                'iat': datetime.utcnow(),
                'iss': 'sage-app'
            }
            
            # Create token
            secret = self.get_jwt_secret()  # This should be awaited in async context
            token = jwt.encode(payload, secret, algorithm='HS256')
            
            logger.info(f"JWT token created for user: {user_data['email']}")
            return token
            
        except Exception as e:
            logger.error(f"Error creating JWT token: {str(e)}")
            raise
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            secret = self.get_jwt_secret()  # This should be awaited in async context
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise ValueError("Invalid token")
        except Exception as e:
            logger.error(f"Error verifying JWT token: {str(e)}")
            raise
    
    async def authenticate_google_oauth(self, authorization_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Authenticate user with Google OAuth"""
        try:
            client_id, client_secret = await self.get_google_credentials()
            
            # Exchange authorization code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=token_data)
                response.raise_for_status()
                token_response = response.json()
            
            # Get user info from Google
            user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={token_response['access_token']}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(user_info_url)
                response.raise_for_status()
                user_info = response.json()
            
            # Store or update user in database
            user_data = await self._create_or_update_user(user_info, token_response)
            
            # Create JWT token
            jwt_token = self.create_jwt_token(user_data)
            
            return {
                'user': user_data,
                'access_token': jwt_token,
                'token_type': 'bearer'
            }
            
        except Exception as e:
            logger.error(f"Google OAuth authentication failed: {str(e)}")
            raise
    
    async def _create_or_update_user(self, google_user_info: Dict[str, Any], oauth_tokens: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user in database"""
        try:
            user_id = google_user_info['id']
            
            # Check if user already exists
            existing_user = await self.document_service.get_document(
                'users', 
                user_id, 
                user_id
            )
            
            user_data = {
                'id': user_id,
                'userId': user_id,
                'email': google_user_info['email'],
                'name': google_user_info.get('name', ''),
                'picture': google_user_info.get('picture', ''),
                'verified_email': google_user_info.get('verified_email', False),
                'locale': google_user_info.get('locale', ''),
                'last_login': datetime.utcnow().isoformat(),
                'created_at': existing_user['created_at'] if existing_user else datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Store encrypted OAuth tokens separately
            oauth_data = {
                'id': f"{user_id}_oauth",
                'userId': user_id,
                'google_access_token': encrypt_token(oauth_tokens['access_token']),
                'google_refresh_token': encrypt_token(oauth_tokens.get('refresh_token', '')),
                'token_type': oauth_tokens.get('token_type', 'Bearer'),
                'expires_in': oauth_tokens.get('expires_in', 3600),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing_user:
                # Update existing user
                await self.document_service.update_document('users', user_data)
                await self.document_service.update_document('users', oauth_data)
                logger.info(f"Updated existing user: {user_data['email']}")
            else:
                # Create new user
                await self.document_service.create_document('users', user_data)
                await self.document_service.create_document('users', oauth_data)
                logger.info(f"Created new user: {user_data['email']}")
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error creating/updating user: {str(e)}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user = await self.document_service.get_document('users', user_id, user_id)
            return user
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise
    
    async def get_user_oauth_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's OAuth tokens"""
        try:
            oauth_data = await self.document_service.get_document(
                'users', 
                f"{user_id}_oauth", 
                user_id
            )
            
            if oauth_data:
                # Decrypt tokens
                oauth_data['google_access_token'] = decrypt_token(oauth_data['google_access_token'])
                if oauth_data.get('google_refresh_token'):
                    oauth_data['google_refresh_token'] = decrypt_token(oauth_data['google_refresh_token'])
            
            return oauth_data
            
        except Exception as e:
            logger.error(f"Error getting OAuth tokens for user {user_id}: {str(e)}")
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data"""
        try:
            # Delete user profile
            await self.document_service.delete_document('users', user_id, user_id)
            
            # Delete OAuth tokens
            await self.document_service.delete_document('users', f"{user_id}_oauth", user_id)
            
            # Delete user's accounts
            accounts = await self.document_service.get_user_documents('accounts', user_id)
            for account in accounts:
                await self.document_service.delete_document('accounts', account['id'], user_id)
            
            # Delete user's transactions
            transactions = await self.document_service.get_user_documents('transactions', user_id)
            for transaction in transactions:
                await self.document_service.delete_document('transactions', transaction['id'], user_id)
            
            # Delete user's Plaid tokens
            plaid_tokens = await self.document_service.get_user_documents('plaid_tokens', user_id)
            for token_doc in plaid_tokens:
                await self.document_service.delete_document('plaid_tokens', token_doc['id'], user_id)
            
            logger.info(f"User {user_id} and all associated data deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise


# Global service instance
auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the global auth service instance"""
    global auth_service
    if auth_service is None:
        auth_service = AuthService()
    return auth_service