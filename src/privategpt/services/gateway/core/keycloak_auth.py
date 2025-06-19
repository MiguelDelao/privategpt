from __future__ import annotations

"""
Keycloak authentication helpers for the gateway.
"""

import logging
from typing import Dict, Any, Optional

import httpx

from privategpt.shared.settings import settings

logger = logging.getLogger(__name__)


class KeycloakAuthService:
    """Service for interacting with Keycloak for authentication."""
    
    def __init__(self):
        self.keycloak_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = "privategpt-ui"  # UI client for direct grant
        self.client_secret = "privategpt-ui-secret-key"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def login_with_password(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Login user with email/password using Keycloak direct grant flow.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Token response if successful, None if failed
        """
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": email,
            "password": password,
            "scope": "openid profile email"
        }
        
        try:
            response = await self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Get user info
                user_info = await self.get_user_info(token_data["access_token"])
                
                return {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "user": user_info
                }
            else:
                logger.warning(f"Login failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from access token."""
        userinfo_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo"
        
        try:
            response = await self.client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "email": user_data.get("email"),
                    "username": user_data.get("preferred_username"),
                    "first_name": user_data.get("given_name"),
                    "last_name": user_data.get("family_name"),
                    "role": self.extract_primary_role(user_data),
                    "roles": user_data.get("realm_access", {}).get("roles", [])
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def extract_primary_role(self, user_data: Dict[str, Any]) -> str:
        """Extract primary role from user data."""
        roles = user_data.get("realm_access", {}).get("roles", [])
        
        if "admin" in roles:
            return "admin"
        elif "user" in roles:
            return "user"
        else:
            return "user"  # default
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }
        
        try:
            response = await self.client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global instance
_keycloak_auth: Optional[KeycloakAuthService] = None


def get_keycloak_auth() -> KeycloakAuthService:
    """Get or create global Keycloak auth service."""
    global _keycloak_auth
    if _keycloak_auth is None:
        _keycloak_auth = KeycloakAuthService()
    return _keycloak_auth