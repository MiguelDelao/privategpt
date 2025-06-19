from __future__ import annotations

"""
User management endpoints for the API Gateway.
Handles user profiles, preferences, and application-specific user data.
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from privategpt.infra.database.session import get_db
from privategpt.shared.auth_middleware import get_current_user, get_admin_user
from privategpt.services.gateway.core.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# Pydantic models for requests/responses
class UserProfileResponse(BaseModel):
    id: int
    keycloak_id: str | None
    email: str
    username: str | None
    first_name: str | None
    last_name: str | None
    role: str
    is_active: bool
    created_at: str | None
    preferences: Dict[str, Any]
    last_login: str | None


class UserProfileUpdate(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserPreferencesUpdate(BaseModel):
    preferences: Dict[str, Any] = Field(..., description="User preferences as key-value pairs")


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)


async def get_current_user_with_sync(
    request: Request,
    user_service: UserService = Depends(get_user_service)
) -> Dict[str, Any]:
    """
    Get current user and ensure they exist in our database.
    Creates user from Keycloak data if they don't exist locally.
    """
    # Get user from token validation
    keycloak_user = await get_current_user(request)
    
    # Sync with local database
    user = await user_service.get_or_create_user_from_keycloak(
        keycloak_user_id=keycloak_user["user_id"],
        email=keycloak_user["email"],
        username=keycloak_user.get("username"),
        first_name=keycloak_user.get("first_name"),
        last_name=keycloak_user.get("last_name"),
        roles=keycloak_user.get("roles", [])
    )
    
    # Record login
    user_service.record_user_login(user.id)
    
    # Return combined user data
    return {
        **keycloak_user,
        "local_user_id": user.id,
        "user": user
    }


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user_with_sync),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user's profile."""
    user_id = current_user["local_user_id"]
    profile = user_service.get_user_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return profile


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    updates: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_with_sync),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user's profile."""
    user_id = current_user["local_user_id"]
    
    # Convert to dict, excluding None values
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    
    try:
        profile = user_service.update_user_profile(user_id, update_data)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me/preferences")
async def get_my_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user_with_sync),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user's preferences."""
    user_id = current_user["local_user_id"]
    profile = user_service.get_user_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"preferences": profile.get("preferences", {})}


@router.put("/me/preferences")
async def update_my_preferences(
    updates: UserPreferencesUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_with_sync),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user's preferences."""
    user_id = current_user["local_user_id"]
    
    try:
        profile = user_service.update_user_preferences(user_id, updates.preferences)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {"preferences": profile.get("preferences", {})}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Admin endpoints
@router.get("/", response_model=List[UserProfileResponse])
async def list_users(
    limit: int = 50,
    offset: int = 0,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """List all users (admin only)."""
    try:
        users = user_service.list_users(limit=limit, offset=offset)
        return users
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Get specific user's profile (admin only)."""
    profile = user_service.get_user_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return profile


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    user_service: UserService = Depends(get_user_service)
):
    """Deactivate user account (admin only)."""
    success = user_service.deactivate_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}