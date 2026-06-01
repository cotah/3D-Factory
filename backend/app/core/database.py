"""Async database engine and session management (SQLModel + SQLAlchemy async).

Works with PostgreSQL (asyncpg) in dev/prod and SQLite (aiosqlite) in tests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings

# SQLite needs a special connect arg; Postgres does not.
_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args=_connect_args,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """Create all tables from SQLModel metadata.

    Used for local dev convenience and tests. In production the schema is
    managed by Alembic migrations.
    """
    # Importing models registers them on SQLModel.metadata.
    import app.models.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
