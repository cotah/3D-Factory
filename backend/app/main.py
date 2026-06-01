"""FastAPI application entrypoint for the Print3D Platform.

Wires up CORS, the API v1 router, a health check and a lifespan hook that
ensures the database tables exist in development.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """On startup, create tables in development for convenience.

    In production the schema is owned by Alembic migrations, so we only
    auto-create when running in development to avoid surprising prod schemas.
    """
    if settings.is_development:
        await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
    # Hide the interactive docs in production (only enabled when debug is on).
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    openapi_url="/openapi.json" if settings.app_debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Serve locally-stored files (Phase 3 LocalStorageService) at /static.
# Create the directory first so the mount never fails on a fresh checkout.
os.makedirs(settings.local_storage_dir, exist_ok=True)
app.mount(
    "/static",
    StaticFiles(directory=settings.local_storage_dir),
    name="static",
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe used by deploys and the setup checklist."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0"}
