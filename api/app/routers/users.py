"""
User management routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from firebase_admin import firestore

from ..models.user import UserCreate, UserUpdate, UserResponse
from ..services.user_service import UserService
from ..dependencies import get_firestore_client, get_current_user_id
from ..exceptions import UserNotFoundError, UserAlreadyExistsError

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: firestore.Client = Depends(get_firestore_client)) -> UserService:
    """Get user service dependency."""
    return UserService(db)


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user."""
    return await user_service.create_user(user_data)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user information."""
    user = await user_service.get_user_by_id(current_user_id)
    if not user:
        raise UserNotFoundError(current_user_id)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID."""
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Update user information."""
    # Users can only update their own information
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot update other users")
    
    return await user_service.update_user(user_id, user_data)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Delete user account."""
    # Users can only delete their own account
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot delete other users")
    
    await user_service.delete_user(user_id)


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    user_service: UserService = Depends(get_user_service)
):
    """List users (for admin purposes)."""
    # In a real application, you would add admin authentication here
    return await user_service.get_users(skip=skip, limit=limit)
