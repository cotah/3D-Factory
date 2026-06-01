"""Seed the database with an initial admin user.

Idempotent: running it twice will not create duplicate admins. Reads the admin
credentials from settings (ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME).

Usage:
    uv run python scripts/seed.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as a plain script (``uv run python scripts/seed.py``) by putting
# the backend root (which contains the ``app`` package) on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select  # noqa: E402

from app.core.config import settings
from app.core.database import async_session_maker, init_db
from app.core.security import hash_password
from app.models.models import User, UserRole


async def seed() -> None:
    # Ensure tables exist (handy when running before the first migration).
    await init_db()

    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == settings.admin_email)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(f"Admin user already exists: {settings.admin_email}")
            return

        admin = User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            full_name=settings.admin_name,
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()
        print(f"Created admin user: {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(seed())
