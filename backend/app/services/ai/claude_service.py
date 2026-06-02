"""Claude (Anthropic) service — generates a structured Production Brief.

Honors ``settings.ai_mock_mode``: when true (default for local dev) it returns
a realistic fake brief that varies by order category, without calling the API.
When false it calls Claude and forces a JSON-only response matching the
``ProductionBrief`` shape.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from loguru import logger

from app.core.config import settings
from app.models.models import Order

# Allowed complexity tiers.
COMPLEXITY_SIMPLE = "simple"
COMPLEXITY_MEDIUM = "medium"
COMPLEXITY_COMPLEX = "complex"
_VALID_COMPLEXITY = {COMPLEXITY_SIMPLE, COMPLEXITY_MEDIUM, COMPLEXITY_COMPLEX}


@dataclass
class ProductionBrief:
    technical_summary: str
    image_prompt: str
    model_3d_prompt: str
    complexity: str  # "simple" | "medium" | "complex"
    designer_probability: float  # 0.0 - 1.0
    risks: list[str] = field(default_factory=list)
    print_alerts: list[str] = field(default_factory=list)
    estimated_price_range: dict = field(default_factory=lambda: {"min": 0, "max": 0})
    raw_json: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        """Brief without the redundant ``raw_json`` blob, for API responses."""
        data = asdict(self)
        data.pop("raw_json", None)
        return data


_SYSTEM_PROMPT = (
    "You are a senior 3D-printing production engineer. Given a customer order, "
    "produce a Production Brief. Respond with ONLY a single valid JSON object, "
    "no markdown, no prose, with exactly these keys: "
    "technical_summary (string), image_prompt (string, for an image generator), "
    "model_3d_prompt (string, for a 3D generator), "
    "complexity (one of 'simple','medium','complex'), "
    "designer_probability (number 0..1), risks (array of strings), "
    "print_alerts (array of strings), "
    "estimated_price_range (object with numeric 'min' and 'max'). "
    "Be practical and specific to the requested part."
)


# Category keyword -> (complexity, designer_probability, price_min, price_max).
# Lets the mock vary realistically without calling the API.
_CATEGORY_PROFILES: list[tuple[tuple[str, ...], tuple[str, float, int, int]]] = [
    (("trophy", "trofeu", "troféu", "award", "premio", "prêmio"),
     (COMPLEXITY_MEDIUM, 0.30, 80, 180)),
    (("functional", "funcional", "gear", "engrenagem", "mechanical", "mecanic", "tool", "suporte", "bracket", "mount"),
     (COMPLEXITY_COMPLEX, 0.50, 60, 200)),
    (("decor", "decorative", "decorativo", "figurine", "miniature", "miniatura", "statue", "enfeite"),
     (COMPLEXITY_SIMPLE, 0.15, 40, 110)),
]
_DEFAULT_PROFILE = (COMPLEXITY_MEDIUM, 0.25, 50, 120)


def _profile_for(order: Order) -> tuple[str, float, int, int]:
    haystack = " ".join(
        filter(None, [order.category or "", order.title or "", order.description or ""])
    ).lower()
    for keywords, profile in _CATEGORY_PROFILES:
        if any(k in haystack for k in keywords):
            return profile
    return _DEFAULT_PROFILE


class ClaudeService:
    """Anthropic wrapper that produces a structured Production Brief."""

    def __init__(self) -> None:
        self.mock = settings.ai_mock_mode

    def generate_production_brief(self, order: Order) -> ProductionBrief:
        if self.mock:
            logger.info("ClaudeService[MOCK] generating brief for order id={}", order.id)
            return self._mock_brief(order)
        logger.info("ClaudeService[REAL] generating brief for order id={}", order.id)
        return self._real_brief(order)

    # ------------------------------ Mock ------------------------------
    def _mock_brief(self, order: Order) -> ProductionBrief:
        complexity, designer_prob, price_min, price_max = _profile_for(order)
        material = order.material or "PLA"
        subject = order.title or "the requested part"

        technical_summary = (
            f"Production brief for '{subject}'. "
            f"{order.description or 'No extra description provided.'} "
            f"Recommended material: {material}. Estimated complexity: {complexity}."
        )
        image_prompt = (
            f"Professional product render of {subject}. "
            f"{order.description or ''} Material look: {material}. "
            "Neutral studio background, soft lighting, high detail."
        ).strip()
        model_3d_prompt = (
            f"A clean, watertight 3D model of {subject}. "
            f"{order.description or ''} Printable, flat base, no floating parts."
        ).strip()

        risks = ["Thin walls may need reinforcement."]
        print_alerts = ["Verify a flat base for bed adhesion."]
        if complexity == COMPLEXITY_COMPLEX:
            risks.append("Overhangs likely require supports.")
            print_alerts.append("Mechanical fit tolerances should be checked.")
        elif complexity == COMPLEXITY_SIMPLE:
            print_alerts.append("Low infill (10-15%) should be sufficient.")

        brief = ProductionBrief(
            technical_summary=technical_summary,
            image_prompt=image_prompt,
            model_3d_prompt=model_3d_prompt,
            complexity=complexity,
            designer_probability=designer_prob,
            risks=risks,
            print_alerts=print_alerts,
            estimated_price_range={"min": price_min, "max": price_max},
        )
        brief.raw_json = json.dumps(brief.to_public_dict(), ensure_ascii=False)
        return brief

    # ------------------------------ Real ------------------------------
    def _real_brief(self, order: Order) -> ProductionBrief:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        user_prompt = self._build_user_prompt(order)
        message = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(
            block.text for block in message.content
            if getattr(block, "type", "") == "text"
        )
        return self._parse_brief(text)

    @staticmethod
    def _build_user_prompt(order: Order) -> str:
        parts = [f"Title: {order.title}", f"Description: {order.description}"]
        for label, value in (
            ("Category", order.category),
            ("Size", order.size),
            ("Colors", order.colors),
            ("Material", order.material),
            ("Deadline", order.deadline),
        ):
            if value:
                parts.append(f"{label}: {value}")
        return "\n".join(parts)

    @staticmethod
    def _parse_brief(text: str) -> ProductionBrief:
        """Parse Claude's JSON response into a ProductionBrief.

        Tolerates the model wrapping JSON in code fences. Raises ValueError on
        unparseable output so the caller can surface a clean 503.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            # Drop a leading language tag like "json".
            if "\n" in cleaned:
                cleaned = cleaned.split("\n", 1)[1]
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Claude response did not contain a JSON object")
        payload = json.loads(cleaned[start : end + 1])

        complexity = str(payload.get("complexity", COMPLEXITY_MEDIUM)).lower()
        if complexity not in _VALID_COMPLEXITY:
            complexity = COMPLEXITY_MEDIUM

        prob = float(payload.get("designer_probability", 0.25))
        prob = max(0.0, min(1.0, prob))

        brief = ProductionBrief(
            technical_summary=str(payload.get("technical_summary", "")),
            image_prompt=str(payload.get("image_prompt", "")),
            model_3d_prompt=str(payload.get("model_3d_prompt", "")),
            complexity=complexity,
            designer_probability=prob,
            risks=[str(r) for r in payload.get("risks", [])],
            print_alerts=[str(a) for a in payload.get("print_alerts", [])],
            estimated_price_range=payload.get("estimated_price_range", {"min": 0, "max": 0}),
        )
        brief.raw_json = json.dumps(brief.to_public_dict(), ensure_ascii=False)
        return brief


def generate_designer_brief(order: Order) -> dict:
    """Build a technical brief for a human designer.

    Intentionally contains NO customer personal data (no name, email, address
    or payment info) — only the order's technical attributes. The reference is
    an opaque order code, never the customer identity.
    """
    brief_data: dict = {}
    if order.ai_brief_json:
        try:
            brief_data = json.loads(order.ai_brief_json)
        except json.JSONDecodeError:
            brief_data = {}

    return {
        "order_reference": f"ORD-{order.id:06d}",
        "title": order.title,
        "category": order.category,
        "size": order.size,
        "colors": order.colors,
        "material": order.material,
        "deadline": order.deadline,
        "technical_summary": brief_data.get("technical_summary", ""),
        "complexity": order.complexity,
        "model_3d_prompt": brief_data.get("model_3d_prompt", ""),
        "risks": brief_data.get("risks", []),
        "print_alerts": brief_data.get("print_alerts", []),
        "ai_attempts": order.ai_attempts,
        "instructions": (
            "Crie um modelo 3D em GLB ou STL seguindo as especificações acima. "
            "O modelo deve ser manifold (sem faces abertas), ter espessura mínima "
            "de 1.5mm e base plana para impressão FDM."
        ),
    }
