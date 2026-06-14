"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.rules import get_season_boost, get_source_hint
from pipeline.content_intelligence.utils import _round_score

DEFAULT_6D_WEIGHTS = {
    "freshness": 0.15,
    "social": 0.25,
    "hook": 0.20,
    "trend": 0.15,
    "audience": 0.15,
    "viral": 0.10,
}
DIMENSION_KEYS = tuple(DEFAULT_6D_WEIGHTS)
HOOK_TYPE_SCORES = {
    "논쟁형": 90.0,
    "공감형": 75.0,
    "정보형": 70.0,
    "한줄팩폭형": 85.0,
    "짤형": 65.0,
    "분석형": 88.0,
    "통찰형": 82.0,
}
# T-AB036: 2026 블라인드 핵심 트렌드 업데이트 (AI 전환 이슈 반영)
# T-AB046: AI 트렌드 topic label 추가 — classification.yaml label=AI 트렌드가
#   HIGH_TREND_TOPICS에 없으면 _trend_relevance_score가 50.0 기본값 반환
HIGH_TREND_TOPICS = {"연봉", "이직", "회사문화", "상사", "구조조정", "AI 대체", "자동화", "AI 트렌드"}
MEDIUM_TREND_TOPICS = {"복지", "재테크", "직장개그", "부동산", "IT", "AI 도구", "ChatGPT", "프롬프트"}
AUDIENCE_SCORES = {
    "전직장인": 85.0,
    "이직준비층": 80.0,
    "초년생": 70.0,
    "관리자층": 60.0,
    "범용": 50.0,
}
VIRAL_SCORES = {
    "분노": 90.0,
    "경악": 85.0,
    "웃김": 80.0,
    # T-AB035: 2026 신규 감정축 바이럴 점수 — 블라인드 AI 일자리/구조조정 게시물 engagement 근거
    "AI_전환": 82.0,  # AI 대체 불안 = 경악급 공감 (2026 핵심 직장인 이슈)
    "고용불안": 78.0,  # 권고사직/구조조정 = 현타 이상 (강한 공유 욕구)
    "현타": 75.0,
    "허탈": 70.0,
    "공감": 65.0,
    "통찰": 55.0,
}


def _freshness_score(post_data: dict[str, Any]) -> float:
    import time

    freshness = 50.0
    scraped_at = post_data.get("scraped_at") or post_data.get("created_at")
    if not scraped_at:
        return freshness
    try:
        import datetime as _dt

        if isinstance(scraped_at, (int, float)):
            age_hours = (time.time() - scraped_at) / 3600
        else:
            ts = _dt.datetime.fromisoformat(str(scraped_at))
            age_hours = (_dt.datetime.now() - ts.replace(tzinfo=None)).total_seconds() / 3600
        return max(5.0, 100.0 * math.exp(-age_hours / 24.0))
    except Exception:
        return freshness


def _social_signal_score(likes: float, comments: float) -> float:
    raw_social = likes + comments * 2.0
    return min(100.0, math.log1p(raw_social) / math.log1p(500) * 100) if raw_social > 0 else 5.0


def _hook_strength_score(title: str, hook_type: str) -> float:
    title_len = len(title.strip())
    hook_score = HOOK_TYPE_SCORES.get(hook_type, 60.0)
    if 8 <= title_len <= 35:
        return min(100.0, hook_score + 8.0)
    if title_len < 4:
        return max(0.0, hook_score - 20.0)
    return hook_score


def _trend_relevance_score(topic_cluster: str, trend_boost: float) -> float:
    if topic_cluster in HIGH_TREND_TOPICS:
        trend = 85.0
    elif topic_cluster in MEDIUM_TREND_TOPICS:
        trend = 65.0
    elif topic_cluster == "기타":
        trend = 35.0
    else:
        trend = 50.0

    season_boost = get_season_boost(topic_cluster)
    if season_boost > 0:
        trend = min(100.0, trend + season_boost)
    if trend_boost > 0:
        trend = min(100.0, trend + trend_boost)
    return trend


def _audience_targeting_score(content: str, audience_fit: str) -> float:
    audience = AUDIENCE_SCORES.get(audience_fit, 50.0)
    if len(content.strip()) >= 150:
        return min(100.0, audience + 5.0)
    return audience


def _viral_potential_score(emotion_axis: str) -> float:
    return VIRAL_SCORES.get(emotion_axis, 50.0)


def _load_6d_weights() -> dict[str, float]:
    weights = dict(DEFAULT_6D_WEIGHTS)
    try:
        from pipeline.cost_db import get_cost_db

        calibrated = get_cost_db().load_calibrated_weights(max_age_days=7)
        if calibrated and all(k in calibrated for k in weights):
            return calibrated
    except Exception as exc:
        logger.debug("load_calibrated_weights failed, using defaults (non-critical): %s", exc)
    return weights


def _weighted_6d_score(dimensions: dict[str, float], weights: dict[str, float]) -> float:
    return _round_score(
        dimensions["freshness_score"] * weights["freshness"]
        + dimensions["social_signal_score"] * weights["social"]
        + dimensions["hook_strength_score"] * weights["hook"]
        + dimensions["trend_relevance_score"] * weights["trend"]
        + dimensions["audience_targeting_score"] * weights["audience"]
        + dimensions["viral_potential_score"] * weights["viral"]
    )


def _apply_source_quality_boost(rank_6d: float, source: str) -> float:
    if not source:
        return rank_6d
    source_hint = get_source_hint(source)
    quality_boost = float(source_hint.get("quality_boost", 1.0))
    return _round_score(rank_6d * quality_boost)


def calculate_6d_score(
    post_data: dict[str, Any],
    topic_cluster: str,
    hook_type: str,
    emotion_axis: str,
    audience_fit: str,
    source: str = "",
    trend_boost: float = 0.0,
) -> tuple[float, dict[str, float]]:
    """6차원 콘텐츠 품질 스코어카드 (Phase 4-B).

    Returns (rank_6d 0-100, dimensions dict).

    Dimensions & weights:
        freshness_score      15% — 게시글 신선도 (scraped_at 기반, 없으면 50점)
        social_signal_score  25% — 좋아요·댓글 소셜 신호
        hook_strength_score  20% — 제목·훅 타입 강도
        trend_relevance_score 15% — 토픽 클러스터 트렌드 적합도
        audience_targeting_score 15% — 독자 타게팅 정확도
        viral_potential_score  10% — 감정 축 바이럴 잠재력
    """
    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")
    try:
        likes = float(post_data.get("likes", 0) or 0)
    except (ValueError, TypeError):
        likes = 0.0
    try:
        comments = float(post_data.get("comments", 0) or 0)
    except (ValueError, TypeError):
        comments = 0.0
    dims = {
        "freshness_score": _round_score(_freshness_score(post_data)),
        "social_signal_score": _round_score(_social_signal_score(likes, comments)),
        "hook_strength_score": _round_score(_hook_strength_score(title, hook_type)),
        "trend_relevance_score": _round_score(_trend_relevance_score(topic_cluster, trend_boost)),
        "audience_targeting_score": _round_score(_audience_targeting_score(content, audience_fit)),
        "viral_potential_score": _round_score(_viral_potential_score(emotion_axis)),
    }
    rank_6d = _weighted_6d_score(dims, _load_6d_weights())
    rank_6d = _apply_source_quality_boost(rank_6d, source)
    return rank_6d, dims


# ── 6D 가중치 자동 보정 (Phase 3-A) ──────────────────────────────────


def _calibration_cutoff(days: int) -> str:
    from datetime import datetime, timedelta

    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def _fetch_calibration_rows(db: Any, cutoff: str) -> list[Any]:
    with db._connect() as conn:
        return conn.execute(
            """SELECT hook_score, virality_score, fit_score,
                      engagement_rate, yt_views
               FROM draft_analytics
               WHERE date >= ? AND published = 1
                 AND engagement_rate > 0""",
            (cutoff,),
        ).fetchall()


def _engagement_values(rows: list[Any]) -> list[float]:
    result = []
    for row in rows:
        try:
            result.append(float(row[3] or 0) + math.log1p(float(row[4] or 0)) * 0.1)
        except (ValueError, TypeError, IndexError):
            result.append(0.0)
    return result


def _dimension_proxies(rows: list[Any]) -> dict[str, list[float]]:
    hooks, virals, audiences = [], [], []
    for row in rows:
        try:
            hooks.append(float(row[0] or 5))
            virals.append(float(row[1] or 5))
            audiences.append(float(row[2] or 5))
        except (ValueError, TypeError, IndexError):
            pass
    return {"hook": hooks, "viral": virals, "audience": audiences}


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n == 0:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x)) or 1e-10
    sy = math.sqrt(sum((yi - my) ** 2 for yi in y)) or 1e-10
    return cov / (sx * sy)


def _calibration_correlations(rows: list[Any]) -> dict[str, float]:
    engagement_vals = _engagement_values(rows)
    dim_proxies = _dimension_proxies(rows)
    return {
        dim: max(0.05, abs(_pearson(dim_proxies[dim], engagement_vals))) if dim in dim_proxies else 0.15
        for dim in DIMENSION_KEYS
    }


def _normalize_calibration_weights(correlations: dict[str, float]) -> dict[str, float]:
    total_corr = sum(correlations.values())
    if not total_corr:
        total_corr = 1.0
    weights = {dim: max(0.05, min(0.40, correlations[dim] / total_corr)) for dim in DIMENSION_KEYS}
    weight_sum = sum(weights.values())
    return {key: round(value / weight_sum, 4) for key, value in weights.items()}


def calibrate_weights(days: int = 30, min_rows: int = 30) -> dict[str, float] | None:
    """draft_analytics의 실제 성과 데이터로 6D 가중치를 자동 보정합니다.

    engagement_rate가 있는 포스트들의 각 6D 차원과 engagement의
    상관계수를 계산하여 가중치를 재배분합니다.

    Args:
        days: 분석할 최근 일수.
        min_rows: 최소 필요 데이터 수. 미달 시 None 반환.

    Returns:
        보정된 가중치 dict. 데이터 부족 시 None.
    """
    try:
        from pipeline.cost_db import get_cost_db

        db = get_cost_db()
        rows = _fetch_calibration_rows(db, _calibration_cutoff(days))

        if len(rows) < min_rows:
            logger.debug("calibrate_weights: not enough data (%d < %d)", len(rows), min_rows)
            return None

        weights = _normalize_calibration_weights(_calibration_correlations(rows))
        db.save_calibrated_weights(weights)
        logger.info("calibrate_weights: new weights = %s (from %d rows)", weights, len(rows))
        return weights

    except Exception as exc:
        logger.debug("calibrate_weights failed: %s", exc)
        return None
