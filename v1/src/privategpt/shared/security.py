from __future__ import annotations

"""Security helpers (password hashing, JWT) reusable across services."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict

import bcrypt
from jose import jwt

from .settings import settings  # type: ignore[attr-defined]

# Config values  (in a real system, prefer Pydantic Settings)
_SECRET_KEY: str = (
    settings.get("security.jwt.secret_key") or os.getenv("JWT_SECRET_KEY", "change_me")
)
_ALGORITHM: str = settings.get("security.jwt.algorithm", "HS256")
_EXPIRY_HOURS: int = int(settings.get("security.jwt.expiry_hours", 24))
_BCRYPT_ROUNDS: int = int(settings.get("security.auth.bcrypt_rounds", 12))


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# JWT handling
# ---------------------------------------------------------------------------

def _build_claims(data: Dict[str, Any], expires_delta: timedelta | None = None) -> Dict[str, Any]:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=_EXPIRY_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return to_encode


def create_access_token(data: Dict[str, Any], *, expires: timedelta | None = None) -> str:
    claims = _build_claims(data, expires)
    return jwt.encode(claims, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM]) 