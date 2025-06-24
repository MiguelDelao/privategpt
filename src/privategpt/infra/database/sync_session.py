from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from privategpt.shared.settings import settings  # type: ignore[attr-defined]


# For sync operations (used in Celery tasks), we need a regular PostgreSQL URL
DATABASE_URL: str = settings.database_url

# Ensure we're using the sync driver
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

sync_engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300
)

SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False, class_=Session)


# Context manager for manual session handling
@contextmanager
def get_sync_session_context() -> Generator[Session, None, None]:
    """Yield a sync `Session` inside a with block."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()