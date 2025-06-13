from __future__ import annotations

"""Shared asynchronous Auth Service client.

Originally duplicated in multiple services; centralised here for reuse.
Minor refactor: module-level constant `AUTH_SERVICE_URL` now falls back to
``privategpt.shared.settings`` if available.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from .settings import settings  # type: ignore – runtime proxy

logger = logging.getLogger(__name__)

# Prefer value from settings; fallback to env var; then to default
AUTH_SERVICE_URL: str = (
    settings.get("services.auth_service")  # type: ignore[attr-defined]
    or os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
)


class AuthServiceClient:
    """Lightweight wrapper around the Auth micro-service REST API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self._user_info_cache: Optional[Dict[str, Any]] = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{AUTH_SERVICE_URL}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                logger.debug("Calling %s %s", method, url)
                response = await client.request(
                    method, url, params=params, headers=self.headers, timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error calling auth service %s: %s - %s",
                    endpoint,
                    exc.response.status_code,
                    exc.response.text,
                )
                return _raise_http_exception(exc)
            except httpx.RequestError as exc:
                logger.error("Request error calling auth service %s: %s", endpoint, exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Auth service unavailable: {exc.__class__.__name__}",
                ) from exc
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error calling auth service %s", endpoint)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unexpected error interacting with auth service.",
                ) from exc

    async def _get_user_info(self) -> Dict[str, Any]:
        """Cache results from `/auth/me` to minimise network chatter."""
        if not self.token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided for user info lookup",
            )

        if self._user_info_cache is None:
            self._user_info_cache = await self._make_request("GET", "/auth/me")
        return self._user_info_cache

    async def verify_access(
        self,
        user_id: str,
        client_id: str,
        permission_action: str,
    ) -> bool:
        """Return *True* if user may perform *permission_action* on *client_id*."""
        try:
            user_info = await self._get_user_info()
            role = user_info.get("role", "")
            if role == "admin":  # Admins allowed everywhere
                return True

            authorized = [c["id"] for c in user_info.get("authorized_clients", [])]
            is_auth = client_id in authorized
            logger.debug(
                "verify_access: user=%s role=%s permitted=%s for client %s",
                user_id,
                role,
                is_auth,
                client_id,
            )
            return is_auth
        except HTTPException:
            return False
        except Exception:  # noqa: BLE001
            logger.exception("verify_access unexpected error")
            return False

    async def get_accessible_client_matters(
        self, user_id: str, permission_action: str
    ) -> List[str]:
        """Return list of client IDs a user can access."""
        try:
            user_info = await self._get_user_info()
            role = user_info.get("role", "")
            if role == "admin":
                return ["__ALL_CLIENTS__"]
            return [c["id"] for c in user_info.get("authorized_clients", [])]
        except Exception:  # noqa: BLE001
            logger.exception("get_accessible_client_matters error")
            return []

    async def get_my_authorized_clients(self) -> List[Dict[str, Any]]:
        """Return list of authorised client dictionaries from `/auth/me`."""
        try:
            user_info = await self._get_user_info()
            return user_info.get("authorized_clients", [])
        except Exception:  # noqa: BLE001
            logger.exception("get_my_authorized_clients error")
            return []


def _raise_http_exception(exc: httpx.HTTPStatusError):  # noqa: D401 – helper fn
    """Translate HTTPStatusError to FastAPI HTTPException with better message."""
    status_code = exc.response.status_code
    detail = "Error communicating with auth service"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        detail = "Not authorized by auth service."
    elif status_code == status.HTTP_403_FORBIDDEN:
        detail = "Access forbidden by auth service."
    elif status_code == status.HTTP_404_NOT_FOUND:
        detail = "Auth service resource not found."

    try:
        if (data := exc.response.json()) and "detail" in data:
            detail = f"Auth service error: {data['detail']}"
    except Exception:  # noqa: BLE001
        pass

    raise HTTPException(status_code=status_code, detail=detail) from exc 