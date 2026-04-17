"""Deterministic scoring and classification for Blind content."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any

logger = logging.getLogger(__name__)


from pipeline.content_intelligence.rules import get_season_boost, get_source_hint
from pipeline.content_intelligence.utils import _round_score

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
    import time

    title = str(post_data.get("title", "") or "")
    content = str(post_data.get("content", "") or "")
    likes = float(post_data.get("likes", 0) or 0)
    comments = float(post_data.get("comments", 0) or 0)

    # ── Freshness (15%) ─────────────────────────────────────────────
    freshness = 50.0  # default when no timestamp
    scraped_at = post_data.get("scraped_at") or post_data.get("created_at")
    if scraped_at:
        try:
            import datetime as _dt

            if isinstance(scraped_at, (int, float)):
                age_hours = (time.time() - scraped_at) / 3600
            else:
                ts = _dt.datetime.fromisoformat(str(scraped_at))
                age_hours = (_dt.datetime.now() - ts.replace(tzinfo=None)).total_seconds() / 3600
            # 0h→100, 6h→80, 24h→50, 72h→20, 168h+→5
            freshness = max(5.0, 100.0 * math.exp(-age_hours / 24.0))
        except Exception:
            pass

    # ── Social Signal (25%) ─────────────────────────────────────────
    raw_social = likes + comments * 2.0
    social = min(100.0, math.log1p(raw_social) / math.log1p(500) * 100) if raw_social > 0 else 5.0

    # ── Hook Strength (20%) ─────────────────────────────────────────
    title_len = len(title.strip())
    hook_base = {
        "논쟁형": 90.0,
        "공감형": 75.0,
        "정보형": 70.0,
        "한줄팩폭형": 85.0,
        "짤형": 65.0,
        "분석형": 88.0,
        "통찰형": 82.0,
    }.get(hook_type, 60.0)
    # title 길이 보너스 (8-35자 최적)
    if 8 <= title_len <= 35:
        hook_base = min(100.0, hook_base + 8.0)
    elif title_len < 4:
        hook_base = max(0.0, hook_base - 20.0)

    # ── Trend Relevance (15%) ───────────────────────────────────────
    # 고인기 토픽에 가중치 + 시즌 부스트 (P0-A2)
    _HIGH_TREND = {"연봉", "이직", "회사문화", "상사"}
    _MED_TREND = {"복지", "재테크", "직장개그", "부동산", "IT"}
    if topic_cluster in _HIGH_TREND:
        trend = 85.0
    elif topic_cluster in _MED_TREND:
        trend = 65.0
    elif topic_cluster == "기타":
        trend = 35.0
    else:
        trend = 50.0
    # 시즌 부스트 추가 (최대 15점)
    season_boost = get_season_boost(topic_cluster)
    if season_boost > 0:
        trend = min(100.0, trend + season_boost)
    # 실시간 트렌드 부스트 (trend_monitor.py에서 전달, 최대 30점)
    if trend_boost > 0:
        trend = min(100.0, trend + trend_boost)

    # ── Audience Targeting (15%) ────────────────────────────────────
    audience_scores = {
        "전직장인": 85.0,
        "이직준비층": 80.0,
        "초년생": 70.0,
        "관리자층": 60.0,
        "범용": 50.0,
    }
    audience = audience_scores.get(audience_fit, 50.0)
    # content 길이 보너스 (충분한 컨텍스트 = 타게팅 가능)
    if len(content.strip()) >= 150:
        audience = min(100.0, audience + 5.0)

    # ── Viral Potential (10%) ───────────────────────────────────────
    viral_scores = {
        "분노": 90.0,
        "경악": 85.0,
        "웃김": 80.0,
        "현타": 75.0,
        "허탈": 70.0,
        "공감": 65.0,
        "통찰": 55.0,
    }
    viral = viral_scores.get(emotion_axis, 50.0)

    # ── Weighted sum (보정 가중치 우선 사용) ──────────────────────────
    weights = {
        "freshness": 0.15,
        "social": 0.25,
        "hook": 0.20,
        "trend": 0.15,
        "audience": 0.15,
        "viral": 0.10,
    }
    try:
        from pipeline.cost_db import get_cost_db

        calibrated = get_cost_db().load_calibrated_weights(max_age_days=7)
        if calibrated and all(k in calibrated for k in weights):
            weights = calibrated
    except Exception:
        pass
    rank_6d = _round_score(
        freshness * weights["freshness"]
        + social * weights["social"]
        + hook_base * weights["hook"]
        + trend * weights["trend"]
        + audience * weights["audience"]
        + viral * weights["viral"]
    )

    # ── Source Quality Boost (P3 통합) ───────────────────────────────
    if source:
        source_hint = get_source_hint(source)
        quality_boost = float(source_hint.get("quality_boost", 1.0))
        rank_6d = _round_score(rank_6d * quality_boost)

    dims = {
        "freshness_score": _round_score(freshness),
        "social_signal_score": _round_score(social),
        "hook_strength_score": _round_score(hook_base),
        "trend_relevance_score": _round_score(trend),
        "audience_targeting_score": _round_score(audience),
        "viral_potential_score": _round_score(viral),
    }
    return rank_6d, dims
# ── 6D 가중치 자동 보정 (Phase 3-A) ──────────────────────────────────


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

        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        with db._connect() as conn:
            rows = conn.execute(
                """SELECT hook_score, virality_score, fit_score,
                          engagement_rate, yt_views
                   FROM draft_analytics
                   WHERE date >= ? AND published = 1
                     AND engagement_rate > 0""",
                (cutoff,),
            ).fetchall()

        if len(rows) < min_rows:
            logger.debug("calibrate_weights: not enough data (%d < %d)", len(rows), min_rows)
            return None

        # 간단한 Pearson 상관계수 계산 (numpy 없이)
        n = len(rows)
        engagement_vals = [r[3] + math.log1p(r[4]) * 0.1 for r in rows]  # combined metric

        # 6D 차원별 proxy 값 (현재 저장된 점수 활용)
        dim_names = ["freshness", "social", "hook", "trend", "audience", "viral"]
        # hook_score → hook, virality_score → viral, fit_score → audience
        # freshness/social/trend는 직접 저장 안 되므로 proxy 사용
        dim_proxies = {
            "hook": [float(r[0] or 5) for r in rows],
            "viral": [float(r[1] or 5) for r in rows],
            "audience": [float(r[2] or 5) for r in rows],
        }

        def _pearson(x: list[float], y: list[float]) -> float:
            mx = sum(x) / n
            my = sum(y) / n
            cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
            sx = math.sqrt(sum((xi - mx) ** 2 for xi in x)) or 1e-10
            sy = math.sqrt(sum((yi - my) ** 2 for yi in y)) or 1e-10
            return cov / (sx * sy)

        correlations = {}
        for dim in dim_names:
            if dim in dim_proxies:
                correlations[dim] = max(0.05, abs(_pearson(dim_proxies[dim], engagement_vals)))
            else:
                correlations[dim] = 0.15  # proxy 없는 차원은 기본값

        # 상관계수 비례로 가중치 재배분 (합=1.0, 각 0.05~0.40)
        total_corr = sum(correlations.values())
        weights = {}
        for dim in dim_names:
            raw = correlations[dim] / total_corr
            weights[dim] = max(0.05, min(0.40, raw))

        # 합 정규화
        w_sum = sum(weights.values())
        weights = {k: round(_v / w_sum, 4) for k, _v in weights.items()}

        # 저장
        db.save_calibrated_weights(weights)
        logger.info("calibrate_weights: new weights = %s (from %d rows)", weights, n)
        return weights

    except Exception as exc:
        logger.debug("calibrate_weights failed: %s", exc)
        return None
