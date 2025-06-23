from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from privategpt.shared.settings import settings  # type: ignore[attr-defined]


# Ensure the async driver is used for PostgreSQL URLs. SQLAlchemy needs an
# async-compatible driver such as *asyncpg* (or psycopg v3) when used via
# `create_async_engine`. If the configured DATABASE_URL uses the common
# blocking driver prefix `postgresql://`, transparently swap it for
# `postgresql+asyncpg://` so we don't require callers to specify it.

DATABASE_URL: str = settings.database_url

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True,
    pool_recycle=300
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Context manager for manual session handling
@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Yield an `AsyncSession` inside an *async with* block."""
    async with AsyncSessionLocal() as session:
        yield session

# FastAPI dependency function
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session 