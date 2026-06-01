"""Pydantic schemas for order endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.models import (
    ApprovalStage,
    ApprovalStatus,
    AssetType,
    OrderStatus,
)


class OrderCreate(BaseModel):
    title: str
    description: str = ""
    category: Optional[str] = None
    size: Optional[str] = None
    colors: Optional[str] = None
    material: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    colors: Optional[str] = None
    material: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[OrderStatus] = None


class OrderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    category: Optional[str]
    size: Optional[str]
    colors: Optional[str]
    material: Optional[str]
    deadline: Optional[str]
    notes: Optional[str]
    status: OrderStatus
    ai_attempts: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetResponse(BaseModel):
    id: int
    order_id: int
    type: AssetType
    filename: str
    storage_url: str
    content_type: Optional[str]
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str


class ApprovalResponse(BaseModel):
    id: int
    order_id: int
    stage: ApprovalStage
    status: ApprovalStatus
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    """Order plus its AI brief, assets, approvals and latest mesh report."""

    ai_brief_json: Optional[str] = None
    complexity: Optional[str] = None
    brief: Optional[dict] = None  # ai_brief_json parsed, for convenience
    assets: list[AssetResponse] = []
    approvals: list[ApprovalResponse] = []
    mesh_report: Optional[dict] = None  # from the latest 3D job result


class ApproveConceptRequest(BaseModel):
    approved: bool
    comment: Optional[str] = None


# Same shape; named for clarity at the final-approval step.
class ApproveFinalRequest(BaseModel):
    approved: bool
    comment: Optional[str] = None
