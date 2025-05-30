"""
Authentication client for PrivateGPT Legal AI
Handles communication with the authentication service
"""

import requests
from typing import Dict, Optional

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
            response = self.session.get(
                f"{self.auth_service_url}/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception:
            return None
    
    def create_user(self, token: str, email: str, password: str, role: str, client_matters: list) -> Dict:
        """Create new user (admin only)"""
        response = self.session.post(
            f"{self.auth_service_url}/auth/create-user",
            json={
                "email": email,
                "password": password,
                "role": role,
                "client_matters": client_matters
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"User creation failed: {response.json().get('detail', 'Unknown error')}")
    
    def list_users(self, token: str) -> Dict:
        """List all users (admin only)"""
        response = self.session.get(
            f"{self.auth_service_url}/auth/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to list users: {response.json().get('detail', 'Unknown error')}") 