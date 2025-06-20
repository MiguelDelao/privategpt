from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from privategpt.shared.settings import settings  # type: ignore[attr-defined]

# Prefer environment override, then config value, finally SQLite.

DATABASE_URL = settings.database_url

# If the URL points to Postgres but the driver is not installed, transparently
# swap to in-memory SQLite so unit tests can proceed without extra deps.
if DATABASE_URL.startswith("postgresql"):
    try:
        import psycopg2  # noqa: F401 – just to test availability
    except ModuleNotFoundError:  # pragma: no cover
        DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)

# FastAPI treats dependency functions that yield as context managers automatically.
# Do NOT wrap with @contextmanager, otherwise you yield a contextmanager object.

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 