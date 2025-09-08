"""
Account Storage Service - Now simplified since accounts are stored in bank documents.
This service provides compatibility methods that delegate to PlaidService for bank-per-document access.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from ..database import cosmos_client
from ..utils.logger import get_logger
from ..constants import Containers
from ..models.plaid import PlaidAccountWithBalance
import json

logger = get_logger(__name__)


class AccountStorageService:
    """Service for managing account data - now delegates to bank documents."""

    def __init__(self):
        # Accounts are now stored in bank documents, not separate container
        pass

    def get_stored_account_data(
        self, user_id: str, max_age_hours: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached account data from bank documents.
        This method provides compatibility with existing code.
        """
        try:
            logger.info(
                f"Retrieving account data from bank documents for user {user_id}"
            )

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected")
                return None

            # Query all bank documents for the user
            query = "SELECT * FROM c WHERE c.userId = @userId"
            parameters = [{"name": "@userId", "value": user_id}]

            bank_documents = cosmos_client.query_items(
                Containers.BANKS, query, parameters, user_id
            )

            all_accounts = []

            for bank_doc in bank_documents:
                bank_accounts = bank_doc.get("accounts", [])
                all_accounts.extend(bank_accounts)

            if not all_accounts:
                logger.info(f"No account data found for user {user_id}")
                return None

            return {
                "accounts": all_accounts,
                "account_count": len(all_accounts),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get account data for user {user_id}: {e}")
            return None

    def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all accounts for a user from bank documents."""
        try:
            data = self.get_stored_account_data(user_id)
            if data and "accounts" in data:
                return data["accounts"]
            return []
        except Exception as e:
            logger.error(f"Failed to get accounts for user {user_id}: {e}")
            return []

    def clear_data(self, user_id: str) -> bool:
        """
        Clear account data - this is now a no-op since accounts are cleared with bank documents.
        Kept for compatibility.
        """
        logger.info(
            f"Clear data called for user {user_id} - accounts are managed in bank documents"
        )
        return True

    # Legacy methods kept for compatibility but simplified
    def store_account_data(self, user_id: str, accounts_data: Dict[str, Any]) -> bool:
        """Legacy method - accounts are now stored in bank documents."""
        logger.info(
            f"store_account_data called for user {user_id} - data is now stored in bank documents"
        )
        return True

    def is_data_valid(self, user_id: str, max_age_hours: int = 24) -> bool:
        """Check if account data exists in bank documents."""
        try:
            data = self.get_stored_account_data(user_id)
            return data is not None and len(data.get("accounts", [])) > 0
        except Exception as e:
            logger.error(f"Failed to check data validity for user {user_id}: {e}")
            return False


# Global instance
account_storage_service = AccountStorageService()
