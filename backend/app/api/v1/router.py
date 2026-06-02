"""Aggregate router for API v1 — mounts every endpoint module."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import assets, auth, designer, orders

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
# Asset routes are nested under a specific order id.
api_router.include_router(assets.router, prefix="/orders", tags=["assets"])
api_router.include_router(designer.router, prefix="/designer", tags=["designer"])
