"""
Database connection and setup.
"""
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)

class FirebaseClient:
    """Firebase client manager."""
    
    def __init__(self):
        self._db: Optional[firestore.Client] = None
        self._app: Optional[firebase_admin.App] = None
    
    async def connect(self) -> None:
        """Initialize Firebase connection."""
        try:
            if not self._app:
                # Load credentials
                cred = credentials.Certificate(settings.firebase_credentials_path)
                
                # Initialize Firebase app
                self._app = firebase_admin.initialize_app(cred, {
                    'projectId': settings.firebase_project_id
                })
                logger.info("Firebase Admin SDK initialized successfully")
            
            if not self._db:
                # Get Firestore client
                self._db = firestore.client(app=self._app)
                logger.info(f"Firestore client connected successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Clean up Firebase connection."""
        try:
            if self._app:
                firebase_admin.delete_app(self._app)
                self._app = None
                self._db = None
                logger.info("Firebase connection closed")
        except Exception as e:
            logger.error(f"Error closing Firebase connection: {e}")
    
    @property
    def db(self) -> firestore.Client:
        """Get Firestore client."""
        if not self._db:
            raise RuntimeError("Firestore client not initialized. Call connect() first.")
        return self._db
    
    @property
    def is_connected(self) -> bool:
        """Check if Firebase is connected."""
        return self._db is not None


# Global Firebase client instance
firebase_client = FirebaseClient()
