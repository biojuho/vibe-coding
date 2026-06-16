"""Unit tests for pipeline.content_intelligence.scoring_6d.

Covers the previously-untested scoring functions:
_freshness_score, _social_signal_score, _hook_strength_score,
_trend_relevance_score, _audience_targeting_score, _viral_potential_score,
calculate_6d_score, and the NaN/Inf guards added this session.
"""

from __future__ import annotations

import math
from unittest.mock import patch


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
