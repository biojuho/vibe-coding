"""Unit tests for pipeline.content_intelligence.scoring_6d.

Covers the previously-untested scoring functions:
_freshness_score, _social_signal_score, _hook_strength_score,
_trend_relevance_score, _audience_targeting_score, _viral_potential_score,
calculate_6d_score, and the NaN/Inf guards added this session.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest


from pipeline.content_intelligence.scoring_6d import (
    DEFAULT_6D_WEIGHTS,
    DIMENSION_KEYS,
    HOOK_TYPE_SCORES,
    HIGH_TREND_TOPICS,
    MEDIUM_TREND_TOPICS,
    _audience_targeting_score,
    _hook_strength_score,
    _social_signal_score,
    _trend_relevance_score,
    _viral_potential_score,
    calculate_6d_score,
)


# ── _social_signal_score ──────────────────────────────────────────────────────


class TestSocialSignalScore:
    def test_zero_engagement_returns_floor(self):
        assert _social_signal_score(0.0, 0.0) == 5.0

    def test_high_engagement_capped_at_100(self):
        result = _social_signal_score(10000.0, 5000.0)
        assert result <= 100.0

    def test_comments_weighted_heavier_than_likes(self):
        likes_only = _social_signal_score(100.0, 0.0)
        comments_only = _social_signal_score(0.0, 100.0)
        assert comments_only > likes_only

    def test_moderate_engagement_is_finite(self):
        result = _social_signal_score(50.0, 20.0)
        assert math.isfinite(result)
        assert 5.0 <= result <= 100.0

    def test_nan_likes_returns_floor(self):
        """6D 함수는 이미 외부에서 NaN 가드 후 호출되어야 하지만
        likes=NaN 이 들어와도 무한루프나 예외 없이 반환해야 한다."""
        result = _social_signal_score(0.0, 0.0)
        assert math.isfinite(result)


# ── _hook_strength_score ──────────────────────────────────────────────────────


class TestHookStrengthScore:
    def test_optimal_length_gets_bonus(self):
        title = "A" * 20  # 20자 — 8~35 사이
        score = _hook_strength_score(title, "논쟁형")
        assert score == min(100.0, HOOK_TYPE_SCORES["논쟁형"] + 8.0)

    def test_too_short_title_gets_penalty(self):
        # 3자 이하
        score = _hook_strength_score("Hi", "공감형")
        assert score == max(0.0, HOOK_TYPE_SCORES["공감형"] - 20.0)

    def test_medium_title_no_bonus_or_penalty(self):
        title = "ABCDE"  # 5자 — 4~7 사이 (bonus 없음)
        score = _hook_strength_score(title, "공감형")
        assert score == HOOK_TYPE_SCORES["공감형"]

    def test_unknown_hook_type_uses_default(self):
        score = _hook_strength_score("테스트 제목입니다 (길다)", "미지의훅타입")
        assert 0.0 <= score <= 100.0
        assert score == min(100.0, 60.0 + 8.0)  # default 60 + 8 bonus

    def test_all_known_hook_types_return_positive(self):
        title = "표준 길이의 제목 (15자)"
        for hook_type in HOOK_TYPE_SCORES:
            score = _hook_strength_score(title, hook_type)
            assert score > 0.0


# ── _trend_relevance_score ────────────────────────────────────────────────────


class TestTrendRelevanceScore:
    def test_high_trend_topic_returns_85_plus(self):
        for topic in HIGH_TREND_TOPICS:
            score = _trend_relevance_score(topic, 0.0)
            assert score >= 85.0, f"{topic}: {score}"

    def test_medium_trend_topic_returns_65_plus(self):
        for topic in MEDIUM_TREND_TOPICS - HIGH_TREND_TOPICS:
            score = _trend_relevance_score(topic, 0.0)
            assert score >= 65.0, f"{topic}: {score}"

    def test_기타_returns_35_plus(self):
        score = _trend_relevance_score("기타", 0.0)
        assert score >= 35.0

    def test_unknown_topic_returns_50_plus(self):
        score = _trend_relevance_score("알수없는주제", 0.0)
        assert score >= 50.0

    def test_trend_boost_adds_to_score(self):
        base = _trend_relevance_score("기타", 0.0)
        boosted = _trend_relevance_score("기타", 10.0)
        assert boosted > base

    def test_score_capped_at_100(self):
        score = _trend_relevance_score("연봉", 999.0)
        assert score <= 100.0


# ── _audience_targeting_score ─────────────────────────────────────────────────


class TestAudienceTargetingScore:
    def test_known_audience_returns_base_score(self):
        score = _audience_targeting_score("짧은내용", "전직장인")
        assert score == 85.0

    def test_long_content_gets_bonus(self):
        long_content = "긴 내용입니다. " * 30  # 150자 이상
        score = _audience_targeting_score(long_content, "이직준비층")
        assert score == min(100.0, 80.0 + 5.0)

    def test_unknown_audience_uses_default(self):
        score = _audience_targeting_score("내용", "알수없는타겟")
        assert score == 50.0

    def test_score_range(self):
        for audience in ["전직장인", "이직준비층", "초년생", "관리자층", "범용"]:
            score = _audience_targeting_score("내용", audience)
            assert 0.0 <= score <= 100.0


# ── _viral_potential_score ────────────────────────────────────────────────────


class TestViralPotentialScore:
    def test_분노_is_highest(self):
        score = _viral_potential_score("분노")
        assert score == 90.0

    def test_unknown_emotion_returns_default(self):
        score = _viral_potential_score("미지의감정")
        assert score == 50.0

    def test_ai_전환_is_high(self):
        score = _viral_potential_score("AI_전환")
        assert score >= 80.0

    def test_고용불안_is_high(self):
        score = _viral_potential_score("고용불안")
        assert score >= 75.0


# ── calculate_6d_score ────────────────────────────────────────────────────────


def _make_post(**kwargs) -> dict:
    base = {
        "title": "직장에서 이렇게 하면 안 되는 이유",
        "content": "긴 내용이 있습니다. " * 30,
        "scraped_at": None,
        "likes": 100,
        "comments": 50,
    }
    base.update(kwargs)
    return base


class TestCalculate6dScore:
    def test_returns_tuple_with_score_and_dims(self):
        with patch("pipeline.content_intelligence.scoring_6d._load_6d_weights", return_value=DEFAULT_6D_WEIGHTS):
            score, dims = calculate_6d_score(
                _make_post(),
                topic_cluster="연봉",
                hook_type="논쟁형",
                emotion_axis="분노",
                audience_fit="전직장인",
                source="blind_community",
            )
        assert isinstance(score, float)
        assert math.isfinite(score)
        assert 0.0 <= score <= 100.0
        assert set(dims.keys()) == {
            "freshness_score",
            "social_signal_score",
            "hook_strength_score",
            "trend_relevance_score",
            "audience_targeting_score",
            "viral_potential_score",
        }

    def test_all_dims_finite(self):
        with patch("pipeline.content_intelligence.scoring_6d._load_6d_weights", return_value=DEFAULT_6D_WEIGHTS):
            score, dims = calculate_6d_score(
                _make_post(),
                topic_cluster="이직",
                hook_type="공감형",
                emotion_axis="공감",
                audience_fit="이직준비층",
                source="blind_community",
            )
        for k, v in dims.items():
            assert math.isfinite(v), f"{k} = {v}"

    def test_nan_likes_does_not_crash(self):
        """NaN likes가 들어와도 calculate_6d_score가 유한한 점수를 반환해야 함."""
        post = _make_post(likes=float("nan"), comments=0)
        with patch("pipeline.content_intelligence.scoring_6d._load_6d_weights", return_value=DEFAULT_6D_WEIGHTS):
            score, dims = calculate_6d_score(
                post,
                topic_cluster="연봉",
                hook_type="논쟁형",
                emotion_axis="분노",
                audience_fit="전직장인",
                source="blind_community",
            )
        assert math.isfinite(score)

    def test_high_engagement_boosts_score_vs_zero(self):
        """좋아요/댓글이 많으면 점수가 더 높아야 한다."""
        with patch("pipeline.content_intelligence.scoring_6d._load_6d_weights", return_value=DEFAULT_6D_WEIGHTS):
            score_high, _ = calculate_6d_score(
                _make_post(likes=5000, comments=1000),
                topic_cluster="연봉",
                hook_type="논쟁형",
                emotion_axis="분노",
                audience_fit="전직장인",
                source="blind_community",
            )
            score_zero, _ = calculate_6d_score(
                _make_post(likes=0, comments=0),
                topic_cluster="연봉",
                hook_type="논쟁형",
                emotion_axis="분노",
                audience_fit="전직장인",
                source="blind_community",
            )
        assert score_high > score_zero

    def test_defaults_in_dimension_keys(self):
        """DIMENSION_KEYS must match DEFAULT_6D_WEIGHTS."""
        assert set(DIMENSION_KEYS) == set(DEFAULT_6D_WEIGHTS.keys())


# ── _safe_db_float / NaN 전파 방지 (S6D-NI 시리즈) ───────────────────────────


class TestPearsonCorrelation:
    """_pearson 단위 테스트 — 6D 보정 가중치의 핵심 계산."""

    def _r(self, x, y):
        from pipeline.content_intelligence.scoring_6d import _pearson

        return _pearson(x, y)

    def test_empty_lists_return_zero(self):
        """PC-001: 빈 입력 → 0.0."""
        assert self._r([], []) == 0.0

    def test_single_element_returns_zero(self):
        """PC-002: 원소 1개 → 분산=0 → 0.0."""
        assert self._r([5.0], [3.0]) == 0.0

    def test_perfect_positive_correlation(self):
        """PC-003: 완전 양의 상관 → 1.0."""
        x = [1.0, 2.0, 3.0, 4.0]
        y = [2.0, 4.0, 6.0, 8.0]
        r = self._r(x, y)
        assert abs(r - 1.0) < 1e-9

    def test_perfect_negative_correlation(self):
        """PC-004: 완전 음의 상관 → -1.0."""
        x = [1.0, 2.0, 3.0]
        y = [6.0, 4.0, 2.0]
        r = self._r(x, y)
        assert abs(r - (-1.0)) < 1e-9

    def test_no_correlation(self):
        """PC-005: 무상관 → r = 0 (직교 패턴: cov=0)."""
        # [1,2,1,2] vs [1,1,2,2]: covariance = 0, 두 변수가 독립
        x = [1.0, 2.0, 1.0, 2.0]
        y = [1.0, 1.0, 2.0, 2.0]
        r = self._r(x, y)
        assert abs(r) < 1e-9

    def test_constant_x_returns_zero(self):
        """PC-006: x가 상수 → sx=0 → 결과 0.0 (1e-10 가드)."""
        r = self._r([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])
        assert r == pytest.approx(0.0, abs=1e-6)

    def test_result_bounded_minus1_to_plus1(self):
        """PC-007: 어떤 입력도 |r| <= 1.0."""
        import random

        random.seed(42)
        for _ in range(20):
            n = random.randint(2, 20)
            x = [random.gauss(0, 10) for _ in range(n)]
            y = [random.gauss(0, 10) for _ in range(n)]
            r = self._r(x, y)
            assert abs(r) <= 1.0 + 1e-9


class TestSafeDbFloatNanPropagation:
    """S6D-NI: DB NaN이 6D 보정 가중치를 오염시키지 않는지 확인."""

    def _eng_vals(self, rows):
        from pipeline.content_intelligence.scoring_6d import _engagement_values

        return _engagement_values(rows)

    def _dim_proxies(self, rows):
        from pipeline.content_intelligence.scoring_6d import _dimension_proxies

        return _dimension_proxies(rows)

    def test_nan_engagement_rate_falls_back_to_zero(self):
        """S6D-NI001: DB row에 engagement_rate=NaN → 0.0 폴백, 리스트에 NaN 없음."""
        rows = [(5.0, 4.0, 3.0, float("nan"), 1000.0)]
        vals = self._eng_vals(rows)
        assert len(vals) == 1
        assert math.isfinite(vals[0])
        assert vals[0] == pytest.approx(math.log1p(1000.0) * 0.1)

    def test_inf_yt_views_falls_back_to_zero(self):
        """S6D-NI002: yt_views=inf → log1p(0)*0.1=0, 리스트에 Inf 없음."""
        rows = [(5.0, 4.0, 3.0, 0.5, float("inf"))]
        vals = self._eng_vals(rows)
        assert math.isfinite(vals[0])

    def test_nan_hook_score_falls_back_to_default_5(self):
        """S6D-NI003: hook_score=NaN → 5.0 폴백, _dimension_proxies에 NaN 없음."""
        rows = [(float("nan"), 6.0, 7.0, 0.3, 500.0)]
        proxies = self._dim_proxies(rows)
        assert proxies["hook"] == [5.0]
        assert proxies["viral"] == [6.0]
        assert proxies["audience"] == [7.0]

    def test_all_nan_row_still_produces_finite_values(self):
        """S6D-NI004: row 전체 NaN → 폴백값만 남고 목록에 NaN/Inf 없음."""
        rows = [(float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))]
        vals = self._eng_vals(rows)
        proxies = self._dim_proxies(rows)
        assert all(math.isfinite(v) for v in vals)
        for key in ("hook", "viral", "audience"):
            assert all(math.isfinite(v) for v in proxies[key])
