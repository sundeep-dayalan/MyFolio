from typing import Dict, Any, List, Optional, Tuple
from firebase_admin import firestore
from ..database import firebase_client
from ..utils.logger import get_logger
from datetime import datetime, timedelta
import math

logger = get_logger(__name__)


class TransactionStorageService:
    """Service for managing stored transaction data in Firestore."""

    def __init__(self):
        self.collection_name = "transactions"

    def store_transactions_batch(
        self,
        user_id: str,
        item_id: str,
        transactions: List[Dict[str, Any]],
        transaction_type: str = "added",
    ) -> bool:
        """
        Stores a batch of transaction data in a Firestore subcollection organized by transaction type.

        Args:
            user_id: The ID of the user.
            item_id: The Plaid Item ID the transactions belong to.
            transactions: A list of cleaned & normalized transaction dictionaries.
            transaction_type: The type of transactions ("added", "modified", or "removed")

        Returns:
            True if the batch write was successful, False otherwise.
        """
        if not transactions:
            logger.info(
                f"No {transaction_type} transactions to store for user {user_id}, item {item_id}."
            )
            return True

        try:
            logger.info(
                f"Storing batch of {len(transactions)} {transaction_type} transactions for user {user_id}, item {item_id}"
            )
            batch = firebase_client.db.batch()

            # Separate path for each transaction type
            base_ref = (
                firebase_client.db.collection(self.collection_name)
                .document(user_id)
                .collection("items")
                .document(item_id)
                .collection(transaction_type)  # "added", "modified", or "removed"
            )

            for tx_data in transactions:
                transaction_id = tx_data.get("transaction_id")
                if not transaction_id:
                    logger.warning("Skipping transaction with no ID.")
                    continue

                # Add user_id and type to transaction data
                tx_data_with_metadata = {
                    **tx_data,
                    "user_id": user_id,
                    "transaction_type": transaction_type,
                    "sync_timestamp": firestore.SERVER_TIMESTAMP,
                }

                # Create a new document reference for each transaction within the batch
                tx_ref = base_ref.document(transaction_id)
                batch.set(tx_ref, tx_data_with_metadata)

            # Commit all the writes in a single operation
            batch.commit()
            logger.info(
                f"Successfully committed {transaction_type} batch for item {item_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to store {transaction_type} transaction data batch for user {user_id}, item {item_id}: {e}",
                exc_info=True,
            )
            return False

    def store_added_transactions_batch(
        self, user_id: str, item_id: str, transactions: List[Dict[str, Any]]
    ) -> bool:
        """Store added transactions in the 'added' collection."""
        return self.store_transactions_batch(user_id, item_id, transactions, "added")

    def store_modified_transactions_batch(
        self, user_id: str, item_id: str, transactions: List[Dict[str, Any]]
    ) -> bool:
        """Store modified transactions in the 'modified' collection."""
        return self.store_transactions_batch(user_id, item_id, transactions, "modified")

    def store_removed_transactions_batch(
        self, user_id: str, item_id: str, transactions: List[Dict[str, Any]]
    ) -> bool:
        """Store removed transactions in the 'removed' collection."""
        return self.store_transactions_batch(user_id, item_id, transactions, "removed")

    # The correct and final version of the deletion logic

    def delete_all_user_transactions(self, user_id: str) -> bool:
        """
        Deletes all transaction data for a specific user by deleting the entire user document
        and all its subcollections. This is a simplified, more reliable version.
        """
        try:
            logger.info(f"Deleting all transaction data for user {user_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot delete transaction data")
                return False

            # Get reference to the user document
            user_doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )

            # Check if user document exists
            user_doc = user_doc_ref.get()
            if not user_doc.exists:
                logger.info(f"No transaction document found for user {user_id}")
                # Still need to check for subcollections even if parent doesn't exist

            # Delete all items subcollection
            items_ref = user_doc_ref.collection("items")
            deleted_items = 0
            deleted_transactions = 0

            # Get all item documents in the subcollection
            item_docs = list(items_ref.stream())
            logger.info(f"Found {len(item_docs)} item documents to delete")

            for item_doc in item_docs:
                item_id = item_doc.id
                logger.info(f"Deleting all data for item {item_id}")

                # Delete all transactions in the data subcollection
                data_ref = item_doc.reference.collection("data")
                deleted_count = self._delete_collection_in_batches(data_ref)
                deleted_transactions += deleted_count

                # Delete the item document itself
                item_doc.reference.delete()
                deleted_items += 1
                logger.info(f"Deleted item {item_id} with {deleted_count} transactions")

            # Delete the user document itself (if it exists)
            if user_doc.exists:
                user_doc_ref.delete()
                logger.info(f"Deleted user document: {user_id}")

            logger.info(
                f"Successfully deleted all transaction data for user {user_id}: {deleted_items} items, {deleted_transactions} transactions"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete all transaction data for user {user_id}: {e}",
                exc_info=True,
            )
            return False

    def delete_item_transactions(self, user_id: str, item_id: str) -> bool:
        """
        Deletes all transaction data for a specific item.

        Args:
            user_id: The ID of the user
            item_id: The Plaid Item ID to delete transactions for

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            logger.info(f"Deleting transactions for user {user_id}, item {item_id}")

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot delete transaction data")
                return False

            # Get reference to the item document
            item_ref = (
                firebase_client.db.collection(self.collection_name)
                .document(user_id)
                .collection("items")
                .document(item_id)
            )

            # Don't check if item document exists - subcollections can exist without parent documents
            # Instead, try to delete the 'data' subcollection directly
            data_ref = item_ref.collection("data")

            # Check if there are any documents in the data collection
            data_docs = list(data_ref.limit(1).stream())
            if not data_docs:
                logger.info(f"No transaction data found for item {item_id}")
                return True

            self._delete_collection_in_batches(data_ref)

            # Delete the item document itself (if it exists)
            if item_ref.get().exists:
                item_ref.delete()
            logger.info(f"Successfully deleted transaction data for item {item_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete transaction data for user {user_id}, item {item_id}: {e}",
                exc_info=True,
            )
            return False

    def delete_transaction(
        self, user_id: str, item_id: str, transaction_id: str
    ) -> bool:
        """
        Deletes a specific transaction document.

        Args:
            user_id: The ID of the user
            item_id: The Plaid Item ID
            transaction_id: The specific transaction ID to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            logger.info(
                f"Deleting transaction {transaction_id} for user {user_id}, item {item_id}"
            )

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot delete transaction")
                return False

            # Get direct reference to the transaction document
            tx_ref = (
                firebase_client.db.collection(self.collection_name)
                .document(user_id)
                .collection("items")
                .document(item_id)
                .collection("data")
                .document(transaction_id)
            )

            # Delete the transaction document directly
            tx_ref.delete()
            logger.info(f"Successfully deleted transaction {transaction_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete transaction {transaction_id} for user {user_id}, item {item_id}: {e}",
                exc_info=True,
            )
            return False

    def _delete_collection_in_batches(self, coll_ref, batch_size: int = 500) -> int:
        """
        Deletes a collection in batches using Firestore batch operations.
        Returns the total number of documents deleted.
        """
        total_deleted = 0

        while True:
            # Get a batch of documents
            docs = list(coll_ref.limit(batch_size).stream())

            if not docs:
                # No more documents to delete
                if total_deleted > 0:
                    logger.info(
                        f"Finished deleting {total_deleted} documents from collection: {coll_ref._path}"
                    )
                return total_deleted

            # Create a batch for deletion
            batch = firebase_client.db.batch()

            for doc in docs:
                batch.delete(doc.reference)

            # Commit the batch deletion
            batch.commit()
            total_deleted += len(docs)
            logger.info(
                f"Deleted batch of {len(docs)} documents from collection: {coll_ref._path}"
            )

            # If we got fewer documents than the batch size, we're done
            if len(docs) < batch_size:
                break

        logger.info(
            f"Finished deleting {total_deleted} documents from collection: {coll_ref._path}"
        )
        return total_deleted

    def get_transactions_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "date",
        sort_order: str = "desc",
        filters: Optional[Dict[str, Any]] = None,
        transaction_type: str = "added",  # New parameter for transaction type
    ) -> Tuple[List[Dict[str, Any]], int, int, bool, bool]:
        """
        Get transactions with pagination and filtering from the new separated collections.

        Args:
            user_id: The ID of the user
            page: Page number (1-indexed)
            page_size: Number of transactions per page
            sort_by: Field to sort by (date, amount, name, etc.)
            sort_order: "asc" or "desc"
            filters: Optional filters dict
            transaction_type: Type of transactions to fetch ("added", "modified", "removed", "all")

        Returns:
            Tuple of (transactions, total_count, total_pages, has_next, has_previous)
        """
        try:
            logger.info(
                f"Getting paginated {transaction_type} transactions for user {user_id}, page {page}"
            )

            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot get transactions")
                return [], 0, 0, False, False

            # Get user's items reference
            items_ref = (
                firebase_client.db.collection(self.collection_name)
                .document(user_id)
                .collection("items")
            )

            # Determine which items to query based on filters
            target_item_ids = []

            if filters and filters.get("institution_name"):
                # Filter by institution name - we need to get item IDs for this institution
                target_item_ids = self._get_item_ids_by_institution(
                    user_id, filters["institution_name"]
                )
                if not target_item_ids:
                    logger.info(
                        f"No items found for institution: {filters['institution_name']}"
                    )
                    return [], 0, 0, False, False
            elif filters and filters.get("item_id"):
                # Filter by specific item_id
                target_item_ids = [filters["item_id"]]
            else:
                # Get all items for the user
                items = list(items_ref.stream())
                target_item_ids = [item.id for item in items]

            if not target_item_ids:
                logger.info(f"No items found for user {user_id}")
                return [], 0, 0, False, False

            logger.info(
                f"Querying {transaction_type} transactions from {len(target_item_ids)} items"
            )

            # Get all transactions for the target items
            all_transactions = []

            # Define which transaction types to query
            transaction_types_to_query = []
            if transaction_type == "all":
                transaction_types_to_query = ["added", "modified", "removed"]
            else:
                transaction_types_to_query = [transaction_type]

            for item_id in target_item_ids:
                for t_type in transaction_types_to_query:
                    # Get transactions from the specific type collection
                    data_ref = items_ref.document(item_id).collection(t_type)

                    # Apply account_id filter at the Firestore query level if provided
                    if filters and filters.get("account_id"):
                        query = data_ref.where(
                            "account_id", "==", filters["account_id"]
                        )
                        transactions = list(query.stream())
                    else:
                        transactions = list(data_ref.stream())

                    for tx_doc in transactions:
                        tx_data = tx_doc.to_dict()
                        tx_data["id"] = tx_doc.id  # Add document ID
                        tx_data["item_id"] = item_id  # Add item_id for reference
                        tx_data["query_type"] = (
                            t_type  # Add which collection this came from
                        )
                        all_transactions.append(tx_data)

            logger.info(
                f"Retrieved {len(all_transactions)} total transactions before filtering"
            )

            # Apply remaining filters
            all_transactions = self._apply_transaction_filters(
                all_transactions, filters
            )

            # Sort transactions
            all_transactions = self._sort_transactions(
                all_transactions, sort_by, sort_order
            )

            # Calculate pagination
            total_count = len(all_transactions)
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
            offset = (page - 1) * page_size
            has_previous = page > 1
            has_next = page < total_pages

            # Get the page of results
            page_transactions = all_transactions[offset : offset + page_size]

            logger.info(
                f"Retrieved {len(page_transactions)} transactions for page {page} (total: {total_count})"
            )
            return page_transactions, total_count, total_pages, has_next, has_previous

        except Exception as e:
            logger.error(
                f"Failed to get paginated transactions for user {user_id}: {e}",
                exc_info=True,
            )
            return [], 0, 0, False, False

    def _get_item_ids_by_institution(
        self, user_id: str, institution_name: str
    ) -> List[str]:
        """
        Get item IDs that belong to a specific institution.
        This queries the access tokens to find items for the given institution.
        """
        try:
            from ..dependencies import get_plaid_service

            plaid_service = get_plaid_service()

            # Get user's access tokens which contain institution information
            tokens = plaid_service.get_user_access_tokens(user_id)

            # Filter tokens by institution name
            matching_item_ids = []
            for token in tokens:
                if token.institution_name == institution_name:
                    matching_item_ids.append(token.item_id)

            logger.info(
                f"Found {len(matching_item_ids)} items for institution '{institution_name}'"
            )
            return matching_item_ids

        except Exception as e:
            logger.error(
                f"Failed to get item IDs for institution {institution_name}: {e}"
            )
            return []

    def _apply_transaction_filters(
        self, transactions: List[Dict[str, Any]], filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply filters to transaction list (excluding item_id, account_id, and institution_name which are handled earlier)"""
        if not filters:
            return transactions

        filtered_transactions = transactions

        # Apply search term filter
        if filters.get("search_term"):
            search_term = filters["search_term"].lower()
            filtered_transactions = []
            for tx in transactions:
                searchable_text = f"{tx.get('name', '')} {tx.get('merchant_name', '')} {tx.get('account_name', '')}".lower()
                if search_term in searchable_text:
                    filtered_transactions.append(tx)

        # Apply category filter
        if filters.get("category"):
            filtered_transactions = [
                tx
                for tx in filtered_transactions
                if filters["category"] in tx.get("category", [])
            ]

        # Apply date filters
        if filters.get("date_from"):
            filtered_transactions = [
                tx
                for tx in filtered_transactions
                if tx.get("date", "") >= filters["date_from"]
            ]

        if filters.get("date_to"):
            filtered_transactions = [
                tx
                for tx in filtered_transactions
                if tx.get("date", "") <= filters["date_to"]
            ]

        return filtered_transactions

    def _sort_transactions(
        self, transactions: List[Dict[str, Any]], sort_by: str, sort_order: str
    ) -> List[Dict[str, Any]]:
        """Sort transactions by the specified field and order"""
        reverse = sort_order.lower() == "desc"

        if sort_by == "date":
            transactions.sort(key=lambda x: x.get("date", ""), reverse=reverse)
        elif sort_by == "amount":
            transactions.sort(key=lambda x: float(x.get("amount", 0)), reverse=reverse)
        elif sort_by == "name":
            transactions.sort(key=lambda x: x.get("name", "").lower(), reverse=reverse)
        elif sort_by == "account_name":
            transactions.sort(
                key=lambda x: x.get("account_name", "").lower(), reverse=reverse
            )
        else:
            transactions.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)

        return transactions

    def get_user_transactions_count(self, user_id: str) -> int:
        """
        Get the total count of transactions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            Total number of transactions
        """
        try:
            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot get transaction count")
                return 0

            # Collection group query to count all transactions for the user
            query = firebase_client.db.collection_group("data").where(
                "user_id", "==", user_id
            )
            return len(list(query.stream()))

        except Exception as e:
            logger.error(
                f"Failed to get transaction count for user {user_id}: {e}",
                exc_info=True,
            )
            return 0


# Global instance to be imported by other services
transaction_storage_service = TransactionStorageService()
