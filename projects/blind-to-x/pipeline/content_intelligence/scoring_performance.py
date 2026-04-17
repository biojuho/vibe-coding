"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.utils import _round_score


def calculate_performance_score(
    topic_cluster: str,
    hook_type: str,
    emotion_axis: str,
    recommended_draft_type: str,
    historical_examples: list[dict[str, Any]] | None = None,
) -> tuple[float, list[str]]:
    if not historical_examples:
        return 45.0, ["no_historical_examples"]

    total_weight = 0.0
    score = 35.0
    rationale: list[str] = []

    for example in historical_examples:
        weight = 1.0 + min(float(example.get("views", 0) or 0) / 10000.0, 2.0)
        total_weight += weight

        if example.get("topic_cluster") == topic_cluster:
            score += 18 * weight
            rationale.append("topic_match")
        if example.get("hook_type") == hook_type:
            score += 15 * weight
            rationale.append("hook_match")
        if example.get("emotion_axis") == emotion_axis:
            score += 12 * weight
            rationale.append("emotion_match")
        if example.get("draft_style") == recommended_draft_type:
            score += 10 * weight
            rationale.append("draft_style_match")

    if total_weight <= 0:
        return 50.0, ["no_weighted_examples"]

    normalized = score / total_weight
    return _round_score(normalized), sorted(set(rationale)) or ["weak_match"]
