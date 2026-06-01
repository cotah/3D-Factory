"""Order endpoints: CRUD plus the Phase 1 lifecycle actions.

Access rules:
- customers only see and mutate their own orders;
- admins and designers can see every order.
"""

from __future__ import annotations

import json
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.models import (
    AIGenerationJob,
    ApprovalStage,
    ApprovalStatus,
    AssetType,
    CustomerApproval,
    DesignerTask,
    JobStatus,
    Order,
    OrderStatus,
    ProjectAsset,
    User,
    UserRole,
    utcnow,
)
from app.schemas.order import (
    ApprovalResponse,
    ApproveConceptRequest,
    ApproveFinalRequest,
    AssetResponse,
    MessageResponse,
    OrderCreate,
    OrderDetailResponse,
    OrderResponse,
    OrderUpdate,
)
from app.services.ai.claude_service import ClaudeService
from app.services.ai.openai_image_service import OpenAIImageService
from app.services.ai.runpod_trellis_service import (
    GenerateModelInput,
    get_3d_provider,
)
from app.services.mesh import mesh_validator
from app.services.storage.storage_service import StorageService, get_storage_service

router = APIRouter()


async def _latest_mesh_report(order_id: int, session: AsyncSession) -> dict | None:
    """Return the mesh report from the most recent succeeded 3D job, if any."""
    result = await session.execute(
        select(AIGenerationJob)
        .where(AIGenerationJob.order_id == order_id)
        .where(AIGenerationJob.job_type == "model_3d")
        .order_by(AIGenerationJob.created_at.desc())
    )
    for job in result.scalars().all():
        if not job.result:
            continue
        try:
            payload = json.loads(job.result)
        except json.JSONDecodeError:
            continue
        if payload.get("mesh_report"):
            return payload["mesh_report"]
    return None


async def _build_order_detail(
    order: Order, session: AsyncSession
) -> OrderDetailResponse:
    """Assemble the rich order response: brief + assets + approvals."""
    assets_result = await session.execute(
        select(ProjectAsset)
        .where(ProjectAsset.order_id == order.id)
        .order_by(ProjectAsset.created_at.asc())
    )
    assets = list(assets_result.scalars().all())

    approvals_result = await session.execute(
        select(CustomerApproval)
        .where(CustomerApproval.order_id == order.id)
        .order_by(CustomerApproval.created_at.asc())
    )
    approvals = list(approvals_result.scalars().all())

    brief = None
    if order.ai_brief_json:
        try:
            brief = json.loads(order.ai_brief_json)
        except json.JSONDecodeError:
            logger.warning("order id={} has invalid ai_brief_json", order.id)

    # Build explicitly from scalar fields. We avoid ``model_validate(order)``
    # because reading the ORM ``assets`` relationship would trigger a lazy load
    # in async context (MissingGreenlet).
    return OrderDetailResponse(
        id=order.id,
        user_id=order.user_id,
        title=order.title,
        description=order.description,
        category=order.category,
        size=order.size,
        colors=order.colors,
        material=order.material,
        deadline=order.deadline,
        notes=order.notes,
        status=order.status,
        ai_attempts=order.ai_attempts,
        created_at=order.created_at,
        updated_at=order.updated_at,
        ai_brief_json=order.ai_brief_json,
        complexity=order.complexity,
        brief=brief,
        mesh_report=await _latest_mesh_report(order.id, session),
        assets=[AssetResponse.model_validate(a, from_attributes=True) for a in assets],
        approvals=[
            ApprovalResponse.model_validate(a, from_attributes=True) for a in approvals
        ],
    )

# Roles allowed to see and act on orders that are not their own.
_STAFF_ROLES = {UserRole.admin, UserRole.designer, UserRole.print_partner}


def _is_staff(user: User) -> bool:
    return user.role in _STAFF_ROLES


async def _get_owned_order(
    order_id: int,
    user: User,
    session: AsyncSession,
) -> Order:
    """Load an order or raise 404. Customers may only access their own."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if not _is_staff(user) and order.user_id != user.id:
        # Hide existence from non-owners by returning 404 rather than 403.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Order:
    order = Order(user_id=current_user.id, **payload.model_dump())
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Order]:
    statement = select(Order).order_by(Order.created_at.desc())
    if not _is_staff(current_user):
        statement = statement.where(Order.user_id == current_user.id)
    result = await session.execute(statement)
    return list(result.scalars().all())


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderDetailResponse:
    order = await _get_owned_order(order_id, current_user, session)
    return await _build_order_detail(order, session)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Order:
    order = await _get_owned_order(order_id, current_user, session)

    updates = payload.model_dump(exclude_unset=True)
    # Only staff may change status directly; customers update content fields.
    if "status" in updates and not _is_staff(current_user):
        updates.pop("status")

    for key, value in updates.items():
        setattr(order, key, value)
    order.updated_at = utcnow()

    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


@router.delete("/{order_id}", response_model=MessageResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Soft delete: mark the order as cancelled rather than removing it."""
    order = await _get_owned_order(order_id, current_user, session)
    order.status = OrderStatus.cancelled
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    return MessageResponse(message="Order cancelled")


# ----------------------------- Lifecycle actions -----------------------------
_MAX_AI_ATTEMPTS = 3


async def _ensure_designer_task(order: Order, session: AsyncSession) -> None:
    """Create a DesignerTask once an order falls back to a human designer."""
    existing = await session.execute(
        select(DesignerTask)
        .where(DesignerTask.order_id == order.id)
        .where(DesignerTask.status == "open")
    )
    if existing.scalars().first() is None:
        session.add(
            DesignerTask(
                order_id=order.id,
                status="open",
                notes="Auto-created after repeated AI failures.",
            )
        )
        await session.commit()


def _write_temp(content: bytes, fmt: str) -> str:
    fd, path = tempfile.mkstemp(suffix=f".{fmt}")
    with os.fdopen(fd, "wb") as fh:
        fh.write(content)
    return path


async def _run_mesh_validation(
    order: Order, content: bytes, fmt: str, attempt: int, session: AsyncSession
) -> dict:
    """Validate the downloaded model, attempt repair if needed, set the status."""
    path = _write_temp(content, fmt)
    try:
        report = mesh_validator.validate(path)
        report_dict = report.to_dict()

        if report.is_valid:
            order.status = OrderStatus.waiting_final_approval
        elif attempt < _MAX_AI_ATTEMPTS:
            report_dict["repair_attempted"] = True
            try:
                repaired, repaired_path = mesh_validator.attempt_repair(path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Mesh repair errored: {}", type(exc).__name__)
                repaired, repaired_path = False, None
            report_dict["repair_succeeded"] = repaired
            if repaired and repaired_path:
                with open(repaired_path, "rb") as fh:
                    repaired_bytes = fh.read()
                storage = get_storage_service()
                key = f"models/{order.id}/repaired_attempt{attempt}.glb"
                url = await storage.save_file(repaired_bytes, key, "model/gltf-binary")
                session.add(
                    ProjectAsset(
                        order_id=order.id,
                        type=AssetType.model_3d,
                        filename=f"model_repaired_attempt{attempt}.glb",
                        storage_url=url,
                        content_type="model/gltf-binary",
                        size_bytes=len(repaired_bytes),
                    )
                )
                order.status = OrderStatus.waiting_final_approval
                try:
                    os.remove(repaired_path)
                except OSError:
                    pass
            else:
                order.status = OrderStatus.ai_revision_required
        else:
            order.status = OrderStatus.designer_required
        return report_dict
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@router.post("/{order_id}/generate-3d", response_model=OrderDetailResponse)
async def generate_3d(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderDetailResponse:
    """Generate the 3D model via the provider, validate the mesh and route status.

    Enforces a 3-attempt budget before falling back to a human designer.
    """
    order = await _get_owned_order(order_id, current_user, session)

    # Allow a fresh start (generating_3d) or a retry after a failed attempt.
    if order.status not in (OrderStatus.generating_3d, OrderStatus.ai_revision_required):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is not ready for 3D generation.",
        )

    if order.ai_attempts >= _MAX_AI_ATTEMPTS:
        order.status = OrderStatus.designer_required
        order.updated_at = utcnow()
        session.add(order)
        await session.commit()
        await session.refresh(order)
        await _ensure_designer_task(order, session)
        return await _build_order_detail(order, session)

    order.ai_attempts += 1
    attempt = order.ai_attempts
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)

    job = AIGenerationJob(
        order_id=order.id,
        job_type="model_3d",
        status=JobStatus.running,
        provider="runpod_trellis",
        result=json.dumps({"attempt": attempt}),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Approved concept images steer the generation.
    img_rows = await session.execute(
        select(ProjectAsset)
        .where(ProjectAsset.order_id == order.id)
        .where(ProjectAsset.type == AssetType.concept_image)
    )
    image_urls = [a.storage_url for a in img_rows.scalars().all()]

    model_prompt = order.title
    if order.ai_brief_json:
        try:
            model_prompt = json.loads(order.ai_brief_json).get(
                "model_3d_prompt", order.title
            )
        except json.JSONDecodeError:
            pass

    provider = get_3d_provider()
    try:
        out = await provider.generate_model(
            GenerateModelInput(
                order_id=order.id,
                image_urls=image_urls,
                model_prompt=model_prompt,
                attempt_number=attempt,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("3D provider crashed for order id={}: {}", order.id, type(exc).__name__)
        job.status = JobStatus.failed
        job.error = "provider error"
        session.add(job)
        await session.commit()
        raise _AI_UNAVAILABLE

    # ---- Failure: route to retry or designer ----
    if not out.success:
        job.status = JobStatus.failed
        job.error = out.error_message
        job.external_id = out.job_id
        session.add(job)
        order.status = (
            OrderStatus.designer_required
            if attempt >= _MAX_AI_ATTEMPTS
            else OrderStatus.ai_revision_required
        )
        order.updated_at = utcnow()
        session.add(order)
        await session.commit()
        await session.refresh(order)
        if order.status == OrderStatus.designer_required:
            await _ensure_designer_task(order, session)
        logger.info(
            "3D generation failed order id={} attempt={} -> {}",
            order.id,
            attempt,
            order.status.value,
        )
        return await _build_order_detail(order, session)

    # ---- Success: store model, validate mesh ----
    storage = get_storage_service()
    content = await StorageService._fetch(out.file_url)
    fmt = out.file_format or "glb"
    key = f"models/{order.id}/{job.id}_attempt{attempt}.{fmt}"
    storage_url = await storage.save_file(content, key, "model/gltf-binary")
    session.add(
        ProjectAsset(
            order_id=order.id,
            type=AssetType.model_3d,
            filename=f"model_attempt{attempt}.{fmt}",
            storage_url=storage_url,
            content_type="model/gltf-binary",
            size_bytes=len(content),
        )
    )

    order.status = OrderStatus.validating_mesh
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()

    report_dict = await _run_mesh_validation(order, content, fmt, attempt, session)

    job.status = JobStatus.succeeded
    job.external_id = out.job_id
    job.result = json.dumps(
        {
            "attempt": attempt,
            "file_url": storage_url,
            "job_id": out.job_id,
            "mesh_report": report_dict,
        }
    )
    session.add(job)
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)

    if order.status == OrderStatus.designer_required:
        await _ensure_designer_task(order, session)

    logger.info(
        "3D generation done order id={} attempt={} -> {}",
        order.id,
        attempt,
        order.status.value,
    )
    return await _build_order_detail(order, session)


@router.post("/{order_id}/validate-mesh", response_model=OrderResponse)
async def validate_mesh(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Order:
    """Simulate mesh validation and move the order to validating_mesh."""
    order = await _get_owned_order(order_id, current_user, session)
    order.status = OrderStatus.validating_mesh
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


@router.post("/{order_id}/upload-final-model", response_model=OrderResponse)
async def upload_final_model(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Order:
    """Admin/designer marks the final model as uploaded (real upload in Phase 2)."""
    if not _is_staff(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can upload the final model",
        )
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = OrderStatus.waiting_final_approval
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


@router.post("/{order_id}/approve-final", response_model=OrderDetailResponse)
async def approve_final(
    order_id: int,
    payload: ApproveFinalRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderDetailResponse:
    """Customer approves or rejects the final 3D model.

    Approve -> ``ready_for_slicing``. Reject -> a new ``generating_3d`` attempt,
    or ``designer_required`` once the AI budget is exhausted.
    """
    order = await _get_owned_order(order_id, current_user, session)

    if order.status != OrderStatus.waiting_final_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is not awaiting final approval.",
        )

    approval = CustomerApproval(
        order_id=order.id,
        stage=ApprovalStage.final,
        status=ApprovalStatus.approved if payload.approved else ApprovalStatus.rejected,
        comment=payload.comment,
    )
    session.add(approval)

    if payload.approved:
        order.status = OrderStatus.ready_for_slicing
    elif order.ai_attempts >= _MAX_AI_ATTEMPTS:
        order.status = OrderStatus.designer_required
    else:
        order.status = OrderStatus.generating_3d

    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)

    if order.status == OrderStatus.designer_required:
        await _ensure_designer_task(order, session)
    return await _build_order_detail(order, session)


# --------------------------- Phase 2: AI brief + concept ---------------------------
_AI_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="AI service is temporarily unavailable. Please try again.",
)


async def _run_concept_generation(order: Order, image_prompt: str, session: AsyncSession) -> None:
    """Generate the concept images and move the order to concept approval."""
    image_service = OpenAIImageService()
    try:
        await image_service.generate_concept_images(order, image_prompt, session)
    except Exception as exc:  # noqa: BLE001
        logger.error("Concept generation failed for order id={}: {}", order.id, type(exc).__name__)
        raise _AI_UNAVAILABLE

    order.status = OrderStatus.waiting_concept_approval
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)


@router.post("/{order_id}/generate-brief", response_model=OrderDetailResponse)
async def generate_brief(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderDetailResponse:
    """Generate the AI Production Brief, then the concept images inline."""
    order = await _get_owned_order(order_id, current_user, session)
    logger.info("generate-brief requested for order id={}", order.id)

    order.status = OrderStatus.waiting_brief
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()

    claude = ClaudeService()
    try:
        brief = claude.generate_production_brief(order)
    except Exception as exc:  # noqa: BLE001
        logger.error("Brief generation failed for order id={}: {}", order.id, type(exc).__name__)
        raise _AI_UNAVAILABLE

    order.ai_brief_json = brief.raw_json
    order.complexity = brief.complexity
    order.status = OrderStatus.generating_concept
    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)

    # Generate the concept images right away so the customer sees them in one step.
    await _run_concept_generation(order, brief.image_prompt, session)
    return await _build_order_detail(order, session)


@router.post("/{order_id}/generate-concept", response_model=OrderDetailResponse)
async def generate_concept(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderDetailResponse:
    """(Re)generate the 6 concept images from the stored brief."""
    order = await _get_owned_order(order_id, current_user, session)

    if not order.ai_brief_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order has no brief yet. Generate the brief first.",
        )
    if order.status not in (
        OrderStatus.generating_concept,
        OrderStatus.waiting_concept_approval,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate concept while status is '{order.status.value}'.",
        )

    try:
        brief = json.loads(order.ai_brief_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored brief is corrupted.",
        )
    image_prompt = brief.get("image_prompt", order.title)

    order.status = OrderStatus.generating_concept
    session.add(order)
    await session.commit()

    await _run_concept_generation(order, image_prompt, session)
    return await _build_order_detail(order, session)


@router.post("/{order_id}/approve-concept", response_model=OrderDetailResponse)
async def approve_concept(
    order_id: int,
    payload: ApproveConceptRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderDetailResponse:
    """Customer approves or rejects the concept images.

    Approve  -> status ``generating_3d`` (Phase 3 takes over).
    Reject   -> status ``generating_concept`` (a new concept can be generated).
    """
    order = await _get_owned_order(order_id, current_user, session)

    if order.status != OrderStatus.waiting_concept_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is not awaiting concept approval.",
        )

    approval = CustomerApproval(
        order_id=order.id,
        stage=ApprovalStage.concept,
        status=ApprovalStatus.approved if payload.approved else ApprovalStatus.rejected,
        comment=payload.comment,
    )
    session.add(approval)

    if payload.approved:
        order.status = OrderStatus.generating_3d
        logger.info("Concept approved for order id={}", order.id)
    else:
        order.status = OrderStatus.generating_concept
        order.ai_attempts += 1
        logger.info("Concept rejected for order id={} (attempt {})", order.id, order.ai_attempts)

    order.updated_at = utcnow()
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return await _build_order_detail(order, session)
