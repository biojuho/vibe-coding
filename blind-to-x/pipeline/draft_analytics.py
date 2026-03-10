"""Helpers for persisting blind-to-x draft analytics and refreshing ML scorer."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def record_draft_event(
    *,
    source: str = "",
    topic_cluster: str = "",
    hook_type: str = "",
    emotion_axis: str = "",
    draft_style: str = "",
    provider_used: str = "",
    final_rank_score: float = 0.0,
    published: bool = False,
    content_url: str = "",
    notion_page_id: str = "",
    hook_score: float = 0.0,
    virality_score: float = 0.0,
    fit_score: float = 0.0,
) -> None:
    try:
        from pipeline.cost_db import CostDatabase

        db = CostDatabase()
        db.record_draft(
            source=source,
            topic_cluster=topic_cluster,
            hook_type=hook_type,
            emotion_axis=emotion_axis,
            draft_style=draft_style,
            provider_used=provider_used,
            final_rank_score=final_rank_score,
            published=published,
            content_url=content_url,
            notion_page_id=notion_page_id,
        )
        if hook_score or virality_score or fit_score:
            db.update_draft_scores(
                content_url=content_url,
                notion_page_id=notion_page_id,
                hook_score=hook_score,
                virality_score=virality_score,
                fit_score=fit_score,
            )
    except Exception as exc:
        logger.debug("Draft analytics record skipped: %s", exc)


def refresh_ml_scorer_if_needed() -> None:
    try:
        from pipeline.ml_scorer import get_ml_scorer

        get_ml_scorer().retrain_if_needed()
    except Exception as exc:
        logger.debug("ML scorer refresh skipped: %s", exc)

