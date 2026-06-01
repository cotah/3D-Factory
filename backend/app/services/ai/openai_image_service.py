"""OpenAI image service — generates 6 concept images for an order.

Honors ``settings.ai_mock_mode``: when true it returns deterministic public
placeholder images (picsum.photos) without calling OpenAI. When false it calls
the configured image model once per angle, with exponential-backoff retries,
and stores each image via ``StorageService``.

Partial failures are tolerated: if some angles fail, the successful ones are
still saved and returned, and the failures are logged.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AssetType, Order, ProjectAsset
from app.services.storage.storage_service import StorageService, get_storage_service

# (angle key, human prompt fragment that steers the camera).
ANGLES: list[tuple[str, str]] = [
    ("front", "front view, facing camera directly"),
    ("back", "rear view"),
    ("left", "left side view"),
    ("right", "right side view"),
    ("diagonal", "45-degree diagonal view"),
    ("top", "top-down view"),
]

_MAX_RETRIES = 3


@dataclass
class ConceptImage:
    angle: str
    url: str  # temporary URL returned by the provider (or placeholder in mock)
    storage_key: str
    storage_url: str  # permanent location after saving


@dataclass
class ConceptImageSet:
    images: list[ConceptImage] = field(default_factory=list)
    prompt_used: str = ""
    errors: list[str] = field(default_factory=list)


class OpenAIImageService:
    def __init__(
        self,
        storage: StorageService | None = None,
        mock_latency_seconds: float = 2.0,
    ) -> None:
        self.mock = settings.ai_mock_mode
        self.storage = storage or get_storage_service()
        self.mock_latency_seconds = mock_latency_seconds

    async def generate_concept_images(
        self,
        order: Order,
        image_prompt: str,
        session: AsyncSession,
    ) -> ConceptImageSet:
        """Generate the 6 concept images and persist each as a ProjectAsset."""
        if self.mock:
            result = await self._mock_images(order, image_prompt)
        else:
            result = await self._real_images(order, image_prompt)

        for image in result.images:
            session.add(
                ProjectAsset(
                    order_id=order.id,
                    type=AssetType.concept_image,
                    filename=f"concept_{image.angle}.png",
                    storage_url=image.storage_url,
                    content_type="image/png",
                    size_bytes=0,
                )
            )
        await session.commit()

        logger.info(
            "OpenAIImageService generated {}/6 concept images for order id={} ({} errors)",
            len(result.images),
            order.id,
            len(result.errors),
        )
        return result

    # ------------------------------ Mock ------------------------------
    async def _mock_images(self, order: Order, image_prompt: str) -> ConceptImageSet:
        logger.info("OpenAIImageService[MOCK] order id={} ({} angles)", order.id, len(ANGLES))
        # Simulate provider latency once for the whole set.
        await asyncio.sleep(self.mock_latency_seconds)

        images: list[ConceptImage] = []
        for angle, _fragment in ANGLES:
            # Deterministic placeholder per order+angle.
            url = f"https://picsum.photos/seed/{order.id}-{angle}/1024"
            images.append(
                ConceptImage(
                    angle=angle,
                    url=url,
                    storage_key=f"concept/{order.id}/{angle}.png",
                    storage_url=url,
                )
            )
        return ConceptImageSet(images=images, prompt_used=image_prompt)

    # ------------------------------ Real ------------------------------
    async def _real_images(self, order: Order, image_prompt: str) -> ConceptImageSet:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        result = ConceptImageSet(prompt_used=image_prompt)

        for angle, fragment in ANGLES:
            angle_prompt = f"{image_prompt}. Camera: {fragment}."
            try:
                data = await self._generate_one(client, angle_prompt)
                storage_url = await self.storage.save(
                    order_id=order.id,
                    filename=f"concept_{angle}.png",
                    data=data,
                )
                result.images.append(
                    ConceptImage(
                        angle=angle,
                        url=storage_url,
                        storage_key=f"concept/{order.id}/{angle}.png",
                        storage_url=storage_url,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - tolerate per-angle failure
                # Never log the prompt/key; just the angle and error type.
                logger.warning(
                    "Concept image failed for order id={} angle={}: {}",
                    order.id,
                    angle,
                    type(exc).__name__,
                )
                result.errors.append(f"{angle}: {type(exc).__name__}")

        return result

    async def _generate_one(self, client, prompt: str) -> bytes:
        """Generate one image with exponential-backoff retries; return bytes."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await client.images.generate(
                    model=settings.openai_image_model,
                    prompt=prompt,
                    size=settings.openai_image_size,
                    n=1,
                )
                item = response.data[0]
                if getattr(item, "b64_json", None):
                    return base64.b64decode(item.b64_json)
                # Some models return a URL; fetch the bytes.
                import httpx

                async with httpx.AsyncClient(timeout=60) as http:
                    img = await http.get(item.url)
                    img.raise_for_status()
                    return img.content
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)  # 1s, 2s, 4s
        assert last_exc is not None
        raise last_exc
