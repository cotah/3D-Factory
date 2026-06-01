"""Unit tests for the mocked ClaudeService Production Brief."""

from __future__ import annotations

from app.models.models import Order
from app.services.ai.claude_service import (
    _VALID_COMPLEXITY,
    ClaudeService,
    ProductionBrief,
)


def _order(title: str = "Thing", **kw) -> Order:
    return Order(user_id=1, title=title, **kw)


def test_mock_brief_has_all_fields():
    brief = ClaudeService().generate_production_brief(
        _order(title="Vase", category="decor")
    )
    assert isinstance(brief, ProductionBrief)
    assert brief.technical_summary
    assert brief.image_prompt
    assert brief.model_3d_prompt
    assert brief.complexity in _VALID_COMPLEXITY
    assert 0.0 <= brief.designer_probability <= 1.0
    assert isinstance(brief.risks, list) and brief.risks
    assert isinstance(brief.print_alerts, list) and brief.print_alerts
    assert "min" in brief.estimated_price_range
    assert "max" in brief.estimated_price_range
    assert brief.raw_json


def test_mock_brief_varies_by_category():
    decor = ClaudeService().generate_production_brief(
        _order(title="Figurine", category="decorative")
    )
    functional = ClaudeService().generate_production_brief(
        _order(title="Bracket", category="functional")
    )
    assert decor.complexity == "simple"
    assert functional.complexity == "complex"
    # Complex parts carry a higher designer probability than simple ones.
    assert functional.designer_probability > decor.designer_probability


def test_raw_json_is_parseable_and_consistent():
    import json

    brief = ClaudeService().generate_production_brief(_order(title="Gear"))
    parsed = json.loads(brief.raw_json)
    assert parsed["complexity"] == brief.complexity
    assert parsed["technical_summary"] == brief.technical_summary
    # raw_json must not leak the redundant raw_json key back into itself.
    assert "raw_json" not in parsed
