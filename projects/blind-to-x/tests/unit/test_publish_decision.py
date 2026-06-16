import pytest

from pipeline.publish_decision import (
    DROP,
    HOLD,
    PUBLISH,
    PublishDecision,
    decide_publish,
    decision_card_lines,
    evaluate_position_rubric,
)

RESEARCH = {
    "source_frame": "상사와 직원의 감정 싸움",
    "real_issue": "권한을 가진 사람이 책임 있게 말하고 행동해야 한다는 문제",
    "universal_value": "책임 있는 권한",
    "killer_sentence": "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다",
    "closure": "open",
    "conflict_risk": 0.2,
    "value_reduction_failed": False,
}

GOOD_DRAFT = (
    '"먼저 가도 된다" 해놓고 평가에서 태도를 봤대요.\n'
    "참 이상한 기준이에요. "
    "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다. "
    "개인 감정으로 끝낼 일이 아니라, 같은 기준을 설명하는 책임의 문제거든요. "
    "정답은 회사마다 달라질 수 있어도 기준은 남습니다."
)


def test_decide_publish_allows_publish_only_when_all_gates_pass():
    decision = decide_publish({"twitter": 95}, {"twitter": {"passed": True}}, RESEARCH, GOOD_DRAFT)

    assert decision.action == PUBLISH
    assert decision.x_publish_status == "Ready to Post"


def test_value_reduction_failed_string_false_does_not_drop_publishable_draft():
    research = dict(RESEARCH)
    research["value_reduction_failed"] = "false"

    decision = decide_publish({"twitter": 95}, {"twitter": {"passed": True}}, research, GOOD_DRAFT)

    assert decision.action == PUBLISH
    assert decision.x_publish_status == "Ready to Post"


def test_decide_publish_holds_regulation_failure_even_with_quality_100():
    decision = decide_publish({"twitter": 100}, {"twitter": {"passed": False}}, RESEARCH, GOOD_DRAFT)

    assert decision.action == HOLD
    assert decision.hard_gate is True
    assert "twitter:regulation_failed" in decision.reasons


def test_decide_publish_drops_when_research_context_cannot_reduce_value():
    decision = decide_publish({"twitter": 100}, {"twitter": {"passed": True}}, {}, GOOD_DRAFT)

    assert decision.action == DROP
    assert decision.reason == "research_context value reduction failed"


def test_zero_position_item_caps_quality_below_publish_threshold():
    weak_draft = (
        "참 기준이 중요해요. 개인 얘기를 원칙으로 봐야 하거든요. 정답은 회사마다 달라질 수 있어도 기준은 남습니다."
    )

    decision = decide_publish({"twitter": 100}, {"twitter": {"passed": True}}, RESEARCH, weak_draft)

    assert decision.action == HOLD
    assert decision.quality_score == 84.0
    assert "position" in decision.reasons


def test_forbidden_ai_tone_is_hard_hold_with_zero_ceiling():
    decision = decide_publish(
        {"twitter": 100},
        {"twitter": {"passed": True}},
        RESEARCH,
        GOOD_DRAFT + " 이것이 조직의 민낯입니다.",
    )

    assert decision.action == HOLD
    assert decision.quality_ceiling == 0.0
    assert "forbidden_tone" in decision.reasons


@pytest.mark.parametrize(
    "bad_phrase",
    [
        "이 시대의 끝판왕이라 할 만합니다.",
        "취재 현장에서 기절할 뻔 했습니다.",
        "이것만이 살 길입니다.",
        # prompts.yaml 동기화 추가분 (T-AB007)
        "정말 어처구니없어서 말이 안 나왔습니다.",
        "그 발표를 듣고 어질어질했습니다.",
        # editorial.yaml 동기화 추가분 (T-AB009)
        "이건 완전 팩폭이에요.",
        "잠깐, 현실 자각 타임 가져봅시다.",
        "정신 차리고 봐, 이게 현실이야.",
        # draft_quality_gate CTA 패턴 동기화 (T-AB022)
        "이 방법 한 수 알려드릴게요.",
    ],
)
def test_influencer_slang_forbidden_tones_are_blocked(bad_phrase):
    decision = decide_publish(
        {"twitter": 100},
        {"twitter": {"passed": True}},
        RESEARCH,
        GOOD_DRAFT + " " + bad_phrase,
    )
    assert decision.action == HOLD
    assert decision.quality_ceiling == 0.0
    assert "forbidden_tone" in decision.reasons


def test_high_conflict_without_value_reduction_drops():
    research = dict(RESEARCH)
    research["conflict_risk"] = 0.95
    weak_conflict_draft = "참 남자 여자 싸움으로 볼 수도 있어요. 댓글은 계속 갈릴 것 같아요."

    decision = decide_publish({"twitter": 100}, {"twitter": {"passed": True}}, research, weak_conflict_draft)

    assert decision.action == DROP
    assert decision.reason == "high conflict risk without universal value reduction"


# ── evaluate_position_rubric 직접 단위 테스트 ───────────────────────────────


class TestEvaluatePositionRubric:
    """evaluate_position_rubric: 5개 축(position/reduction/tone/voice/ending) 독립 검증."""

    def test_all_pass_gives_ceiling_100(self):
        result = evaluate_position_rubric(GOOD_DRAFT, RESEARCH)
        assert result["quality_ceiling"] == 100.0
        assert result["zero_items"] == []
        assert result["forbidden_tone"] == []

    def test_score_is_average_of_five_items(self):
        result = evaluate_position_rubric(GOOD_DRAFT, RESEARCH)
        expected = sum(result["items"].values()) / len(result["items"])
        assert result["score"] == expected

    def test_forbidden_tone_sets_ceiling_to_zero(self):
        result = evaluate_position_rubric(GOOD_DRAFT + " 이것이 조직의 민낯입니다.", RESEARCH)
        assert result["quality_ceiling"] == 0.0
        assert "tone" in result["zero_items"]
        assert result["forbidden_tone"]

    def test_missing_position_sets_ceiling_to_84(self):
        no_position = (
            "개인 감정으로 끝낼 일이 아니라, 같은 기준을 설명하는 책임의 문제거든요. "
            "정답은 회사마다 달라질 수 있어도 기준은 남습니다."
        )
        result = evaluate_position_rubric(no_position, RESEARCH)
        assert result["quality_ceiling"] == 84.0
        assert "position" in result["zero_items"]

    def test_items_keys_are_exactly_five_axes(self):
        result = evaluate_position_rubric(GOOD_DRAFT, RESEARCH)
        assert set(result["items"]) == {"position", "reduction", "tone", "voice", "ending"}


# ── decision_card_lines 직접 단위 테스트 ────────────────────────────────────


class TestDecisionCardLines:
    """decision_card_lines: PublishDecision/dict/None 세 경로 검증."""

    def _make(self, action=PUBLISH, score=90.0):
        return PublishDecision(
            action=action,
            reason="all gates passed",
            x_publish_status="Ready to Post",
            quality_score=score,
            quality_ceiling=100.0,
            reasons=["ok"],
            metrics={"weighted_length": 120, "hashtags": 0},
        )

    def test_publish_decision_instance_emits_action_and_score(self):
        lines = decision_card_lines(self._make())
        combined = "\n".join(lines)
        assert f"결정: {PUBLISH}" in combined
        assert "90.0" in combined

    def test_dict_payload_emits_action_and_reason(self):
        payload = {
            "action": HOLD,
            "reason": "quality_score_below_threshold",
            "quality_score": 80.0,
            "metrics": {"weighted_length": 150},
            "reasons": ["quality_score_below_threshold"],
        }
        lines = decision_card_lines(payload)
        combined = "\n".join(lines)
        assert f"결정: {HOLD}" in combined
        assert "quality_score_below_threshold" in combined

    def test_none_payload_uses_hold_fallback(self):
        lines = decision_card_lines(None)
        combined = "\n".join(lines)
        assert f"결정: {HOLD}" in combined
        assert "publish decision missing" in combined

    def test_empty_metrics_omits_detail_line(self):
        d = PublishDecision(
            action=PUBLISH,
            reason="ok",
            x_publish_status="Ready to Post",
            quality_score=90.0,
            quality_ceiling=100.0,
            reasons=[],
            metrics={},
        )
        assert not any("결정 근거:" in line for line in decision_card_lines(d))


# ── rubric 서브 함수 직접 단위 테스트 ────────────────────────────────────────


class TestHasValueFrame:
    """_has_value_frame: killer_sentence 매칭 우선, FRAME_RE 폴백."""

    def setup_method(self):
        from pipeline.publish_decision import _has_value_frame

        self._fn = _has_value_frame

    def test_killer_sentence_in_text_returns_true(self):
        assert self._fn(
            "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다.",
            {"killer_sentence": "이건 윗사람을 공격하자는 게 아니라 권한에는 책임이 따른다는 말입니다"},
        )

    def test_killer_sentence_absent_falls_back_to_frame_re(self):
        # _FRAME_RE: "이건 X가 아니라 Y입니다"
        assert self._fn(
            "이건 개인의 문제가 아니라 조직 구조의 문제입니다.",
            {"killer_sentence": "전혀 다른 문장"},
        )

    def test_no_killer_and_no_frame_returns_false(self):
        assert not self._fn(
            "직장인들이 많이 고민하는 이야기입니다.",
            {},
        )

    def test_empty_text_returns_false(self):
        assert not self._fn("", {"killer_sentence": "뭔가"})


class TestHasUniversalReduction:
    """_has_universal_reduction: universal_value 매칭 우선, 키워드 폴백."""

    def setup_method(self):
        from pipeline.publish_decision import _has_universal_reduction

        self._fn = _has_universal_reduction

    def test_universal_value_in_text_returns_true(self):
        assert self._fn(
            "권한에는 책임이 따른다는 원칙이 있습니다.",
            {"universal_value": "권한에는 책임이 따른다"},
        )

    def test_keyword_fallback_책임_returns_true(self):
        assert self._fn("조직의 책임 문제입니다.", {})

    def test_keyword_fallback_기준_returns_true(self):
        assert self._fn("기준이 명확해야 합니다.", {})

    def test_no_match_returns_false(self):
        assert not self._fn("그냥 일상적인 이야기입니다.", {})


class TestHasOperatorVoice:
    """_has_operator_voice: 공손체 AND 구어체 마커 둘 다 필요."""

    def setup_method(self):
        from pipeline.publish_decision import _has_operator_voice

        self._fn = _has_operator_voice

    def test_polite_and_conversational_returns_true(self):
        assert self._fn("참 이상한 기준이에요. 책임의 문제거든요.")

    def test_only_polite_returns_false(self):
        # 공손체만 있고 구어체 없음
        assert not self._fn("이것은 조직의 책임 문제입니다.")

    def test_only_conversational_returns_false(self):
        # 구어체 마커("결국", "근데")는 있지만 공손체 어미("요"/"습니다") 없음 — 반말체
        assert not self._fn("결국 근데 이게 문제야. 다들 그렇게 생각한다.")

    def test_empty_text_returns_false(self):
        assert not self._fn("")


class TestEndingMatches:
    """_ending_matches: open/closed closure 분기."""

    def setup_method(self):
        from pipeline.publish_decision import _ending_matches

        self._fn = _ending_matches

    def test_open_closure_with_정답은_token(self):
        assert self._fn(
            "정답은 회사마다 다를 수 있습니다.",
            {"closure": "open"},
        )

    def test_open_closure_with_남습니다_token(self):
        assert self._fn("기준은 남습니다.", {"closure": "open"})

    def test_open_closure_missing_tokens_returns_false(self):
        assert not self._fn("잘 생각해야 합니다.", {"closure": "open"})

    def test_closed_closure_with_명확한_종결어미(self):
        assert self._fn(
            "이건 반드시 해야 합니다.",
            {"closure": "closed"},
        )

    def test_closed_closure_ending_with_question_returns_false(self):
        # 닫힌 결말인데 의문문으로 끝나면 실패
        assert not self._fn(
            "어떻게 생각해야 할까요?",
            {"closure": "closed"},
        )

    def test_default_closure_treated_as_open(self):
        # closure 키 없으면 "open" 기본값
        assert self._fn("정답은 없습니다.", {})


# ── _coerce_score / _quality_score 경계 조건 테스트 ─────────────────────────


class TestCoerceScore:
    """_coerce_score: 0-10 자동 스케일업 + 경계 조건."""

    def setup_method(self):
        from pipeline.publish_decision import _coerce_score

        self._fn = _coerce_score

    def test_none_returns_none(self):
        assert self._fn(None) is None

    def test_empty_string_returns_none(self):
        assert self._fn("") is None

    def test_non_numeric_returns_none(self):
        assert self._fn("excellent") is None

    def test_score_in_0_to_10_range_is_scaled_to_100(self):
        # LLM often returns 0-10 scale; coerce multiplies by 10
        assert self._fn(7.5) == 75.0

    def test_score_exactly_10_becomes_100(self):
        assert self._fn(10) == 100.0

    def test_score_above_10_treated_as_0_to_100_scale(self):
        # 85 is clearly in 0-100 range — no multiplication
        assert self._fn(85) == 85.0

    def test_score_is_clamped_at_100(self):
        assert self._fn(1000) == 100.0

    def test_score_is_clamped_at_zero(self):
        assert self._fn(-5) == 0.0

    def test_string_numeric_is_accepted(self):
        assert self._fn("9") == 90.0

    def test_nan_float_returns_none(self):
        """BTX-PD-CS001: float('nan') → None (min(100,nan)=100 둔갑 방지)."""
        assert self._fn(float("nan")) is None

    def test_inf_float_returns_none(self):
        """BTX-PD-CS002: float('inf') → None."""
        assert self._fn(float("inf")) is None

    def test_neg_inf_returns_none(self):
        """BTX-PD-CS003: float('-inf') → None."""
        assert self._fn(float("-inf")) is None

    def test_string_nan_returns_none(self):
        """BTX-PD-CS004: 'nan' 문자열 → None."""
        assert self._fn("nan") is None

    def test_string_inf_returns_none(self):
        """BTX-PD-CS005: 'inf' 문자열 → None."""
        assert self._fn("inf") is None


class TestQualityScore:
    """_quality_score: dict averaging + single-value passthrough."""

    def setup_method(self):
        from pipeline.publish_decision import _quality_score

        self._fn = _quality_score

    def test_single_100_scale_value_returns_directly(self):
        assert self._fn(90.0) == 90.0

    def test_dict_averages_numeric_values(self):
        # 8.0 → 80.0, 9.0 → 90.0 → average = 85.0
        assert self._fn({"twitter": 8.0, "instagram": 9.0}) == 85.0

    def test_dict_with_all_none_returns_none(self):
        assert self._fn({"twitter": None, "instagram": ""}) is None

    def test_dict_skips_none_in_average(self):
        # Only 9.0 (→90.0) is numeric; None is skipped
        result = self._fn({"twitter": 9.0, "x": None})
        assert result == 90.0


# ── _regulation_failures 경계 조건 테스트 ────────────────────────────────────


class TestRegulationFailures:
    """_regulation_failures: None/str/dict/object 경로 + 다중 플랫폼."""

    def setup_method(self):
        from pipeline.publish_decision import _regulation_failures

        self._fn = _regulation_failures

    def test_none_returns_empty(self):
        assert self._fn(None) == []

    def test_empty_string_returns_empty(self):
        assert self._fn("") == []

    def test_string_with_FAILED_returns_report_failure(self):
        assert self._fn("FAILED 검사 결과") == ["regulation_report_not_passed"]

    def test_string_with_경고_returns_report_failure(self):
        assert self._fn("경고: 글자 수 초과") == ["regulation_report_not_passed"]

    def test_string_without_keywords_returns_empty(self):
        assert self._fn("정상 통과") == []

    def test_non_dict_non_string_returns_empty(self):
        assert self._fn(42) == []

    def test_dict_with_passed_false_appends_platform_failure(self):
        result = self._fn({"twitter": {"passed": False}})
        assert result == ["twitter:regulation_failed"]

    def test_dict_with_passed_true_returns_empty(self):
        assert self._fn({"twitter": {"passed": True}}) == []

    def test_dict_multi_platform_partial_failure(self):
        result = self._fn({"twitter": {"passed": True}, "instagram": {"passed": False}})
        assert result == ["instagram:regulation_failed"]

    def test_dict_with_object_having_passed_attr_false(self):
        class Report:
            passed = False

        result = self._fn({"linkedin": Report()})
        assert result == ["linkedin:regulation_failed"]


# ── _research_failed 경계 조건 테스트 ────────────────────────────────────────


class TestResearchFailed:
    """_research_failed: None/empty/non-dict + value_reduction_failed + universal_value 누락."""

    def setup_method(self):
        from pipeline.publish_decision import _research_failed

        self._fn = _research_failed

    def test_none_returns_true(self):
        assert self._fn(None) is True

    def test_empty_dict_returns_true(self):
        assert self._fn({}) is True

    def test_non_dict_string_returns_true(self):
        assert self._fn("some string") is True

    def test_dict_without_universal_value_key_returns_true(self):
        assert self._fn({"conflict_risk": 0.1}) is True

    def test_dict_with_empty_universal_value_returns_true(self):
        assert self._fn({"universal_value": ""}) is True

    def test_dict_with_value_reduction_failed_true_returns_true(self):
        assert self._fn({"universal_value": "책임", "value_reduction_failed": True}) is True

    def test_dict_with_value_reduction_failed_string_true_returns_true(self):
        assert self._fn({"universal_value": "책임", "value_reduction_failed": "true"}) is True

    def test_dict_with_universal_value_and_no_failure_returns_false(self):
        assert self._fn({"universal_value": "책임 있는 권한"}) is False

    def test_dict_with_value_reduction_failed_false_returns_false(self):
        assert self._fn({"universal_value": "공정한 기준", "value_reduction_failed": False}) is False

    def test_dict_with_value_reduction_failed_string_false_returns_false(self):
        assert self._fn({"universal_value": "공정한 기준", "value_reduction_failed": "false"}) is False


# ── _has_forbidden_tone 테스트 (BTX-FT 시리즈) ────────────────────────────────


class TestHasForbiddenTone:
    """_has_forbidden_tone: 금지 어휘 패턴 감지 (BTX-FT 시리즈)."""

    def setup_method(self):
        from pipeline.publish_decision import _has_forbidden_tone

        self._fn = _has_forbidden_tone

    def test_clean_text_returns_empty_list(self):
        """BTX-FT001: 금지 어휘 없는 텍스트 → 빈 리스트."""
        assert self._fn("직장인이 회사에서 겪는 갑질 문제를 봤어요") == []

    def test_empty_text_returns_empty_list(self):
        """BTX-FT002: 빈 문자열 → 빈 리스트."""
        assert self._fn("") == []

    def test_끝판왕_detected(self):
        """BTX-FT003: '끝판왕' 감지."""
        result = self._fn("이 방법이 끝판왕이에요")
        assert "끝판왕" in result

    def test_팩폭_detected(self):
        """BTX-FT004: '팩폭' 감지."""
        result = self._fn("이건 팩폭이죠")
        assert "팩폭" in result

    def test_어질어질_detected(self):
        """BTX-FT005: '어질어질' 감지."""
        result = self._fn("연봉 격차가 어질어질해요")
        assert "어질어질" in result

    def test_의_감각_pattern_detected(self):
        """BTX-FT006: '~의 감각' 패턴 감지."""
        result = self._fn("리더의 감각이 중요합니다")
        assert "~의 감각" in result

    def test_의_민낯_pattern_detected(self):
        """BTX-FT007: '~의 민낯' 패턴 감지."""
        result = self._fn("직장의 민낯을 봤어요")
        assert "~의 민낯" in result

    def test_현실_자각_타임_with_space_detected(self):
        """BTX-FT008: '현실 자각 타임' (공백 포함) 감지."""
        result = self._fn("이제 현실 자각 타임입니다")
        assert "현실 자각 타임" in result

    def test_현실자각타임_without_space_detected(self):
        """BTX-FT009: '현실자각타임' (공백 없음)도 감지 (\\s* 패턴)."""
        result = self._fn("현실자각타임이에요")
        assert "현실 자각 타임" in result

    def test_multiple_forbidden_returns_all(self):
        """BTX-FT010: 여러 금지 어휘 동시 포함 → 모두 반환."""
        result = self._fn("끝판왕 팩폭 어질어질")
        assert "끝판왕" in result
        assert "팩폭" in result
        assert "어질어질" in result

    def test_기절할뻔_with_space_detected(self):
        """BTX-FT011: '기절할 뻔' (공백 있음) 감지."""
        result = self._fn("기절할 뻔 했어요")
        assert "기절할 뻔" in result


# ── NaN/Inf conflict_risk guard (PD-NI series) ───────────────────────────────


class TestPublishDecisionConflictRiskNanInf:
    """PD-NI: conflict_risk NaN/Inf → 0.0 폴백, DROP 미발동 보장."""

    def test_nan_conflict_risk_does_not_drop(self):
        """PD-NI001: conflict_risk=NaN → 0.0 폴백, publishable draft가 DROP 안 됨."""
        research = dict(RESEARCH, conflict_risk=float("nan"))
        decision = decide_publish({"twitter": 95}, {"twitter": {"passed": True}}, research, GOOD_DRAFT)
        assert decision.action != "drop"
        assert decision.metrics.get("conflict_risk") == 0.0

    def test_inf_conflict_risk_does_not_drop(self):
        """PD-NI002: conflict_risk=inf → 0.0 폴백, publishable draft가 DROP 안 됨."""
        research = dict(RESEARCH, conflict_risk=float("inf"))
        decision = decide_publish({"twitter": 95}, {"twitter": {"passed": True}}, research, GOOD_DRAFT)
        assert decision.action != "drop"
        assert decision.metrics.get("conflict_risk") == 0.0

    def test_negative_conflict_risk_becomes_zero(self):
        """PD-NI003: conflict_risk=-1.0 → 0.0 폴백 (음수 위험 점수 무효)."""
        research = dict(RESEARCH, conflict_risk=-1.0)
        decision = decide_publish({"twitter": 95}, {"twitter": {"passed": True}}, research, GOOD_DRAFT)
        assert decision.metrics.get("conflict_risk") == 0.0

    def test_valid_high_conflict_risk_metric_stored_correctly(self):
        """PD-NI004: conflict_risk=0.9 (유효) → metrics에 0.9 그대로 저장, NaN으로 오염 안 됨."""
        import math

        research = dict(RESEARCH, conflict_risk=0.9)
        decision = decide_publish({"twitter": 95}, {"twitter": {"passed": True}}, research, GOOD_DRAFT)
        stored = decision.metrics.get("conflict_risk")
        assert stored is not None
        assert math.isfinite(stored)
        assert stored == 0.9
