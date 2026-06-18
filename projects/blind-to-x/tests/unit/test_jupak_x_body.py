"""쥬팍식 4단 X 본문 회귀 테스트 (2026-06-18).

사용자 지시: X 본문은 훅 / 팩트 본문 / 요약 한 줄 / 느낌점 4단 블록 구조.
- 공통 규칙: 반말, '~다' 종결 금지, CTA 금지, X 가중 280자 이내, 추상어 동어반복 금지.
- 원문 보존: 핵심 숫자·고유명사를 그대로 살린다.
- 스레드(thread)·단문(short) 포맷 폐기 → X 본문은 단일 280자 standard 하나만.

게이트 강도: 하드룰(280자/CTA)은 error(차단), 구조(4단/'~다'/추상어)는 warning.
"""

from __future__ import annotations

from pipeline.draft_generator import TweetDraftGenerator
from pipeline.draft_quality_gate import DraftQualityGate
from pipeline.rules_loader import load_rules


def _assembled_x_prompt(topic_cluster: str) -> str:
    """토픽 클러스터별 실제 조립된 X 사용자 프롬프트 전체 텍스트."""
    gen = TweetDraftGenerator(
        config={
            "llm": {"providers": ["anthropic"]},
            "anthropic": {"enabled": True, "api_key": "k", "model": "m"},
            "tweet_style": {"tone": "casual", "max_length": 280},
        }
    )
    post = {
        "title": "t",
        "content": "세후 450만원 받는 직장인 이야기. 1200만원 티켓 같은 비현실적 숫자.",
        "source": "blind",
        "content_profile": {"topic_cluster": topic_cluster},
    }
    p = gen._build_prompt(post, top_examples=[], output_formats=["twitter"])
    return str(p) + "\n" + p.anthropic_user_prompt


# ── 프롬프트(쥬팍식 4단) 회귀 ──────────────────────────────────────────


def _twitter_standard_prompt() -> str:
    rules = load_rules()
    twitter = rules["prompt_templates"]["twitter"]
    # 스레드 포맷 폐기: twitter 템플릿은 standard 하나만 남아야 한다.
    assert "thread" not in twitter
    return twitter["standard"].format(max_length=280, source="blind", recommended_draft_type="공감형")


def test_twitter_standard_prompt_declares_four_block_structure():
    prompt = _twitter_standard_prompt()
    assert "쥬팍식 4단 구조" in prompt
    assert "훅" in prompt
    assert "팩트 본문" in prompt
    assert "요약 한 줄" in prompt
    assert "느낌점" in prompt
    assert "펀치라인" in prompt


def test_twitter_standard_prompt_states_common_rules():
    prompt = _twitter_standard_prompt()
    assert "반말로 쓴다" in prompt
    assert "'~다'로 끝나는 문어체 종결을 쓰지 않는다" in prompt
    assert "CTA 금지" in prompt
    assert "280자 이내" in prompt


def test_twitter_standard_prompt_preserves_source_numbers_and_bans_tautology():
    prompt = _twitter_standard_prompt()
    # 원문 보존 규칙 + 예시 숫자·고유명사
    assert "원문의 핵심 숫자·고유명사는 반드시 그대로 살린다" in prompt
    assert "1200만원" in prompt
    assert "뉴욕 닉스" in prompt
    # 추상어 동어반복·가치 선언은 '금지'로만 등장하고, 강제 문구는 사라져야 한다.
    assert '"이건 ~가 아니라 ~입니다"' in prompt
    assert "가치 선언을 반드시 넣으세요" not in prompt


# ── 게이트(쥬팍식 4단 검사) 회귀 ──────────────────────────────────────

# 4단 블록·반말·구체 훅을 모두 만족하는 모범 본문.
_GOOD_BODY = (
    "뉴욕 닉스 홈 최저가 티켓이 1200만원\n"
    "\n"
    "제일 비싼 자리는 2.7억\n"
    "없어서 못 가는 사람 수두룩\n"
    "\n"
    "1200만원 매진 도시에 호텔방은 남아돔\n"
    "\n"
    "돈 도는 동네는 따로 있구나 싶음\n"
    "나는 중계나 봐야지"
)


def _failed_rules(platform: str, draft: str) -> set[str]:
    result = DraftQualityGate().validate(platform, draft)
    return {item.rule for item in result.items if not item.passed}


def test_good_jupak_body_passes_without_structure_warnings():
    result = DraftQualityGate().validate("twitter", _GOOD_BODY)
    failed = {item.rule for item in result.items if not item.passed}
    assert "4단 블록 구조" not in failed
    assert "반말 종결" not in failed
    assert "추상어 동어반복" not in failed
    # 하드룰(길이/CTA/금지어) 위반이 없어 발행 가능해야 한다.
    assert result.passed, [i.rule for i in result.items if not i.passed]


def test_da_ending_triggers_banmal_warning():
    body = (
        "뉴욕 닉스 홈 최저가 티켓이 1200만원이다.\n"
        "\n"
        "제일 비싼 자리는 2.7억이다.\n"
        "\n"
        "돈 도는 동네는 따로 있다.\n"
        "\n"
        "나는 중계나 봐야겠다."
    )
    result = DraftQualityGate().validate("twitter", body)
    failed = {item.rule for item in result.items if not item.passed}
    assert "반말 종결" in failed
    # 구조는 경고일 뿐 — '~다' 종결만으로 차단(passed=False)되면 안 된다.
    banmal = next(i for i in result.items if i.rule == "반말 종결")
    assert banmal.severity == "warning"


def test_single_block_triggers_structure_warning():
    body = "뉴욕 닉스 홈 최저가 티켓이 1200만원 제일 비싼 자리는 2.7억 나는 중계나 봐야지"
    failed = _failed_rules("twitter", body)
    assert "4단 블록 구조" in failed


def test_abstract_tautology_triggers_warning():
    body = "팀장이 야근을 당연하게 여김\n\n이건 개인의 예민함이 아니라 모두가 납득할 기준의 문제\n\n나는 그냥 칼퇴함"
    result = DraftQualityGate().validate("twitter", body)
    failed = {item.rule for item in result.items if not item.passed}
    assert "추상어 동어반복" in failed
    abstract = next(i for i in result.items if i.rule == "추상어 동어반복")
    assert abstract.severity == "warning"


def test_over_280_weighted_is_hard_blocked():
    body = "가" * 141  # 한글 1자=2가중 → 282자 > 280
    result = DraftQualityGate().validate("twitter", body)
    failed = {(item.rule, item.severity) for item in result.items if not item.passed}
    assert ("최대 글자 수", "error") in failed
    assert result.passed is False


def test_cta_ending_is_hard_blocked():
    body = "연봉 3000만원 이야기\n\n다들 부럽지?\n\n여러분 생각은 어떠신가요?"
    result = DraftQualityGate().validate("twitter", body)
    assert result.passed is False
    failed = {item.rule for item in result.items if not item.passed}
    # 상투적 CTA(error) 또는 마무리 여운(질문 종결, error) 중 하나 이상이 차단해야 한다.
    assert failed & {"상투적 CTA", "마무리 여운"}


def test_jupak_structure_checks_scoped_to_twitter_only():
    # threads 등 다른 플랫폼에는 4단 구조·반말 종결 검사를 적용하지 않는다.
    body = "오늘 점심은 김치찌개였다. 맛있었다. 또 먹고 싶다."
    failed = _failed_rules("threads", body)
    assert "4단 블록 구조" not in failed
    assert "반말 종결" not in failed


def test_abstract_repetition_ignores_compound_nouns():
    # 합성어/고유명사(기준금리, 3차원)는 추상어 동어반복으로 오발하지 않는다.
    from pipeline.draft_quality_gate import _find_abstract_repetition

    assert _find_abstract_repetition("기준금리가 올랐어\n\n기준금리 인상 영향\n\n끝") is None
    assert _find_abstract_repetition("3차원에서 2차원으로 바뀜") is None
    # 단독 추상어 동어반복은 여전히 잡는다.
    assert _find_abstract_repetition("납득할 기준의 문제\n\n결국 그 기준의 문제임") is not None


def test_assembled_x_prompt_retires_lingering_and_question_endings():
    # 조립된 X 프롬프트(토픽 전략 포함)에 옛 '여운/질문/가치선언 강제'가 남으면 안 된다.
    # (twitter.standard 템플릿 단독이 아니라 topic_prompt_strategies까지 합친 전체를 검사)
    for cluster in ("재테크", "회사문화", "IT", "정치"):
        prompt = _assembled_x_prompt(cluster)
        assert "여운으로 마무리" not in prompt, cluster
        assert "마무리 질문 방식" not in prompt, cluster
        assert "가치 선언을 반드시 넣으세요" not in prompt, cluster
        assert "느낌점" in prompt, cluster


# ── CTA 감지 확장 (engagement-bait 변형) ──────────────────────────────


def test_expanded_generic_cta_variants_are_hard_blocked():
    # 기존 6패턴이 놓치던 참여 유도 변형(공감하면/공감되면/다들 공감/너희 생각/여러분도)을
    # 상투적 CTA(error)로 차단해야 한다.
    for body in (
        "연봉 3000만원 이야기\n\n생각보다 적네\n\n다들 공감하지?",
        "월급 명세서 공개\n\n세후 450만원\n\n공감하면 알려줘",
        "퇴사 후기 5줄 정리\n\n속이 시원하네\n\n너희 생각은?",
        "주 4일제 시범 도입\n\n금요일이 사라짐\n\n여러분도 부럽지?",
    ):
        result = DraftQualityGate().validate("twitter", body)
        failed = {item.rule for item in result.items if not item.passed}
        assert result.passed is False, body
        assert "상투적 CTA" in failed, (body, failed)


def test_valid_jupak_punchline_not_misflagged_as_cta():
    # 정상 1인칭 펀치라인은 CTA 오탐되면 안 된다 (over-block 회귀 방지).
    failed = {item.rule for item in DraftQualityGate().validate("twitter", _GOOD_BODY).items if not item.passed}
    assert "상투적 CTA" not in failed


# ── 반말 종결 프롬프트 강화 (구체 예시) ───────────────────────────────


def test_twitter_prompt_gives_concrete_banmal_ending_examples():
    # 모델 준수도를 높이기 위해 문어체→구어체 변환 예시를 명시한다.
    prompt = _twitter_standard_prompt()
    assert "고민이다→고민됨" in prompt
    assert "문제입니다→문제임" in prompt
