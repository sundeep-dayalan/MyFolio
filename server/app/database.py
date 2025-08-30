"""
Database connection and setup for Azure CosmosDB.
"""

import logging
from typing import Optional
from azure.cosmos import CosmosClient, DatabaseProxy, ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError

from .settings import settings
from .constants import Containers

logger = logging.getLogger(__name__)


class CosmosDBClient:
    """CosmosDB client manager."""

    def __init__(self):
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._containers: dict[str, ContainerProxy] = {}

    async def connect(self) -> None:
        """Initialize CosmosDB connection."""
        try:
            if not self._client:
                # Initialize Cosmos client
                self._client = CosmosClient(
                    settings.cosmos_db_endpoint, credential=settings.cosmos_db_key
                )
                logger.info("CosmosDB client initialized successfully")

            if not self._database:
                # Get database
                self._database = self._client.get_database_client(
                    settings.cosmos_db_name
                )
                logger.info(
                    f"Connected to CosmosDB database: {settings.cosmos_db_name}"
                )

                # Initialize container references
                self._initialize_containers()

        except Exception as e:
            logger.error(f"Failed to initialize CosmosDB: {e}")
            raise

    def _initialize_containers(self) -> None:
        """Initialize container references."""
        container_names = [Containers.USERS, Containers.TRANSACTIONS]

        for container_name in container_names:
            try:
                container = self._database.get_container_client(container_name)
                self._containers[container_name] = container
                logger.info(f"Initialized container reference: {container_name}")
            except CosmosResourceNotFoundError:
                logger.warning(f"Container not found: {container_name}")
            except Exception as e:
                logger.error(f"Failed to initialize container {container_name}: {e}")

    async def disconnect(self) -> None:
        """Clean up CosmosDB connection."""
        try:
            if self._client:
                self._client.close()
                self._client = None
                self._database = None
                self._containers = {}
                logger.info("CosmosDB connection closed")
        except Exception as e:
            logger.error(f"Error closing CosmosDB connection: {e}")

    @property
    def database(self) -> DatabaseProxy:
        """Get CosmosDB database client."""
        if not self._database:
            raise RuntimeError(
                "CosmosDB database not initialized. Call connect() first."
            )
        return self._database

    @property
    def is_connected(self) -> bool:
        """Check if CosmosDB is connected."""
        return self._database is not None

    async def ensure_connected(self) -> None:
        """Ensure CosmosDB connection is established, connecting if needed."""
        if not self.is_connected:
            await self.connect()

    def get_container(self, container_name: str) -> ContainerProxy:
        """Get a specific container client."""
        if not self.is_connected:
            raise RuntimeError("CosmosDB not connected. Call connect() first.")

        if container_name not in self._containers:
            # Try to get container if not cached
            try:
                container = self._database.get_container_client(container_name)
                self._containers[container_name] = container
            except CosmosResourceNotFoundError:
                raise RuntimeError(
                    f"Container '{container_name}' not found in database"
                )

        return self._containers[container_name]

    def create_item(self, container_name: str, item: dict, user_id: str = None) -> dict:
        """Create an item in a container."""
        container = self.get_container(container_name)

        # Ensure userId is set for partitioning
        if user_id and "userId" not in item:
            item["userId"] = user_id

        try:
            response = container.create_item(item)
            logger.debug(f"Created item in {container_name}: {response.get('id')}")
            return response
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to create item in {container_name}: {e}")
            raise

    def get_item(self, container_name: str, item_id: str, user_id: str) -> dict:
        """Get an item by ID."""
        container = self.get_container(container_name)

        try:
            response = container.read_item(item_id, partition_key=user_id)
            logger.debug(f"Retrieved item from {container_name}: {item_id}")
            return response
        except CosmosResourceNotFoundError:
            logger.debug(f"Item not found in {container_name}: {item_id}")
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to get item from {container_name}: {e}")
            raise

    def update_item(
        self, container_name: str, item_id: str, user_id: str, updates: dict
    ) -> dict:
        """Update an item."""
        container = self.get_container(container_name)

        try:
            # First get the current item
            current_item = self.get_item(container_name, item_id, user_id)
            if not current_item:
                raise CosmosResourceNotFoundError(f"Item {item_id} not found")

            # Update the item with new data
            current_item.update(updates)

            response = container.replace_item(item_id, current_item)
            logger.debug(f"Updated item in {container_name}: {item_id}")
            return response
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to update item in {container_name}: {e}")
            raise

    def delete_item(self, container_name: str, item_id: str, user_id: str) -> bool:
        """Delete an item."""
        container = self.get_container(container_name)

        try:
            container.delete_item(item_id, partition_key=user_id)
            logger.debug(f"Deleted item from {container_name}: {item_id}")
            return True
        except CosmosResourceNotFoundError:
            logger.debug(f"Item not found for deletion in {container_name}: {item_id}")
            return False
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to delete item from {container_name}: {e}")
            raise

    def query_items(
        self,
        container_name: str,
        query: str,
        parameters: list = None,
        user_id: str = None,
    ) -> list:
        """Query items in a container."""
        container = self.get_container(container_name)

        try:
            # Enable cross partition queries if no user_id specified
            enable_cross_partition = user_id is None

            items = list(
                container.query_items(
                    query=query,
                    parameters=parameters or [],
                    enable_cross_partition_query=enable_cross_partition,
                    partition_key=user_id if user_id else None,
                )
            )

            logger.debug(f"Queried {len(items)} items from {container_name}")
            return items
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to query items from {container_name}: {e}")
            raise

    def get_items_by_user(
        self, container_name: str, user_id: str, limit: int = None
    ) -> list:
        """Get all items for a specific user."""
        query = "SELECT * FROM c WHERE c.userId = @userId"
        if limit:
            query += f" OFFSET 0 LIMIT {limit}"

        parameters = [{"name": "@userId", "value": user_id}]

        return self.query_items(container_name, query, parameters, user_id)


# Global CosmosDB client instance
cosmos_client = CosmosDBClient()
