"""
Security utilities for Azure-based backend
Handles encryption, decryption, and security operations
"""

import os
import logging
from typing import Optional
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages encryption and security operations"""
    
    def __init__(self):
        self._encryption_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key"""
        if self._encryption_key is None:
            # Try to get key from environment
            key_env = os.getenv('ENCRYPTION_KEY')
            if key_env:
                try:
                    self._encryption_key = base64.urlsafe_b64decode(key_env)
                except Exception as e:
                    logger.warning(f"Invalid encryption key in environment: {str(e)}")
            
            # Generate key from secret if not provided
            if self._encryption_key is None:
                secret = os.getenv('SECRET_KEY', 'default-secret-key-for-development-only')
                # Create a deterministic key from the secret
                key_material = hashlib.sha256(secret.encode()).digest()
                self._encryption_key = base64.urlsafe_b64encode(key_material)
        
        return self._encryption_key
    
    def _get_fernet(self) -> Fernet:
        """Get Fernet encryption instance"""
        if self._fernet is None:
            key = self._get_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt string data"""
        try:
            if not data:
                return data
            
            # For development, return data as-is (as mentioned in CLAUDE.md)
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                logger.debug("Development mode: encryption disabled")
                return data
            
            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        try:
            if not encrypted_data:
                return encrypted_data
            
            # For development, return data as-is (as mentioned in CLAUDE.md)
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                logger.debug("Development mode: decryption disabled")
                return encrypted_data
            
            fernet = self._get_fernet()
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            # Return original data if decryption fails (for backwards compatibility)
            return encrypted_data


# Global security manager instance
security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get the global security manager instance"""
    global security_manager
    if security_manager is None:
        security_manager = SecurityManager()
    return security_manager


def encrypt_token(token: str) -> str:
    """Encrypt a token string"""
    manager = get_security_manager()
    return manager.encrypt_data(token)


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token string"""
    manager = get_security_manager()
    return manager.decrypt_data(encrypted_token)


def generate_encryption_key() -> str:
    """Generate a new encryption key for production use"""
    key = Fernet.generate_key()
    return base64.urlsafe_b64encode(key).decode()


def hash_password(password: str) -> str:
    """Hash a password (for future use if needed)"""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def generate_random_string(length: int = 32) -> str:
    """Generate a random string for various security purposes"""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_jwt_secret(secret: str) -> bool:
    """Validate JWT secret strength"""
    if len(secret) < 32:
        return False
    
    has_letters = any(c.isalpha() for c in secret)
    has_digits = any(c.isdigit() for c in secret)
    
    return has_letters and has_digits