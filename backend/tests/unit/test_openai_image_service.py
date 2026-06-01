"""Unit tests for the mocked OpenAIImageService."""

from __future__ import annotations

from sqlmodel import select

from app.models.models import AssetType, Order, ProjectAsset, User
from app.services.ai.openai_image_service import ANGLES, OpenAIImageService


async def _make_order(session) -> Order:
    user = User(email="img@example.com", hashed_password="x")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    order = Order(user_id=user.id, title="Cube")
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def test_mock_generates_six_images(session):
    order = await _make_order(session)
    service = OpenAIImageService(mock_latency_seconds=0)

    result = await service.generate_concept_images(order, "a cube", session)

    assert len(result.images) == 6
    assert {img.angle for img in result.images} == {a for a, _ in ANGLES}
    for img in result.images:
        assert img.angle
        assert img.url
        assert img.storage_url
        assert img.storage_key


async def test_mock_persists_concept_assets(session):
    order = await _make_order(session)
    service = OpenAIImageService(mock_latency_seconds=0)

    await service.generate_concept_images(order, "a cube", session)

    rows = await session.execute(
        select(ProjectAsset).where(ProjectAsset.order_id == order.id)
    )
    assets = list(rows.scalars().all())
    assert len(assets) == 6
    assert all(a.type == AssetType.concept_image for a in assets)
