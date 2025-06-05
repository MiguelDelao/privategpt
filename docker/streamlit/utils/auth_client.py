"""
Authentication client for PrivateGPT Legal AI
Handles communication with the authentication service
"""

import requests
from typing import Dict, Optional, List

class AuthClient:
    """Client for authentication service"""
    
    def __init__(self, auth_service_url: str):
        self.auth_service_url = auth_service_url.rstrip('/')
        self.session = requests.Session()
        
    def login(self, email: str, password: str) -> Dict:
        """Login user and return token response"""
        response = self.session.post(
            f"{self.auth_service_url}/auth/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Login failed: {response.json().get('detail', 'Unknown error')}")
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user info"""
        try:
            response = self.session.post(
                f"{self.auth_service_url}/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception:
            return None
    
    def create_user(self, token: str, email: str, password: str, role: str) -> Dict:
        """Create new user (admin only, uses the public registration endpoint)"""
        response = self.session.post(
            f"{self.auth_service_url}/auth/register",
            json={
                "email": email,
                "password": password,
                "role": role
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"User creation failed: {response.json().get('detail', 'Unknown error')}")
    
    def list_users(self, token: str) -> Dict:
        """List all users (admin only)"""
        response = self.session.get(
            f"{self.auth_service_url}/auth/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list users: {response.json().get('detail', 'Unknown error')}")

    # --- Client Management Methods (Admin) ---
    def list_clients(self, token: str) -> List[Dict]:
        """List all defined clients."""
        response = self.session.get(
            f"{self.auth_service_url}/admin/clients/",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', 'Failed to list clients')
            raise Exception(f"List clients failed: {response.status_code} - {error_detail}")

    def create_client(self, token: str, name: str) -> Dict:
        """Create a new client."""
        response = self.session.post(
            f"{self.auth_service_url}/admin/clients/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": name}
        )
        if response.status_code == 201: # Created
            return response.json()
        else:
            error_detail = response.json().get('detail', 'Failed to create client')
            raise Exception(f"Create client failed: {response.status_code} - {error_detail}")

    def delete_client(self, token: str, client_id: str) -> bool:
        """Delete a client by its ID."""
        response = self.session.delete(
            f"{self.auth_service_url}/admin/clients/{client_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 204: # No Content
            return True
        elif response.status_code == 404:
            raise Exception(f"Delete client failed: Client not found (ID: {client_id})")
        else:
            error_detail = response.json().get('detail', 'Failed to delete client')
            raise Exception(f"Delete client failed: {response.status_code} - {error_detail}")

    # --- User-Client Association Methods (Admin) ---
    def get_user_authorized_clients(self, token: str, user_email: str) -> List[Dict]:
        """Get the list of clients a specific user is authorized for."""
        response = self.session.get(
            f"{self.auth_service_url}/admin/users/{user_email}/clients",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', 'Failed to get user clients')
            raise Exception(f"Get user clients failed for {user_email}: {response.status_code} - {error_detail}")

    def update_user_authorized_clients(self, token: str, user_email: str, client_ids: List[str]) -> Dict:
        """Update the list of clients a specific user is authorized for."""
        response = self.session.put(
            f"{self.auth_service_url}/admin/users/{user_email}/clients",
            headers={"Authorization": f"Bearer {token}"},
            json={"client_ids": client_ids}
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get('detail', 'Failed to update user clients')
            raise Exception(f"Update user clients failed for {user_email}: {response.status_code} - {error_detail}")

    # --- Method for current user to get their own authorized clients ---
    def get_my_authorized_clients(self, token: str) -> List[Dict]:
        """Fetches the current user's info and extracts their authorized clients."""
        response = self.session.get(
            f"{self.auth_service_url}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get("authorized_clients", [])
        else:
            error_detail = response.json().get('detail', 'Failed to get current user info')
            raise Exception(f"Get my authorized clients failed: {response.status_code} - {error_detail}") 