from __future__ import annotations

"""
User profile and preferences management for the API Gateway.
Handles application-specific user data beyond what Keycloak manages.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from privategpt.infra.database.models import User
from privategpt.shared.logging import get_logger

logger = get_logger("gateway-user-service")


class UserService:
    """Service for managing user profiles and application-specific user data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_or_create_user_from_keycloak(
        self, 
        keycloak_user_id: str, 
        email: str, 
        username: str = None,
        first_name: str = None,
        last_name: str = None,
        roles: list[str] = None
    ) -> User:
        """
        Get existing user or create new user from Keycloak data.
        This syncs Keycloak users with our local user table.
        """
        # Try to find existing user by keycloak ID or email
        user = self.db.query(User).filter(
            (User.keycloak_id == keycloak_user_id) | (User.email == email)
        ).first()
        
        if user:
            # Update existing user with latest Keycloak data
            user.keycloak_id = keycloak_user_id
            user.email = email
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            
            # Update role from Keycloak roles
            if roles:
                user.role = "admin" if "admin" in roles else "user"
            
            self.db.commit()
            self.db.refresh(user)
            logger.info("Updated user from Keycloak", user_id=user.id, email=email)
        else:
            # Create new user from Keycloak data
            try:
                user = User(
                    keycloak_id=keycloak_user_id,
                    email=email,
                    username=username or email.split("@")[0],
                    first_name=first_name,
                    last_name=last_name,
                    role="admin" if roles and "admin" in roles else "user",
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info("Created new user from Keycloak", user_id=user.id, email=email)
            except IntegrityError:
                self.db.rollback()
                # Race condition - user was created by another request
                user = self.db.query(User).filter(User.email == email).first()
                if not user:
                    raise ValueError("Failed to create or find user")
        
        return user
    
    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile with application-specific data."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        return {
            "id": user.id,
            "keycloak_id": user.keycloak_id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "preferences": user.preferences or {},
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    
    def update_user_profile(
        self, 
        user_id: int, 
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update user profile data (non-auth fields only)."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Only allow updating specific fields (not auth-related ones)
        allowed_fields = {"username", "first_name", "last_name", "preferences"}
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            logger.info("Updated user profile", user_id=user_id, fields=list(updates.keys()))
            return self.get_user_profile(user_id)
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Failed to update user profile")
    
    def update_user_preferences(
        self, 
        user_id: int, 
        preferences: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update user preferences (app-specific settings)."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Merge with existing preferences
        current_prefs = user.preferences or {}
        current_prefs.update(preferences)
        user.preferences = current_prefs
        
        try:
            self.db.commit()
            self.db.refresh(user)
            logger.info("Updated user preferences", user_id=user_id)
            return self.get_user_profile(user_id)
        except Exception:
            self.db.rollback()
            raise ValueError("Failed to update user preferences")
    
    def record_user_login(self, user_id: int) -> None:
        """Record when user last logged in."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login = datetime.utcnow()
            self.db.commit()
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account (soft delete)."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        logger.info("Deactivated user", user_id=user_id)
        return True
    
    def list_users(self, limit: int = 50, offset: int = 0) -> list[Dict[str, Any]]:
        """List users for admin purposes."""
        users = self.db.query(User).offset(offset).limit(limit).all()
        return [self.get_user_profile(user.id) for user in users]