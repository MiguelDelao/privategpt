from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from privategpt.shared.settings import settings  # type: ignore[attr-defined]


DATABASE_URL = settings.database_url

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

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