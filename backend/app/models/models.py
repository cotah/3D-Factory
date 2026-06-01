"""SQLModel database models for the Print3D Platform.

All tables for Phase 1 (and forward-looking tables used in later phases) live
here so the schema is defined in one place.

Note: we deliberately do *not* use ``from __future__ import annotations`` here.
SQLModel resolves ``Relationship`` targets from the field annotations at class
definition time, and fully stringized annotations break that resolution on
SQLAlchemy 2.0.x (it raises "seems to be using a generic class as the argument
to relationship()"). Keeping real annotations avoids that.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    """Current UTC time as a naive datetime.

    Columns are mapped to ``TIMESTAMP WITHOUT TIME ZONE``; asyncpg rejects
    timezone-aware values for those, so we store naive UTC consistently.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ------------------------------- Enums -------------------------------
class UserRole(str, Enum):
    customer = "customer"
    admin = "admin"
    designer = "designer"
    print_partner = "print_partner"


class OrderStatus(str, Enum):
    draft = "draft"
    waiting_brief = "waiting_brief"
    generating_concept = "generating_concept"
    waiting_concept_approval = "waiting_concept_approval"
    generating_3d = "generating_3d"
    validating_mesh = "validating_mesh"
    ai_revision_required = "ai_revision_required"
    designer_required = "designer_required"
    waiting_final_approval = "waiting_final_approval"
    ready_for_slicing = "ready_for_slicing"
    slicing = "slicing"
    ready_to_print = "ready_to_print"
    printing = "printing"
    post_processing = "post_processing"
    shipped = "shipped"
    completed = "completed"
    cancelled = "cancelled"


class AssetType(str, Enum):
    reference = "reference"
    concept_image = "concept_image"
    model_3d = "model_3d"
    final_model = "final_model"
    other = "other"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ApprovalStage(str, Enum):
    concept = "concept"
    final = "final"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ------------------------------- Tables ------------------------------
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    hashed_password: str
    full_name: str = Field(default="", max_length=255)
    role: UserRole = Field(default=UserRole.customer)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    orders: list["Order"] = Relationship(back_populates="user")


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    title: str = Field(max_length=255)
    description: str = Field(default="")
    category: Optional[str] = Field(default=None, max_length=100)
    size: Optional[str] = Field(default=None, max_length=100)
    colors: Optional[str] = Field(default=None, max_length=255)
    material: Optional[str] = Field(default=None, max_length=100)
    deadline: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None)

    status: OrderStatus = Field(default=OrderStatus.draft, index=True)
    ai_attempts: int = Field(default=0)

    # Phase 2: AI Production Brief (full JSON) and the parsed complexity tier.
    ai_brief_json: Optional[str] = Field(default=None)
    complexity: Optional[str] = Field(default=None, max_length=50)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    user: Optional[User] = Relationship(back_populates="orders")
    assets: list["ProjectAsset"] = Relationship(back_populates="order")


class ProjectAsset(SQLModel, table=True):
    __tablename__ = "project_assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)

    type: AssetType = Field(default=AssetType.reference)
    filename: str = Field(max_length=512)
    storage_url: str = Field(max_length=1024)
    content_type: Optional[str] = Field(default=None, max_length=255)
    size_bytes: int = Field(default=0)

    created_at: datetime = Field(default_factory=utcnow)

    order: Optional[Order] = Relationship(back_populates="assets")


class AIGenerationJob(SQLModel, table=True):
    __tablename__ = "ai_generation_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)

    job_type: str = Field(max_length=100)  # brief | concept | model_3d
    status: JobStatus = Field(default=JobStatus.pending)
    provider: Optional[str] = Field(default=None, max_length=100)
    external_id: Optional[str] = Field(default=None, max_length=255)
    result: Optional[str] = Field(default=None)  # JSON string
    error: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)


class DesignerTask(SQLModel, table=True):
    __tablename__ = "designer_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)

    status: str = Field(default="open", max_length=50)
    assigned_to: Optional[int] = Field(default=None, foreign_key="users.id")
    notes: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)


class CustomerApproval(SQLModel, table=True):
    __tablename__ = "customer_approvals"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)

    stage: ApprovalStage = Field(default=ApprovalStage.concept)
    status: ApprovalStatus = Field(default=ApprovalStatus.pending)
    comment: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)


class PrintJob(SQLModel, table=True):
    __tablename__ = "print_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)

    status: str = Field(default="queued", max_length=50)
    config: Optional[str] = Field(default=None)  # JSON string

    created_at: datetime = Field(default_factory=utcnow)
