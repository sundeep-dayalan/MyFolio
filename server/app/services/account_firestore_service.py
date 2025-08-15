"""
Account Firestore Service for managing account data in Firestore.
This service provides persistent storage for account balances and information,
reducing the need for frequent Plaid API calls.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore
from ..database import firebase_client
from ..utils.logger import get_logger
from ..models.plaid import PlaidAccountWithBalance
import json

logger = get_logger(__name__)


class AccountFirestoreService:
    """Service for managing account data stored in Firestore."""

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

            # Prepare storage data with timestamp
            now = datetime.now(timezone.utc)
            storage_data = {
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
            doc_ref.set(storage_data)

            logger.info(
                f"Successfully stored account data for user {user_id} - {storage_data['account_count']} accounts, ${storage_data['total_balance']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store account data for user {user_id}: {e}")
            return False

    def get_account_data(
        self, user_id: str, max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve account data from Firestore.

        Args:
            user_id: User ID to get data for
            max_age_hours: Maximum age of stored data in hours (default 24)

        Returns:
            Dict containing account data or None if not found/expired
        """
        try:
            logger.info(f"Retrieving account data for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot retrieve account data")
                return None

            # Get stored data from Firestore
            doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            doc = doc_ref.get()

            if not doc.exists:
                logger.info(f"No account data found for user {user_id}")
                return None

            stored_data = doc.to_dict()

            # Check if data is still valid (not expired)
            last_updated = stored_data.get("last_updated")
            if last_updated:
                # Convert Firestore timestamp to datetime if needed
                if hasattr(last_updated, "replace"):
                    last_updated = last_updated.replace(tzinfo=timezone.utc)

                # Check if data is expired
                max_age = timedelta(hours=max_age_hours)
                if datetime.now(timezone.utc) - last_updated > max_age:
                    logger.info(
                        f"Account data for user {user_id} is expired (age: {datetime.now(timezone.utc) - last_updated})"
                    )
                    return None

            # Convert timestamps to ISO format for JSON serialization
            if stored_data.get("last_updated"):
                stored_data["last_updated"] = last_updated.isoformat()
            if stored_data.get("created_at"):
                created_at = stored_data["created_at"]
                if hasattr(created_at, "replace"):
                    created_at = created_at.replace(tzinfo=timezone.utc)
                stored_data["created_at"] = created_at.isoformat()

            logger.info(
                f"Retrieved account data for user {user_id} - {stored_data.get('account_count', 0)} accounts, last updated: {stored_data.get('last_updated')}"
            )
            return stored_data

        except Exception as e:
            logger.error(
                f"Failed to retrieve account data for user {user_id}: {e}"
            )
            return None

    def is_data_valid(self, user_id: str, max_age_hours: int = 24) -> bool:
        """
        Check if stored data exists and is still valid.

        Args:
            user_id: User ID to check
            max_age_hours: Maximum age of stored data in hours

        Returns:
            bool: True if valid data exists, False otherwise
        """
        try:
            stored_data = self.get_account_data(user_id, max_age_hours)
            return stored_data is not None
        except Exception as e:
            logger.error(f"Failed to check data validity for user {user_id}: {e}")
            return False

    def get_data_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about stored data (last updated, age, etc.) without returning full data.

        Args:
            user_id: User ID to get info for

        Returns:
            Dict containing data metadata or None if not found
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
                    "is_expired": age_hours > 24,  # Default 24 hour expiration
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get data info for user {user_id}: {e}")
            return None

    def clear_data(self, user_id: str) -> bool:
        """
        Clear stored account data for a user.

        Args:
            user_id: User ID to clear data for

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

    def update_data_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update data metadata without changing account data.

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
            logger.error(f"Failed to update data metadata for user {user_id}: {e}")
            return False


# Global instance
account_firestore_service = AccountFirestoreService()