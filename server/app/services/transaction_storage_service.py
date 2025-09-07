import asyncio
from typing import List, Optional
from datetime import datetime, timezone
from azure.cosmos import CosmosClient, ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from ..database import cosmos_client
from ..utils.logger import get_logger
from ..constants import Containers
from ..models.plaid import TransactionDocument

logger = get_logger(__name__)


class TransactionStorageService:
    """
    A modern, efficient service for managing transaction documents in Cosmos DB.

    This service uses asyncio.gather to execute concurrent upsert and patch
    operations, which is the recommended pattern for high-throughput writes
    in the azure-cosmos v4+ SDK.
    """

    def __init__(self):
        self.container_name = Containers.TRANSACTIONS
        self._container: Optional[ContainerProxy] = None

    def _get_container(self) -> ContainerProxy:
        """Lazily initializes and returns the Cosmos container client."""
        if self._container is None:
            self._container = cosmos_client.get_container(self.container_name)
        return self._container

    async def upsert_transactions(self, documents: List[TransactionDocument]) -> None:
        """
        Upserts a batch of transaction documents sequentially with proper error handling.
        This handles both newly added and modified transactions seamlessly.

        Args:
            documents: A list of TransactionDocument Pydantic models.
        """
        if not documents:
            return

        logger.info(
            f"Preparing to upsert {len(documents)} transaction documents."
        )
        container = self._get_container()

        success_count = 0
        errors = []

        for doc in documents:
            try:
                # Use mode='json' to properly serialize datetime objects to ISO strings
                doc_data = doc.model_dump(mode='json', by_alias=True, exclude_none=True)
                container.upsert_item(body=doc_data)
                success_count += 1
            except Exception as e:
                error_msg = f"Failed to upsert document {doc.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(
            f"Successfully upserted {success_count}/{len(documents)} documents."
        )

        if errors:
            logger.error(f"Encountered {len(errors)} errors during upsert operation")
            # Still raise an exception if there were failures, but don't fail completely
            if success_count == 0:
                raise Exception(f"All upsert operations failed. First error: {errors[0]}")
            elif len(errors) > len(documents) / 2:  # More than 50% failed
                raise Exception(f"Too many upsert failures ({len(errors)}/{len(documents)}). First error: {errors[0]}")

    async def soft_delete_transactions(
        self, user_id: str, transaction_ids: List[str], sync_cursor: str
    ) -> None:
        """
        Soft-deletes a batch of transactions by setting the '_meta.isRemoved' flag
        using concurrent patch operations.

        Args:
            user_id: The partition key for the documents.
            transaction_ids: A list of Plaid transaction IDs to soft-delete.
            sync_cursor: The Plaid sync cursor that triggered this deletion.
        """
        if not transaction_ids:
            return

        logger.info(
            f"Preparing to concurrently soft-delete {len(transaction_ids)} transactions for user '{user_id}'."
        )
        container = self._get_container()
        now_iso = datetime.now(timezone.utc).isoformat()

        patch_operations = [
            {"op": "set", "path": "/_meta/isRemoved", "value": True},
            {"op": "set", "path": "/_meta/updatedAt", "value": now_iso},
            {"op": "set", "path": "/_meta/sourceSyncCursor", "value": sync_cursor},
        ]

        # Create a list of awaitable tasks for each patch operation
        tasks = [
            container.patch_item(
                item=f"user-{user_id}-transaction-{tx_id}",
                partition_key=user_id,
                patch_operations=patch_operations,
            )
            for tx_id in transaction_ids
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = 0
            for result in results:
                if isinstance(result, CosmosResourceNotFoundError):
                    # This can happen in rare race conditions; usually safe to ignore
                    logger.warning(
                        f"Attempted to soft-delete a transaction that was not found: {result}"
                    )
                elif isinstance(result, Exception):
                    logger.error(f"An individual patch in the batch failed: {result}")
                else:
                    success_count += 1

            logger.info(
                f"Concurrently soft-deleted {success_count}/{len(transaction_ids)} documents."
            )
            if success_count < len(transaction_ids):
                # Log or raise an exception based on whether this is a critical failure
                logger.error(
                    "One or more transactions failed to soft-delete in the batch."
                )

        except Exception as e:
            logger.error(f"Concurrent soft-delete operation failed: {e}", exc_info=True)
            raise

    async def delete_item_transactions(self, user_id: str, item_id: str) -> int:
        """
        Performs a HARD delete of all transactions associated with a Plaid item.
        This is a destructive operation intended for user data cleanup (e.g., GDPR).

        Args:
            user_id: The ID of the user.
            item_id: The Plaid Item ID to delete transactions for.

        Returns:
            The number of documents deleted.
        """
        logger.warning(
            f"Performing HARD delete for all transactions of user '{user_id}', item '{item_id}'."
        )
        container = self._get_container()

        query = (
            "SELECT c.id FROM c WHERE c.userId = @userId AND c.plaidItemId = @itemId"
        )
        parameters = [
            {"name": "@userId", "value": user_id},
            {"name": "@itemId", "value": item_id},
        ]

        docs_to_delete = cosmos_client.query_items(
            self.container_name, query, parameters, user_id
        )

        if not docs_to_delete:
            logger.info(f"No transactions found to delete for item '{item_id}'.")
            return 0

        # Delete items sequentially since bulk operations are not available in this SDK version
        deleted_count = 0
        errors = []
        
        for doc in docs_to_delete:
            try:
                container.delete_item(item=doc["id"], partition_key=user_id)
                deleted_count += 1
            except Exception as e:
                error_msg = f"Failed to delete document {doc['id']}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(
            f"Successfully hard-deleted {deleted_count}/{len(docs_to_delete)} transactions for item '{item_id}'."
        )
        
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during deletion")
            
        return deleted_count


# Global instance to be imported by other services
transaction_storage_service = TransactionStorageService()
