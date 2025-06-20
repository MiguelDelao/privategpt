from __future__ import annotations

"""
Authentication client for PrivateGPT UI (v2).
Handles communication with the authentication service.
The base URL is taken from the AUTH_URL environment variable unless
explicitly provided.
"""

from typing import Dict, List, Optional
import os
import requests


class AuthClient:  # noqa: D101
    def __init__(self, gateway_url: str | None = None):
        # Prefer explicit argument, then env var, then sensible localhost default.
        base = gateway_url or os.getenv("GATEWAY_URL") or "http://localhost:8000"
        # Normalise and strip trailing slashes
        self.gateway_url = base.rstrip("/")
        self.session = requests.Session()

    # ---------------------------------------------------------------------
    # Public API matching v1 behaviour (some endpoints not yet ported)
    # ---------------------------------------------------------------------
    def login(self, email: str, password: str) -> Dict:  # noqa: D401
        """Login user and return token response."""
        # For now, this will use direct Keycloak integration
        # TODO: Implement proper OIDC flow
        resp = self.session.post(
            f"{self.gateway_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        raise Exception(f"Login failed: {resp.json().get('detail', resp.text)}")

    def verify_token(self, token: str) -> Optional[Dict]:  # noqa: D401
        """Verify JWT token and return user info (or None)."""
        try:
            resp = self.session.post(
                f"{self.gateway_url}/api/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Admin routes – placeholders until backend parity
    # ------------------------------------------------------------------
    def create_user(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("create_user not yet implemented in v2 UI")

    def list_users(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("list_users not yet implemented in v2 UI")

    def list_clients(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("list_clients not yet implemented in v2 UI")

    def create_client(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("create_client not yet implemented in v2 UI")

    def delete_client(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("delete_client not yet implemented in v2 UI")

    def get_user_authorized_clients(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("get_user_authorized_clients not yet implemented in v2 UI")

    def update_user_authorized_clients(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("update_user_authorized_clients not yet implemented in v2 UI")

    def get_my_authorized_clients(self, *args, **kwargs):  # noqa: D401
        raise NotImplementedError("get_my_authorized_clients not yet implemented in v2 UI") 