from pipeline.research_context import build_research_context, extract_anchor_words


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
