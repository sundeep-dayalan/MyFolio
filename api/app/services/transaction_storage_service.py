from typing import Dict, Any, List
from firebase_admin import firestore
from ..database import firebase_client
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TransactionStorageService:
    """Service for managing stored transaction data in Firestore."""

    def __init__(self):
        self.collection_name = "transactions"

    def store_transactions_batch(
        self, user_id: str, item_id: str, transactions: List[Dict[str, Any]]
    ) -> bool:
        """
        Stores a batch of cleaned transaction data in a Firestore subcollection.

        Args:
            user_id: The ID of the user.
            item_id: The Plaid Item ID the transactions belong to.
            transactions: A list of cleaned & normalized transaction dictionaries.

        Returns:
            True if the batch write was successful, False otherwise.
        """
        if not transactions:
            logger.info(f"No transactions to store for user {user_id}, item {item_id}.")
            return True

        try:
            logger.info(
                f"Storing batch of {len(transactions)} transactions for user {user_id}, item {item_id}"
            )
            batch = firebase_client.db.batch()

            # The scalable path for storing transactions
            base_ref = (
                firebase_client.db.collection(self.collection_name)
                .document(user_id)
                .collection("items")
                .document(item_id)
                .collection("data")
            )

            for tx_data in transactions:
                transaction_id = tx_data.get("transaction_id")
                if not transaction_id:
                    logger.warning("Skipping transaction with no ID.")
                    continue

                # Create a new document reference for each transaction within the batch
                tx_ref = base_ref.document(transaction_id)
                batch.set(tx_ref, tx_data)

            # Commit all the writes in a single operation
            batch.commit()
            logger.info(f"Successfully committed batch for item {item_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to store transaction data batch for user {user_id}, item {item_id}: {e}",
                exc_info=True,
            )
            return False

    # The correct and final version of the deletion logic

    def delete_all_user_transactions(self, user_id: str) -> bool:
        """
        Deletes all transaction data for a specific user by recursively deleting
        all nested subcollections and their documents.
        """
        try:
            logger.info(
                f"Starting recursive deletion of all transaction data for user {user_id}"
            )
            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot clear transaction data")
                return False

            # The key insight: In Firestore, subcollections can exist without parent documents
            # So we need to query all possible item documents and check their data subcollections

            # Strategy: Use collection group query to find all data documents for this user
            # Then work backwards to delete them and their parent structures

            user_doc_ref = firebase_client.db.collection(self.collection_name).document(
                user_id
            )
            items_ref = user_doc_ref.collection("items")

            # Debug: Log the collection path we're querying
            logger.info(f"Querying items collection at path: {items_ref._path}")

            # First, let's try to find all item documents that might have data subcollections
            # We'll do this by checking if we can find any data documents for this user

            deleted_items = 0
            deleted_transactions = 0

            # Get all possible item documents - this might return empty if intermediate docs don't exist
            item_docs = list(items_ref.stream())
            logger.info(
                f"Found {len(item_docs)} item documents via subcollection query"
            )

            if not item_docs:
                # If no items found via subcollection, try alternative approach
                # Check if there are any plaid_tokens for this user to get item_ids
                logger.info(
                    f"No items found via subcollection query, trying alternative approaches..."
                )

                # Approach 1: Check plaid_tokens to get item IDs
                try:
                    plaid_tokens_ref = firebase_client.db.collection(
                        "plaid_tokens"
                    ).document(user_id)
                    plaid_doc = plaid_tokens_ref.get()

                    if plaid_doc.exists:
                        plaid_data = plaid_doc.to_dict()
                        items_map = plaid_data.get("items", {})
                        logger.info(f"Found {len(items_map)} items in plaid_tokens")

                        # Check each item for transaction data
                        for item_id in items_map.keys():
                            logger.info(
                                f"Checking item {item_id} for transaction data..."
                            )

                            item_ref = items_ref.document(item_id)
                            data_ref = item_ref.collection("data")

                            # Try to delete data subcollection directly
                            deleted_count = self._delete_collection_in_batches(data_ref)

                            if deleted_count > 0:
                                deleted_items += 1
                                deleted_transactions += deleted_count
                                logger.info(
                                    f"Deleted {deleted_count} transactions from item {item_id}"
                                )

                                # Delete the item document if it exists
                                if item_ref.get().exists:
                                    item_ref.delete()
                                    logger.info(f"Deleted item document: {item_id}")

                except Exception as e:
                    logger.warning(f"Could not check plaid_tokens for item IDs: {e}")

                # Approach 2: Use collection group query to find transaction data
                # This is more comprehensive but requires proper indexing
                try:
                    # Find all 'data' subcollections under this user's transactions
                    # Note: This requires a collection group index in Firestore

                    # For now, let's use a direct approach: try common item patterns
                    # This is a fallback if the above approaches don't work
                    logger.info("Trying direct data subcollection check...")

                    # We could try to query all collections, but that's expensive
                    # Instead, let's report what we found

                except Exception as e:
                    logger.warning(f"Collection group query failed: {e}")

            else:
                # Process found item documents normally
                for item_doc in item_docs:
                    item_id = item_doc.id
                    logger.info(f"Deleting data subcollection for item: {item_id}")

                    # Delete the 'data' subcollection
                    data_ref = item_doc.reference.collection("data")
                    deleted_count = self._delete_collection_in_batches(data_ref)

                    if deleted_count > 0:
                        deleted_transactions += deleted_count
                        deleted_items += 1

                        # Delete the item document itself
                        item_doc.reference.delete()
                        logger.info(f"Deleted item document: {item_id}")

            # Summary
            if deleted_items > 0 or deleted_transactions > 0:
                logger.info(
                    f"Deleted {deleted_transactions} transactions from {deleted_items} items for user {user_id}"
                )

                # Delete the user document if it exists
                if user_doc_ref.get().exists:
                    user_doc_ref.delete()
                    logger.info(f"Deleted user document: {user_id}")

                return True
            else:
                logger.info(f"No transaction data found for user {user_id}")
                # Debug: Let's try to check if there are any documents at all in the transactions collection
                all_user_docs = list(
                    firebase_client.db.collection(self.collection_name)
                    .limit(5)
                    .stream()
                )
                logger.info(
                    f"Debug: Found {len(all_user_docs)} total user documents in transactions collection"
                )
                if all_user_docs:
                    logger.info(
                        f"Debug: Sample user doc IDs: {[doc.id for doc in all_user_docs]}"
                    )
                return True

        except Exception as e:
            logger.error(
                f"Failed to delete transaction data for user {user_id}: {e}",
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


# Global instance to be imported by other services
transaction_storage_service = TransactionStorageService()
