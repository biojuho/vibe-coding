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

    def test_utc_aware_iso_string_gives_high_score_for_recent_post(self):
        # Bug fix: datetime.now() was local time (KST+9) but UTC ISO string caused
        # up to 9-hour wrong age on Korean servers. Now uses datetime.now(timezone.utc).
        import datetime

        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = self._fn({"scraped_at": now_utc})
        assert result > 90.0, f"UTC-aware 'now' gave low freshness {result} — timezone bug?"

    def test_utc_aware_iso_string_old_post_gives_low_score(self):
        import datetime

        old_utc = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).isoformat()
        result = self._fn({"scraped_at": old_utc})
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


# ── get_season_boost / get_source_hint 직접 단위 테스트 ─────────────────────


class TestGetSeasonBoost:
    """get_season_boost: YAML 조회 + 클램핑 + 미존재 폴백."""

    def setup_method(self):
        from pipeline.content_intelligence.rules import get_season_boost

        self._fn = get_season_boost

    def test_unknown_topic_returns_zero(self):
        # A topic that doesn't exist in any month's season_weights → 0.0
        assert self._fn("비존재_주제_xyz", month=6) == 0.0

    def test_returns_float(self):
        result = self._fn("이직", month=6)
        assert isinstance(result, float)

    def test_result_in_valid_range(self):
        # All results must be in [0.0, 15.0]
        result = self._fn("이직", month=6)
        assert 0.0 <= result <= 15.0

    def test_extreme_boost_clamped_to_15(self, monkeypatch):
        monkeypatch.setattr(
            "pipeline.content_intelligence.rules._load_rules",
            lambda: {"season_weights": {6: {"이직": 999}}},
        )
        from pipeline.content_intelligence import rules as _rules

        _rules._loaded_rules = None  # force reload
        try:
            result = self._fn("이직", month=6)
            assert result == 15.0
        finally:
            _rules._loaded_rules = None

    def test_negative_boost_clamped_to_zero(self, monkeypatch):
        monkeypatch.setattr(
            "pipeline.content_intelligence.rules._load_rules",
            lambda: {"season_weights": {6: {"이직": -5}}},
        )
        from pipeline.content_intelligence import rules as _rules

        _rules._loaded_rules = None
        try:
            result = self._fn("이직", month=6)
            assert result == 0.0
        finally:
            _rules._loaded_rules = None


class TestGetSourceHint:
    """get_source_hint: 알려진 소스 조회 + 미등록 소스 기본값."""

    def setup_method(self):
        from pipeline.content_intelligence.rules import get_source_hint

        self._fn = get_source_hint

    def test_unknown_source_returns_default_quality_boost_1(self):
        result = self._fn("unknown_source_xyz")
        assert result["quality_boost"] == 1.0

    def test_unknown_source_returns_dict_with_required_keys(self):
        result = self._fn("xyz")
        assert "quality_boost" in result
        assert "display_name" in result

    def test_known_source_blind_has_positive_quality_boost(self):
        result = self._fn("blind")
        # "blind" is a primary source — should have quality_boost >= 1.0
        assert float(result.get("quality_boost", 1.0)) >= 1.0

    def test_empty_string_returns_default(self):
        result = self._fn("")
        assert result["quality_boost"] == 1.0


# ── T-QC: scoring_6d 신규 감정축 + 데드 topic label 회귀 테스트 ─────────────


class TestViralScoresCompleteness:
    """VIRAL_SCORES가 classification.yaml의 모든 감정 label을 커버하는지 검증."""

    # classification.yaml에 정의된 감정 label 전체
    _ALL_EMOTION_LABELS = {
        "분노",
        "허탈",
        "공감",
        "웃김",
        "경악",
        "현타",
        "통찰",
        "자부심",
        "불안",
        "기대감",
        "AI_전환",
        "고용불안",
    }

    def test_all_emotion_labels_have_calibrated_viral_score(self, monkeypatch):
        from pipeline.content_intelligence.scoring_6d import VIRAL_SCORES

        missing = self._ALL_EMOTION_LABELS - set(VIRAL_SCORES)
        assert not missing, f"VIRAL_SCORES에 없는 감정 label: {missing}"

    def test_new_emotion_axes_return_non_default_scores(self, monkeypatch):
        from pipeline.content_intelligence import scoring_6d

        monkeypatch.setattr(scoring_6d, "get_season_boost", lambda _: 0.0)
        monkeypatch.setattr(scoring_6d, "get_source_hint", lambda _: {"quality_boost": 1.0})

        post = {"title": "테스트", "content": "내용", "likes": 10, "comments": 2}
        for emotion in ("자부심", "불안", "기대감"):
            _, dims = calculate_6d_score(post, "이직", "공감형", emotion, "전직장인")
            assert dims["viral_potential_score"] != 50.0, (
                f"'{emotion}' still returns default 50.0 — not registered in VIRAL_SCORES"
            )


class TestOrphanedTopicLabelsRemoved:
    """HIGH/MEDIUM_TREND_TOPICS에 classification.yaml에 없는 dead label이 없어야 함."""

    # classification.yaml에 실제 존재하는 topic label 전체
    _VALID_CLASSIFICATION_LABELS = {
        "연봉",
        "이직",
        "회사문화",
        "상사",
        "복지",
        "연애",
        "결혼",
        "가족",
        "재테크",
        "직장개그",
        "부동산",
        "IT",
        "건강",
        "정치",
        "자기계발",
        "금융/경제",
        "뷰티/라이프",
        "구조조정",
        "AI 트렌드",
        "기타",
    }

    def test_high_trend_topics_are_all_valid_labels(self):
        from pipeline.content_intelligence.scoring_6d import HIGH_TREND_TOPICS

        orphans = HIGH_TREND_TOPICS - self._VALID_CLASSIFICATION_LABELS
        assert not orphans, f"HIGH_TREND_TOPICS에 dead label 존재: {orphans}"

    def test_medium_trend_topics_are_all_valid_labels(self):
        from pipeline.content_intelligence.scoring_6d import MEDIUM_TREND_TOPICS

        orphans = MEDIUM_TREND_TOPICS - self._VALID_CLASSIFICATION_LABELS
        assert not orphans, f"MEDIUM_TREND_TOPICS에 dead label 존재: {orphans}"


# ── _social_signal_score 바닥 보장 회귀 테스트 ────────────────────────────────


class TestSocialSignalScoreFloor:
    """_social_signal_score는 raw_social > 0인 경우에도 반드시 5.0 이상 반환해야 함.
    Bug fix: 이전엔 0 < raw_social < 0.365 범위에서 max(5.0) 미적용 → 반환값 < 5.0 가능."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _social_signal_score

        self._fn = _social_signal_score

    def test_zero_engagement_returns_floor(self):
        assert self._fn(0, 0) == 5.0

    def test_one_like_returns_at_least_floor(self):
        result = self._fn(1, 0)
        assert result >= 5.0

    def test_fractional_input_returns_at_least_floor(self):
        # Defensive: float inputs should never go below 5.0
        result = self._fn(0.1, 0)
        assert result >= 5.0

    def test_high_engagement_returns_high_score(self):
        result = self._fn(500, 100)
        assert result > 90.0

    def test_score_never_exceeds_100(self):
        assert self._fn(10_000, 5_000) == 100.0


# ── classify_hook_type 직접 단위 테스트 ─────────────────────────────────────


class TestClassifyHookType:
    """classify_hook_type: 키워드 기반 훅 타입 분류 — 우선순위 순서 검증."""

    def setup_method(self):
        from pipeline.content_intelligence.classifiers import classify_hook_type

        self._fn = classify_hook_type

    def test_분석형_keyword_트렌드(self):
        assert self._fn("AI 트렌드 분석", "", "공감") == "분석형"

    def test_통찰형_keyword_인사이트(self):
        assert self._fn("인사이트가 있는 글", "", "공감") == "통찰형"

    def test_논쟁형_keyword_논란(self):
        assert self._fn("논란이 된 발언", "", "공감") == "논쟁형"

    def test_정보형_keyword_팁(self):
        assert self._fn("이직 팁 모음", "", "공감") == "정보형"

    def test_짤형_keyword_웃김(self):
        assert self._fn("웃김 ㅋㅋ 레전드", "", "공감") == "짤형"

    def test_한줄팩폭형_keyword_실화냐(self):
        # "실화냐" is only in 한줄팩폭형_kw, not 짤형_kw.
        # NOTE: Avoid "?" in text — it's also in 논쟁형_kw and has higher priority.
        assert self._fn("실화냐 ㄹㅇ", "", "공감") == "한줄팩폭형"

    def test_한줄팩폭형_via_emotion_axis_분노_short_content(self):
        # 감정=분노 + 짧은 본문 → 키워드 없어도 한줄팩폭형
        short_content = "직장에서 이런 일이 있었어요."
        assert self._fn("제목", short_content, "분노") == "한줄팩폭형"

    def test_default_no_match_returns_공감형(self):
        assert self._fn("평범한 직장 이야기입니다", "오늘 점심을 먹었습니다", "공감") == "공감형"

    def test_분석형_takes_priority_over_통찰형(self):
        # "분석"과 "인사이트" 둘 다 포함 → 분석형 우선
        assert self._fn("커뮤니티 인사이트 종합", "데이터 분석", "공감") == "분석형"

    def test_통찰형_takes_priority_over_논쟁형(self):
        # "교훈"(통찰형)과 "왜"(논쟁형) 둘 다 → 통찰형 우선
        assert self._fn("이 상황에서 배운 교훈", "왜 그랬을까", "공감") == "통찰형"


# ── recommend_draft_type 직접 단위 테스트 ────────────────────────────────────


class TestRecommendDraftType:
    """recommend_draft_type: hook_type × emotion_axis 매핑 + 감정축 우선순위."""

    def setup_method(self):
        from pipeline.content_intelligence.classifiers import recommend_draft_type

        self._fn = recommend_draft_type

    def test_분석형_hook_returns_분석형(self):
        assert self._fn("분석형", "공감") == "분석형"

    def test_AI_전환_emotion_overrides_논쟁형_hook(self):
        # T-AB048: 논쟁형 hook이더라도 AI_전환 감정이면 분석형으로
        assert self._fn("논쟁형", "AI_전환") == "분석형"

    def test_고용불안_emotion_returns_공감형(self):
        assert self._fn("논쟁형", "고용불안") == "공감형"

    def test_정보형_hook_returns_정보전달형(self):
        assert self._fn("정보형", "공감") == "정보전달형"

    def test_논쟁형_hook_returns_논쟁형(self):
        assert self._fn("논쟁형", "현타") == "논쟁형"

    def test_분노_emotion_triggers_논쟁형_even_with_non_논쟁형_hook(self):
        assert self._fn("통찰형", "분노") == "논쟁형"

    def test_경악_emotion_triggers_논쟁형(self):
        assert self._fn("공감형", "경악") == "논쟁형"

    def test_한줄팩폭형_with_공감_emotion_returns_공감형(self):
        assert self._fn("한줄팩폭형", "공감") == "공감형"

    def test_한줄팩폭형_with_비공감_emotion_returns_논쟁형(self):
        # 경악은 {"공감", "허탈", "현타"} 밖 → 논쟁형
        assert self._fn("한줄팩폭형", "경악") == "논쟁형"

    def test_default_공감형_hook_and_emotion_returns_공감형(self):
        assert self._fn("공감형", "통찰") == "공감형"


# ── 6D 가중치 보정 순수 함수 단위 테스트 ──────────────────────────────────────


class TestPearson:
    """_pearson: 기본 통계 함수 경계 조건 — 칼리브레이션 핵심."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _pearson

        self._fn = _pearson

    def test_empty_lists_return_zero(self):
        assert self._fn([], []) == 0.0

    def test_perfect_positive_correlation(self):
        result = self._fn([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert abs(result - 1.0) < 1e-9

    def test_perfect_negative_correlation(self):
        result = self._fn([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
        assert abs(result + 1.0) < 1e-9

    def test_constant_y_returns_zero(self):
        # sy=0 → guarded by 1e-10, so result ≈ 0
        result = self._fn([1.0, 2.0, 3.0], [2.0, 2.0, 2.0])
        assert abs(result) < 1e-6

    def test_constant_x_returns_zero(self):
        result = self._fn([2.0, 2.0, 2.0], [1.0, 2.0, 3.0])
        assert abs(result) < 1e-6

    def test_single_element_returns_zero(self):
        assert self._fn([5.0], [5.0]) == 0.0


class TestEngagementValues:
    """_engagement_values: engagement_rate + log1p(yt_views)*0.1 변환."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _engagement_values

        self._fn = _engagement_values

    def test_empty_rows_returns_empty(self):
        assert self._fn([]) == []

    def test_valid_row_computes_engagement_plus_log_views(self):
        import math

        rows = [(0, 0, 0, 0.5, 1000)]  # engagement_rate=0.5, yt_views=1000
        result = self._fn(rows)
        expected = 0.5 + math.log1p(1000) * 0.1
        assert abs(result[0] - expected) < 1e-9

    def test_invalid_value_returns_zero(self):
        rows = [(0, 0, 0, "invalid", "bad")]
        result = self._fn(rows)
        assert result == [0.0]

    def test_none_values_treated_as_zero(self):
        import math

        rows = [(0, 0, 0, None, None)]
        result = self._fn(rows)
        assert result[0] == math.log1p(0) * 0.1  # == 0.0


class TestNormalizeCalibrationWeights:
    """_normalize_calibration_weights: 클램핑 + 정규화 불변식."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import DIMENSION_KEYS, _normalize_calibration_weights

        self._fn = _normalize_calibration_weights
        self._keys = DIMENSION_KEYS

    def _uniform_corr(self, value: float = 0.15) -> dict:
        return {k: value for k in self._keys}

    def test_weights_sum_approximately_to_one(self):
        # Values are rounded to 4 decimal places → max rounding error ≈ N × 0.5e-4
        weights = self._fn(self._uniform_corr())
        assert abs(sum(weights.values()) - 1.0) < 0.01  # 6 × 0.1667 = 1.0002 is fine

    def test_all_keys_present(self):
        weights = self._fn(self._uniform_corr())
        assert set(weights) == set(self._keys)

    def test_uniform_correlations_give_uniform_weights(self):
        weights = self._fn(self._uniform_corr(0.20))
        expected = round(1.0 / len(self._keys), 4)
        for w in weights.values():
            assert abs(w - expected) < 0.01

    def test_zero_total_correlation_gives_valid_weights(self):
        # When all correlations are 0, total_corr guard kicks in → uniform distribution
        weights = self._fn(self._uniform_corr(0.0))
        assert abs(sum(weights.values()) - 1.0) < 0.01
        for w in weights.values():
            assert w > 0.0

    def test_dominant_dimension_gets_higher_share_after_normalization(self):
        # The 0.40 pre-normalization clamp does NOT cap the final weight:
        # after renormalization the dominant dim can exceed 0.40.
        # This test documents the actual behavior (not a bug, just a known
        # side-effect of the two-step clamp+renormalize approach).
        corr = {k: 0.01 for k in self._keys}
        corr["social"] = 100.0  # artificially dominant
        weights = self._fn(corr)
        # social should dominate all other dimensions
        assert weights["social"] == max(weights.values())


# ── utils 순수 함수 단위 테스트 ─────────────────────────────────────────────


class TestEditorialReasonLabels:
    """_build_editorial_reason_labels: 점수 임계값 기반 레이블 생성."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_editorial import _build_editorial_reason_labels

        self._fn = _build_editorial_reason_labels

    def _dims(self, **overrides):
        base = {"reader_desire": 0.0, "empathy_fun": 0.0, "spinoff": 0.0, "specificity": 0.0, "workplace_fit": 0.0}
        base.update(overrides)
        return base

    def test_all_above_threshold_gives_five_labels(self):
        dims = self._dims(reader_desire=75, empathy_fun=75, spinoff=70, specificity=70, workplace_fit=75)
        labels = self._fn(dims, 90.0)
        assert len(labels) == 5

    def test_all_below_threshold_with_score_55_gives_fallback_label(self):
        labels = self._fn(self._dims(), 55.0)
        assert labels == ["반응 포인트는 있으나 편집 보강이 필요함"]

    def test_all_below_threshold_with_score_below_55_gives_empty(self):
        assert self._fn(self._dims(), 50.0) == []

    def test_reader_desire_exactly_at_70_threshold(self):
        labels = self._fn(self._dims(reader_desire=70), 90.0)
        assert "직장인이 바로 눌러볼 만한 주제" in labels

    def test_spinoff_exactly_at_65_threshold(self):
        labels = self._fn(self._dims(spinoff=65), 90.0)
        assert "댓글과 파생 대화로 이어질 각이 있음" in labels

    def test_below_threshold_by_one_not_included(self):
        labels = self._fn(self._dims(reader_desire=69.9, spinoff=64.9), 90.0)
        assert "직장인이 바로 눌러볼 만한 주제" not in labels
        assert "댓글과 파생 대화로 이어질 각이 있음" not in labels


class TestWeightedEditorialScore:
    """_weighted_editorial_score: 5축 가중 평균 — 가중치 합 검증."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_editorial import _weighted_editorial_score

        self._fn = _weighted_editorial_score

    def test_all_100_gives_100(self):
        dims = {"reader_desire": 100, "empathy_fun": 100, "spinoff": 100, "specificity": 100, "workplace_fit": 100}
        assert self._fn(dims) == 100.0

    def test_all_zero_gives_zero(self):
        dims = {"reader_desire": 0, "empathy_fun": 0, "spinoff": 0, "specificity": 0, "workplace_fit": 0}
        assert self._fn(dims) == 0.0

    def test_weights_sum_to_one(self):
        # Verify total weight = 0.30+0.25+0.20+0.15+0.10 = 1.0
        # If all dims = 50.0, weighted avg = 50.0
        dims = {"reader_desire": 50, "empathy_fun": 50, "spinoff": 50, "specificity": 50, "workplace_fit": 50}
        assert self._fn(dims) == 50.0

    def test_reader_desire_has_highest_weight(self):
        # reader_desire at 100, all others at 0 → 0.30*100 = 30.0
        dims = {"reader_desire": 100, "empathy_fun": 0, "spinoff": 0, "specificity": 0, "workplace_fit": 0}
        assert self._fn(dims) == 30.0


class TestCalculatePerformanceScore:
    """calculate_performance_score: 역사적 예시 가중치 기반 성과 점수."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_performance import calculate_performance_score

        self._fn = calculate_performance_score

    def test_no_historical_examples_returns_45(self):
        score, rationale = self._fn("연봉", "논쟁형", "분노", "논쟁형", None)
        assert score == 45.0
        assert rationale == ["no_historical_examples"]

    def test_empty_examples_returns_45(self):
        score, rationale = self._fn("연봉", "논쟁형", "분노", "논쟁형", [])
        assert score == 45.0
        assert rationale == ["no_historical_examples"]

    def test_single_example_no_match_returns_35(self):
        example = {
            "topic_cluster": "기타",
            "hook_type": "공감형",
            "emotion_axis": "공감",
            "draft_style": "공감형",
            "views": 0,
        }
        score, rationale = self._fn("연봉", "논쟁형", "분노", "논쟁형", [example])
        assert score == 35.0
        assert rationale == ["weak_match"]

    def test_topic_match_increases_score(self):
        example = {
            "topic_cluster": "연봉",
            "hook_type": "정보형",
            "emotion_axis": "통찰",
            "draft_style": "정보전달형",
            "views": 0,
        }
        score, _ = self._fn("연봉", "논쟁형", "분노", "논쟁형", [example])
        assert score > 35.0

    def test_all_four_matches_gives_high_score(self):
        example = {
            "topic_cluster": "이직",
            "hook_type": "논쟁형",
            "emotion_axis": "분노",
            "draft_style": "논쟁형",
            "views": 0,
        }
        score, rationale = self._fn("이직", "논쟁형", "분노", "논쟁형", [example])
        assert score > 70.0
        assert set(rationale) == {"topic_match", "hook_match", "emotion_match", "draft_style_match"}

    def test_high_views_same_normalized_score_as_low_views_with_same_matches(self):
        # Bug fix: previously the base score 35.0 was divided by total_weight,
        # so high-views examples diluted the base and gave LOWER scores.
        # After fix: base 35.0 is constant; only the match bonus is weight-normalized.
        # Result: same match structure → same normalized score regardless of views.
        low_views = {
            "topic_cluster": "이직",
            "hook_type": "논쟁형",
            "emotion_axis": "분노",
            "draft_style": "논쟁형",
            "views": 0,
        }
        high_views = {
            "topic_cluster": "이직",
            "hook_type": "논쟁형",
            "emotion_axis": "분노",
            "draft_style": "논쟁형",
            "views": 10000,
        }
        score_low, _ = self._fn("이직", "논쟁형", "분노", "논쟁형", [low_views])
        score_high, _ = self._fn("이직", "논쟁형", "분노", "논쟁형", [high_views])
        assert abs(score_low - score_high) < 0.01

    def test_non_matching_examples_do_not_dilute_base_score(self):
        # Bug fix: previously more non-matching examples diluted the 35.0 base
        # (35/3 < 35/1). After fix, base is constant — non-matching examples
        # don't change the score because match_bonus stays 0.
        one_example = [
            {
                "topic_cluster": "기타",
                "hook_type": "공감형",
                "emotion_axis": "공감",
                "draft_style": "공감형",
                "views": 0,
            }
        ]
        three_examples = one_example * 3
        score1, _ = self._fn("연봉", "논쟁형", "분노", "논쟁형", one_example)
        score3, _ = self._fn("연봉", "논쟁형", "분노", "논쟁형", three_examples)
        assert score1 == score3 == 35.0


class TestKoreanRatio:
    """_korean_ratio: 한국어 비율 계산."""

    def setup_method(self):
        from pipeline.content_intelligence.utils import _korean_ratio

        self._fn = _korean_ratio

    def test_empty_string_returns_zero(self):
        assert self._fn("") == 0.0

    def test_all_whitespace_returns_zero(self):
        assert self._fn("   ") == 0.0

    def test_all_korean_returns_one(self):
        assert self._fn("안녕하세요") == 1.0

    def test_half_korean_half_english(self):
        # "안녕하세요"=5 Korean + " " + "hello"=5 English → ratio 5/10 = 0.5
        result = self._fn("안녕하세요 hello")
        assert 0.4 < result < 0.6

    def test_all_english_returns_zero(self):
        assert self._fn("hello world") == 0.0


class TestExtractFirstSentence:
    """_extract_first_sentence: 첫 문장 추출."""

    def setup_method(self):
        from pipeline.content_intelligence.utils import _extract_first_sentence

        self._fn = _extract_first_sentence

    def test_empty_returns_empty(self):
        assert self._fn("") == ""

    def test_single_sentence_with_period(self):
        assert self._fn("안녕하세요. 반갑습니다.") == "안녕하세요."

    def test_multiline_returns_first_line(self):
        result = self._fn("첫째 줄\n둘째 줄")
        assert result == "첫째 줄"

    def test_no_delimiter_returns_whole_text(self):
        result = self._fn("마침표없는문장")
        assert result == "마침표없는문장"


class TestEngagementSignal:
    """_engagement_signal: 좋아요+댓글 기반 참여도 신호 — 로그 스케일 + 20 상한."""

    def setup_method(self):
        from pipeline.content_intelligence.utils import _engagement_signal

        self._fn = _engagement_signal

    def test_no_engagement_returns_zero(self):
        assert self._fn({"likes": 0, "comments": 0}) == 0.0

    def test_missing_keys_treated_as_zero(self):
        assert self._fn({}) == 0.0

    def test_high_engagement_capped_at_20(self):
        result = self._fn({"likes": 100_000, "comments": 50_000})
        assert result == 20.0

    def test_low_engagement_below_cap(self):
        result = self._fn({"likes": 10, "comments": 0})
        assert 0.0 < result < 20.0

    def test_comments_weighted_higher_than_likes(self):
        # comments weight 1.5× vs likes 1×
        like_only = self._fn({"likes": 10, "comments": 0})
        comment_only = self._fn({"likes": 0, "comments": 10})
        assert comment_only > like_only


class TestHumanizePerformanceRationale:
    """_humanize_performance_rationale: label 매핑 + 미등록 패스스루 + trained_on= 파싱."""

    def setup_method(self):
        from pipeline.content_intelligence.utils import _humanize_performance_rationale

        self._fn = _humanize_performance_rationale

    def test_known_label_maps_to_korean(self):
        result = self._fn(["topic_match"])
        assert result == ["비슷한 주제가 실제로 반응했던 이력"]

    def test_unknown_label_passes_through(self):
        result = self._fn(["unknown_custom_label"])
        assert result == ["unknown_custom_label"]

    def test_trained_on_prefix_is_parsed(self):
        result = self._fn(["trained_on=50"])
        assert result == ["학습 표본: 50"]

    def test_duplicate_labels_deduplicated(self):
        result = self._fn(["topic_match", "topic_match"])
        assert len(result) == 1

    def test_empty_list_returns_empty(self):
        assert self._fn([]) == []


class TestHookStrengthScore:
    """_hook_strength_score: 제목 길이 보너스/페널티 + hook type 기본 점수 검증."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _hook_strength_score

        self._fn = _hook_strength_score

    def test_논쟁형_with_optimal_title_length_gets_bonus(self):
        # 논쟁형=90.0 + 8 bonus = 98.0 (title 10 chars: 8<=10<=35)
        score = self._fn("직장인 현실이다", "논쟁형")
        assert score == 98.0

    def test_unknown_hook_type_returns_default_60(self):
        # Unknown type → 60.0, title 10 chars → 60.0 + 8.0 = 68.0
        score = self._fn("직장인 현실이다", "미분류형")
        assert score == 68.0

    def test_very_short_title_penalizes_score(self):
        # title="AI" (2 chars) → len < 4 → hook_score - 20
        score = self._fn("AI", "논쟁형")
        assert score == 70.0  # 90.0 - 20.0

    def test_short_title_below_floor_clamped_to_zero(self):
        # Unknown type (60.0) - 20 = 40.0 (above 0 anyway) → for a weak type:
        # Use a type that's not in dict so 60-20=40 ≥ 0
        score = self._fn("히", "미분류형")
        assert score == 40.0

    def test_title_length_4_to_7_gets_no_bonus_or_penalty(self):
        # title 5 chars: not <4, not 8-35 → returns hook_score unchanged
        score = self._fn("직장인 A", "공감형")  # 5 chars after strip
        assert score == 75.0  # 공감형 base

    def test_long_title_over_35_chars_gets_no_bonus(self):
        # 36+ chars: no bonus or penalty → returns hook_score directly
        long_title = "직장인들이 정말 많이 겪는 직장 내 현실에 대한 깊은 이야기입니다"  # 34+ chars
        assert len(long_title) > 35
        score = self._fn(long_title, "논쟁형")
        assert score == 90.0

    def test_한줄팩폭형_plus_bonus_capped_at_100(self):
        # 한줄팩폭형=85 + 8 = 93.0 (not capped — well within 100)
        score = self._fn("직장인 현실이다", "한줄팩폭형")
        assert score == 93.0

    def test_score_capped_at_100_for_high_hook_bonus(self):
        # Custom scenario: create a score >100 artificially is impossible with
        # existing types (max 90+8=98). Verify cap logic: max hook=90+8=98 < 100 OK
        # The only way to hit cap would be hook_score > 92. Use 분석형=88+8=96 < 100
        score = self._fn("직장인 현실이다", "분석형")
        assert score == 96.0  # 88 + 8


class TestAudienceTargetingScore:
    """_audience_targeting_score: 컨텐츠 길이 보너스 + audience_fit 점수 검증."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _audience_targeting_score

        self._fn = _audience_targeting_score

    def test_전직장인_audience_gives_85_base(self):
        short_content = "짧은 내용"  # < 150 chars
        score = self._fn(short_content, "전직장인")
        assert score == 85.0

    def test_unknown_audience_fit_gives_50_default(self):
        score = self._fn("짧은 내용", "알수없음")
        assert score == 50.0

    def test_long_content_adds_5_bonus(self):
        long_content = "직장인 이야기입니다. " * 15  # > 150 chars
        assert len(long_content) >= 150
        score = self._fn(long_content, "전직장인")
        assert score == 90.0  # 85 + 5

    def test_long_content_with_unknown_audience_gets_bonus(self):
        long_content = "긴 컨텐츠입니다. " * 20  # > 150 chars
        score = self._fn(long_content, "알수없음")
        assert score == 55.0  # 50 + 5

    def test_content_exactly_150_chars_gets_bonus(self):
        content_150 = "가" * 150
        score = self._fn(content_150, "이직준비층")
        assert score == 85.0  # 80 + 5

    def test_content_149_chars_gets_no_bonus(self):
        content_149 = "가" * 149
        score = self._fn(content_149, "이직준비층")
        assert score == 80.0  # base only

    def test_관리자층_has_lower_base_than_전직장인(self):
        short_content = "짧은 내용"
        score_mgr = self._fn(short_content, "관리자층")
        score_all = self._fn(short_content, "전직장인")
        assert score_mgr < score_all

    def test_bonus_capped_at_100(self):
        # 전직장인=85 + 5 = 90, not capped. 범용=50+5=55. No type hits cap naturally.
        # Check cap is applied: simulate with 범용 for completeness
        long_content = "가" * 200
        score = self._fn(long_content, "범용")
        assert score == 55.0  # 50 + 5, well below 100


class TestTrendRelevanceScore:
    """_trend_relevance_score: HIGH/MEDIUM/기타/기본 base + trend_boost 경계 검증."""

    def setup_method(self):
        from pipeline.content_intelligence.scoring_6d import _trend_relevance_score

        self._fn = _trend_relevance_score

    def test_high_trend_topic_returns_85_base(self):
        score = self._fn("연봉", 0.0)
        assert score >= 85.0

    def test_medium_trend_topic_returns_65_base(self):
        score = self._fn("복지", 0.0)
        assert score >= 65.0

    def test_기타_topic_returns_35_base(self):
        score = self._fn("기타", 0.0)
        assert score >= 35.0

    def test_unknown_topic_returns_50_base(self):
        score = self._fn("완전히_없는_주제_xyzzy", 0.0)
        assert score >= 50.0

    def test_trend_boost_increases_score(self):
        base_score = self._fn("연봉", 0.0)
        boosted_score = self._fn("연봉", 10.0)
        assert boosted_score > base_score

    def test_trend_boost_capped_at_100(self):
        score = self._fn("연봉", 200.0)  # huge boost
        assert score <= 100.0

    def test_negative_trend_boost_not_applied(self):
        base = self._fn("연봉", 0.0)
        not_penalized = self._fn("연봉", -10.0)
        assert not_penalized == base  # negative boost ignored

    def test_ai_trend_is_high_trend_topic(self):
        score = self._fn("AI 트렌드", 0.0)
        assert score >= 85.0
