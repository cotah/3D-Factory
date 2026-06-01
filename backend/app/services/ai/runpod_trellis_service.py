"""3D generation providers (TRELLIS.2 via RunPod) behind a common interface.

- ``MockThreeDProvider`` (dev): returns a public Duck.glb so the viewer works,
  fails deterministically on attempt 2 to exercise the retry/designer fallback,
  and succeeds on attempt 3.
- ``RunpodTrellisProvider`` (prod): calls the RunPod ``runsync`` endpoint.

Chosen by ``settings.runpod_mock_mode``.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from loguru import logger

from app.core.config import settings

# Public sample GLB used by the mock so the frontend viewer renders a real model.
DUCK_GLB_URL = (
    "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/"
    "master/2.0/Duck/glTF-Binary/Duck.glb"
)


@dataclass
class GenerateModelInput:
    order_id: int
    image_urls: list[str]
    model_prompt: str
    attempt_number: int = 1


@dataclass
class GenerateModelOutput:
    success: bool
    file_url: str | None = None
    file_format: str | None = None  # "glb" | "obj" | "stl"
    job_id: str | None = None
    error_message: str | None = None
    metadata: dict = field(default_factory=dict)


class ThreeDGenerationProvider(ABC):
    @abstractmethod
    async def generate_model(self, data: GenerateModelInput) -> GenerateModelOutput:
        raise NotImplementedError


class MockThreeDProvider(ThreeDGenerationProvider):
    def __init__(self, latency_seconds: float = 3.0) -> None:
        self.latency_seconds = latency_seconds

    async def generate_model(self, data: GenerateModelInput) -> GenerateModelOutput:
        logger.info(
            "MockThreeDProvider[order={} attempt={}] generating (latency {}s)",
            data.order_id,
            data.attempt_number,
            self.latency_seconds,
        )
        await asyncio.sleep(self.latency_seconds)

        # Deterministic failure on attempt 2 to test retries.
        if data.attempt_number == 2:
            return GenerateModelOutput(
                success=False,
                job_id=f"mock-{data.order_id}-2",
                error_message="Mock TRELLIS failure on attempt 2 (simulated).",
            )

        return GenerateModelOutput(
            success=True,
            file_url=DUCK_GLB_URL,
            file_format="glb",
            job_id=f"mock-{data.order_id}-{data.attempt_number}",
            metadata={"provider": "mock", "attempt": data.attempt_number},
        )


class RunpodTrellisProvider(ThreeDGenerationProvider):
    async def generate_model(self, data: GenerateModelInput) -> GenerateModelOutput:
        import httpx

        url = f"https://api.runpod.io/v2/{settings.runpod_trellis_endpoint_id}/runsync"
        headers = {"Authorization": f"Bearer {settings.runpod_api_key}"}
        payload = {
            "input": {
                "images": data.image_urls,
                "prompt": data.model_prompt,
                "order_id": str(data.order_id),
            }
        }
        try:
            async with httpx.AsyncClient(timeout=settings.runpod_timeout_seconds) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except httpx.TimeoutException:
            return GenerateModelOutput(
                success=False,
                error_message=(
                    f"RunPod timed out after {settings.runpod_timeout_seconds}s."
                ),
            )
        except httpx.HTTPError as exc:
            return GenerateModelOutput(
                success=False,
                error_message=f"RunPod request failed: {type(exc).__name__}",
            )

        if body.get("status") != "COMPLETED":
            return GenerateModelOutput(
                success=False,
                job_id=body.get("id"),
                error_message=body.get("error") or f"RunPod status: {body.get('status')}",
            )

        output = body.get("output") or {}
        return GenerateModelOutput(
            success=True,
            file_url=output.get("model_url") or output.get("url"),
            file_format=output.get("format", "glb"),
            job_id=body.get("id"),
            metadata=output,
        )


def get_3d_provider() -> ThreeDGenerationProvider:
    if settings.runpod_mock_mode:
        return MockThreeDProvider()
    return RunpodTrellisProvider()
