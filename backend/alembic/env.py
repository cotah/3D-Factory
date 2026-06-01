"""Alembic migration environment.

Runs migrations with a synchronous psycopg engine (derived from the app's
async DATABASE_URL) and targets the SQLModel metadata so ``--autogenerate``
sees every table.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.core.config import settings

# Importing the models registers them on SQLModel.metadata.
import app.models.models  # noqa: F401,E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def _sync_database_url() -> str:
    """Convert the async DATABASE_URL into a sync driver Alembic can use."""
    url = settings.database_url
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg")
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("+aiosqlite", "")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
