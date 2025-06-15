from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict

import bcrypt
from jose import jwt

from .settings import settings  # type: ignore[attr-defined]

_SECRET_KEY: str = settings.get("security.jwt.secret_key") or os.getenv("JWT_SECRET_KEY", "change_me")
_ALGORITHM: str = settings.get("security.jwt.algorithm", "HS256")
_EXPIRY_HOURS: int = int(settings.get("security.jwt.expiry_hours", 24))
_BCRYPT_ROUNDS: int = int(settings.get("security.auth.bcrypt_rounds", 12))


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def _build_claims(data: Dict[str, Any], expires_delta: timedelta | None = None) -> Dict[str, Any]:
    claims = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=_EXPIRY_HOURS))
    claims.update({"exp": expire, "iat": datetime.utcnow()})
    return claims


def create_access_token(data: Dict[str, Any], *, expires: timedelta | None = None) -> str:
    return jwt.encode(_build_claims(data, expires), _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM]) 