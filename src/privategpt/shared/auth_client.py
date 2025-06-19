from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from .settings import settings  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL: str = settings.get("services.auth_service") or os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")


class AuthServiceClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"} if token else {}
        self._user_info_cache: Optional[Dict[str, Any]] = None

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{AUTH_SERVICE_URL}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                r = await client.request(method, url, headers=self.headers, timeout=10.0, **kwargs)
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as exc:
                logger.error("auth client http error %s: %s", exc.response.status_code, exc.response.text)
                _raise(exc)
            except httpx.RequestError as exc:
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    async def _me(self) -> Dict[str, Any]:
        if self._user_info_cache is None:
            self._user_info_cache = await self._request("GET", "/auth/me")
        return self._user_info_cache

    async def verify_access(self, client_id: str) -> bool:
        info = await self._me()
        if info.get("role") == "admin":
            return True
        allowed = [c["id"] for c in info.get("authorized_clients", [])]
        return client_id in allowed

    async def get_authorized_clients(self) -> List[Dict]:
        return (await self._me()).get("authorized_clients", [])


def _raise(exc: httpx.HTTPStatusError):  # helper
    code = exc.response.status_code
    detail = exc.response.json().get("detail", exc.response.text) if exc.response.text else "error"
    raise HTTPException(code, detail) 