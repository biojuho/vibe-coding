"""B-5: 품질 게이트 불통과 → LLM 자동 재생성 루프 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock
from typing import Any

from pipeline.draft_quality_gate import (
    DraftQualityGate,
)


class TestQualityGateRetryPrompt(unittest.TestCase):
    """_build_retry_prompt 메서드 테스트."""

    def _make_generator(self) -> Any:
        """최소 config로 TweetDraftGenerator 인스턴스 생성."""
        from pipeline.draft_generator import TweetDraftGenerator

        class FakeConfig:
            def get(self, key, default=None):
                defaults = {
                    "tweet_style": {},
                    "threads_style": {},
                    "naver_blog_style": {},
                    "llm.strategy": "fallback",
                    "llm.max_retries_per_provider": 2,
                    "llm.request_timeout_seconds": 10,
                    "llm.providers": [],
                    "anthropic.enabled": False,
                    "openai.enabled": False,
                    "openai.chat_enabled": False,
                    "gemini.enabled": False,
                    "xai.enabled": False,
                    "ollama.enabled": False,
                }
                return defaults.get(key, default)

        with patch("pipeline.draft_generator.RegulationChecker"):
            gen = TweetDraftGenerator(config=FakeConfig())
        return gen

    def test_retry_prompt_includes_feedback(self):
        gen = self._make_generator()
        feedback = [
            {"platform": "twitter", "score": 50, "issues": ["최소 글자 수: 40자 (최소 60자 필요)"]},
            {"platform": "threads", "score": 30, "issues": ["초안이 비어 있습니다"]},
        ]
        result = gen._build_retry_prompt("원본 프롬프트", feedback)
        assert "원본 프롬프트" in result
        assert "twitter" in result
        assert "최소 글자 수" in result
        assert "threads" in result
        assert "재작성 지침" in result

    def test_retry_prompt_empty_feedback(self):
        gen = self._make_generator()
        result = gen._build_retry_prompt("원본", [])
        assert "원본" in result
        assert "재작성 지침" in result

    def test_retry_prompt_preserves_original(self):
        gen = self._make_generator()
        original = "[게시글 정보]\n출처: 블라인드\n제목: 연봉 이야기"
        feedback = [{"platform": "twitter", "score": 60, "issues": ["CTA 없음"]}]
        result = gen._build_retry_prompt(original, feedback)
        assert "[게시글 정보]" in result
        assert "출처: 블라인드" in result


class TestQualityGateRetryDecision(unittest.TestCase):
    """품질 게이트의 should_retry 판단 로직 테스트."""

    def test_error_severity_triggers_retry(self):
        gate = DraftQualityGate()
        # 너무 짧은 트윗 → error severity → should_retry
        result = gate.validate("twitter", "짧은 글")
        assert result.should_retry is True
        assert result.passed is False

    def test_warning_only_no_retry(self):
        gate = DraftQualityGate()
        # CTA warning이 있더라도 error severity가 아니면 retry는 안 함
        # 60자 이상 + 280자 이하 범위를 충족해야 min/max_len error를 피할 수 있음
        good_text = (
            "블라인드에서 연봉 5천 자랑글이 올라오자 댓글창이 바로 불붙었습니다. "
            "당신이라면 이런 글에 한 줄로 뭐라고 답하시겠어요? 실제 반응을 댓글로 남겨주세요!"
        )
        assert len(good_text) >= 60, f"테스트 텍스트가 너무 짧음: {len(good_text)}자"
        result = gate.validate("twitter", good_text)
        # warning만 있는 경우 should_retry는 False
        assert result.should_retry is False

    def test_passing_draft_no_retry(self):
        gate = DraftQualityGate()
        # 길이 OK + CTA OK → should_retry=False
        text = (
            "연봉 협상 전에 꼭 챙겨야 할 체크리스트 3가지가 있습니다. "
            "첫 제안 받았을 때 가장 먼저 확인하는 숫자가 뭔가요? 실전 팁을 댓글로 공유해주세요."
        )
        result = gate.validate("twitter", text)
        assert result.should_retry is False


class TestGenerateDraftsQualityFeedback(unittest.TestCase):
    """generate_drafts에 quality_feedback 전달 시 캐시 스킵 등 동작 테스트."""

    def _make_generator(self) -> Any:
        from pipeline.draft_generator import TweetDraftGenerator

        class FakeConfig:
            def get(self, key, default=None):
                defaults = {
                    "tweet_style": {},
                    "threads_style": {},
                    "naver_blog_style": {},
                    "llm.strategy": "fallback",
                    "llm.max_retries_per_provider": 1,
                    "llm.request_timeout_seconds": 5,
                    "llm.providers": ["gemini"],
                    "anthropic.enabled": False,
                    "openai.enabled": False,
                    "openai.chat_enabled": False,
                    "gemini.enabled": True,
                    "xai.enabled": False,
                    "ollama.enabled": False,
                }
                return defaults.get(key, default)

        with patch("pipeline.draft_generator.RegulationChecker"):
            gen = TweetDraftGenerator(config=FakeConfig())
        gen.gemini_enabled = True
        gen.gemini_api_key = "fake-key"
        return gen

    def test_quality_feedback_skips_cache(self):
        """quality_feedback이 있으면 캐시 조회를 건너뛰어야 함."""
        gen = self._make_generator()
        feedback = [{"platform": "twitter", "score": 40, "issues": ["Too short"]}]

        # 캐시를 mock하여 호출 여부 추적
        mock_cache = MagicMock()
        mock_cache.get.return_value = ({"twitter": "cached"}, None)
        gen.draft_cache = mock_cache

        import asyncio

        async def _run():
            # quality_feedback이 있으므로 캐시 get은 호출되지 않아야 함
            # 하지만 실제 LLM 호출은 실패할 것이므로 에러 무시
            try:
                await gen.generate_drafts(
                    {"title": "test", "content": "test content"},
                    output_formats=["twitter"],
                    quality_feedback=feedback,
                )
            except Exception:
                pass
            # quality_feedback이 있으므로 cache.get은 호출되지 않아야 함
            mock_cache.get.assert_not_called()

        asyncio.run(_run())

    def test_no_feedback_uses_cache(self):
        """quality_feedback이 없으면 캐시를 정상 조회해야 함."""
        gen = self._make_generator()

        mock_cache = MagicMock()
        mock_cache.get.return_value = ({"twitter": "cached", "_provider_used": "cached"}, None)
        gen.draft_cache = mock_cache

        import asyncio

        async def _run():
            result = await gen.generate_drafts(
                {"title": "test", "content": "test content"},
                output_formats=["twitter"],
            )
            mock_cache.get.assert_called_once()
            assert result[0]["twitter"] == "cached"

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
