"""
Azure Cosmos DB connection and configuration
Replaces Firebase Firestore with Azure Cosmos DB
"""

import os
import logging
from typing import Optional, Dict, Any, List
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class CosmosDBClient:
    """Azure Cosmos DB client for managing database operations"""
    
    def __init__(self):
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.containers = {}
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Cosmos DB client"""
        try:
            # Get configuration from environment variables
            cosmos_endpoint = os.getenv('COSMOS_DB_ENDPOINT')
            cosmos_key = os.getenv('COSMOS_DB_KEY')
            database_name = os.getenv('COSMOS_DB_NAME', 'sage-db')
            
            if not cosmos_endpoint:
                raise ValueError("COSMOS_DB_ENDPOINT environment variable is required")
            
            # Initialize client with key or managed identity
            if cosmos_key:
                self.client = CosmosClient(cosmos_endpoint, cosmos_key)
            else:
                # Use managed identity in production
                credential = DefaultAzureCredential()
                self.client = CosmosClient(cosmos_endpoint, credential)
            
            # Get database
            self.database = self.client.get_database_client(database_name)
            
            # Initialize containers
            self._initialize_containers()
            
            logger.info("Cosmos DB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos DB client: {str(e)}")
            raise
    
    def _initialize_containers(self):
        """Initialize database containers"""
        container_configs = [
            {
                'name': 'users',
                'partition_key': '/userId',
                'description': 'User profiles and authentication data'
            },
            {
                'name': 'accounts',
                'partition_key': '/userId',
                'description': 'Financial account information'
            },
            {
                'name': 'transactions',
                'partition_key': '/userId',
                'description': 'Financial transaction records'
            },
            {
                'name': 'plaid_tokens',
                'partition_key': '/userId',
                'description': 'Encrypted Plaid access tokens'
            }
        ]
        
        for config in container_configs:
            try:
                container = self.database.get_container_client(config['name'])
                self.containers[config['name']] = container
                logger.info(f"Container '{config['name']}' connected successfully")
            except exceptions.CosmosResourceNotFoundError:
                logger.warning(f"Container '{config['name']}' not found. It should be created during infrastructure deployment.")
            except Exception as e:
                logger.error(f"Error connecting to container '{config['name']}': {str(e)}")
    
    def get_container(self, container_name: str):
        """Get a container client"""
        if container_name not in self.containers:
            raise ValueError(f"Container '{container_name}' not initialized")
        return self.containers[container_name]
    
    def health_check(self) -> bool:
        """Check if Cosmos DB connection is healthy"""
        try:
            # Simple read operation to check connectivity
            list(self.database.list_containers())
            return True
        except Exception as e:
            logger.error(f"Cosmos DB health check failed: {str(e)}")
            return False


class DocumentService:
    """Service for document operations in Cosmos DB"""
    
    def __init__(self, cosmos_client: CosmosDBClient):
        self.cosmos_client = cosmos_client
    
    async def create_document(self, container_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document"""
        try:
            container = self.cosmos_client.get_container(container_name)
            
            # Ensure the document has an id
            if 'id' not in document:
                raise ValueError("Document must have an 'id' field")
            
            created_item = container.create_item(body=document)
            logger.info(f"Document created in {container_name}: {document.get('id')}")
            return created_item
            
        except exceptions.CosmosResourceExistsError:
            logger.error(f"Document with id {document.get('id')} already exists in {container_name}")
            raise ValueError(f"Document with id {document.get('id')} already exists")
        except Exception as e:
            logger.error(f"Error creating document in {container_name}: {str(e)}")
            raise
    
    async def get_document(self, container_name: str, document_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            container = self.cosmos_client.get_container(container_name)
            item = container.read_item(item=document_id, partition_key=partition_key)
            return item
            
        except exceptions.CosmosResourceNotFoundError:
            logger.info(f"Document {document_id} not found in {container_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting document {document_id} from {container_name}: {str(e)}")
            raise
    
    async def update_document(self, container_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing document"""
        try:
            container = self.cosmos_client.get_container(container_name)
            
            if 'id' not in document:
                raise ValueError("Document must have an 'id' field")
            
            updated_item = container.replace_item(item=document['id'], body=document)
            logger.info(f"Document updated in {container_name}: {document.get('id')}")
            return updated_item
            
        except exceptions.CosmosResourceNotFoundError:
            logger.error(f"Document {document.get('id')} not found in {container_name}")
            raise ValueError(f"Document with id {document.get('id')} not found")
        except Exception as e:
            logger.error(f"Error updating document in {container_name}: {str(e)}")
            raise
    
    async def delete_document(self, container_name: str, document_id: str, partition_key: str) -> bool:
        """Delete a document"""
        try:
            container = self.cosmos_client.get_container(container_name)
            container.delete_item(item=document_id, partition_key=partition_key)
            logger.info(f"Document deleted from {container_name}: {document_id}")
            return True
            
        except exceptions.CosmosResourceNotFoundError:
            logger.info(f"Document {document_id} not found in {container_name}")
            return False
        except Exception as e:
            logger.error(f"Error deleting document {document_id} from {container_name}: {str(e)}")
            raise
    
    async def query_documents(self, container_name: str, query: str, parameters: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Query documents using SQL"""
        try:
            container = self.cosmos_client.get_container(container_name)
            
            items = container.query_items(
                query=query,
                parameters=parameters or [],
                enable_cross_partition_query=True
            )
            
            return list(items)
            
        except Exception as e:
            logger.error(f"Error querying documents in {container_name}: {str(e)}")
            raise
    
    async def get_user_documents(self, container_name: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific user"""
        query = "SELECT * FROM c WHERE c.userId = @userId"
        parameters = [{"name": "@userId", "value": user_id}]
        return await self.query_documents(container_name, query, parameters)


# Global instances
cosmos_client: Optional[CosmosDBClient] = None
document_service: Optional[DocumentService] = None


def get_cosmos_client() -> CosmosDBClient:
    """Get the global Cosmos DB client instance"""
    global cosmos_client
    if cosmos_client is None:
        cosmos_client = CosmosDBClient()
    return cosmos_client


def get_document_service() -> DocumentService:
    """Get the global document service instance"""
    global document_service
    if document_service is None:
        client = get_cosmos_client()
        document_service = DocumentService(client)
    return document_service


async def initialize_database():
    """Initialize database connections"""
    try:
        # Initialize Cosmos DB client
        get_cosmos_client()
        get_document_service()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


async def close_database():
    """Close database connections"""
    global cosmos_client, document_service
    try:
        # Cosmos DB client doesn't require explicit closing
        cosmos_client = None
        document_service = None
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")