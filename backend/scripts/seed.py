"""Seed the database with an admin, a demo customer and sample orders.

Idempotent: running it again will not create duplicates. Admin credentials come
from settings (ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME).

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

# The status lines use emoji; force UTF-8 so the Windows console (cp1252)
# doesn't raise UnicodeEncodeError. Linux/Railway is already UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass

from sqlmodel import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import async_session_maker, init_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.models import Order, User, UserRole  # noqa: E402

DEMO_CUSTOMER_EMAIL = "cliente@test.com"
DEMO_CUSTOMER_PASSWORD = "cliente123"

SAMPLE_ORDERS = [
    {
        "title": "Troféu de campeonato",
        "description": "Troféu personalizado para torneio de e-sports.",
        "category": "trophy",
        "material": "PLA",
    },
    {
        "title": "Suporte de headset",
        "description": "Suporte de mesa para fone gamer, com base estável.",
        "category": "functional",
        "material": "PETG",
    },
]


async def _get_or_create_user(
    session, email: str, password: str, name: str, role: UserRole
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing, False
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=name,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, True


async def seed() -> None:
    # Ensure tables exist (handy when running before the first migration).
    await init_db()

    async with async_session_maker() as session:
        admin, admin_created = await _get_or_create_user(
            session,
            settings.admin_email,
            settings.admin_password,
            settings.admin_name,
            UserRole.admin,
        )
        print(
            f"{'✅ Usuário criado' if admin_created else 'ℹ️  Já existe'}: "
            f"{admin.email} (admin)"
        )

        customer, customer_created = await _get_or_create_user(
            session,
            DEMO_CUSTOMER_EMAIL,
            DEMO_CUSTOMER_PASSWORD,
            "Cliente Demo",
            UserRole.customer,
        )
        print(
            f"{'✅ Usuário criado' if customer_created else 'ℹ️  Já existe'}: "
            f"{customer.email} (customer)"
        )

        # Sample orders only if the demo customer has none yet.
        existing_orders = await session.execute(
            select(Order).where(Order.user_id == customer.id)
        )
        if existing_orders.scalars().first() is None:
            for data in SAMPLE_ORDERS:
                session.add(Order(user_id=customer.id, **data))
            await session.commit()
            print(f"✅ {len(SAMPLE_ORDERS)} pedidos de exemplo criados")
        else:
            print("ℹ️  Pedidos de exemplo já existem")

    print("✅ Seed concluído!")


if __name__ == "__main__":
    asyncio.run(seed())
