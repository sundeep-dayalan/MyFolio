"""
JWT key service for Azure Key Vault-based JWT operations.
"""

from typing import Optional
from datetime import datetime, timedelta
import base64
import json
import hashlib
from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm
from azure.identity import DefaultAzureCredential
from jose import jwt, JWTError

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JwtKeyService:
    """Service for JWT operations using Azure Key Vault cryptographic keys."""

    def __init__(self):
        self.key_vault_url = settings.key_vault_url
        self.crypto_client = None

        if self.key_vault_url:
            try:
                credential = DefaultAzureCredential()
                self.crypto_client = CryptographyClient(
                    f"{self.key_vault_url}/keys/secrets-encryption-key", credential
                )
                logger.info(
                    "Azure Key Vault JWT crypto client initialized successfully"
                )
            except Exception as e:
                logger.error(f"Failed to initialize JWT Key Vault client: {e}")
                raise RuntimeError(f"Key Vault initialization failed: {e}")
        else:
            logger.error(
                "Key Vault URL not configured. JWT operations require Key Vault."
            )
            raise RuntimeError("KEY_VAULT_URL environment variable is required.")

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token using Key Vault."""
        if not self.crypto_client:
            raise RuntimeError(
                "Key Vault not configured. JWT operations require Key Vault."
            )

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        return self._create_token_with_keyvault(to_encode)

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token using Key Vault only."""
        if not self.crypto_client:
            logger.error("Key Vault crypto client not available for token verification")
            raise RuntimeError(
                "Key Vault not configured. JWT operations require Key Vault."
            )

        try:
            logger.debug(f"Verifying token: {token[:50]}...")
            # Only accept RS256 tokens signed by Key Vault
            parts = token.split(".")
            if len(parts) == 3:
                header_b64 = parts[0]
                header_b64 += "=" * (4 - len(header_b64) % 4)
                header_json = base64.urlsafe_b64decode(header_b64).decode()
                header = json.loads(header_json)

                logger.debug(f"Token header: {header}")

                if header.get("alg") != "RS256":
                    logger.error(
                        f"Invalid token algorithm: {header.get('alg')}. Only RS256 tokens are accepted."
                    )
                    return None

                result = self._verify_token_with_keyvault(token)
                logger.debug(
                    f"Token verification result: {'SUCCESS' if result else 'FAILED'}"
                )
                return result
            else:
                logger.error(
                    f"Invalid token format: expected 3 parts, got {len(parts)}"
                )
                return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

    def _create_token_with_keyvault(self, payload: dict) -> str:
        """Create JWT token using Key Vault RSA signing."""
        header = {"alg": "RS256", "typ": "JWT"}

        # Convert datetime objects to timestamps for JSON serialization
        serializable_payload = {}
        for key, value in payload.items():
            if isinstance(value, datetime):
                serializable_payload[key] = int(value.timestamp())
            else:
                serializable_payload[key] = value

        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )

        payload_b64 = (
            base64.urlsafe_b64encode(
                json.dumps(serializable_payload, separators=(",", ":")).encode()
            )
            .decode()
            .rstrip("=")
        )

        message = f"{header_b64}.{payload_b64}"

        # Hash the message with SHA256 for RS256 algorithm
        message_hash = hashlib.sha256(message.encode()).digest()

        signature_result = self.crypto_client.sign(
            SignatureAlgorithm.rs256, message_hash
        )

        signature_b64 = (
            base64.urlsafe_b64encode(signature_result.signature).decode().rstrip("=")
        )

        return f"{message}.{signature_b64}"

    def _verify_token_with_keyvault(self, token: str) -> Optional[dict]:
        """Verify JWT token using Key Vault RSA verification."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts
            message = f"{header_b64}.{payload_b64}"

            # Hash the message with SHA256 for RS256 algorithm
            message_hash = hashlib.sha256(message.encode()).digest()

            signature_b64 += "=" * (4 - len(signature_b64) % 4)
            signature = base64.urlsafe_b64decode(signature_b64)

            verification_result = self.crypto_client.verify(
                SignatureAlgorithm.rs256, message_hash, signature
            )

            if verification_result.is_valid:
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload_json = base64.urlsafe_b64decode(payload_b64).decode()
                payload = json.loads(payload_json)

                # Check token expiration
                if payload.get("exp"):
                    current_time = datetime.utcnow().timestamp()
                    token_exp = payload["exp"]
                    logger.debug(
                        f"Token exp: {token_exp}, Current time: {current_time}, Valid: {current_time < token_exp}"
                    )

                    if current_time > token_exp:
                        logger.info("Token has expired")
                        return None

                return payload
            else:
                logger.warning("Token signature verification failed")
                return None

        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return None


key_vault_service = JwtKeyService()
