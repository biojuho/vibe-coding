"""Pre-validate topics before the full pipeline runs.

Saves LLM/TTS/image costs by rejecting unsuitable topics early
with a single cheap LLM call.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from shorts_maker_v2.providers.llm_router import LLMRouter

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a YouTube Shorts topic validator. Evaluate whether the given topic \
is suitable for a 60-second vertical video on the specified channel.

Score each dimension 1-10 and decide pass/fail (pass >= 6 on ALL dimensions).

Return JSON exactly matching this schema:
{
  "visual_feasibility": <int 1-10>,
  "fact_verifiability": <int 1-10>,
  "format_suitability": <int 1-10>,
  "channel_relevance": <int 1-10>,
  "is_valid": <bool>,
  "confidence": <float 0-1>,
  "reason": "<one-sentence explanation>",
  "suggestions": ["<better variant 1>", "<better variant 2>"]
}

Dimension guidelines:
- visual_feasibility: Can this be visualized with images/stock footage in 60s?
- fact_verifiability: Are there concrete, verifiable facts to present?
- format_suitability: Does it fit the hook-body-CTA Shorts format?
- channel_relevance: Does it match the target channel's audience and niche?

If is_valid is false, provide 2-3 improved topic suggestions in "suggestions".
If is_valid is true, "suggestions" should be an empty list.\
"""


@dataclass(frozen=True)
class TopicValidation:
    """Result of topic pre-validation."""

    is_valid: bool
    confidence: float
    reason: str
    suggestions: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)


def validate_topic(
    topic: str,
    channel: str,
    config: dict,
    *,
    llm_router: LLMRouter | None = None,
) -> TopicValidation:
    """Validate a topic before running the full video pipeline.

    Args:
        topic: The topic string to validate.
        channel: Target YouTube channel name or description.
        config: Raw config dict (or AppConfig-derived dict) with at least
                ``providers`` section for LLM router setup.
        llm_router: Optional pre-configured LLMRouter instance.
                    If None, one is created from config.

    Returns:
        TopicValidation with pass/fail decision and suggestions.
    """
    if not topic or not topic.strip():
        return TopicValidation(
            is_valid=False,
            confidence=1.0,
            reason="Empty topic provided.",
            suggestions=["Provide a specific, concrete topic."],
        )

    router = llm_router or _build_router(config)
    user_prompt = f"Topic: {topic}\nChannel: {channel}"

    try:
        result = router.generate_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
        )
    except RuntimeError:
        logger.warning("Topic validation LLM call failed; allowing topic by default.")
        return TopicValidation(
            is_valid=True,
            confidence=0.0,
            reason="Validation skipped: LLM unavailable.",
        )

    return _parse_result(result)


def _build_router(config: dict) -> LLMRouter:
    """Create a minimal LLMRouter from config dict."""
    providers_cfg = config.get("providers", {})
    providers = providers_cfg.get("llm_providers", [])
    models = providers_cfg.get("llm_models", None)
    timeout = config.get("limits", {}).get("request_timeout_sec", 60)

    return LLMRouter(
        providers=providers or [providers_cfg.get("llm", "openai")],
        models=models,
        max_retries=1,
        request_timeout_sec=min(timeout, 30),
    )


def _parse_result(data: dict) -> TopicValidation:
    """Parse LLM JSON response into TopicValidation."""
    try:
        is_valid = bool(data.get("is_valid", False))
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        reason = str(data.get("reason", "No reason provided."))

        raw_suggestions = data.get("suggestions", [])
        suggestions = (
            [str(s) for s in raw_suggestions if s]
            if isinstance(raw_suggestions, list)
            else []
        )

        score_keys = [
            "visual_feasibility",
            "fact_verifiability",
            "format_suitability",
            "channel_relevance",
        ]
        scores = {}
        for key in score_keys:
            val = data.get(key)
            if val is not None:
                scores[key] = max(1, min(10, int(val)))

        return TopicValidation(
            is_valid=is_valid,
            confidence=confidence,
            reason=reason,
            suggestions=suggestions,
            scores=scores,
        )
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to parse validation response: %s", exc)
        return TopicValidation(
            is_valid=True,
            confidence=0.0,
            reason=f"Parse error, allowing topic: {exc}",
        )
