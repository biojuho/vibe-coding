"""ResearchStep 유닛 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock

from shorts_maker_v2.pipeline.research_step import ResearchContext, ResearchStep

# ── ResearchContext ──────────────────────────────────────────────────────────


class TestResearchContext:
    def test_empty_context_has_no_content(self):
        ctx = ResearchContext(topic="test")
        assert not ctx.has_content
        assert ctx.to_prompt_block() == ""

    def test_context_with_facts(self):
        ctx = ResearchContext(
            topic="AI",
            facts=["GPT-4 has 1.8T parameters"],
            key_data_points=["2024년 AI 시장 규모: $200B"],
        )
        assert ctx.has_content
        block = ctx.to_prompt_block()
        assert "Research Context" in block
        assert "GPT-4 has 1.8T parameters" in block
        assert "$200B" in block

    def test_prompt_block_limits_items(self):
        ctx = ResearchContext(
            topic="test",
            facts=[f"fact {i}" for i in range(20)],
            key_data_points=[f"dp {i}" for i in range(20)],
            sources=[f"source {i}" for i in range(10)],
        )
        block = ctx.to_prompt_block()
        # facts는 최대 7개, data_points는 5개, sources는 3개
        assert block.count("fact ") <= 7
        assert block.count("dp ") <= 5

    def test_prompt_block_contains_instruction(self):
        ctx = ResearchContext(topic="test", facts=["fact1"])
        block = ctx.to_prompt_block()
        assert "Prefer these researched facts" in block


# ── ResearchStep ─────────────────────────────────────────────────────────────


def _make_config(enabled: bool = True, provider: str = "gemini"):
    config = MagicMock()
    config.research.enabled = enabled
    config.research.provider = provider
    return config


class TestResearchStepGrounding:
    """Gemini Google Search Grounding 경로 테스트."""

    def test_grounding_success(self):
        config = _make_config()
        google_client = MagicMock()

        # Mock Gemini response
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = None
        mock_response = MagicMock()
        mock_response.text = '{"facts": ["fact1"], "key_data_points": ["dp1"], "sources": ["src1"], "summary": "sum"}'
        mock_response.candidates = [mock_candidate]
        google_client.client.models.generate_content.return_value = mock_response

        step = ResearchStep(config=config, google_client=google_client)
        ctx = step.run("AI 트렌드")

        assert ctx.has_content
        assert "fact1" in ctx.facts
        assert "dp1" in ctx.key_data_points
        assert ctx.elapsed_sec >= 0

    def test_grounding_failure_falls_back_to_llm(self):
        config = _make_config()
        google_client = MagicMock()
        google_client.client.models.generate_content.side_effect = RuntimeError("API error")

        llm_router = MagicMock()
        llm_router.generate_json.return_value = {
            "facts": ["llm_fact"],
            "key_data_points": [],
            "sources": [],
            "summary": "llm summary",
        }

        step = ResearchStep(config=config, google_client=google_client, llm_router=llm_router)
        ctx = step.run("테스트 주제")

        assert ctx.has_content
        assert "llm_fact" in ctx.facts
        assert ctx.summary == "llm summary"

    def test_all_methods_fail_returns_empty(self):
        config = _make_config()
        google_client = MagicMock()
        google_client.client.models.generate_content.side_effect = RuntimeError("fail")

        llm_router = MagicMock()
        llm_router.generate_json.side_effect = RuntimeError("fail")

        step = ResearchStep(config=config, google_client=google_client, llm_router=llm_router)
        ctx = step.run("실패 주제")

        assert not ctx.has_content
        assert ctx.topic == "실패 주제"


class TestResearchStepLLMOnly:
    """LLM Router 전용 경로 테스트."""

    def test_llm_only_success(self):
        config = _make_config(provider="llm")
        llm_router = MagicMock()
        llm_router.generate_json.return_value = {
            "facts": ["수면 7-9시간 권장"],
            "key_data_points": ["수면 부족 시 사고율 33% 증가"],
            "sources": ["NIH"],
            "summary": "수면이 건강에 미치는 영향",
        }

        step = ResearchStep(config=config, google_client=None, llm_router=llm_router)
        ctx = step.run("수면의 중요성")

        assert ctx.has_content
        assert len(ctx.facts) == 1
        assert "NIH" in ctx.sources


class TestResearchStepParseJson:
    def test_parse_clean_json(self):
        raw = '{"facts": ["a"], "key_data_points": []}'
        assert ResearchStep._parse_json(raw) == {"facts": ["a"], "key_data_points": []}

    def test_parse_markdown_wrapped_json(self):
        raw = '```json\n{"facts": ["a"]}\n```'
        assert ResearchStep._parse_json(raw) == {"facts": ["a"]}

    def test_parse_invalid_json_returns_empty(self):
        assert ResearchStep._parse_json("not json") == {}
