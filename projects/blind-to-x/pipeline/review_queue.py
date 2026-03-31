"""Review queue decision helpers."""

from __future__ import annotations

from typing import Any


def build_review_decision(
    config,
    post_data: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    review_threshold = float(
        config.get("review.auto_move_to_review_threshold", config.get("ranking.final_rank_min", 60))
    )
    final_rank_min = float(config.get("ranking.final_rank_min", 60))
    effective_threshold = max(review_threshold, final_rank_min)

    title = str(post_data.get("title", "") or "").strip()
    content = str(post_data.get("content", "") or "").strip()

    if config.get("review.reject_on_missing_title", True) and not title:
        return {
            "should_queue": False,
            "status": "보류",
            "review_reason": "missing_title",
            "review_priority": "low",
        }

    if config.get("review.reject_on_missing_content", True) and not content:
        return {
            "should_queue": False,
            "status": "보류",
            "review_reason": "missing_content",
            "review_priority": "low",
        }

    final_rank_score = float(profile.get("final_rank_score", 0) or 0)
    if final_rank_score < effective_threshold:
        return {
            "should_queue": False,
            "status": "보류",
            "review_reason": "final_rank_below_threshold",
            "review_priority": "low",
        }

    if final_rank_score >= 80:
        priority = "high"
    elif final_rank_score >= 70:
        priority = "medium"
    else:
        priority = "normal"

    return {
        "should_queue": True,
        "status": "검토필요",
        "review_reason": "queued_for_review",
        "review_priority": priority,
    }
