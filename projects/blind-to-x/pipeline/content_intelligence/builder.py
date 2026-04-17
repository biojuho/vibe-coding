"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.models import ContentProfile
from pipeline.content_intelligence.classifiers import (
    classify_topic_cluster, classify_emotion_axis, classify_audience_fit,
    classify_hook_type, recommend_draft_type
)
from pipeline.content_intelligence.scoring_editorial import calculate_publishability_score
from pipeline.content_intelligence.scoring_performance import calculate_performance_score
from pipeline.content_intelligence.scoring_6d import calculate_6d_score
from pipeline.content_intelligence.boosting import estimate_viral_boost_llm
from pipeline.content_intelligence.utils import _round_score, _humanize_performance_rationale

def build_content_profile(
    post_data: dict[str, Any],
    scrape_quality_score: float,
    historical_examples: list[dict[str, Any]] | None = None,
    ranking_weights: dict[str, float] | None = None,
    llm_viral_boost: bool = False,
    trend_boost: float = 0.0,
) -> ContentProfile:
    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")

    topic_cluster = classify_topic_cluster(title, content)
    emotion_axis = classify_emotion_axis(title, content)
    audience_fit = classify_audience_fit(title, content)
    hook_type = classify_hook_type(title, content, emotion_axis)
    recommended_draft_type = recommend_draft_type(hook_type, emotion_axis)

    publishability_score, publishability_rationale, editorial_brief = calculate_publishability_score(
        post_data,
        topic_cluster,
        hook_type,
        emotion_axis,
    )

    # LLM 바이럴 부스트: 보더라인 점수(50-70)인 경우에만 호출 → API 비용 절감
    if llm_viral_boost and 50 <= publishability_score <= 70:
        boost = estimate_viral_boost_llm(title, content, topic_cluster, emotion_axis)
        if boost > 0:
            boost = min(10.0, boost)  # 최대 10점으로 캡 (과도한 부스트 방지)
            publishability_score = _round_score(publishability_score + boost)
            publishability_rationale.append("바이럴 가능성 보정 반영")

    # ML 점수 (100건 이상 축적 시 자동 활성화, 미만 시 heuristic 폴백)
    ml_score, ml_meta = 0.0, {}
    try:
        from pipeline.ml_scorer import get_ml_scorer

        _ml = get_ml_scorer()
        if _ml.is_active():
            ml_score, ml_meta = _ml.predict_score(
                topic_cluster=topic_cluster,
                hook_type=hook_type,
                emotion_axis=emotion_axis,
                draft_style=recommended_draft_type,
            )
    except Exception as _ml_exc:
        logger.debug("ML scorer unavailable: %s", _ml_exc)

    if ml_meta.get("method") == "ml":
        # ML 모델이 활성화된 경우 performance_score를 ML 예측으로 대체
        performance_score = ml_score
        performance_rationale = ["ml_model", f"trained_on={ml_meta.get('trained_on', '?')}"]
        logger.debug("Performance score via ML: %.1f (proba=%.4f)", ml_score, ml_meta.get("publish_proba", 0))
    else:
        performance_score, performance_rationale = calculate_performance_score(
            topic_cluster,
            hook_type,
            emotion_axis,
            recommended_draft_type,
            historical_examples=historical_examples,
        )

    weights = ranking_weights or {
        "scrape_quality": 0.35,
        "publishability": 0.40,
        "performance": 0.25,
    }
    final_rank_score = _round_score(
        scrape_quality_score * float(weights.get("scrape_quality", 0.35))
        + publishability_score * float(weights.get("publishability", 0.40))
        + performance_score * float(weights.get("performance", 0.25))
    )

    # Phase 4-B: 6D scorecard
    rank_6d, dims_6d = calculate_6d_score(
        post_data,
        topic_cluster,
        hook_type,
        emotion_axis,
        audience_fit,
        source=str(post_data.get("source", "")),
        trend_boost=trend_boost,
    )

    rationale = list(dict.fromkeys(publishability_rationale + _humanize_performance_rationale(performance_rationale)))
    return ContentProfile(
        topic_cluster=topic_cluster,
        hook_type=hook_type,
        emotion_axis=emotion_axis,
        audience_fit=audience_fit,
        recommended_draft_type=recommended_draft_type,
        scrape_quality_score=_round_score(scrape_quality_score),
        publishability_score=publishability_score,
        performance_score=performance_score,
        final_rank_score=final_rank_score,
        rationale=rationale,
        selection_summary=str(editorial_brief.get("selection_summary", "")),
        selection_reason_labels=list(editorial_brief.get("selection_reason_labels", []) or []),
        audience_need=str(editorial_brief.get("audience_need", "")),
        emotion_lane=str(editorial_brief.get("emotion_lane", "")),
        empathy_anchor=str(editorial_brief.get("empathy_anchor", "")),
        spinoff_angle=str(editorial_brief.get("spinoff_angle", "")),
        freshness_score=dims_6d["freshness_score"],
        social_signal_score=dims_6d["social_signal_score"],
        hook_strength_score=dims_6d["hook_strength_score"],
        trend_relevance_score=dims_6d["trend_relevance_score"],
        audience_targeting_score=dims_6d["audience_targeting_score"],
        viral_potential_score=dims_6d["viral_potential_score"],
        rank_6d=rank_6d,
    )
