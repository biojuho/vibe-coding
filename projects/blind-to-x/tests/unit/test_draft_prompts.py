"""Tests for pipeline.draft_prompts pure helpers."""

from __future__ import annotations

from unittest.mock import patch

from pipeline.draft_prompts import DraftPromptsMixin


# ── _extract_content_essence (static, no LLM) ───────────────────────────────


class TestExtractContentEssence:
    """Tests for the deterministic content essence extractor."""

    def test_numbers_with_context(self):
        post = {"content": "연봉이 5000만원인데 3개월만에 50배 올랐다"}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["key_numbers"]) >= 1
        # At least one number snippet should contain a digit
        assert any(c.isdigit() for snippet in result["key_numbers"] for c in snippet)

    def test_quotes_extraction(self):
        post = {"content": "그는 \"일이 사람을 만든다\"라고 말했다. 또한 '포기하지 마'라는 격언도 있다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["quotes"]) >= 1

    def test_quotes_korean_brackets(self):
        post = {"content": "기사에서 「경제 위기」와 『생존 전략』을 다루었다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["quotes"]) >= 1

    def test_empty_content(self):
        result = DraftPromptsMixin._extract_content_essence({})
        assert result["key_numbers"] == []
        assert result["quotes"] == []
        assert result["emotional_peaks"] == []
        assert result["opening"] == ""
        assert result["closing"] == ""

    def test_title_preserved(self):
        post = {"title": "연봉 협상 꿀팁", "content": "본문입니다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert result["title"] == "연봉 협상 꿀팁"

    def test_opening_closing(self):
        post = {"content": "첫 문장은 이렇게 시작합니다. 중간 문장이 있습니다. 마지막으로 결론을 맺습니다."}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert "첫 문장" in result["opening"]
        assert "결론" in result["closing"]

    def test_max_numbers_cap(self):
        # Generate content with many numbers
        numbers = " ".join(f"{i * 100}만원" for i in range(1, 20))
        post = {"content": numbers}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["key_numbers"]) <= 8

    def test_max_quotes_cap(self):
        quotes = " ".join(f'"인용구 번호 {i}입니다 충분히 긴 문장"' for i in range(10))
        post = {"content": quotes}
        result = DraftPromptsMixin._extract_content_essence(post)
        assert len(result["quotes"]) <= 5


class TestBuildPromptResearchContext:
    def _make_instance(self):
        obj = object.__new__(DraftPromptsMixin)
        obj.tone = "담담한 직장인 톤"
        obj.max_length = 280
        obj.threads_tone = "친근한 톤"
        obj.threads_max_length = 500
        obj.threads_hashtags_count = 2
        obj.blog_tone = "전문 에디터 톤"
        obj.blog_min_length = 450
        obj.blog_max_length = 900
        obj.blog_seo_tags_count = 3

        class _RegulationChecker:
            def build_regulation_context(self, platforms):
                return ""

        obj.regulation_checker = _RegulationChecker()
        return obj

    @patch(
        "pipeline.draft_prompts._load_draft_rules",
        return_value={"prompt_templates": {}, "tone_mapping": {}, "emotion_rules": []},
    )
    def test_research_context_is_injected_into_user_prompt(self, mock_rules):
        obj = self._make_instance()
        prompt = obj._build_prompt(
            {
                "source": "blind",
                "title": "상사가 야근을 당연하게 여긴다는 글",
                "content": "팀장이 매일 퇴근 직전에 일을 줍니다.",
                "research_context": {
                    "source_frame": "개인이 편하게 일하고 싶다는 문제",
                    "real_issue": "일의 책임과 개인 시간의 경계를 어디에 둘 것인가",
                    "universal_value": "경계 존중",
                    "killer_sentence": "이건 편하게 일하자는 게 아니라 일과 삶의 경계를 지키자는 말입니다",
                    "closure": "open",
                    "conflict_risk": 0.91,
                    "anchor": "팀장이 매일 퇴근 직전에 일을 줍니다.",
                },
            },
            top_examples=[],
            output_formats=["twitter"],
        )

        assert "[오토리서치 컨텍스트 - 반드시 반영]" in prompt.anthropic_user_prompt
        assert "보편 가치: 경계 존중" in prompt.anthropic_user_prompt
        assert "갈등 위험 높음" in prompt.anthropic_user_prompt
        assert "위 킬러 문장을 그대로 1회 포함" in prompt.anthropic_user_prompt


# ── _select_examples_deterministically ───────────────────────────────────────


class TestSelectExamplesDeterministically:
    def test_deterministic_same_seed(self):
        examples = [{"text": f"example {i}"} for i in range(10)]
        r1 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_a")
        r2 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_a")
        assert r1 == r2

    def test_different_seed_different_result(self):
        examples = [{"text": f"example {i}"} for i in range(10)]
        r1 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_a")
        r2 = DraftPromptsMixin._select_examples_deterministically(examples, 3, "seed_b")
        # Different seeds should (almost certainly) produce different orderings
        assert r1 != r2

    def test_limit_exceeds_list(self):
        examples = [{"text": "a"}, {"text": "b"}]
        result = DraftPromptsMixin._select_examples_deterministically(examples, 5, "seed")
        assert len(result) == 2

    def test_empty_list(self):
        result = DraftPromptsMixin._select_examples_deterministically([], 3, "seed")
        assert result == []

    def test_limit_zero(self):
        examples = [{"text": "a"}]
        result = DraftPromptsMixin._select_examples_deterministically(examples, 0, "seed")
        # limit=0 → len(examples)=1 > 0 is True, so sorting happens then [:0]
        assert len(result) == 0


# ── _build_retry_prompt ──────────────────────────────────────────────────────


class TestBuildRetryPrompt:
    def _make_instance(self):
        """Create a minimal object with the mixin."""
        obj = object.__new__(DraftPromptsMixin)
        return obj

    def test_basic_feedback_injection(self):
        obj = self._make_instance()
        feedback = [
            {"platform": "twitter", "score": 40, "issues": ["최소 글자 수 미달"]},
        ]
        result = obj._build_retry_prompt("원본 프롬프트", feedback)
        assert "원본 프롬프트" in result
        assert "twitter" in result
        assert "40/100" in result
        assert "최소 글자 수 미달" in result
        # Fix instruction should be matched
        assert "수정 방법" in result

    def test_multiple_platforms(self):
        obj = self._make_instance()
        feedback = [
            {"platform": "twitter", "score": 30, "issues": ["CTA 위반"]},
            {"platform": "threads", "score": 50, "issues": ["해시태그 초과"]},
        ]
        result = obj._build_retry_prompt("prompt", feedback)
        assert "twitter" in result
        assert "threads" in result

    def test_unmatched_issue_still_listed(self):
        obj = self._make_instance()
        feedback = [
            {"platform": "x", "score": 60, "issues": ["알 수 없는 문제"]},
        ]
        result = obj._build_retry_prompt("prompt", feedback)
        assert "알 수 없는 문제" in result
        assert "x" in result
