"""Integration tests for the Phase 4 designer-fallback flow."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.models import User, UserRole
from app.services.ai.openai_image_service import OpenAIImageService
from app.services.ai.runpod_trellis_service import (
    GenerateModelInput,
    GenerateModelOutput,
    ThreeDGenerationProvider,
)


class _AlwaysFailProvider(ThreeDGenerationProvider):
    async def generate_model(self, data: GenerateModelInput) -> GenerateModelOutput:
        return GenerateModelOutput(success=False, error_message="fail", job_id="j")


@pytest.fixture(autouse=True)
def fast_and_failing(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.orders.OpenAIImageService",
        lambda *a, **k: OpenAIImageService(mock_latency_seconds=0),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.orders.get_3d_provider", lambda: _AlwaysFailProvider()
    )


async def _make_user(
    client: AsyncClient, session: AsyncSession, email: str, role: UserRole
) -> dict:
    session.add(
        User(
            email=email,
            hashed_password=hash_password("secret123"),
            full_name="Staff Member",
            role=role,
        )
    )
    await session.commit()
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secret123"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _drive_to_designer_required(client: AsyncClient, headers: dict) -> int:
    r = await client.post("/api/v1/orders", headers=headers, json={"title": "Hard part"})
    oid = r.json()["id"]
    await client.post(f"/api/v1/orders/{oid}/generate-brief", headers=headers)
    await client.post(
        f"/api/v1/orders/{oid}/approve-concept", headers=headers, json={"approved": True}
    )
    for _ in range(3):  # 3 failed attempts -> designer_required
        await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=headers)
    return oid


async def test_full_designer_flow(
    client: AsyncClient, auth_headers: dict, session: AsyncSession
):
    admin = await _make_user(client, session, "admin@staff.com", UserRole.admin)
    designer = await _make_user(client, session, "designer@staff.com", UserRole.designer)

    oid = await _drive_to_designer_required(client, auth_headers)

    # The order reached the human-designer fallback.
    detail = await client.get(f"/api/v1/orders/{oid}", headers=auth_headers)
    assert detail.json()["status"] == "designer_required"
    assert detail.json()["ai_attempts"] == 3

    # Admin requests a designer; a task with a personal-data-free brief is made.
    req = await client.post(f"/api/v1/orders/{oid}/request-designer", headers=admin)
    assert req.status_code == 200, req.text
    task = req.json()
    assert task["brief"]["order_reference"].startswith("ORD-")
    assert "instructions" in task["brief"]
    # Privacy: the customer's email must never appear in the designer brief.
    import json as _json

    assert "customer@example.com" not in _json.dumps(task)

    # Idempotent: requesting again returns the same task, not a duplicate.
    req2 = await client.post(f"/api/v1/orders/{oid}/request-designer", headers=admin)
    assert req2.json()["id"] == task["id"]

    # Admin assigns the designer.
    designer_user = await client.get("/api/v1/auth/me", headers=designer)
    assign = await client.patch(
        f"/api/v1/orders/{oid}/designer-task",
        headers=admin,
        json={"designer_id": designer_user.json()["id"], "instructions": "Keep it simple"},
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["status"] == "in_progress"
    assert assign.json()["assigned_to"] == designer_user.json()["id"]

    # Designer sees the task in their list and can read it.
    my_tasks = await client.get("/api/v1/designer/tasks", headers=designer)
    assert len(my_tasks.json()) == 1
    one = await client.get(
        f"/api/v1/designer/tasks/{task['id']}", headers=designer
    )
    assert one.status_code == 200
    assert len(one.json()["concept_images"]) == 6  # approved concepts visible

    # Designer uploads the final model.
    files = {"file": ("final.glb", io.BytesIO(b"fake glb bytes"), "model/gltf-binary")}
    up = await client.post(
        f"/api/v1/orders/{oid}/upload-final-model", headers=designer, files=files
    )
    assert up.status_code == 200, up.text
    assert up.json()["status"] == "waiting_final_approval"
    assert any(a["type"] == "final_model" for a in up.json()["assets"])

    # Customer approves the final model.
    final = await client.post(
        f"/api/v1/orders/{oid}/approve-final",
        headers=auth_headers,
        json={"approved": True},
    )
    assert final.json()["status"] == "ready_for_slicing"


async def test_request_designer_requires_admin(
    client: AsyncClient, auth_headers: dict, session: AsyncSession
):
    oid = await _drive_to_designer_required(client, auth_headers)
    # A customer cannot request a designer.
    resp = await client.post(f"/api/v1/orders/{oid}/request-designer", headers=auth_headers)
    assert resp.status_code == 403


async def test_upload_final_model_rejects_bad_extension(
    client: AsyncClient, session: AsyncSession
):
    admin = await _make_user(client, session, "admin2@staff.com", UserRole.admin)
    # Admin creates an order to upload against.
    r = await client.post("/api/v1/orders", headers=admin, json={"title": "X"})
    oid = r.json()["id"]
    files = {"file": ("bad.txt", io.BytesIO(b"nope"), "text/plain")}
    resp = await client.post(
        f"/api/v1/orders/{oid}/upload-final-model", headers=admin, files=files
    )
    assert resp.status_code == 400


async def test_designer_only_sees_own_tasks(
    client: AsyncClient, auth_headers: dict, session: AsyncSession
):
    admin = await _make_user(client, session, "admin3@staff.com", UserRole.admin)
    designer_a = await _make_user(client, session, "da@staff.com", UserRole.designer)
    designer_b = await _make_user(client, session, "db@staff.com", UserRole.designer)

    oid = await _drive_to_designer_required(client, auth_headers)
    req = await client.post(f"/api/v1/orders/{oid}/request-designer", headers=admin)
    task_id = req.json()["id"]
    me_a = await client.get("/api/v1/auth/me", headers=designer_a)
    await client.patch(
        f"/api/v1/orders/{oid}/designer-task",
        headers=admin,
        json={"designer_id": me_a.json()["id"]},
    )
    # Designer B (not assigned) cannot see designer A's task.
    resp = await client.get(f"/api/v1/designer/tasks/{task_id}", headers=designer_b)
    assert resp.status_code == 404
    assert len((await client.get("/api/v1/designer/tasks", headers=designer_b)).json()) == 0
