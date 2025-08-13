"""
Account Cache Service for managing cached account data in Firestore.
This service helps reduce Plaid API costs by caching account balances and information.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore
from ..database import firebase_client
from ..utils.logger import get_logger
from ..models.plaid import PlaidAccountWithBalance
import json

logger = get_logger(__name__)


class AccountCacheService:
    """Service for managing cached account data in Firestore."""

    def __init__(self):
        self.collection_name = "accounts"

    def store_account_data(self, user_id: str, accounts_data: Dict[str, Any]) -> bool:
        """
        Store account data in Firestore cache under user's collection.

        Args:
            user_id: User ID to store data for
            accounts_data: Account data from Plaid API containing accounts, total_balance, etc.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Storing account cache for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot store account cache")
                raise Exception("Firebase connection required for account caching")

            # Prepare cache data with timestamp
            now = datetime.now(timezone.utc)
            cache_data = {
                "user_id": user_id,
                "accounts": accounts_data.get("accounts", []),
                "total_balance": accounts_data.get("total_balance", 0.0),
                "account_count": accounts_data.get("account_count", 0),
                "last_updated": now,
                "created_at": now,
                "data_source": "plaid_api",
            }

            # Store in Firestore under user's document
            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc_ref.set(cache_data)

            logger.info(
                f"Successfully cached account data for user {user_id} - {cache_data['account_count']} accounts, ${cache_data['total_balance']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store account cache for user {user_id}: {e}")
            return False

    def get_cached_account_data(
        self, user_id: str, max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached account data from Firestore.

        Args:
            user_id: User ID to get data for
            max_age_hours: Maximum age of cached data in hours (default 24)

        Returns:
            Dict containing account data or None if not found/expired
        """
        try:
            logger.info(f"Retrieving cached account data for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot retrieve account cache")
                return None

            # Get cached data from Firestore
            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc = doc_ref.get()

            if not doc.exists:
                logger.info(f"No cached account data found for user {user_id}")
                return None

            cache_data = doc.to_dict()

            # Check if data is still valid (not expired)
            last_updated = cache_data.get("last_updated")
            if last_updated:
                # Convert Firestore timestamp to datetime if needed
                if hasattr(last_updated, "replace"):
                    last_updated = last_updated.replace(tzinfo=timezone.utc)

                # Check if data is expired
                max_age = timedelta(hours=max_age_hours)
                if datetime.now(timezone.utc) - last_updated > max_age:
                    logger.info(
                        f"Cached account data for user {user_id} is expired (age: {datetime.now(timezone.utc) - last_updated})"
                    )
                    return None

            # Convert timestamps to ISO format for JSON serialization
            if cache_data.get("last_updated"):
                cache_data["last_updated"] = last_updated.isoformat()
            if cache_data.get("created_at"):
                created_at = cache_data["created_at"]
                if hasattr(created_at, "replace"):
                    created_at = created_at.replace(tzinfo=timezone.utc)
                cache_data["created_at"] = created_at.isoformat()

            logger.info(
                f"Retrieved cached account data for user {user_id} - {cache_data.get('account_count', 0)} accounts, last updated: {cache_data.get('last_updated')}"
            )
            return cache_data

        except Exception as e:
            logger.error(
                f"Failed to retrieve cached account data for user {user_id}: {e}"
            )
            return None

    def is_cache_valid(self, user_id: str, max_age_hours: int = 24) -> bool:
        """
        Check if cached data exists and is still valid.

        Args:
            user_id: User ID to check
            max_age_hours: Maximum age of cached data in hours

        Returns:
            bool: True if valid cache exists, False otherwise
        """
        try:
            cached_data = self.get_cached_account_data(user_id, max_age_hours)
            return cached_data is not None
        except Exception as e:
            logger.error(f"Failed to check cache validity for user {user_id}: {e}")
            return False

    def get_cache_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about cached data (last updated, age, etc.) without returning full data.

        Args:
            user_id: User ID to get info for

        Returns:
            Dict containing cache metadata or None if not found
        """
        try:
            if not firebase_client.is_connected:
                return None

            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc = doc_ref.get()

            if not doc.exists:
                return None

            cache_data = doc.to_dict()
            last_updated = cache_data.get("last_updated")

            if last_updated:
                if hasattr(last_updated, "replace"):
                    last_updated = last_updated.replace(tzinfo=timezone.utc)

                age_hours = (
                    datetime.now(timezone.utc) - last_updated
                ).total_seconds() / 3600

                return {
                    "last_updated": last_updated.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "account_count": cache_data.get("account_count", 0),
                    "total_balance": cache_data.get("total_balance", 0.0),
                    "is_expired": age_hours > 24,  # Default 24 hour expiration
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get cache info for user {user_id}: {e}")
            return None

    def clear_cache(self, user_id: str) -> bool:
        """
        Clear cached account data for a user.

        Args:
            user_id: User ID to clear cache for

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Clearing account cache for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot clear account cache")
                return False

            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc_ref.delete()

            logger.info(f"Successfully cleared account cache for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear account cache for user {user_id}: {e}")
            return False

    def update_cache_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update cache metadata without changing account data.

        Args:
            user_id: User ID to update
            metadata: Metadata to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not firebase_client.is_connected:
                return False

            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc_ref.update(metadata)

            return True

        except Exception as e:
            logger.error(f"Failed to update cache metadata for user {user_id}: {e}")
            return False


# Global instance
account_cache_service = AccountCacheService()
