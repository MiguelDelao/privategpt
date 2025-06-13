from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import uuid


@dataclass(slots=True)
class User:
    """A minimal domain representation of a system user."""

    id: str
    email: str
    role: str = "user"
    authorized_clients: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def new(cls, *, email: str, role: str = "user", authorized_clients: List[str] | None = None) -> "User":
        return cls(
            id=str(uuid.uuid4()),
            email=email,
            role=role,
            authorized_clients=authorized_clients or [],
        ) 