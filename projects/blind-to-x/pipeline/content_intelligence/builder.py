"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pipeline.content_intelligence.boosting import estimate_viral_boost_llm
from pipeline.content_intelligence.classifiers import (
    classify_audience_fit,
    classify_emotion_axis,
    classify_hook_type,
    classify_topic_cluster,
    recommend_draft_type,
)
from pipeline.content_intelligence.models import ContentProfile
from pipeline.content_intelligence.scoring_6d import calculate_6d_score
from pipeline.content_intelligence.scoring_editorial import calculate_publishability_score
from pipeline.content_intelligence.scoring_performance import calculate_performance_score
from pipeline.content_intelligence.utils import _humanize_performance_rationale, _round_score

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ClassifiedPost:
    title: str
    content: str
    topic_cluster: str
    emotion_axis: str
    audience_fit: str
    hook_type: str
    recommended_draft_type: str


def build_content_profile(
    post_data: dict[str, Any],
    scrape_quality_score: float,
    historical_examples: list[dict[str, Any]] | None = None,
    ranking_weights: dict[str, float] | None = None,
    llm_viral_boost: bool = False,
    trend_boost: float = 0.0,
) -> ContentProfile:
    classified = _classify_post(post_data)
    publishability_score, publishability_rationale, editorial_brief = calculate_publishability_score(
        post_data,
        classified.topic_cluster,
        classified.hook_type,
        classified.emotion_axis,
    )
    publishability_score, publishability_rationale = _apply_llm_viral_boost(
        classified,
        publishability_score,
        publishability_rationale,
        enabled=llm_viral_boost,
    )
    performance_score, performance_rationale = _resolve_performance_score(
        classified,
        historical_examples=historical_examples,
    )
    final_rank_score = _calculate_final_rank_score(
        scrape_quality_score,
        publishability_score,
        performance_score,
        ranking_weights,
    )
    rank_6d, dims_6d = _calculate_rank_6d(post_data, classified, trend_boost)
    rationale = _merge_rationale(publishability_rationale, performance_rationale)

    return _build_profile(
        classified=classified,
        scrape_quality_score=scrape_quality_score,
        publishability_score=publishability_score,
        performance_score=performance_score,
        final_rank_score=final_rank_score,
        rationale=rationale,
        editorial_brief=editorial_brief,
        rank_6d=rank_6d,
        dims_6d=dims_6d,
    )


def _classify_post(post_data: dict[str, Any]) -> _ClassifiedPost:
    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")
    topic_cluster = classify_topic_cluster(title, content)
    emotion_axis = classify_emotion_axis(title, content)
    audience_fit = classify_audience_fit(title, content)
    hook_type = classify_hook_type(title, content, emotion_axis)
    recommended_draft_type = recommend_draft_type(hook_type, emotion_axis)
    return _ClassifiedPost(
        title=title,
        content=content,
        topic_cluster=topic_cluster,
        emotion_axis=emotion_axis,
        audience_fit=audience_fit,
        hook_type=hook_type,
        recommended_draft_type=recommended_draft_type,
    )


def _apply_llm_viral_boost(
    classified: _ClassifiedPost,
    publishability_score: float,
    publishability_rationale: list[str],
    *,
    enabled: bool,
) -> tuple[float, list[str]]:
    rationale = list(publishability_rationale)
    if not enabled or not 50 <= publishability_score <= 70:
        return publishability_score, rationale

    boost = estimate_viral_boost_llm(
        classified.title,
        classified.content,
        classified.topic_cluster,
        classified.emotion_axis,
    )
    if boost <= 0:
        return publishability_score, rationale

    boost = min(10.0, boost)
    rationale.append("바이럴 가능성 보정 반영")
    return _round_score(publishability_score + boost), rationale


def _resolve_performance_score(
    classified: _ClassifiedPost,
    *,
    historical_examples: list[dict[str, Any]] | None,
) -> tuple[float, list[str]]:
    ml_score, ml_meta = _predict_ml_performance(classified)
    if ml_meta.get("method") == "ml":
        logger.debug("Performance score via ML: %.1f (proba=%.4f)", ml_score, ml_meta.get("publish_proba", 0))
        return ml_score, ["ml_model", f"trained_on={ml_meta.get('trained_on', '?')}"]

    return calculate_performance_score(
        classified.topic_cluster,
        classified.hook_type,
        classified.emotion_axis,
        classified.recommended_draft_type,
        historical_examples=historical_examples,
    )


def _predict_ml_performance(classified: _ClassifiedPost) -> tuple[float, dict[str, Any]]:
    try:
        from pipeline.ml_scorer import get_ml_scorer

        ml_scorer = get_ml_scorer()
        if ml_scorer.is_active():
            return ml_scorer.predict_score(
                topic_cluster=classified.topic_cluster,
                hook_type=classified.hook_type,
                emotion_axis=classified.emotion_axis,
                draft_style=classified.recommended_draft_type,
            )
    except Exception as ml_exc:
        logger.debug("ML scorer unavailable: %s", ml_exc)
    return 0.0, {}


def _calculate_final_rank_score(
    scrape_quality_score: float,
    publishability_score: float,
    performance_score: float,
    ranking_weights: dict[str, float] | None,
) -> float:
    weights = ranking_weights or {
        "scrape_quality": 0.35,
        "publishability": 0.40,
        "performance": 0.25,
    }
    return _round_score(
        scrape_quality_score * float(weights.get("scrape_quality", 0.35))
        + publishability_score * float(weights.get("publishability", 0.40))
        + performance_score * float(weights.get("performance", 0.25))
    )


def _calculate_rank_6d(
    post_data: dict[str, Any],
    classified: _ClassifiedPost,
    trend_boost: float,
) -> tuple[float, dict[str, float]]:
    return calculate_6d_score(
        post_data,
        classified.topic_cluster,
        classified.hook_type,
        classified.emotion_axis,
        classified.audience_fit,
        source=str(post_data.get("source", "")),
        trend_boost=trend_boost,
    )


def _merge_rationale(publishability_rationale: list[str], performance_rationale: list[str]) -> list[str]:
    return list(dict.fromkeys(publishability_rationale + _humanize_performance_rationale(performance_rationale)))


def _build_profile(
    *,
    classified: _ClassifiedPost,
    scrape_quality_score: float,
    publishability_score: float,
    performance_score: float,
    final_rank_score: float,
    rationale: list[str],
    editorial_brief: dict[str, Any],
    rank_6d: float,
    dims_6d: dict[str, float],
) -> ContentProfile:
    return ContentProfile(
        topic_cluster=classified.topic_cluster,
        hook_type=classified.hook_type,
        emotion_axis=classified.emotion_axis,
        audience_fit=classified.audience_fit,
        recommended_draft_type=classified.recommended_draft_type,
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
