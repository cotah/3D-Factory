"""Unit tests for S3StorageService (R2) with boto3 mocked — no real network."""

from __future__ import annotations

from unittest.mock import MagicMock

import boto3

from app.core.config import settings
from app.services.storage.storage_service import S3StorageService


def _service(monkeypatch) -> tuple[S3StorageService, MagicMock]:
    mock_client = MagicMock()
    monkeypatch.setattr(boto3, "client", lambda *a, **k: mock_client)
    monkeypatch.setattr(settings, "storage_public_url", "https://cdn.example.com")
    monkeypatch.setattr(settings, "storage_bucket", "print3d-assets")
    return S3StorageService(), mock_client


async def test_save_file_calls_put_object(monkeypatch):
    service, mock_client = _service(monkeypatch)

    url = await service.save_file(b"hello", "models/1/a.glb", "model/gltf-binary")

    mock_client.put_object.assert_called_once()
    kwargs = mock_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "print3d-assets"
    assert kwargs["Key"] == "models/1/a.glb"
    assert kwargs["Body"] == b"hello"
    assert kwargs["ContentType"] == "model/gltf-binary"
    assert url == "https://cdn.example.com/models/1/a.glb"


async def test_get_public_url(monkeypatch):
    service, _ = _service(monkeypatch)
    url = await service.get_public_url("images/3/front.png")
    assert url == "https://cdn.example.com/images/3/front.png"


async def test_delete_file_calls_delete_object(monkeypatch):
    service, mock_client = _service(monkeypatch)
    ok = await service.delete_file("models/1/a.glb")
    assert ok is True
    mock_client.delete_object.assert_called_once_with(
        Bucket="print3d-assets", Key="models/1/a.glb"
    )


async def test_factory_returns_local_in_mock_mode(monkeypatch):
    from app.services.storage.storage_service import (
        LocalStorageService,
        get_storage_service,
    )

    monkeypatch.setattr(settings, "storage_mock_mode", True)
    assert isinstance(get_storage_service(), LocalStorageService)
