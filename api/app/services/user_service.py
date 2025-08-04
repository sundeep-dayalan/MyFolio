"""
User service for business logic.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from firebase_admin import firestore

from ..models.user import UserCreate, UserUpdate, UserResponse, UserInDB
from ..exceptions import UserNotFoundError, UserAlreadyExistsError, FirebaseError
from ..utils.logger import get_logger
from ..utils.security import sanitize_input

logger = get_logger(__name__)


class UserService:
    """User service class."""
    
    def __init__(self, db: firestore.Client):
        self.db = db
        self.collection = "users"
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""
        try:
            # Check if user already exists
            if await self.get_user_by_id(user_data.id):
                raise UserAlreadyExistsError(user_data.id)
            
            # Sanitize input data
            sanitized_data = self._sanitize_user_data(user_data.dict())
            
            # Add timestamps
            now = datetime.utcnow()
            user_doc = {
                **sanitized_data,
                "created_at": now,
                "updated_at": now,
                "is_active": True,
                "metadata": {}
            }
            
            # Save to Firestore
            doc_ref = self.db.collection(self.collection).document(user_data.id)
            doc_ref.set(user_doc)
            
            logger.info(f"User created successfully: {user_data.id}")
            return UserResponse(**user_doc)
            
        except UserAlreadyExistsError:
            raise
        except Exception as e:
            logger.error(f"Error creating user {user_data.id}: {str(e)}")
            raise FirebaseError(f"Failed to create user: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        try:
            doc_ref = self.db.collection(self.collection).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                user_data['id'] = user_id
                return UserResponse(**user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise FirebaseError(f"Failed to get user: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email."""
        try:
            query = self.db.collection(self.collection).where("email", "==", email).limit(1)
            docs = query.stream()
            
            for doc in docs:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                return UserResponse(**user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            raise FirebaseError(f"Failed to get user: {str(e)}")
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user."""
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise UserNotFoundError(user_id)
            
            # Prepare update data
            update_data = {}
            for field, value in user_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = sanitize_input(str(value)) if isinstance(value, str) else value
            
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                
                # Update in Firestore
                doc_ref = self.db.collection(self.collection).document(user_id)
                doc_ref.update(update_data)
                
                logger.info(f"User updated successfully: {user_id}")
            
            # Return updated user
            return await self.get_user_by_id(user_id)
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise FirebaseError(f"Failed to update user: {str(e)}")
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user (soft delete by setting is_active to False)."""
        try:
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise UserNotFoundError(user_id)
            
            # Soft delete
            doc_ref = self.db.collection(self.collection).document(user_id)
            doc_ref.update({
                "is_active": False,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"User deleted successfully: {user_id}")
            return True
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise FirebaseError(f"Failed to delete user: {str(e)}")
    
    async def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get list of users with optimized querying to avoid composite indexes."""
        try:
            # Option 1: Get all active users first (if using single field index)
            # This approach works well when you have an index on 'is_active' field
            query = (
                self.db.collection(self.collection)
                .where("is_active", "==", True)
                .limit(limit + skip)
            )
            
            users = []
            count = 0
            
            for doc in query.stream():
                if count < skip:
                    count += 1
                    continue
                    
                if len(users) >= limit:
                    break
                
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                users.append(UserResponse(**user_data))
                count += 1
            
            # Sort by created_at in memory (for small datasets)
            users.sort(key=lambda x: x.created_at)
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            
            # Fallback: Simple query without filtering (if is_active index doesn't exist)
            try:
                logger.info("Falling back to simple query without is_active filter")
                query = (
                    self.db.collection(self.collection)
                    .order_by("created_at")
                    .limit(limit + skip + 20)  # Get a few extra to account for inactive users
                )
                
                users = []
                count = 0
                skipped = 0
                
                for doc in query.stream():
                    user_data = doc.to_dict()
                    user_data['id'] = doc.id
                    
                    # Filter active users in memory
                    if user_data.get('is_active', True):
                        if skipped < skip:
                            skipped += 1
                            continue
                        
                        if count >= limit:
                            break
                            
                        users.append(UserResponse(**user_data))
                        count += 1
                
                return users
                
            except Exception as fallback_error:
                logger.error(f"Fallback query also failed: {str(fallback_error)}")
                raise FirebaseError(f"Failed to get users: {str(e)}")
    
    def _sanitize_user_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize user input data."""
        sanitized = {}
        string_fields = ["name", "given_name", "family_name"]
        
        for key, value in data.items():
            if key in string_fields and isinstance(value, str):
                sanitized[key] = sanitize_input(value)
            else:
                sanitized[key] = value
        
        return sanitized
