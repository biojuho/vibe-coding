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
    match_bonus = 0.0  # weighted match increments, normalized separately from base
    rationale: list[str] = []

    for example in historical_examples:
        weight = 1.0 + min(float(example.get("views", 0) or 0) / 10000.0, 2.0)
        total_weight += weight

        if example.get("topic_cluster") == topic_cluster:
            match_bonus += 18 * weight
            rationale.append("topic_match")
        if example.get("hook_type") == hook_type:
            match_bonus += 15 * weight
            rationale.append("hook_match")
        if example.get("emotion_axis") == emotion_axis:
            match_bonus += 12 * weight
            rationale.append("emotion_match")
        if example.get("draft_style") == recommended_draft_type:
            match_bonus += 10 * weight
            rationale.append("draft_style_match")

    if total_weight <= 0:
        return 50.0, ["no_weighted_examples"]

    # Base score 35.0 is a constant prior independent of example count/weight.
    # Only the match bonus is weight-normalized so high-viewed examples count more.
    normalized = 35.0 + match_bonus / total_weight
    return _round_score(normalized), sorted(set(rationale)) or ["weak_match"]
