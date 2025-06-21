from __future__ import annotations

"""
Authentication endpoints for the API Gateway.
Handles login, logout, token verification, and Keycloak integration.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from privategpt.infra.database.session import get_db
from privategpt.services.gateway.core.keycloak_auth import KeycloakAuthService
from privategpt.services.gateway.core.user_service import UserService
from privategpt.shared.settings import settings
from privategpt.shared.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Request/Response models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class TokenVerifyResponse(BaseModel):
    valid: bool
    user: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Dependencies
def get_keycloak_service() -> KeycloakAuthService:
    """Get Keycloak authentication service instance."""
    return KeycloakAuthService()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Get user service instance."""
    return UserService(db)


# Direct authentication endpoints (no auth middleware needed)
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    keycloak_service: KeycloakAuthService = Depends(get_keycloak_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Authenticate user with email and password.
    
    For development/demo mode, accepts:
    - admin@admin.com / admin
    """
    try:
        # Try Keycloak authentication first
        token_response = await keycloak_service.login_with_password(
            request.email, 
            request.password
        )
        
        if token_response:
            # Decode token to get user info
            try:
                # Get user info from token
                user_info = await keycloak_service.get_user_info(token_response["access_token"])
                
                # Sync user with local database
                local_user = await user_service.get_or_create_user_from_keycloak(
                    keycloak_user_id=user_info.get("sub", ""),
                    email=user_info.get("email", request.email),
                    username=user_info.get("preferred_username"),
                    first_name=user_info.get("given_name"),
                    last_name=user_info.get("family_name"),
                    roles=user_info.get("realm_access", {}).get("roles", [])
                )
                
                # Record login
                user_service.record_user_login(local_user.id)
                
                # Build user response
                user_data = {
                    "user_id": local_user.id,
                    "email": local_user.email,
                    "username": local_user.username,
                    "first_name": local_user.first_name,
                    "last_name": local_user.last_name,
                    "role": local_user.role
                }
                
                return LoginResponse(
                    access_token=token_response["access_token"],
                    expires_in=token_response.get("expires_in", 3600),
                    refresh_token=token_response.get("refresh_token"),
                    user=user_data
                )
            except Exception as e:
                logger.error(f"Failed to process token: {e}")
                # Return token without user info
                return LoginResponse(
                    access_token=token_response["access_token"],
                    expires_in=token_response.get("expires_in", 3600),
                    refresh_token=token_response.get("refresh_token")
                )
        
        # Authentication failed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(
    request: Request,
    keycloak_service: KeycloakAuthService = Depends(get_keycloak_service),
):
    """
    Verify the validity of an access token.
    Token should be provided in Authorization header.
    """
    # Extract token from header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return TokenVerifyResponse(valid=False)
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # First try Keycloak verification
        is_valid = await keycloak_service.verify_token(token)
        
        if is_valid:
            # Get user info from token
            user_info = await keycloak_service.get_user_info(token)
            return TokenVerifyResponse(
                valid=True,
                user=user_info
            )
        
        # If Keycloak verification fails, token is invalid
        
        return TokenVerifyResponse(valid=False)
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return TokenVerifyResponse(valid=False)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    keycloak_service: KeycloakAuthService = Depends(get_keycloak_service),
):
    """Refresh access token using refresh token."""
    try:
        token_response = await keycloak_service.refresh_token(request.refresh_token)
        
        if token_response:
            return LoginResponse(
                access_token=token_response["access_token"],
                expires_in=token_response.get("expires_in", 3600),
                refresh_token=token_response.get("refresh_token")
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    request: Request,
    keycloak_service: KeycloakAuthService = Depends(get_keycloak_service),
):
    """
    Logout user and invalidate tokens.
    Token should be provided in Authorization header.
    """
    # Extract token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Try to logout from Keycloak
            await keycloak_service.logout(token)
        except Exception as e:
            logger.error(f"Keycloak logout error: {e}")
            # Continue even if Keycloak logout fails
    
    return {"message": "Logout successful"}


@router.get("/keycloak/config")
async def get_keycloak_config():
    """
    Get Keycloak configuration for frontend.
    Used for Keycloak.js initialization.
    """
    return {
        "url": settings.keycloak_url,
        "realm": settings.keycloak_realm,
        "clientId": settings.keycloak_client_id
    }