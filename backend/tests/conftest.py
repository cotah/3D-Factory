"""Shared test fixtures.

Integration tests run against an in-memory SQLite database (aiosqlite) with a
StaticPool so every session shares the same connection. The app's ``get_session``
dependency is overridden to use this test engine.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

# Import models so they are registered on SQLModel.metadata before create_all.
import app.models.models  # noqa: F401
from app.core.database import get_session
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def engine():
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as s:
            yield s

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a customer and return Authorization headers for them."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer@example.com",
            "password": "secret123",
            "full_name": "Test Customer",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
