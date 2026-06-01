"""Asset upload/listing endpoints, nested under an order.

Phase 1 stores files locally via ``StorageService``. Validation checks both the
file extension (against ``settings.allowed_extensions``) and the byte size
(against ``settings.upload_max_bytes``).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.models import AssetType, Order, ProjectAsset, User, UserRole
from app.schemas.order import AssetResponse
from app.services.storage.storage_service import get_storage_service

router = APIRouter()

_STAFF_ROLES = {UserRole.admin, UserRole.designer, UserRole.print_partner}


async def _get_accessible_order(
    order_id: int, user: User, session: AsyncSession
) -> Order:
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if user.role not in _STAFF_ROLES and order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def _extension_of(filename: str) -> str:
    return os.path.splitext(filename)[1].lower().lstrip(".")


@router.post(
    "/{order_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    order_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProjectAsset:
    order = await _get_accessible_order(order_id, current_user, session)

    filename = file.filename or "upload"
    extension = _extension_of(filename)
    if extension not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File type '.{extension}' is not allowed. "
                f"Allowed: {', '.join(sorted(settings.allowed_extensions))}"
            ),
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(data) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.upload_max_file_size_mb}MB limit",
        )

    storage = get_storage_service()
    storage_url = await storage.save(order_id=order.id, filename=filename, data=data)

    asset = ProjectAsset(
        order_id=order.id,
        type=AssetType.reference,
        filename=filename,
        storage_url=storage_url,
        content_type=file.content_type,
        size_bytes=len(data),
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


@router.get("/{order_id}/assets", response_model=list[AssetResponse])
async def list_assets(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectAsset]:
    order = await _get_accessible_order(order_id, current_user, session)
    result = await session.execute(
        select(ProjectAsset)
        .where(ProjectAsset.order_id == order.id)
        .order_by(ProjectAsset.created_at.desc())
    )
    return list(result.scalars().all())
