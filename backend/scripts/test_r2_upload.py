"""Smoke-test Cloudflare R2 uploads via S3StorageService.

Requires the STORAGE_* settings to point at a real R2 bucket (set them in the
environment or .env). Run:

    uv run python scripts/test_r2_upload.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.storage.storage_service import S3StorageService  # noqa: E402


async def main() -> None:
    storage = S3StorageService()

    content = b"Hello R2 from Print3D Platform!"
    url = await storage.save_file(content, "test/hello.txt", "text/plain")
    print(f"Upload OK: {url}")

    duck_url = (
        "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/"
        "master/2.0/Duck/glTF-Binary/Duck.glb"
    )
    model_url = await storage.save_from_url(duck_url, "test/duck.glb")
    print(f"URL re-upload OK: {model_url}")


if __name__ == "__main__":
    asyncio.run(main())
