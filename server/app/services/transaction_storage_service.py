from typing import Dict, Any, List, Optional, Tuple
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from ..database import cosmos_client
from ..utils.logger import get_logger
from ..constants import Containers, DocumentFields
from datetime import datetime, timedelta, timezone
import math
import uuid

logger = get_logger(__name__)


class TransactionStorageService:
    """Service for managing stored transaction data in CosmosDB."""

    def __init__(self):
        self.container_name = Containers.TRANSACTIONS

    def store_transactions_batch(
        self,
        user_id: str,
        item_id: str,
        transactions: List[Dict[str, Any]],
        transaction_type: str = "added",
    ) -> bool:
        """
        Stores a batch of transaction data in CosmosDB.

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

            # Store each transaction individually in CosmosDB
            success_count = 0
            for tx_data in transactions:
                transaction_id = tx_data.get("transaction_id")
                if not transaction_id:
                    logger.warning("Skipping transaction with no ID.")
                    continue

                # Create document with required CosmosDB fields
                tx_doc = {
                    "id": f"{user_id}_{item_id}_{transaction_id}_{transaction_type}",  # Unique doc ID
                    "userId": user_id,  # Partition key
                    "transaction_id": transaction_id,
                    "item_id": item_id,
                    "transaction_type": transaction_type,
                    "sync_timestamp": datetime.utcnow().isoformat(),
                    **tx_data,
                }

                try:
                    cosmos_client.create_item(self.container_name, tx_doc, user_id)
                    success_count += 1
                except CosmosHttpResponseError as e:
                    if e.status_code == 409:  # Conflict - document exists, try update
                        try:
                            cosmos_client.update_item(
                                self.container_name, tx_doc["id"], user_id, tx_doc
                            )
                            success_count += 1
                        except Exception as update_e:
                            logger.error(
                                f"Failed to update transaction {transaction_id}: {update_e}"
                            )
                    else:
                        logger.error(
                            f"Failed to store transaction {transaction_id}: {e}"
                        )

            logger.info(
                f"Successfully stored {success_count}/{len(transactions)} {transaction_type} transactions for item {item_id}"
            )
            return success_count == len(transactions)

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

    def delete_all_user_transactions(self, user_id: str) -> bool:
        """
        Deletes all transaction data for a specific user.
        """
        try:
            logger.info(f"Deleting all transaction data for user {user_id}")

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot delete transaction data")
                return False

            # Query all transactions for the user
            query = "SELECT c.id FROM c WHERE c.userId = @userId"
            parameters = [{"name": "@userId", "value": user_id}]

            transactions = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )

            deleted_count = 0
            for tx in transactions:
                try:
                    cosmos_client.delete_item(self.container_name, tx["id"], user_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete transaction {tx['id']}: {e}")

            logger.info(
                f"Successfully deleted {deleted_count} transactions for user {user_id}"
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

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot delete transaction data")
                return False

            # Query all transactions for the user and item
            query = (
                "SELECT c.id FROM c WHERE c.userId = @userId AND c.item_id = @itemId"
            )
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@itemId", "value": item_id},
            ]

            transactions = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )

            deleted_count = 0
            for tx in transactions:
                try:
                    cosmos_client.delete_item(self.container_name, tx["id"], user_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete transaction {tx['id']}: {e}")

            logger.info(
                f"Successfully deleted {deleted_count} transactions for item {item_id}"
            )
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

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot delete transaction")
                return False

            # Query for all versions of this transaction (added, modified, removed)
            query = "SELECT c.id FROM c WHERE c.userId = @userId AND c.item_id = @itemId AND c.transaction_id = @transactionId"
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@itemId", "value": item_id},
                {"name": "@transactionId", "value": transaction_id},
            ]

            transactions = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )

            deleted_count = 0
            for tx in transactions:
                try:
                    cosmos_client.delete_item(self.container_name, tx["id"], user_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to delete transaction version {tx['id']}: {e}"
                    )

            logger.info(
                f"Successfully deleted {deleted_count} versions of transaction {transaction_id}"
            )
            return deleted_count > 0

        except Exception as e:
            logger.error(
                f"Failed to delete transaction {transaction_id} for user {user_id}, item {item_id}: {e}",
                exc_info=True,
            )
            return False

    def get_transactions_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "date",
        sort_order: str = "desc",
        filters: Optional[Dict[str, Any]] = None,
        transaction_type: str = "added",
    ) -> Tuple[List[Dict[str, Any]], int, int, bool, bool]:
        """
        Get transactions with pagination and filtering from CosmosDB.

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

            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot get transactions")
                return [], 0, 0, False, False

            # Build base query
            query_parts = ["SELECT * FROM c WHERE c.userId = @userId"]
            parameters = [{"name": "@userId", "value": user_id}]

            # Add transaction type filter
            if transaction_type != "all":
                query_parts.append("AND c.transaction_type = @transactionType")
                parameters.append(
                    {"name": "@transactionType", "value": transaction_type}
                )

            # Add filters
            if filters:
                if filters.get("item_id"):
                    query_parts.append("AND c.item_id = @itemId")
                    parameters.append({"name": "@itemId", "value": filters["item_id"]})

                if filters.get("account_id"):
                    query_parts.append("AND c.account_id = @accountId")
                    parameters.append(
                        {"name": "@accountId", "value": filters["account_id"]}
                    )

                if filters.get("date_from"):
                    query_parts.append("AND c.date >= @dateFrom")
                    parameters.append(
                        {"name": "@dateFrom", "value": filters["date_from"]}
                    )

                if filters.get("date_to"):
                    query_parts.append("AND c.date <= @dateTo")
                    parameters.append({"name": "@dateTo", "value": filters["date_to"]})

                if filters.get("category"):
                    query_parts.append("AND ARRAY_CONTAINS(c.category, @category)")
                    parameters.append(
                        {"name": "@category", "value": filters["category"]}
                    )

            # Add sorting
            sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
            if sort_by == "date":
                query_parts.append(f"ORDER BY c.date {sort_direction}")
            elif sort_by == "amount":
                query_parts.append(f"ORDER BY c.amount {sort_direction}")
            elif sort_by == "name":
                query_parts.append(f"ORDER BY c.name {sort_direction}")
            else:
                query_parts.append(f"ORDER BY c.{sort_by} {sort_direction}")

            query = " ".join(query_parts)

            # Get all matching transactions
            all_transactions = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )

            # Apply search term filter (CosmosDB doesn't have good full-text search)
            if filters and filters.get("search_term"):
                search_term = filters["search_term"].lower()
                filtered_transactions = []
                for tx in all_transactions:
                    searchable_text = f"{tx.get('name', '')} {tx.get('merchant_name', '')} {tx.get('account_name', '')}".lower()
                    if search_term in searchable_text:
                        filtered_transactions.append(tx)
                all_transactions = filtered_transactions

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
        This queries the plaid_tokens container to find items for the given institution.
        """
        try:
            # Query plaid_tokens container for items with matching institution
            query = "SELECT c.item_id FROM c WHERE c.userId = @userId AND c.institution_name = @institutionName"
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@institutionName", "value": institution_name},
            ]

            tokens = cosmos_client.query_items(
                "plaid_tokens", query, parameters, user_id
            )
            matching_item_ids = [token["item_id"] for token in tokens]

            logger.info(
                f"Found {len(matching_item_ids)} items for institution '{institution_name}'"
            )
            return matching_item_ids

        except Exception as e:
            logger.error(
                f"Failed to get item IDs for institution {institution_name}: {e}"
            )
            return []

    def get_user_transactions_count(self, user_id: str) -> int:
        """
        Get the total count of transactions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            Total number of transactions
        """
        try:
            if not cosmos_client.is_connected:
                logger.error("CosmosDB not connected - cannot get transaction count")
                return 0

            # Query to count all transactions for the user
            query = "SELECT VALUE COUNT(1) FROM c WHERE c.userId = @userId"
            parameters = [{"name": "@userId", "value": user_id}]

            results = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )

            return results[0] if results else 0

        except Exception as e:
            logger.error(
                f"Failed to get transaction count for user {user_id}: {e}",
                exc_info=True,
            )
            return 0

    def get_last_sync_cursor(self, user_id: str, item_id: str) -> Optional[str]:
        """Get the last sync cursor for an item."""
        try:
            # Get from plaid_tokens container
            doc_id = f"{user_id}_{item_id}"
            result = cosmos_client.get_item("plaid_tokens", doc_id, user_id)
            
            if result and DocumentFields.TRANSACTIONS in result:
                return result[DocumentFields.TRANSACTIONS].get("last_cursor")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get sync cursor for {item_id}: {e}")
            return None

    def update_sync_cursor(self, user_id: str, item_id: str, cursor: str) -> bool:
        """Update the sync cursor for an item."""
        try:
            doc_id = f"{user_id}_{item_id}"
            update_data = {
                "transactions.last_cursor": cursor,
                "transactions.last_sync_at": datetime.now(timezone.utc).isoformat()
            }
            
            cosmos_client.update_item("plaid_tokens", doc_id, user_id, update_data)
            logger.info(f"Updated sync cursor for item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update sync cursor for {item_id}: {e}")
            return False

    def clear_item_transactions(self, user_id: str, item_id: str) -> bool:
        """Clear all transactions for a specific item."""
        try:
            logger.info(f"Clearing transactions for item {item_id}")
            
            # Query all transactions for this item
            query = "SELECT c.id FROM c WHERE c.userId = @userId AND c.item_id = @itemId"
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@itemId", "value": item_id}
            ]
            
            results = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )
            
            # Delete each transaction
            deleted_count = 0
            for result in results:
                try:
                    cosmos_client.delete_item(
                        self.container_name, result["id"], user_id
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete transaction {result['id']}: {e}")
            
            logger.info(f"Cleared {deleted_count} transactions for item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear transactions for item {item_id}: {e}")
            return False

    def get_user_transactions(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get all transactions for a user in the last N days."""
        try:
            # Calculate date filter
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_date_str = cutoff_date.isoformat()
            
            query = """
                SELECT * FROM c 
                WHERE c.userId = @userId 
                AND c.date >= @cutoffDate
                ORDER BY c.date DESC
            """
            
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@cutoffDate", "value": cutoff_date_str}
            ]
            
            results = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )
            
            logger.info(f"Retrieved {len(results)} transactions for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get transactions for user {user_id}: {e}")
            return []

    def get_account_transactions(
        self, user_id: str, account_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get transactions for a specific account in the last N days."""
        try:
            # Calculate date filter
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_date_str = cutoff_date.isoformat()
            
            query = """
                SELECT * FROM c 
                WHERE c.userId = @userId 
                AND c.account_id = @accountId
                AND c.date >= @cutoffDate
                ORDER BY c.date DESC
            """
            
            parameters = [
                {"name": "@userId", "value": user_id},
                {"name": "@accountId", "value": account_id},
                {"name": "@cutoffDate", "value": cutoff_date_str}
            ]
            
            results = cosmos_client.query_items(
                self.container_name, query, parameters, user_id
            )
            
            logger.info(f"Retrieved {len(results)} transactions for account {account_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to get transactions for account {account_id}: {e}")
            return []

    def handle_removed_transactions(
        self, user_id: str, item_id: str, removed_transactions: List[Dict]
    ) -> bool:
        """Handle removed transactions from Plaid sync."""
        try:
            logger.info(f"Handling {len(removed_transactions)} removed transactions")
            
            removed_count = 0
            for removed_txn in removed_transactions:
                transaction_id = removed_txn.get("transaction_id")
                if not transaction_id:
                    continue
                
                # Find and delete the transaction (try different type suffixes)
                for suffix in ["added", "modified", "removed"]:
                    doc_id = f"{user_id}_{item_id}_{transaction_id}_{suffix}"
                    try:
                        cosmos_client.delete_item(self.container_name, doc_id, user_id)
                        removed_count += 1
                        break  # Found and removed, stop trying other suffixes
                    except CosmosResourceNotFoundError:
                        # Transaction doesn't exist, try next suffix
                        continue
                    except Exception as e:
                        logger.error(f"Failed to remove transaction {transaction_id}: {e}")
                        break
            
            logger.info(f"Handled {removed_count} removed transactions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle removed transactions: {e}")
            return False

    def store_transactions(
        self, user_id: str, item_id: str, transactions: List[Dict], transaction_type: str
    ) -> bool:
        """Store transactions from Plaid sync."""
        try:
            logger.info(f"💾 STORING TRANSACTIONS: {len(transactions)} {transaction_type} transactions for item {item_id}")
            
            if not cosmos_client.is_connected:
                logger.error("❌ CosmosDB not connected - cannot store transactions")
                return False
                
            stored_count = 0
            for i, txn in enumerate(transactions):
                try:
                    # Convert Plaid Transaction object to dict if needed
                    if hasattr(txn, 'to_dict'):
                        txn_dict = txn.to_dict()
                    elif hasattr(txn, '__dict__'):
                        txn_dict = txn.__dict__
                    else:
                        txn_dict = txn
                    
                    # Extract transaction data from the dict
                    transaction_id = txn_dict.get("transaction_id") or getattr(txn, 'transaction_id', None)
                    account_id = txn_dict.get("account_id") or getattr(txn, 'account_id', None)
                    
                    logger.info(f"Processing transaction {i+1}/{len(transactions)}: {transaction_id}")
                    logger.debug(f"Transaction type: {type(txn)}")
                    
                    if not transaction_id or not account_id:
                        logger.warning(f"❌ Skipping transaction {i+1} with missing ID or account_id: {transaction_id}, {account_id}")
                        logger.debug(f"Transaction has attributes: {[attr for attr in dir(txn) if not attr.startswith('_')]}")
                        continue
                    
                    # Create document ID (just use transaction_id as primary key)
                    doc_id = f"{transaction_id}_{transaction_type}"
                    
                    # Helper function to safely get value from Plaid object or dict
                    def get_txn_value(key, default=None):
                        """Get value from Plaid transaction object or dict."""
                        try:
                            if hasattr(txn, key):
                                return getattr(txn, key)
                            elif isinstance(txn_dict, dict):
                                return txn_dict.get(key, default)
                            else:
                                return default
                        except:
                            return default
                    
                    # Clean and convert Plaid data to JSON-serializable format
                    def clean_value(value):
                        """Convert any non-JSON serializable values to strings."""
                        try:
                            if value is None:
                                return None
                            elif hasattr(value, 'value'):  # Enum
                                return value.value
                            elif hasattr(value, 'to_dict'):  # Plaid object
                                return clean_value(value.to_dict())
                            elif isinstance(value, datetime):
                                return value.isoformat()
                            elif hasattr(value, 'isoformat'):  # datetime.date objects
                                return value.isoformat()
                            elif isinstance(value, (list, tuple)):
                                return [clean_value(item) for item in value]
                            elif isinstance(value, dict):
                                return {k: clean_value(v) for k, v in value.items()}
                            else:
                                return value
                        except:
                            return str(value) if value is not None else None
                    
                    # Prepare transaction document with cleaned data
                    transaction_doc = {
                        "id": doc_id,
                        "userId": user_id,  # Partition key
                        "item_id": item_id,
                        "transaction_id": transaction_id,
                        "account_id": account_id,
                        "transaction_type": transaction_type,
                        "amount": clean_value(get_txn_value("amount")),
                        "date": clean_value(get_txn_value("date")),
                        "authorized_date": clean_value(get_txn_value("authorized_date")),
                        "name": clean_value(get_txn_value("name")),
                        "merchant_name": clean_value(get_txn_value("merchant_name")),
                        "category": clean_value(get_txn_value("category", [])),
                        "category_id": clean_value(get_txn_value("category_id")),
                        "iso_currency_code": clean_value(get_txn_value("iso_currency_code")),
                        "unofficial_currency_code": clean_value(get_txn_value("unofficial_currency_code")),
                        "location": clean_value(get_txn_value("location", {})),
                        "payment_meta": clean_value(get_txn_value("payment_meta", {})),
                        "account_owner": clean_value(get_txn_value("account_owner")),
                        "transaction_code": clean_value(get_txn_value("transaction_code")),
                        "personal_finance_category": clean_value(get_txn_value("personal_finance_category", {})),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "plaid_data": clean_value(txn_dict)  # Store full cleaned Plaid data
                    }
                    
                    logger.debug(f"Prepared transaction document with {len(transaction_doc)} fields")
                    
                    # Store in CosmosDB (upsert)
                    logger.info(f"📝 Storing transaction {transaction_id} with doc_id: {doc_id}")
                    try:
                        cosmos_client.create_item(self.container_name, transaction_doc, user_id)
                        logger.info(f"✅ Created new transaction document: {doc_id}")
                    except CosmosHttpResponseError as e:
                        if e.status_code == 409:  # Document exists, update it
                            # Get existing document to preserve created_at
                            try:
                                existing_doc = cosmos_client.get_item(
                                    self.container_name, doc_id, user_id
                                )
                                if existing_doc and "created_at" in existing_doc:
                                    transaction_doc["created_at"] = existing_doc["created_at"]
                            except Exception as get_error:
                                logger.warning(f"Could not get existing transaction for created_at: {get_error}")
                            
                            # Add last_updated timestamp
                            transaction_doc["last_updated"] = datetime.now(timezone.utc).isoformat()
                            
                            cosmos_client.update_item(
                                self.container_name, doc_id, user_id, transaction_doc
                            )
                            logger.info(f"✅ Updated existing transaction document: {doc_id}")
                        else:
                            logger.error(f"❌ CosmosDB error for transaction {transaction_id}: {e}")
                            raise
                    
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to store transaction {transaction_id}: {e}", exc_info=True)
                    continue
            
            logger.info(f"🎉 TRANSACTION STORAGE COMPLETE: {stored_count}/{len(transactions)} {transaction_type} transactions stored successfully")
            return stored_count > 0
            
        except Exception as e:
            logger.error(f"Failed to store transactions: {e}")
            return False


# Global instance to be imported by other services
transaction_storage_service = TransactionStorageService()
