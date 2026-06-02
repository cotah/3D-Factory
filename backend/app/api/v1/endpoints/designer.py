"""Designer panel endpoints.

Designers only see tasks assigned to them; admins see all. Responses carry the
technical brief only — never customer personal data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.v1.endpoints.orders import _designer_task_detail
from app.core.database import get_session
from app.core.dependencies import require_roles
from app.models.models import DesignerTask, Order, User, UserRole
from app.schemas.order import DesignerTaskResponse

router = APIRouter()


@router.get("/tasks", response_model=list[DesignerTaskResponse])
async def list_my_tasks(
    current_user: User = Depends(require_roles(UserRole.designer, UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> list[DesignerTaskResponse]:
    statement = select(DesignerTask).order_by(DesignerTask.created_at.desc())
    if current_user.role == UserRole.designer:
        statement = statement.where(DesignerTask.assigned_to == current_user.id)

    rows = await session.execute(statement)
    out: list[DesignerTaskResponse] = []
    for task in rows.scalars().all():
        order = await session.get(Order, task.order_id)
        if order is not None:
            out.append(await _designer_task_detail(task, order, session))
    return out


@router.get("/tasks/{task_id}", response_model=DesignerTaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(require_roles(UserRole.designer, UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> DesignerTaskResponse:
    task = await session.get(DesignerTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    # Designers may only see their own tasks (hide others as 404).
    if current_user.role == UserRole.designer and task.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    order = await session.get(Order, task.order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return await _designer_task_detail(task, order, session)
