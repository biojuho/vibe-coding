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
