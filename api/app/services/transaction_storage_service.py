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
        Deletes all transaction data for a specific user by deleting the entire user document
        and all its subcollections. This is a simplified, more reliable version.
        """
        try:
            logger.info(f"Deleting all transaction data for user {user_id}")
            
            if not firebase_client.is_connected:
                logger.error("Firebase not connected - cannot delete transaction data")
                return False

            # Get reference to the user document
            user_doc_ref = firebase_client.db.collection(self.collection_name).document(user_id)
            
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
            
            logger.info(f"Successfully deleted all transaction data for user {user_id}: {deleted_items} items, {deleted_transactions} transactions")
            return True

        except Exception as e:
            logger.error(f"Failed to delete all transaction data for user {user_id}: {e}", exc_info=True)
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
