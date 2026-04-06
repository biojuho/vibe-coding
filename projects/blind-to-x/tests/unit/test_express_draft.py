"""Unit tests for pipeline.express_draft — ExpressDraftPipeline."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.express_draft import ExpressDraftPipeline, ExpressDraftResult
from pipeline.enrichment_engine import EnrichedContext


class _MockConfig:
    def get(self, key, default=None):
        return default


def _mock_enrichment_engine():
    """ContextEnrichmentEngine 모킹 — process_topic이 None 반환."""
    mock = MagicMock()
    mock.process_topic = AsyncMock(return_value=None)
    return mock


class TestExpressDraftResult:
    """ExpressDraftResult 데이터 클래스 테스트."""

    def test_defaults(self):
        r = ExpressDraftResult()
        assert r.success is False
        assert r.draft_x == ""
        assert r.draft_threads == ""
        assert r.error == ""
        assert r.cost_usd == 0.0


class TestExpressDraftPipeline:
    """ExpressDraftPipeline 단위 테스트."""

    def _make_pipeline(self, draft_generator=None, timeout=60):
        config = _MockConfig()
        pipeline = ExpressDraftPipeline(
            config_mgr=config,
            draft_generator=draft_generator,
            timeout_seconds=timeout,
        )
        # 기본적으로 enrichment engine을 mock으로 교체 (외부 API 호출 방지)
        pipeline._enrichment_engine = _mock_enrichment_engine()
        return pipeline

    @pytest.mark.asyncio
    async def test_generate_timeout(self):
        """타임아웃 시 에러 메시지 반환."""
        pipeline = self._make_pipeline(timeout=1)

        # _call_llm이 오래 걸리도록 mock
        async def slow_llm(*args, **kwargs):
            import asyncio

            await asyncio.sleep(10)
            return {"response": "too late"}

        pipeline._call_llm = slow_llm

        result = await pipeline.generate(
            title="테스트",
            content_preview="내용",
            source="blind",
        )
        assert result.success is False
        assert "타임아웃" in result.error
        assert result.generation_time_sec > 0

    @pytest.mark.asyncio
    async def test_generate_success_with_mock_provider(self):
        """Mock LLM provider로 정상 생성."""
        mock_provider = MagicMock()
        mock_provider.name = "deepseek"
        mock_response = json.dumps(
            {
                "x": "🔥 블라인드에서 지금 난리남",
                "threads": "블라인드에서 화제인 글이 있는데...",
            }
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        mock_generator = MagicMock()
        mock_generator.providers = [mock_provider]

        pipeline = self._make_pipeline(draft_generator=mock_generator)

        result = await pipeline.generate(
            title="연봉 1억 달성 후기",
            content_preview="드디어 5년차에 연봉 1억을 달성했습니다...",
            source="blind",
            velocity_score=12.5,
        )
        assert result.success is True
        assert len(result.draft_x) > 0
        assert len(result.draft_threads) > 0
        assert result.provider_used == "deepseek"

    @pytest.mark.asyncio
    async def test_generate_no_provider_raises(self):
        """provider 없으면 에러."""
        pipeline = self._make_pipeline()
        result = await pipeline.generate(
            title="테스트",
            content_preview="내용",
        )
        assert result.success is False
        assert len(result.error) > 0

    @pytest.mark.asyncio
    async def test_generate_provider_all_fail_fallback(self):
        """모든 provider 실패 시 에러."""
        mock_provider = MagicMock()
        mock_provider.name = "broken"
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("API 에러"))

        mock_generator = MagicMock()
        mock_generator.providers = [mock_provider]

        pipeline = self._make_pipeline(draft_generator=mock_generator)
        result = await pipeline.generate(
            title="실패",
            content_preview="",
        )
        assert result.success is False

    @pytest.mark.asyncio
    async def test_generate_with_enriched_context(self):
        """[Phase 7] enrichment engine이 데이터를 반환하면 프롬프트에 주입."""
        mock_provider = MagicMock()
        mock_provider.name = "deepseek"
        mock_response = json.dumps(
            {
                "x": "🔥 AI 인재 전쟁 시작",
                "threads": "AI 채용 시장이 뜨겁습니다...",
            }
        )
        mock_provider.generate = AsyncMock(return_value=mock_response)

        mock_generator = MagicMock()
        mock_generator.providers = [mock_provider]

        pipeline = self._make_pipeline(draft_generator=mock_generator)

        # enrichment engine이 실제 데이터를 반환하도록 설정
        enriched = EnrichedContext(
            original_topic="AI 채용",
            deep_insights="전년 대비 200% 수요 증가",
            global_references=["https://example.com/ai-hiring"],
            sentiment_angle="열광적 - 기술 기업 대거 채용 중",
        )
        pipeline._enrichment_engine.process_topic = AsyncMock(return_value=enriched)

        result = await pipeline.generate(
            title="AI 채용",
            content_preview="AI 개발자 연봉 폭등",
            source="blind",
            velocity_score=15.0,
        )
        assert result.success is True

        # provider.generate에 전달된 user_prompt에 enriched context가 주입되었는지 확인
        call_args = mock_provider.generate.call_args
        user_prompt = call_args.kwargs.get("user_prompt", "")
        assert "200%" in user_prompt or "Enriched" in user_prompt

    def test_parse_response_json(self):
        """JSON 포맷 응답 파싱."""
        raw = {"response": '{"x": "트윗", "threads": "스레드"}'}
        parsed = ExpressDraftPipeline._parse_response(raw)
        assert parsed["x"] == "트윗"
        assert parsed["threads"] == "스레드"

    def test_parse_response_json_in_text(self):
        """텍스트 안에 JSON이 포함된 경우."""
        raw = {"response": '여기 결과입니다:\n{"x": "결과", "threads": "스레드"}\n끝'}
        parsed = ExpressDraftPipeline._parse_response(raw)
        assert parsed["x"] == "결과"

    def test_parse_response_plain_text_fallback(self):
        """JSON 없으면 텍스트 전체를 초안으로 사용."""
        raw = {"response": "그냥 텍스트 응답입니다"}
        parsed = ExpressDraftPipeline._parse_response(raw)
        assert parsed["x"] == "그냥 텍스트 응답입니다"
        assert len(parsed["threads"]) > 0

    def test_parse_response_empty(self):
        """빈 응답."""
        raw = {"response": ""}
        parsed = ExpressDraftPipeline._parse_response(raw)
        assert parsed["x"] == ""

    def test_build_user_prompt_includes_context(self):
        """사용자 프롬프트에 소스, 속도점수, 제목, 내용이 포함."""
        pipeline = self._make_pipeline()
        prompt = pipeline._build_user_prompt(
            title="연봉 후기",
            content_preview="5년차 연봉 1억",
            source="blind",
            velocity_score=8.5,
        )
        assert "블라인드" in prompt
        assert "8.5" in prompt
        assert "연봉 후기" in prompt
        assert "5년차 연봉 1억" in prompt

    def test_build_user_prompt_unknown_source(self):
        """알 수 없는 소스는 원문 그대로."""
        pipeline = self._make_pipeline()
        prompt = pipeline._build_user_prompt(
            title="t",
            content_preview="c",
            source="reddit",
            velocity_score=1.0,
        )
        assert "reddit" in prompt

    def test_build_user_prompt_with_enriched(self):
        """[Phase 7] EnrichedContext가 주어지면 프롬프트에 포함."""
        pipeline = self._make_pipeline()
        enriched = EnrichedContext(
            original_topic="블라인드 연봉",
            deep_insights="한국 IT 업계 연봉 상승 추세",
            global_references=["https://ref.com/salary"],
            sentiment_angle="긍정적",
        )
        prompt = pipeline._build_user_prompt(
            title="연봉 공유",
            content_preview="내용",
            source="blind",
            velocity_score=5.0,
            enriched=enriched,
        )
        assert "Enriched Deep Context" in prompt
        assert "한국 IT 업계 연봉 상승 추세" in prompt
        assert "https://ref.com/salary" in prompt
