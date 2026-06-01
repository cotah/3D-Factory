"""Integration tests for the Phase 2 brief + concept + approval flow."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.ai.openai_image_service import OpenAIImageService


@pytest.fixture(autouse=True)
def fast_images(monkeypatch):
    """Remove the mock 2s latency so the flow tests run fast."""
    monkeypatch.setattr(
        "app.api.v1.endpoints.orders.OpenAIImageService",
        lambda *a, **k: OpenAIImageService(mock_latency_seconds=0),
    )


async def _create_order(client: AsyncClient, headers: dict, **fields) -> int:
    payload = {"title": "Test part", **fields}
    resp = await client.post("/api/v1/orders", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_generate_brief_creates_brief_and_concepts(
    client: AsyncClient, auth_headers: dict
):
    oid = await _create_order(client, auth_headers, title="Trophy", category="trophy")

    resp = await client.post(
        f"/api/v1/orders/{oid}/generate-brief", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "waiting_concept_approval"
    assert body["ai_brief_json"]
    assert body["complexity"] in ("simple", "medium", "complex")
    assert body["brief"]["complexity"] == body["complexity"]
    assert len(body["assets"]) == 6
    assert all(a["type"] == "concept_image" for a in body["assets"])


async def test_approve_concept_moves_to_generating_3d(
    client: AsyncClient, auth_headers: dict
):
    oid = await _create_order(client, auth_headers, title="Vase")
    await client.post(f"/api/v1/orders/{oid}/generate-brief", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/orders/{oid}/approve-concept",
        headers=auth_headers,
        json={"approved": True},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "generating_3d"
    assert len(body["approvals"]) == 1
    assert body["approvals"][0]["status"] == "approved"
    assert body["approvals"][0]["stage"] == "concept"


async def test_reject_concept_regenerates(client: AsyncClient, auth_headers: dict):
    oid = await _create_order(client, auth_headers, title="Box")
    await client.post(f"/api/v1/orders/{oid}/generate-brief", headers=auth_headers)

    resp = await client.post(
        f"/api/v1/orders/{oid}/approve-concept",
        headers=auth_headers,
        json={"approved": False, "comment": "too tall"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "generating_concept"
    assert body["ai_attempts"] == 1
    assert body["approvals"][0]["status"] == "rejected"
    assert body["approvals"][0]["comment"] == "too tall"


async def test_generate_concept_requires_brief(
    client: AsyncClient, auth_headers: dict
):
    oid = await _create_order(client, auth_headers, title="No brief")
    resp = await client.post(
        f"/api/v1/orders/{oid}/generate-concept", headers=auth_headers
    )
    assert resp.status_code == 400


async def test_approve_concept_requires_correct_status(
    client: AsyncClient, auth_headers: dict
):
    # Fresh draft order is not awaiting concept approval.
    oid = await _create_order(client, auth_headers, title="Draft")
    resp = await client.post(
        f"/api/v1/orders/{oid}/approve-concept",
        headers=auth_headers,
        json={"approved": True},
    )
    assert resp.status_code == 409


async def test_regenerate_concept_after_reject(
    client: AsyncClient, auth_headers: dict
):
    oid = await _create_order(client, auth_headers, title="Lamp")
    await client.post(f"/api/v1/orders/{oid}/generate-brief", headers=auth_headers)
    await client.post(
        f"/api/v1/orders/{oid}/approve-concept",
        headers=auth_headers,
        json={"approved": False},
    )
    # Now status is generating_concept; regenerate should produce 6 more assets.
    resp = await client.post(
        f"/api/v1/orders/{oid}/generate-concept", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "waiting_concept_approval"
    assert len(body["assets"]) == 12  # 6 original + 6 regenerated
