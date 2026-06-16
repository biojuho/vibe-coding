from pipeline.research_context import (
    _decide_closure,
    _estimate_conflict_risk,
    build_research_context,
    ensure_research_context,
    extract_anchor_words,
)


# ── extract_anchor_words ──────────────────────────────────────────────────────


def test_anchor_extracts_up_to_max_words():
    text = "연봉 인상 요청을 했더니 팀장이 거절했습니다 이런 경우 어떻게 해야 할까요"
    anchor = extract_anchor_words(text, max_words=3)
    assert anchor == "연봉 인상 요청을"


def test_anchor_empty_string_returns_empty():
    assert extract_anchor_words("") == ""


def test_anchor_single_word_within_limit():
    assert extract_anchor_words("연봉") == "연봉"


def test_anchor_collapses_extra_whitespace():
    assert extract_anchor_words("연봉   인상   요청", max_words=2) == "연봉 인상"


# ── _estimate_conflict_risk ──────────────────────────────────────────────────


def test_conflict_risk_no_keywords_returns_baseline():
    risk, flags = _estimate_conflict_risk("일반적인 직장 이야기입니다")
    assert risk == 0.15
    assert flags == []


def test_conflict_risk_single_keyword_above_baseline():
    risk, flags = _estimate_conflict_risk("MZ세대 이야기")
    assert 0.45 <= risk < 0.85
    assert any("MZ" in f for f in flags)


def test_conflict_risk_gender_slang_forces_max():
    risk, flags = _estimate_conflict_risk("한남 페미 갈등")
    assert risk >= 0.85
    assert any("한남" in f for f in flags)


def test_conflict_risk_multiple_keywords_accumulate():
    risk_one, _ = _estimate_conflict_risk("남직원 이야기")
    risk_two, _ = _estimate_conflict_risk("남직원 여직원 이야기")
    # Two unique keywords → higher risk than one
    assert risk_two > risk_one


def test_conflict_risk_capped_at_095():
    risk, _ = _estimate_conflict_risk("한남 페미 남자 여자 노조 진보 보수 정치 MZ 꼰대 세대 갑질")
    assert risk <= 0.95


# ── _decide_closure ──────────────────────────────────────────────────────────


def test_decide_closure_defaults_to_open():
    assert _decide_closure("직장 고민입니다") == "open"


def test_decide_closure_returns_closed_for_illegality_keyword():
    assert _decide_closure("이건 성희롱 사건입니다") == "closed"


def test_decide_closure_returns_closed_for_임금체불():
    assert _decide_closure("임금체불을 당했습니다") == "closed"


def test_decide_closure_갑질_returns_closed():
    assert _decide_closure("명백한 갑질입니다") == "closed"


# ── ensure_research_context ──────────────────────────────────────────────────


def test_ensure_research_context_builds_when_missing():
    post_data = {
        "title": "팀장이 야근 강요합니다",
        "content": "주말에도 출근하라고 합니다.",
    }
    ctx = ensure_research_context(post_data)
    assert isinstance(ctx, dict)
    assert "universal_value" in ctx
    assert post_data["research_context"] is ctx


def test_ensure_research_context_reuses_existing():
    existing = {"universal_value": "경계 존중", "killer_sentence": "테스트"}
    post_data = {"research_context": existing}
    result = ensure_research_context(post_data)
    assert result is existing


def test_ensure_research_context_ignores_non_dict_existing():
    post_data = {"research_context": "문자열은 무시됨"}
    ctx = ensure_research_context(post_data)
    assert isinstance(ctx, dict)
    assert ctx is not "문자열은 무시됨"  # noqa: F632


# ── build_research_context ────────────────────────────────────────────────────


def test_build_research_context_names_value_and_killer_sentence():
    context = build_research_context(
        {
            "title": "팀장이 먼저 퇴근하라고 해놓고 평가에서 태도를 봤다고 합니다",
            "content": "직원이 야근하지 않았다는 이유로 낮은 평가를 받았다는 사연입니다.",
        }
    )

    assert context["universal_value"] == "경계 존중"
    assert context["killer_sentence"]
    assert context["value_reduction_failed"] is False


def test_build_research_context_marks_short_source_as_drop_candidate():
    context = build_research_context({"title": "별로", "content": "내용 없음"})

    assert context["value_reduction_failed"] is True
    assert context["universal_value"] is None


def test_conflict_risk_detects_gender_or_camp_escalation_terms():
    context = build_research_context(
        {
            "title": "한남 페미 남직원 여직원 싸움으로 번진 회사 글",
            "content": "댓글이 성별 갈등으로 갈라질 가능성이 큰 사연입니다.",
        }
    )

    assert context["conflict_risk"] > 0.8
    assert context["conflict_requires_value_reduction"] is True


def test_anchor_extraction_uses_whitespace_boundaries_only():
    assert extract_anchor_words("빠르기때문에 잘렸다는 말이 나왔습니다", max_words=1) == "빠르기때문에"
