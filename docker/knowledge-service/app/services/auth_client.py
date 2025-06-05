import httpx
import os
import logging
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000") # Default for docker-compose

class AuthServiceClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self._user_info_cache = None  # Cache user info to avoid repeated calls

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                url = f"{AUTH_SERVICE_URL}{endpoint}"
                logger.debug(f"Calling {method} {url} with params: {params}")
                response = await client.request(method, url, params=params, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling auth service endpoint {endpoint}: {e.response.status_code} - {e.response.text}")
                detail = f"Error communicating with auth service: {e.response.status_code}"
                if e.response.status_code == status.HTTP_401_UNAUTHORIZED:
                    detail = "Not authorized by auth service."
                elif e.response.status_code == status.HTTP_403_FORBIDDEN:
                    detail = "Access forbidden by auth service."
                elif e.response.status_code == status.HTTP_404_NOT_FOUND:
                    detail = "Auth service resource not found."
                
                # Try to parse error message from auth service if available
                try:
                    error_data = e.response.json()
                    if "detail" in error_data:
                        detail = f"Auth service error: {error_data['detail']}"
                except:
                    pass # Keep generic detail if parsing fails
                    
                raise HTTPException(status_code=e.response.status_code, detail=detail)
            except httpx.RequestError as e:
                logger.error(f"Request error calling auth service endpoint {endpoint}: {e}")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Auth service unavailable: {e.__class__.__name__}")
            except Exception as e:
                logger.error(f"Unexpected error calling auth service endpoint {endpoint}: {e}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error interacting with auth service.")

    async def _get_user_info(self) -> Dict[str, Any]:
        """Get current user info from /auth/me endpoint"""
        if not self.token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided for user info lookup")
        
        if self._user_info_cache is None:
            self._user_info_cache = await self._make_request("GET", "/auth/me")
        return self._user_info_cache

    async def verify_access(self, user_id: str, client_id: str, permission_action: str) -> bool:
        """
        Verify if the user has access to a specific client.
        Since the current auth service doesn't have /internal/verify-access,
        we'll use /auth/me to get the user's authorized clients and check if client_id is in the list.
        Admin users have access to all clients.
        """
        try:
            user_info = await self._get_user_info()
            user_role = user_info.get("role", "")
            
            # Admin users have access to all clients
            if user_role == "admin":
                logger.debug(f"User {user_id} is admin - granting access to client {client_id}")
                return True
            
            # Regular users need to be in the authorized clients list
            authorized_clients = user_info.get("authorized_clients", [])
            authorized_client_ids = [client["id"] for client in authorized_clients]
            
            # Check if the client_id is in the user's authorized clients
            is_authorized = client_id in authorized_client_ids
            
            logger.debug(f"User {user_id} (role: {user_role}) access check: has access to clients {authorized_client_ids}, requested {client_id}, authorized: {is_authorized}")
            return is_authorized
            
        except HTTPException as e:
            logger.warning(f"verify_access call for user {user_id} on client {client_id} (action: {permission_action}) resulted in HTTPException: {e.detail}. Defaulting to access denied.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in verify_access for user {user_id} on client {client_id}: {e}", exc_info=True)
            return False

    async def get_accessible_client_matters(self, user_id: str, permission_action: str) -> List[str]:
        """
        Get list of client IDs the user has access to.
        Uses /auth/me to get the user's authorized_clients and returns their IDs.
        If user is admin, returns a special marker indicating access to all clients.
        """
        try:
            user_info = await self._get_user_info()
            user_role = user_info.get("role", "")
            
            # Admin users have access to all clients
            if user_role == "admin":
                logger.debug(f"User {user_id} is admin - has access to all clients")
                return ["__ALL_CLIENTS__"]  # Special marker for admin access
            
            # Regular users only get their authorized clients
            authorized_clients = user_info.get("authorized_clients", [])
            client_ids = [client["id"] for client in authorized_clients]
            
            logger.debug(f"User {user_id} (role: {user_role}) has access to clients: {client_ids}")
            return client_ids
            
        except HTTPException as e:
            logger.warning(f"get_accessible_client_matters call for user {user_id} (action: {permission_action}) resulted in HTTPException: {e.detail}. Defaulting to no accessible matters.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_accessible_client_matters for user {user_id}: {e}", exc_info=True)
            return []

    async def get_my_authorized_clients(self) -> List[Dict]:
        """
        Get the current user's authorized clients.
        This method matches the interface expected by the Streamlit frontend.
        """
        try:
            user_info = await self._get_user_info()
            return user_info.get("authorized_clients", [])
        except Exception as e:
            logger.error(f"Error getting authorized clients: {e}", exc_info=True)
            return []

# Example usage (for testing or direct use if token is managed elsewhere)
async def get_auth_client(token: Optional[str] = None) -> AuthServiceClient:
    return AuthServiceClient(token=token) 