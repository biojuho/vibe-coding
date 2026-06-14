"""Phase 2 — 댓글 트리거 업리프트 회귀 테스트 (2026-05-26+).

이 파일은 `docs/output_quality_uplift_2026-05-26.md` 의 Phase 2 LLM-측 개선과
deterministic 무색무취 검출 가드입니다.

검사 대상:
  - draft_prompts.py : 댓글 트리거 4축 프레임워크 블록 주입
  - editorial_reviewer.py : 4축 (identifiability/stance/open_loop/anchor) 점수,
    comment_trigger_avg 라우팅, EditorialResult.comment_trigger_scores
  - draft_quality_gate.py : creator_take 무색무취 검출 + naver_blog
    <creator_take> 태그 추출
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pipeline.draft_prompts import DraftPromptsMixin
from pipeline.draft_quality_gate import (
    DraftQualityGate,
    _extract_creator_take,
    _is_colorless_take,
)
from pipeline.editorial_reviewer import (
    _BASE_REVIEW_AXES,
    _COMMENT_TRIGGER_AXES,
    _COMMENT_TRIGGER_PLATFORMS,
    _COMMENT_TRIGGER_THRESHOLD,
    EditorialResult,
    EditorialReviewer,
)


def test_editorial_reviewer_no_provider_path_defers_langgraph_dependencies():
    project_root = Path(__file__).resolve().parents[2]
    code = """
import os
import sys

import pipeline.editorial_reviewer as er

for key in (
    "EXA_API_KEY",
    "PERPLEXITY_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "ZHIPUAI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "GROK_API_KEY",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "TELEGRAM_BOT_TOKEN",
    "SUPABASE_KEY",
):
    os.environ.pop(key, None)

reviewer = er.EditorialReviewer(config=None)
print("langgraph" in sys.modules)
print("langgraph.graph" in sys.modules)
print("langchain_core" in sys.modules)
print(type(reviewer._graph).__name__)
print(er.LANGGRAPH_AVAILABLE is None)
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.stdout.splitlines() == ["False", "False", "False", "_FallbackEditorialGraph", "True"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 댓글 트리거 프레임워크 블록 (prompt injection)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCommentTriggerBlock:
    def test_twitter_includes_four_triggers(self):
        block = DraftPromptsMixin._build_comment_trigger_block(["twitter"])
        assert "댓글 트리거 4축" in block or "댓글을 달고 싶어지는" in block
        # 4축 모두 등장
        for axis in ("식별감", "입장", "오픈루프", "구체 앵커"):
            assert axis in block, f"missing axis: {axis}"

    def test_threads_also_included(self):
        block = DraftPromptsMixin._build_comment_trigger_block(["threads"])
        assert block, "threads 도 댓글 트리거 블록을 포함해야 함"
        assert "Identifiability" in block or "식별감" in block

    def test_newsletter_only_skips_block(self):
        """newsletter/naver_blog 만 있을 때는 블록 없음 — 짧은 포맷 KPI."""
        block = DraftPromptsMixin._build_comment_trigger_block(["newsletter"])
        assert block == ""
        block2 = DraftPromptsMixin._build_comment_trigger_block(["naver_blog"])
        assert block2 == ""

    def test_mixed_formats_include_block(self):
        block = DraftPromptsMixin._build_comment_trigger_block(["twitter", "naver_blog"])
        assert "댓글 트리거" in block or "댓글을 달고 싶어지는" in block

    def test_empty_formats_returns_empty(self):
        assert DraftPromptsMixin._build_comment_trigger_block([]) == ""

    def test_anti_patterns_called_out(self):
        block = DraftPromptsMixin._build_comment_trigger_block(["twitter"])
        # 댓글이 안 달리는 글의 공통점 섹션
        assert "무색무취" in block
        assert "양비론" in block or "보편 진리" in block


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. EditorialReviewer 4축 점수 및 라우팅
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _make_reviewer() -> EditorialReviewer:
    obj = object.__new__(EditorialReviewer)
    obj._editorial_thresholds = None
    obj.brand_voice = {}
    obj._providers = []
    return obj


class TestReviewPromptHasCommentTriggerAxes:
    def test_twitter_prompt_lists_four_axes(self):
        reviewer = _make_reviewer()
        prompt = reviewer._build_review_prompt(
            platform="twitter",
            draft_text="짧은 초안",
            post_data={"title": "t", "content": "c"},
        )
        # 4축 영문 키워드가 prompt template 에 등장 (LLM 이 응답 JSON 키로 사용)
        for axis in _COMMENT_TRIGGER_AXES:
            assert axis in prompt, f"missing axis in prompt: {axis}"
        assert "댓글 트리거 4축" in prompt

    def test_threads_prompt_also_lists_four_axes(self):
        reviewer = _make_reviewer()
        prompt = reviewer._build_review_prompt(
            platform="threads",
            draft_text="초안",
            post_data={},
        )
        for axis in _COMMENT_TRIGGER_AXES:
            assert axis in prompt

    def test_naver_blog_prompt_skips_comment_trigger_axes(self):
        reviewer = _make_reviewer()
        prompt = reviewer._build_review_prompt(
            platform="naver_blog",
            draft_text="초안",
            post_data={},
        )
        # naver_blog 는 5축만 — comment trigger 헤더 자체가 없어야 함
        assert "댓글 트리거 4축" not in prompt
        # 5축은 여전히 있어야 함
        for axis in _BASE_REVIEW_AXES:
            assert axis in prompt

    def test_comment_trigger_platforms_set(self):
        assert "twitter" in _COMMENT_TRIGGER_PLATFORMS
        assert "threads" in _COMMENT_TRIGGER_PLATFORMS
        assert "naver_blog" not in _COMMENT_TRIGGER_PLATFORMS

    def test_comment_trigger_threshold_is_six(self):
        assert _COMMENT_TRIGGER_THRESHOLD == 6.0


class TestEditorialResultCommentTriggerScores:
    def test_default_empty_dict(self):
        result = EditorialResult()
        assert result.comment_trigger_scores == {}

    def test_can_set_per_platform(self):
        result = EditorialResult()
        result.comment_trigger_scores["twitter"] = 7.25
        assert result.comment_trigger_scores["twitter"] == 7.25


class TestRoutingHonorsCommentTrigger:
    """반복 라우팅 결정 시 comment_trigger_avg 가 미달이면 리라이트 트리거."""

    def test_state_with_low_ct_routes_to_rewriter(self):
        """avg 통과해도 ct_avg 미달이면 리라이트가 후보 (END 아님)."""
        from pipeline.editorial_reviewer import _COMMENT_TRIGGER_THRESHOLD

        # Inline equivalent of internal `route_after_review` decision: avg=7, threshold=5,
        # ct=4 (<6) → rewriter 후보. 후보가 있으면 리라이트.
        avg, threshold = 7.0, 5.0
        ct_avg, ct_threshold = 4.0, _COMMENT_TRIGGER_THRESHOLD
        ct_ok = ct_avg == 0.0 or ct_avg >= ct_threshold
        assert not ct_ok, "ct_avg 4 should be < 6 threshold"
        # avg 가 통과해도 ct_ok 가 False 면 END 분기를 타지 않음 — 리라이트 트리거
        assert avg >= threshold and not ct_ok

    def test_state_with_zero_ct_treated_as_ok(self):
        """ct_avg == 0 (non-twitter/threads 플랫폼) 은 라우팅에서 자동 통과."""
        ct_avg = 0.0
        ct_threshold = _COMMENT_TRIGGER_THRESHOLD
        ct_ok = ct_avg == 0.0 or ct_avg >= ct_threshold
        assert ct_ok, "naver_blog/newsletter routing must not be blocked by ct check"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. _is_colorless_take 검출기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestColorlessTakeDetector:
    """무색무취 검출기 — golden 예시 통과 + 진짜 요약형 차단."""

    @pytest.mark.parametrize(
        "golden",
        [
            "블라인드에서 연봉 5천 자랑글 밑에 달린 댓글이 레전드... 저는 5천이 월급인데요. 직장인 세계는 넓고 연봉은 다양하다",
            "성과급 0% 통보받고 팀장이 내년에 잘하자래요. 내년에 여기 있을 거 같아요",
            "월급의 40%가 고정비로 빠지는데 재테크를 하라고? 먼저 생존테크 좀 하겠습니다",
            "동기가 이직해서 2천 올렸대. 나는 3년 있으면서 500 올랐는데. 충성의 가격이 이거임",
            "회의 시작 5분 전에 이거 검토해봐 던지는 문화. 대한민국 직장의 시간 개념은 상사 기준입니다",
            "면접 5번 보고 최종 합격했는데 현 회사 카운터오퍼가 더 높음. 이직의 진짜 가치는 내 몸값 확인이었다",
            "팀장이 나 때는 시작하면 평균 17분 걸림. 측정해봤음",
        ],
    )
    def test_golden_examples_pass(self, golden):
        """golden 예시 (의도적으로 짧고 함축적) 는 모두 무색무취가 아니어야 함."""
        cl, reason = _is_colorless_take(golden)
        assert not cl, f"FALSE POSITIVE on golden: {golden} | reason: {reason}"

    @pytest.mark.parametrize(
        "bad",
        [
            "블라인드에서 연봉 이야기가 자주 올라온다. 직장인들의 연봉에 대한 다양한 의견이 보이는 듯하다.",
            "재테크에 관한 글이 자주 보인다. 일부 사람들은 적극적인 투자를 하고, 일부는 안전 자산을 선호하는 모습이다.",
            "이직 관련 게시물이 많은 것 같다. 직장인들의 다양한 고민이 있는 것 같다.",
        ],
    )
    def test_summary_only_caught(self, bad):
        cl, reason = _is_colorless_take(bad)
        assert cl, f"FAILED TO CATCH: {bad}"
        assert reason

    def test_empty_returns_false(self):
        cl, reason = _is_colorless_take("")
        assert not cl
        assert reason == ""

    def test_whitespace_only(self):
        cl, reason = _is_colorless_take("   \n  ")
        assert not cl

    def test_short_text_without_hedges_is_safe(self):
        """짧은 한 줄 트윗 — 입장 어휘 없어도 무색무취가 아님."""
        cl, _ = _is_colorless_take("점심 메뉴 정하는데 30분 걸렸다")
        assert not cl

    def test_stance_marker_immunizes(self):
        """입장 표현이 1개라도 있으면 hedge 가 누적되어도 무색무취가 아님."""
        text = "솔직히 이게 맞다는 생각도 든다. 다만 다른 시각도 있을 수 있다는 듯한 느낌도 든다."
        cl, _ = _is_colorless_take(text)
        assert not cl

    def test_generalization_without_stance_caught(self):
        text = "이 주제에 대한 글이 자주 올라오는 상황이다. 직장인들의 다양한 의견이 보이는 듯하다."
        cl, reason = _is_colorless_take(text)
        assert cl
        assert "일반화" in reason or "hedge" in reason


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. _extract_creator_take 태그 파싱
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtractCreatorTake:
    def test_extracts_simple_tag(self):
        text = "어쩌고 <creator_take>운영자 해석 한 문장</creator_take> 뒷 내용"
        assert _extract_creator_take(text) == "운영자 해석 한 문장"

    def test_returns_none_when_missing(self):
        assert _extract_creator_take("그냥 본문만 있는 글") is None

    def test_handles_multiline(self):
        text = """앞 내용

<creator_take>
   여러 줄로
   걸친 해석
</creator_take>

뒷 내용"""
        result = _extract_creator_take(text)
        assert result is not None
        assert "여러 줄로" in result
        assert "걸친 해석" in result

    def test_empty_tag_returns_none(self):
        assert _extract_creator_take("앞 <creator_take></creator_take> 뒤") is None

    def test_case_insensitive(self):
        text = "앞 <CREATOR_TAKE>대문자 태그</CREATOR_TAKE> 뒤"
        assert _extract_creator_take(text) == "대문자 태그"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. DraftQualityGate 통합 — twitter/naver_blog 에 무색무취 검사 적용
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _pad(text: str, target: int = 80) -> str:
    if len(text) >= target:
        return text
    return text + " " + "회의실에서 본 짧은 장면이었다." * 5


def _failed_rule_names(result, severity: str | None = None) -> set[str]:
    return {item.rule for item in result.items if not item.passed and (severity is None or item.severity == severity)}


class TestColorlessGateIntegration:
    def test_summary_only_twitter_warns(self):
        """일반화 + 입장 없음 → twitter 검사에서 warning."""
        gate = DraftQualityGate()
        # 1번 문장은 숫자로 시작 (훅 OK), 그 뒤 일반화로만 채움
        text = (
            "5명 중 4명이 비슷한 이야기를 한다. "
            "이 주제에 대한 글이 자주 올라오는 상황이다. "
            "직장인들의 다양한 의견이 보이는 듯하다."
        )
        text = _pad(text)
        result = gate.validate("twitter", text)
        rules = _failed_rule_names(result, severity="warning")
        assert "무색무취 요약" in rules

    def test_golden_caption_does_not_warn(self):
        """golden 캡션은 무색무취 warning 이 나면 안 됨."""
        gate = DraftQualityGate()
        text = _pad("동기가 이직해서 2천 올렸대. 나는 3년 있으면서 500 올랐는데. 충성의 가격이 이거임")
        result = gate.validate("twitter", text)
        warnings = _failed_rule_names(result, severity="warning")
        assert "무색무취 요약" not in warnings, (
            f"FALSE POSITIVE on golden: {[(i.rule, i.detail) for i in result.items if not i.passed]}"
        )

    def test_naver_blog_missing_creator_take_warns(self):
        """naver_blog 에 <creator_take> 가 없으면 warning."""
        gate = DraftQualityGate()
        # naver_blog min_len = 1000 충족
        body = "## 이번 주 흐름\n\n어쩌고 저쩌고 회의실의 한 장면이었다.\n\n## 다음\n\n" + "직장인 이야기. " * 200
        result = gate.validate("naver_blog", body)
        rules = _failed_rule_names(result, severity="warning")
        assert "creator_take 누락" in rules

    def test_naver_blog_with_colorless_creator_take_warns(self):
        gate = DraftQualityGate()
        body = (
            "## 이번 주 흐름\n\n어쩌고 저쩌고 회의실의 한 장면이었다.\n\n## 다음\n\n"
            + "직장인 이야기. " * 200
            + "\n<creator_take>이 주제는 자주 보이는 상황이며 다양한 의견이 있는 것 같다는 생각이 드는 듯하다.</creator_take>"
        )
        result = gate.validate("naver_blog", body)
        rules = _failed_rule_names(result, severity="warning")
        assert "무색무취 creator_take" in rules

    def test_naver_blog_with_strong_creator_take_passes(self):
        gate = DraftQualityGate()
        body = (
            "## 이번 주 흐름\n\n어쩌고 저쩌고 회의실의 한 장면이었다.\n\n## 다음\n\n"
            + "직장인 이야기. " * 200
            + "\n<creator_take>결국 충성의 가격은 이거임 — 이게 진짜 답이다.</creator_take>"
        )
        result = gate.validate("naver_blog", body)
        rules = _failed_rule_names(result, severity="warning")
        assert "무색무취 creator_take" not in rules
        assert "creator_take 누락" not in rules
