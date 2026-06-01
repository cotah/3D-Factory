"""Integration tests for auth and the orders CRUD/lifecycle endpoints."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient


# ------------------------------- Auth ---------------------------------
async def test_register_and_me(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "secret123", "full_name": "A"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"
    assert me.json()["role"] == "customer"


async def test_register_duplicate_email_conflicts(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "secret123"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_success_and_failure(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "secret123"},
    )
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "secret123"},
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401


async def test_refresh_token_flow(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "ref@example.com", "password": "secret123"},
    )
    refresh_token = reg.json()["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ------------------------------ Orders --------------------------------
async def test_create_and_list_order(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={"title": "Dragon figurine", "description": "A small dragon"},
    )
    assert create.status_code == 201, create.text
    order = create.json()
    assert order["title"] == "Dragon figurine"
    assert order["status"] == "draft"

    listing = await client.get("/api/v1/orders", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_get_update_and_cancel_order(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/orders", headers=auth_headers, json={"title": "Vase"}
    )
    order_id = create.json()["id"]

    got = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert got.status_code == 200

    patched = await client.patch(
        f"/api/v1/orders/{order_id}",
        headers=auth_headers,
        json={"description": "A tall vase"},
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "A tall vase"

    cancelled = await client.delete(
        f"/api/v1/orders/{order_id}", headers=auth_headers
    )
    assert cancelled.status_code == 200

    after = await client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert after.json()["status"] == "cancelled"


async def test_customer_cannot_set_status_via_patch(
    client: AsyncClient, auth_headers: dict
):
    create = await client.post(
        "/api/v1/orders", headers=auth_headers, json={"title": "Box"}
    )
    order_id = create.json()["id"]
    patched = await client.patch(
        f"/api/v1/orders/{order_id}",
        headers=auth_headers,
        json={"status": "printing"},
    )
    # Status change is ignored for customers; it stays draft.
    assert patched.status_code == 200
    assert patched.json()["status"] == "draft"


async def test_order_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/orders/9999", headers=auth_headers)
    assert resp.status_code == 404


async def test_customer_cannot_see_others_orders(client: AsyncClient):
    # User one creates an order.
    r1 = await client.post(
        "/api/v1/auth/register",
        json={"email": "u1@example.com", "password": "secret123"},
    )
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    created = await client.post(
        "/api/v1/orders", headers=h1, json={"title": "Private"}
    )
    order_id = created.json()["id"]

    # User two cannot read it.
    r2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "secret123"},
    )
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    resp = await client.get(f"/api/v1/orders/{order_id}", headers=h2)
    assert resp.status_code == 404


async def test_generate_3d_rejects_wrong_status(
    client: AsyncClient, auth_headers: dict
):
    # Phase 3: generate-3d only runs from the generating_3d state. A fresh
    # draft order must be rejected (the full happy path lives in
    # test_3d_generation.py).
    create = await client.post(
        "/api/v1/orders", headers=auth_headers, json={"title": "Phone stand"}
    )
    order_id = create.json()["id"]

    gen = await client.post(
        f"/api/v1/orders/{order_id}/generate-3d", headers=auth_headers
    )
    assert gen.status_code == 409

    # The Phase 1 validate-mesh helper still moves the order to validating_mesh.
    val = await client.post(
        f"/api/v1/orders/{order_id}/validate-mesh", headers=auth_headers
    )
    assert val.json()["status"] == "validating_mesh"

    # approve-final also guards on status.
    approved = await client.post(
        f"/api/v1/orders/{order_id}/approve-final",
        headers=auth_headers,
        json={"approved": True},
    )
    assert approved.status_code == 409


async def test_upload_final_model_requires_staff(
    client: AsyncClient, auth_headers: dict
):
    create = await client.post(
        "/api/v1/orders", headers=auth_headers, json={"title": "Gear"}
    )
    order_id = create.json()["id"]
    resp = await client.post(
        f"/api/v1/orders/{order_id}/upload-final-model", headers=auth_headers
    )
    assert resp.status_code == 403


# ------------------------------ Assets --------------------------------
async def test_upload_and_list_asset(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/orders", headers=auth_headers, json={"title": "Keychain"}
    )
    order_id = create.json()["id"]

    files = {"file": ("ref.png", io.BytesIO(b"fake image bytes"), "image/png")}
    upload = await client.post(
        f"/api/v1/orders/{order_id}/assets", headers=auth_headers, files=files
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["filename"] == "ref.png"

    listing = await client.get(
        f"/api/v1/orders/{order_id}/assets", headers=auth_headers
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_upload_rejects_bad_extension(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/orders", headers=auth_headers, json={"title": "Bad"}
    )
    order_id = create.json()["id"]

    files = {"file": ("virus.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    upload = await client.post(
        f"/api/v1/orders/{order_id}/assets", headers=auth_headers, files=files
    )
    assert upload.status_code == 400
