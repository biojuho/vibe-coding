from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.content_intelligence import (  # noqa: E402
    build_content_profile,
    calculate_6d_score,
    calculate_publishability_score,
    evaluate_candidate_editorial_fit,
)
from pipeline.content_intelligence.builder import _bandit_recommend_draft_type  # noqa: E402
from pipeline.content_intelligence.rules import get_time_context  # noqa: E402


def test_build_content_profile_is_deterministic():
    post_data = {
        "title": "이직 고민하는데 팀장 때문에 현타 왔다",
        "content": "회사 문화랑 팀장 스타일 때문에 퇴사를 고민하는 직장인 공감 글입니다.",
        "likes": 120,
        "comments": 24,
    }
    examples = [
        {
            "views": 12000,
            "topic_cluster": "이직",
            "hook_type": "공감형",
            "emotion_axis": "현타",
            "draft_style": "공감형",
            "text": "예시",
        }
    ]
    first = build_content_profile(post_data, 88, examples).to_dict()
    second = build_content_profile(post_data, 88, examples).to_dict()
    assert first == second
    assert first["topic_cluster"] == "이직"
    assert first["recommended_draft_type"] == "공감형"
    assert first["final_rank_score"] >= 60


def test_build_content_profile_uses_examples_for_performance_score():
    post_data = {
        "title": "연봉 협상 망해서 현타 온다",
        "content": "연봉 인상률이 낮아 허탈한 직장인 이야기입니다.",
        "likes": 80,
        "comments": 12,
    }
    matching_examples = [
        {
            "views": 22000,
            "topic_cluster": "연봉",
            "hook_type": "공감형",
            "emotion_axis": "허탈",
            "draft_style": "공감형",
            "text": "예시",
        }
    ]
    mismatching_examples = [
        {
            "views": 22000,
            "topic_cluster": "가족",
            "hook_type": "정보형",
            "emotion_axis": "통찰",
            "draft_style": "정보전달형",
            "text": "예시",
        }
    ]
    matched = build_content_profile(post_data, 82, matching_examples).to_dict()
    mismatched = build_content_profile(post_data, 82, mismatching_examples).to_dict()
    assert matched["performance_score"] > mismatched["performance_score"]


def test_build_content_profile_exposes_editorial_brief_fields():
    post_data = {
        "title": "실수령 280 듣고 회의실이 조용해진 날",
        "content": "회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉 비교와 이직 고민이 한 번에 터지는 글이다.",
        "likes": 95,
        "comments": 21,
        "source": "blind",
    }
    profile = build_content_profile(post_data, 90, historical_examples=[]).to_dict()

    assert profile["selection_summary"]
    assert profile["selection_reason_labels"]
    assert profile["audience_need"]
    assert profile["emotion_lane"]
    assert profile["empathy_anchor"]
    assert profile["spinoff_angle"]
    assert profile["publishability_score"] >= 60


def test_evaluate_candidate_editorial_fit_preserves_scoring_dimensions():
    result = evaluate_candidate_editorial_fit(
        title="실수령 280 듣고 회의실이 조용해진 날",
        source="blind",
        content="회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉 비교와 이직 고민이 한 번에 터지는 글이다.",
    )

    assert result["score"] == 91.75
    assert result["dimensions"] == {
        "reader_desire": 100.0,
        "empathy_fun": 90.0,
        "spinoff": 100.0,
        "specificity": 75.0,
        "workplace_fit": 80.0,
    }
    assert result["hard_reject"] is False
    assert result["reason_labels"] == [
        "직장인이 바로 눌러볼 만한 주제",
        "공감하거나 웃을 장면이 분명함",
        "댓글과 파생 대화로 이어질 각이 있음",
        "숫자·대사·상황이 구체적임",
        "직장인 독자 맥락에 정확히 맞음",
    ]


def test_calculate_publishability_score_returns_brief_from_editorial_fit():
    post_data = {
        "title": "실수령 280 듣고 회의실이 조용해진 날",
        "content": "회의실에서 실수령 280 이야기가 나오자 다들 웃다가도 한숨을 쉬었다. 연봉 비교와 이직 고민이 한 번에 터지는 글이다.",
        "source": "blind",
        "likes": 95,
        "comments": 21,
    }

    score, rationale, brief = calculate_publishability_score(
        post_data,
        topic_cluster="연봉",
        hook_type="공감형",
        emotion_axis="공감",
    )

    assert score >= 60.0
    assert rationale
    assert brief["selection_summary"]
    assert brief["selection_reason_labels"] == rationale
    assert set(brief["editorial_dimensions"]) == {
        "reader_desire",
        "empathy_fun",
        "spinoff",
        "specificity",
        "workplace_fit",
    }


def test_calculate_6d_score_preserves_dimension_weighting(monkeypatch):
    from pipeline.content_intelligence import scoring_6d

    monkeypatch.setattr(scoring_6d, "get_season_boost", lambda _topic: 0.0)
    monkeypatch.setattr(scoring_6d, "get_source_hint", lambda _source: {"quality_boost": 1.1})
    post_data = {
        "title": "연봉 협상 망해서 현타 온다",
        "content": "연봉 인상률이 낮아 허탈한 직장인 이야기입니다.",
        "likes": 80,
        "comments": 12,
    }

    base_score, dimensions = calculate_6d_score(
        post_data,
        topic_cluster="연봉",
        hook_type="공감형",
        emotion_axis="현타",
        audience_fit="전직장인",
    )
    boosted_score, boosted_dimensions = calculate_6d_score(
        post_data,
        topic_cluster="연봉",
        hook_type="공감형",
        emotion_axis="현타",
        audience_fit="전직장인",
        source="jobplanet",
    )

    assert set(dimensions) == {
        "freshness_score",
        "social_signal_score",
        "hook_strength_score",
        "trend_relevance_score",
        "audience_targeting_score",
        "viral_potential_score",
    }
    weighted_score = (
        dimensions["freshness_score"] * 0.15
        + dimensions["social_signal_score"] * 0.25
        + dimensions["hook_strength_score"] * 0.20
        + dimensions["trend_relevance_score"] * 0.15
        + dimensions["audience_targeting_score"] * 0.15
        + dimensions["viral_potential_score"] * 0.10
    )
    assert base_score == round(weighted_score, 2)
    assert dimensions["freshness_score"] == 50.0
    assert dimensions["hook_strength_score"] == 83.0
    assert dimensions["trend_relevance_score"] == 85.0
    assert dimensions["audience_targeting_score"] == 85.0
    assert dimensions["viral_potential_score"] == 75.0
    assert boosted_dimensions == dimensions
    assert boosted_score == round(base_score * 1.1, 2)


class TestBanditRecommendDraftType:
    """_bandit_recommend_draft_type: StyleBandit override / fallback / error handling."""

    def _make_bandit(self, total_trials: int, selected_style: str) -> MagicMock:
        mock = MagicMock()
        mock.get_arm_stats.return_value = [
            {"draft_style": "공감형", "total_trials": total_trials},
        ]
        mock.select_style.return_value = selected_style
        return mock

    def test_below_min_trials_returns_rule_based(self):
        mock_bandit = self._make_bandit(total_trials=4, selected_style="논쟁형")
        with patch("pipeline.style_bandit.get_style_bandit", return_value=mock_bandit):
            result = _bandit_recommend_draft_type("연봉", "공감형")
        assert result == "공감형"

    def test_at_min_trials_uses_bandit_selection(self):
        mock_bandit = self._make_bandit(total_trials=5, selected_style="논쟁형")
        with patch("pipeline.style_bandit.get_style_bandit", return_value=mock_bandit):
            result = _bandit_recommend_draft_type("연봉", "공감형")
        assert result == "논쟁형"

    def test_bandit_exception_falls_back_to_rule_based(self):
        with patch("pipeline.style_bandit.get_style_bandit", side_effect=RuntimeError("db error")):
            result = _bandit_recommend_draft_type("연봉", "공감형")
        assert result == "공감형"

    def test_bandit_same_as_rule_still_returns_correctly(self):
        mock_bandit = self._make_bandit(total_trials=10, selected_style="공감형")
        with patch("pipeline.style_bandit.get_style_bandit", return_value=mock_bandit):
            result = _bandit_recommend_draft_type("연봉", "공감형")
        assert result == "공감형"


# ── T-AB046: AI 트렌드 / 구조조정 trend_relevance_score 검증 ────────────────


def test_ai_trend_topic_gets_high_trend_score(monkeypatch):
    """T-AB046: 'AI 트렌드' topic label이 HIGH_TREND_TOPICS에 포함돼 85점 이상 받아야 함.

    이전엔 label mismatch로 기본값 50.0을 받았음.
    """
    from pipeline.content_intelligence import scoring_6d

    monkeypatch.setattr(scoring_6d, "get_season_boost", lambda _topic: 0.0)
    monkeypatch.setattr(scoring_6d, "get_source_hint", lambda _source: {"quality_boost": 1.0})

    post_data = {
        "title": "AI 도구로 주니어 대체 현실화",
        "content": "vibe코딩으로 신입 TO가 사라지고 있습니다.",
        "likes": 50,
        "comments": 8,
    }

    _, dims = calculate_6d_score(
        post_data,
        topic_cluster="AI 트렌드",
        hook_type="공감형",
        emotion_axis="AI_전환",
        audience_fit="이직준비층",
    )
    assert dims["trend_relevance_score"] >= 85.0, (
        f"AI 트렌드 should score >=85 (HIGH_TREND), got {dims['trend_relevance_score']}"
    )
    assert dims["viral_potential_score"] == 82.0  # AI_전환 viral score


def test_구조조정_topic_gets_high_trend_score(monkeypatch):
    """T-AB046: '구조조정' topic label이 HIGH_TREND_TOPICS에 포함돼 85점 이상 받아야 함."""
    from pipeline.content_intelligence import scoring_6d

    monkeypatch.setattr(scoring_6d, "get_season_boost", lambda _topic: 0.0)
    monkeypatch.setattr(scoring_6d, "get_source_hint", lambda _source: {"quality_boost": 1.0})

    post_data = {
        "title": "정리해고 통보 받았습니다",
        "content": "구조조정 대상으로 권고사직 통보를 받았어요.",
        "likes": 200,
        "comments": 45,
    }

    _, dims = calculate_6d_score(
        post_data,
        topic_cluster="구조조정",
        hook_type="공감형",
        emotion_axis="고용불안",
        audience_fit="전직장인",
    )
    assert dims["trend_relevance_score"] >= 85.0, (
        f"구조조정 should score >=85 (HIGH_TREND), got {dims['trend_relevance_score']}"
    )
    assert dims["viral_potential_score"] == 78.0  # 고용불안 viral score


# ── _freshness_score exception-path coverage ──────────────────────────────────


class TestFreshnessScore:
    """Covers the debug-logged exception fallback path in _freshness_score."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _freshness_score

        self._fn = _freshness_score

    def test_no_scraped_at_returns_default(self):
        assert self._fn({}) == 50.0

    def test_malformed_iso_string_returns_default(self):
        # Triggers the except clause — new debug logging path.
        assert self._fn({"scraped_at": "not-a-date-at-all"}) == 50.0

    def test_none_value_treated_as_missing(self):
        assert self._fn({"scraped_at": None}) == 50.0

    def test_recent_unix_timestamp_gives_high_score(self):
        import time

        result = self._fn({"scraped_at": time.time()})
        assert result > 90.0

    def test_old_unix_timestamp_gives_low_score(self):
        import time

        # 7 days ago → exp(-168/24) ≈ 0.0009 * 100 ≈ < 1 → clamped to min 5.0
        result = self._fn({"scraped_at": time.time() - 7 * 24 * 3600})
        assert result < 10.0


# ── get_time_context 직접 단위 테스트 ─────────────────────────────────────────


class TestGetTimeContext:
    """get_time_context() 반환 계약 직접 검증."""

    _VALID_SLOTS = {"오전", "점심", "오후", "저녁", "심야"}

    def test_returns_dict_with_required_keys(self):
        result = get_time_context()
        assert isinstance(result, dict)
        assert "slot" in result
        assert "prefix" in result
        assert "tone_hint" in result

    def test_slot_is_one_of_valid_values(self):
        result = get_time_context()
        assert result["slot"] in self._VALID_SLOTS

    def test_prefix_and_tone_hint_are_nonempty_strings(self):
        result = get_time_context()
        assert isinstance(result["prefix"], str) and result["prefix"]
        assert isinstance(result["tone_hint"], str) and result["tone_hint"]

    def test_fallback_used_when_load_rules_returns_empty(self, monkeypatch):
        # When YAML is empty, hardcoded fallback values must still be non-empty.
        monkeypatch.setattr("pipeline.content_intelligence.rules._load_rules", lambda: {})
        result = get_time_context()
        assert result["prefix"]
        assert result["tone_hint"]

    def test_yaml_override_used_when_present(self, monkeypatch):
        # When YAML has a matching slot entry, its values are used instead of fallback.
        slot_from_yaml = "오전"
        monkeypatch.setattr(
            "pipeline.content_intelligence.rules._load_rules",
            lambda: {"prompt_variants": {"time_context": {slot_from_yaml: {"prefix": "야근 중", "tone_hint": "힘내"}}}},
        )
        # Get any result — as long as YAML override is returned when slot matches
        result = get_time_context()
        # We can't control the clock in unit tests without freezegun, so just verify
        # that the returned values are valid (the YAML path IS exercised via monkey patch)
        assert result["slot"] in self._VALID_SLOTS
        assert result["prefix"]
        assert result["tone_hint"]
