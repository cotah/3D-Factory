"""Integration tests for the Phase 3 3D generation + final approval flow.

Uses a locally-generated cube.glb served via a ``file://`` URL so the pipeline
(download -> store -> mesh validate) runs without any network access.
"""

from __future__ import annotations

import pytest
import trimesh
from httpx import AsyncClient

from app.services.ai.openai_image_service import OpenAIImageService
from app.services.ai.runpod_trellis_service import (
    GenerateModelInput,
    GenerateModelOutput,
    ThreeDGenerationProvider,
)


@pytest.fixture(scope="session")
def cube_glb_url(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("models") / "cube.glb"
    trimesh.creation.box(extents=(10, 10, 10)).export(str(path))
    return "file:///" + str(path).replace("\\", "/")


class FakeProvider(ThreeDGenerationProvider):
    def __init__(self, url: str, fail_on: set[int] | None = None) -> None:
        self.url = url
        self.fail_on = fail_on or set()

    async def generate_model(self, data: GenerateModelInput) -> GenerateModelOutput:
        if data.attempt_number in self.fail_on:
            return GenerateModelOutput(
                success=False,
                error_message=f"simulated failure on attempt {data.attempt_number}",
                job_id=f"job-{data.attempt_number}",
            )
        return GenerateModelOutput(
            success=True,
            file_url=self.url,
            file_format="glb",
            job_id=f"job-{data.attempt_number}",
        )


@pytest.fixture(autouse=True)
def fast_images(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.orders.OpenAIImageService",
        lambda *a, **k: OpenAIImageService(mock_latency_seconds=0),
    )


def _use_provider(monkeypatch, provider: ThreeDGenerationProvider) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.orders.get_3d_provider", lambda: provider
    )


async def _drive_to_generating_3d(client: AsyncClient, headers: dict) -> int:
    r = await client.post("/api/v1/orders", headers=headers, json={"title": "Part"})
    oid = r.json()["id"]
    await client.post(f"/api/v1/orders/{oid}/generate-brief", headers=headers)
    await client.post(
        f"/api/v1/orders/{oid}/approve-concept",
        headers=headers,
        json={"approved": True},
    )
    return oid


async def test_generate_3d_success(
    client: AsyncClient, auth_headers: dict, cube_glb_url: str, monkeypatch
):
    _use_provider(monkeypatch, FakeProvider(cube_glb_url))
    oid = await _drive_to_generating_3d(client, auth_headers)

    resp = await client.post(
        f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "waiting_final_approval"
    assert body["ai_attempts"] == 1
    assert any(a["type"] == "model_3d" for a in body["assets"])
    assert body["mesh_report"] is not None
    assert body["mesh_report"]["face_count"] > 0
    assert body["mesh_report"]["is_valid"] is True


async def test_generate_3d_creates_job_and_asset(
    client: AsyncClient, auth_headers: dict, cube_glb_url: str, monkeypatch, session
):
    from sqlmodel import select

    from app.models.models import AIGenerationJob

    _use_provider(monkeypatch, FakeProvider(cube_glb_url))
    oid = await _drive_to_generating_3d(client, auth_headers)
    await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)

    rows = await session.execute(
        select(AIGenerationJob).where(AIGenerationJob.order_id == oid)
    )
    jobs = list(rows.scalars().all())
    assert len(jobs) == 1
    assert jobs[0].job_type == "model_3d"
    assert jobs[0].status.value == "succeeded"


async def test_three_failures_fall_back_to_designer(
    client: AsyncClient, auth_headers: dict, cube_glb_url: str, monkeypatch
):
    # Fail every attempt -> after 3 attempts the order needs a human designer.
    _use_provider(monkeypatch, FakeProvider(cube_glb_url, fail_on={1, 2, 3}))
    oid = await _drive_to_generating_3d(client, auth_headers)

    r1 = await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)
    assert r1.json()["status"] == "ai_revision_required"
    assert r1.json()["ai_attempts"] == 1

    r2 = await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)
    assert r2.json()["status"] == "ai_revision_required"
    assert r2.json()["ai_attempts"] == 2

    r3 = await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)
    assert r3.json()["status"] == "designer_required"
    assert r3.json()["ai_attempts"] == 3


async def test_attempt_2_fails_then_3_succeeds(
    client: AsyncClient, auth_headers: dict, cube_glb_url: str, monkeypatch
):
    _use_provider(monkeypatch, FakeProvider(cube_glb_url, fail_on={2}))
    oid = await _drive_to_generating_3d(client, auth_headers)

    # Attempt 1 succeeds.
    r1 = await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)
    assert r1.json()["status"] == "waiting_final_approval"

    # Customer rejects -> back to generating_3d for attempt 2.
    rej = await client.post(
        f"/api/v1/orders/{oid}/approve-final",
        headers=auth_headers,
        json={"approved": False},
    )
    assert rej.json()["status"] == "generating_3d"

    # Attempt 2 fails -> ai_revision_required.
    r2 = await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)
    assert r2.json()["status"] == "ai_revision_required"

    # Attempt 3 (retry from ai_revision_required) succeeds.
    r3 = await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)
    assert r3.json()["status"] == "waiting_final_approval"
    assert r3.json()["ai_attempts"] == 3


async def test_approve_final_ready_for_slicing(
    client: AsyncClient, auth_headers: dict, cube_glb_url: str, monkeypatch
):
    _use_provider(monkeypatch, FakeProvider(cube_glb_url))
    oid = await _drive_to_generating_3d(client, auth_headers)
    await client.post(f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/orders/{oid}/approve-final",
        headers=auth_headers,
        json={"approved": True, "comment": "Looks great"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready_for_slicing"
    assert any(
        a["stage"] == "final" and a["status"] == "approved" for a in body["approvals"]
    )


async def test_generate_3d_requires_generating_status(
    client: AsyncClient, auth_headers: dict
):
    r = await client.post("/api/v1/orders", headers=auth_headers, json={"title": "X"})
    oid = r.json()["id"]
    resp = await client.post(
        f"/api/v1/orders/{oid}/generate-3d", headers=auth_headers
    )
    assert resp.status_code == 409
