"""
Account Storage Service for managing stored account data in Firestore.
This service helps reduce Plaid API costs by storing account balances and information locally.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore
from ..database import firebase_client
from ..utils.logger import get_logger
from ..models.plaid import PlaidAccountWithBalance
import json

logger = get_logger(__name__)


class AccountStorageService:
    """Service for managing stored account data in Firestore."""

    def __init__(self):
        self.collection_name = "accounts"

    def store_account_data(self, user_id: str, accounts_data: Dict[str, Any]) -> bool:
        """
        Store account data in Firestore under user's collection.

        Args:
            user_id: User ID to store data for
            accounts_data: Account data from Plaid API containing accounts, total_balance, etc.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Storing account data for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot store account data")
                raise Exception("Firebase connection required for account storage")

            # Prepare stored data with timestamp
            now = datetime.now(timezone.utc)
            stored_data = {
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
            doc_ref.set(stored_data)

            logger.info(
                f"Successfully stored account data for user {user_id} - {stored_data['account_count']} accounts, ${stored_data['total_balance']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store account data for user {user_id}: {e}")
            return False

    def get_stored_account_data(
        self, user_id: str, max_age_hours: int = None  # None means no age limit
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored account data from Firestore.

        Args:
            user_id: User ID to get data for
            max_age_hours: Maximum age of stored data in hours (None = no limit)

        Returns:
            Dict containing account data or None if not found
        """
        try:
            logger.info(
                f"Retrieving stored account data for user {user_id} (age limit: {max_age_hours} hours)"
            )

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot retrieve account data")
                return None

            # Get stored data from Firestore
            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc = doc_ref.get()

            if not doc.exists:
                logger.info(f"No stored account data found for user {user_id}")
                return None

            stored_data = doc.to_dict()
            logger.info(f"Raw stored data for user {user_id}: {stored_data}")

            # Check age but don't filter out - just log
            last_updated = stored_data.get("last_updated")
            logger.info(
                f"Last updated value for user {user_id}: {last_updated} (type: {type(last_updated)})"
            )

            if last_updated:
                # Convert Firestore timestamp to datetime if needed
                if hasattr(last_updated, "replace"):
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                    logger.info(f"Converted timestamp to UTC: {last_updated}")
                elif isinstance(last_updated, str):
                    # Handle case where timestamp was manually entered as string
                    try:
                        last_updated = datetime.fromisoformat(
                            last_updated.replace("Z", "+00:00")
                        )
                        logger.info(f"Parsed string timestamp: {last_updated}")
                    except Exception as parse_error:
                        logger.error(
                            f"Failed to parse timestamp string {last_updated}: {parse_error}"
                        )
                        # Don't return None - still show the data even if timestamp is bad
                        last_updated = None

                # Calculate age but don't use it to filter
                if last_updated and max_age_hours:
                    max_age = timedelta(hours=max_age_hours)
                    age = datetime.now(timezone.utc) - last_updated
                    logger.info(
                        f"Data age for user {user_id}: {age}, max_age: {max_age}"
                    )

                    # Log but don't filter out
                    if age > max_age:
                        logger.info(
                            f"Data is older than limit but showing anyway (age: {age})"
                        )

            # Convert timestamps to ISO format for JSON serialization
            if stored_data.get("last_updated"):
                if last_updated:
                    stored_data["last_updated"] = last_updated.isoformat()
            if stored_data.get("created_at"):
                created_at = stored_data["created_at"]
                if hasattr(created_at, "replace"):
                    created_at = created_at.replace(tzinfo=timezone.utc)
                stored_data["created_at"] = created_at.isoformat()

            logger.info(
                f"Retrieved stored account data for user {user_id} - {stored_data.get('account_count', 0)} accounts, last updated: {stored_data.get('last_updated')}"
            )
            return stored_data

        except Exception as e:
            logger.error(
                f"Failed to retrieve stored account data for user {user_id}: {e}"
            )
            return None

    def is_data_valid(self, user_id: str, max_age_hours: int = 24) -> bool:
        """
        Check if stored data exists and is still valid.

        Args:
            user_id: User ID to check
            max_age_hours: Maximum age of stored data in hours

        Returns:
            bool: True if valid cache exists, False otherwise
        """
        try:
            cached_data = self.get_cached_account_data(user_id, max_age_hours)
            return cached_data is not None
        except Exception as e:
            logger.error(f"Failed to check cache validity for user {user_id}: {e}")
            return False

    def get_data_info(
        self, user_id: str, max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about stored data (last updated, age, etc.) without returning full data.

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

            stored_data = doc.to_dict()
            last_updated = stored_data.get("last_updated")

            if last_updated:
                if hasattr(last_updated, "replace"):
                    last_updated = last_updated.replace(tzinfo=timezone.utc)

                age_hours = (
                    datetime.now(timezone.utc) - last_updated
                ).total_seconds() / 3600

                return {
                    "last_updated": last_updated.isoformat(),
                    "age_hours": round(age_hours, 2),
                    "account_count": stored_data.get("account_count", 0),
                    "total_balance": stored_data.get("total_balance", 0.0),
                    "is_expired": age_hours
                    > max_age_hours,  # Use the parameter instead of hardcoded 24
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get cache info for user {user_id}: {e}")
            return None

    def clear_data(self, user_id: str) -> bool:
        """
        Clear stored account data for a user.

        Args:
            user_id: User ID to clear cache for

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Clearing account data for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot clear account data")
                return False

            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc_ref.delete()

            logger.info(f"Successfully cleared account data for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear account data for user {user_id}: {e}")
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
account_storage_service = AccountStorageService()
