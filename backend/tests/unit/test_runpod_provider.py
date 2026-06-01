"""Unit tests for the mock 3D provider attempt pattern."""

from __future__ import annotations

from app.services.ai.runpod_trellis_service import (
    DUCK_GLB_URL,
    GenerateModelInput,
    MockThreeDProvider,
)


def _input(attempt: int) -> GenerateModelInput:
    return GenerateModelInput(
        order_id=1, image_urls=[], model_prompt="x", attempt_number=attempt
    )


async def test_attempt_1_succeeds():
    provider = MockThreeDProvider(latency_seconds=0)
    out = await provider.generate_model(_input(1))
    assert out.success is True
    assert out.file_url == DUCK_GLB_URL
    assert out.file_format == "glb"


async def test_attempt_2_fails():
    provider = MockThreeDProvider(latency_seconds=0)
    out = await provider.generate_model(_input(2))
    assert out.success is False
    assert out.error_message


async def test_attempt_3_succeeds():
    provider = MockThreeDProvider(latency_seconds=0)
    out = await provider.generate_model(_input(3))
    assert out.success is True
    assert out.file_url == DUCK_GLB_URL
