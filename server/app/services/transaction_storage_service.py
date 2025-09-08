import asyncio
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
import math

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

        logger.info(f"Preparing to upsert {len(documents)} transaction documents.")
        container = self._get_container()

        success_count = 0
        errors = []

        for doc in documents:
            try:
                # Use mode='json' to properly serialize datetime objects to ISO strings
                doc_data = doc.model_dump(mode="json", by_alias=True, exclude_none=True)
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
                raise Exception(
                    f"All upsert operations failed. First error: {errors[0]}"
                )
            elif len(errors) > len(documents) / 2:  # More than 50% failed
                raise Exception(
                    f"Too many upsert failures ({len(errors)}/{len(documents)}). First error: {errors[0]}"
                )

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

    def get_transactions_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "date",
        sort_order: str = "desc",
        account_id: Optional[str] = None,
        item_id: Optional[str] = None,
        status: Optional[str] = None,
        is_pending: Optional[bool] = None,
        payment_channel: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        currency: Optional[str] = None,
        search_term: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int, bool, bool]:
        """
        Get paginated transactions with comprehensive filtering and sorting.

        Returns:
            Tuple of (transactions, total_count, total_pages, has_next, has_previous)
        """
        # Build the WHERE clause conditions
        conditions = ["c.userId = @userId"]
        parameters = [
            {"name": "@userId", "value": user_id},
        ]
        
        # Only add type filter if we're filtering by transaction type
        # Some documents might not have the 'type' field
        if hasattr(self, '_require_type_filter') and self._require_type_filter:
            conditions.append("c.type = 'transaction'")
        
        logger.info(f"Starting transaction query for user '{user_id}' with base conditions: {conditions}")
        
        # First, let's do a broad query to see what's in the container
        broad_query = "SELECT TOP 5 c.userId, c.type, c.id FROM c"
        broad_result = list(cosmos_client.query_items(self.container_name, broad_query, [], user_id))
        logger.info(f"Container sample data: {broad_result}")
        
        # Then test query for this specific user
        test_query = f"SELECT TOP 5 c.id, c.userId FROM c WHERE c.userId = @userId"
        test_result = list(cosmos_client.query_items(self.container_name, test_query, parameters, user_id))
        logger.info(f"Test query found {len(test_result)} documents for user '{user_id}'")
        if test_result:
            logger.info(f"Sample documents: {test_result[:3]}")
        
        # If no data at all, return empty result immediately
        if not test_result:
            logger.warning(f"No documents found for user '{user_id}' in container {self.container_name}")
            return [], 0, 1, False, False

        # Core Identity Filters
        if account_id:
            conditions.append("c.plaidAccountId = @accountId")
            parameters.append({"name": "@accountId", "value": account_id})

        if item_id:
            conditions.append("c.plaidItemId = @itemId")
            parameters.append({"name": "@itemId", "value": item_id})

        # State & Type Filters
        if status:
            if status == "pending":
                conditions.append("c.isPending = true")
            elif status == "posted":
                conditions.append("c.isPending = false")
            elif status == "removed":
                conditions.append("c._meta.isRemoved = true")
        else:
            # By default, exclude removed transactions if the field exists
            # Use IS_DEFINED to check if the field exists first
            conditions.append("(NOT IS_DEFINED(c._meta.isRemoved) OR c._meta.isRemoved = false)")

        # Separate isPending filter (can be used in combination with status)
        if is_pending is not None:
            conditions.append("c.isPending = @isPending")
            parameters.append({"name": "@isPending", "value": is_pending})

        if payment_channel:
            conditions.append("c.paymentChannel = @paymentChannel")
            parameters.append({"name": "@paymentChannel", "value": payment_channel})

        # Date & Financial Filters
        if date_from:
            conditions.append("c.date >= @dateFrom")
            parameters.append({"name": "@dateFrom", "value": date_from})

        if date_to:
            conditions.append("c.date <= @dateTo")
            parameters.append({"name": "@dateTo", "value": date_to})

        if min_amount is not None:
            conditions.append("c.amount >= @minAmount")
            parameters.append({"name": "@minAmount", "value": min_amount})

        if max_amount is not None:
            conditions.append("c.amount <= @maxAmount")
            parameters.append({"name": "@maxAmount", "value": max_amount})

        if currency:
            conditions.append("c.currency = @currency")
            parameters.append({"name": "@currency", "value": currency})

        # Content & Category Filters
        if search_term:
            conditions.append(
                "(CONTAINS(LOWER(c.description), LOWER(@searchTerm)) OR ARRAY_LENGTH(ARRAY(SELECT VALUE cp FROM cp IN c.counterparties WHERE CONTAINS(LOWER(cp.name), LOWER(@searchTerm)))) > 0)"
            )
            parameters.append({"name": "@searchTerm", "value": search_term})

        if category:
            conditions.append("c.category.primary = @category")
            parameters.append({"name": "@category", "value": category})

        # Build the complete WHERE clause
        where_clause = " AND ".join(conditions)

        # Sorting
        sort_field_map = {
            "date": "c.date",
            "amount": "c.amount",
        }
        sort_field = sort_field_map.get(sort_by, "c.date")
        sort_direction = "ASC" if sort_order.lower() == "asc" else "DESC"

        # Count query for pagination
        count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"

        logger.info(f"Count query: {count_query}")
        logger.info(f"Parameters: {parameters}")

        try:
            # Get total count
            count_result = list(
                cosmos_client.query_items(
                    self.container_name, count_query, parameters, user_id
                )
            )
            total_count = count_result[0] if count_result else 0
            
            logger.info(f"Total count result: {total_count}")

            # Calculate pagination
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
            offset = (page - 1) * page_size
            has_next = page < total_pages
            has_previous = page > 1

            # Main query with pagination
            main_query = f"""
                SELECT * FROM c 
                WHERE {where_clause} 
                ORDER BY {sort_field} {sort_direction}
                OFFSET {offset} LIMIT {page_size}
            """
            
            logger.info(f"Main query: {main_query}")

            # Execute main query
            transactions = list(
                cosmos_client.query_items(
                    self.container_name, main_query, parameters, user_id
                )
            )
            
            logger.info(f"Raw transactions count: {len(transactions)}")
            if transactions:
                logger.info(f"First transaction keys: {list(transactions[0].keys()) if transactions[0] else 'None'}")

            logger.info(
                f"Retrieved {len(transactions)} transactions for user {user_id}, "
                f"page {page}/{total_pages}, total: {total_count}"
            )

            return transactions, total_count, total_pages, has_next, has_previous

        except Exception as e:
            logger.error(
                f"Failed to get paginated transactions for user {user_id}: {e}",
                exc_info=True,
            )
            raise

    def get_user_transactions_count(self, user_id: str) -> int:
        """Get the total count of transactions for a user."""
        query = (
            "SELECT VALUE COUNT(1) FROM c WHERE c.userId = @userId "
            "AND c.type = 'transaction' AND c._meta.isRemoved = false"
        )
        parameters = [{"name": "@userId", "value": user_id}]

        try:
            result = list(
                cosmos_client.query_items(
                    self.container_name, query, parameters, user_id
                )
            )
            return result[0] if result else 0
        except Exception as e:
            logger.error(
                f"Failed to get transaction count for user {user_id}: {e}",
                exc_info=True,
            )
            raise


# Global instance to be imported by other services
transaction_storage_service = TransactionStorageService()
