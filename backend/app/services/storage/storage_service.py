"""Storage abstraction for uploaded and generated files.

Two backends:
- ``LocalStorageService`` (dev): writes under ``settings.local_storage_dir`` and
  serves files via the FastAPI ``/static`` mount.
- ``S3StorageService`` (prod): uploads to an S3/R2 bucket via boto3.

The backend is chosen by ``settings.storage_mock_mode`` (true -> local).

Keys are internal, slash-separated paths like ``models/42/abcd_model.glb``.
"""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod

import httpx
from loguru import logger

from app.core.config import settings


class StorageService(ABC):
    """Interface every storage backend implements."""

    @abstractmethod
    async def save_file(self, file_content: bytes, key: str, content_type: str) -> str:
        """Persist ``file_content`` at ``key``; return a public URL."""
        raise NotImplementedError

    @abstractmethod
    async def get_public_url(self, key: str) -> str:
        """Return the public URL for an existing ``key``."""
        raise NotImplementedError

    async def save_from_url(self, url: str, key: str) -> str:
        """Download ``url`` (http(s) or file://) and store it at ``key``."""
        content = await self._fetch(url)
        content_type = "application/octet-stream"
        return await self.save_file(content, key, content_type)

    @staticmethod
    async def _fetch(url: str) -> bytes:
        if url.startswith("file://"):
            # file:///abs/path or file://./relative — strip scheme and read.
            path = url[len("file://") :]
            if path.startswith("/") and os.name == "nt" and len(path) > 2 and path[2] == ":":
                path = path[1:]  # /C:/... -> C:/...
            with open(path, "rb") as fh:
                return fh.read()
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    # Back-compat helper used by Phase 1/2 (asset upload, concept images).
    async def save(self, *, order_id: int, filename: str, data: bytes) -> str:
        safe_name = os.path.basename(filename)
        key = f"uploads/{order_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
        return await self.save_file(data, key, "application/octet-stream")


class LocalStorageService(StorageService):
    """Write files to a local directory served by the ``/static`` mount."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = base_dir or settings.local_storage_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _abs_path(self, key: str) -> str:
        # Split on "/" so the key's logical subfolders become real directories.
        return os.path.join(self.base_dir, *key.split("/"))

    async def save_file(self, file_content: bytes, key: str, content_type: str) -> str:
        path = self._abs_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(file_content)
        logger.info("LocalStorage saved {} bytes -> {}", len(file_content), key)
        return await self.get_public_url(key)

    async def get_public_url(self, key: str) -> str:
        return f"{settings.static_base_url.rstrip('/')}/{key}"


class S3StorageService(StorageService):
    """Upload files to an S3-compatible bucket (AWS S3 or Cloudflare R2)."""

    def __init__(self) -> None:
        import boto3  # lazy: only needed in production

        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            endpoint_url=settings.storage_endpoint_url or None,
            region_name=settings.storage_region,
        )
        self._bucket = settings.storage_bucket

    async def save_file(self, file_content: bytes, key: str, content_type: str) -> str:
        # boto3 is synchronous; acceptable for the prod upload path.
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_content,
            ContentType=content_type,
        )
        return await self.get_public_url(key)

    async def get_public_url(self, key: str) -> str:
        return f"{settings.storage_public_url.rstrip('/')}/{key}"


def get_storage_service() -> StorageService:
    """Return the storage backend for the current environment."""
    if settings.storage_mock_mode:
        return LocalStorageService()
    return S3StorageService()
