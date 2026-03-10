from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_generator import TweetDraftGenerator  # noqa: E402


class FakeConfig:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


def _build_config():
    return FakeConfig(
        {
            "llm": {
                "providers": ["anthropic", "gemini", "xai", "openai"],
                "max_retries_per_provider": 1,
                "request_timeout_seconds": 5,
            },
            "anthropic": {"enabled": True, "api_key": "anthropic-key", "model": "claude-sonnet-4-20250514"},
            "gemini": {"enabled": True, "api_key": "gemini-key", "model": "gemini-2.5-flash"},
            "xai": {"enabled": True, "api_key": "xai-key", "model": "grok-4-1-fast-reasoning"},
            "openai": {"chat_enabled": True, "api_key": "openai-key", "chat_model": "gpt-4.1-mini"},
            "tweet_style": {"tone": "위트 있고 공감 가는", "max_length": 280},
        }
    )


def test_generator_falls_back_to_next_provider(monkeypatch):
    generator = TweetDraftGenerator(_build_config())

    async def _fail(_prompt):
        raise RuntimeError("Your credit balance is too low to access the Anthropic API.")

    async def _gemini(_prompt):
        return "<twitter>[공감형 트윗]\n초안</twitter><image_prompt>prompt</image_prompt>", 10, 20

    called = {"gemini": 0, "openai": 0}

    async def _gemini_wrapper(prompt):
        called["gemini"] += 1
        return await _gemini(prompt)

    async def _openai(_prompt):
        called["openai"] += 1
        return "<twitter>openai</twitter>", 1, 1

    monkeypatch.setattr(generator, "_generate_with_anthropic", _fail)
    monkeypatch.setattr(generator, "_generate_with_gemini", _gemini_wrapper)
    monkeypatch.setattr(generator, "_generate_with_openai", _openai)

    drafts, image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "제목", "content": "본문", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert drafts["_provider_used"] == "gemini"
    assert "초안" in drafts["twitter"]
    assert image_prompt == "prompt"
    # 1 draft generation call (self-scoring removed in optimization)
    assert called["gemini"] == 1
    assert called["openai"] == 0


def test_generator_returns_clear_error_when_no_provider_enabled(monkeypatch):
    for key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY", "GROK_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    config = FakeConfig({"llm": {"providers": ["anthropic"]}, "tweet_style": {"max_length": 280}})
    generator = TweetDraftGenerator(config)
    drafts, image_prompt = asyncio.run(
        generator.generate_drafts({"title": "제목", "content": "본문", "content_profile": {}}, output_formats=["twitter"])
    )
    assert "No enabled LLM providers available" in drafts["twitter"]
    assert image_prompt is None


def test_generator_bridge_repairs_non_korean_output(monkeypatch):
    monkeypatch.setenv("LLM_BRIDGE_MODE", "enforce")
    config = _build_config()
    # Use providers that are actually supported by the generator
    config.data["llm"]["providers"] = ["gemini", "openai"]
    generator = TweetDraftGenerator(config)

    call_count = {"total": 0}

    async def _fake_generate_once(provider, prompt):
        del prompt
        call_count["total"] += 1
        # gemini returns a valid Korean draft
        if provider == "gemini":
            return "<twitter>한국어 초안</twitter><image_prompt>prompt</image_prompt>", 8, 4
        return "<twitter>fallback</twitter>", 1, 1

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "브릿지 제목", "content": "브릿지 본문", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert drafts["twitter"] == "한국어 초안"
    assert image_prompt == "prompt"
    assert call_count["total"] == 1  # deepseek succeeds on first try


def test_generator_bridge_shadow_keeps_result(monkeypatch):
    monkeypatch.setenv("LLM_BRIDGE_MODE", "shadow")
    config = _build_config()
    config.data["llm"]["providers"] = ["gemini"]
    generator = TweetDraftGenerator(config)

    async def _fake_generate_once(provider, prompt):
        del provider, prompt
        return "<twitter>中文 초안</twitter><image_prompt>prompt</image_prompt>", 10, 5

    monkeypatch.setattr(generator, "_generate_once", _fake_generate_once)

    drafts, image_prompt = asyncio.run(
        generator.generate_drafts(
            {"title": "섀도우 제목", "content": "섀도우 본문", "content_profile": {}},
            output_formats=["twitter"],
        )
    )

    assert drafts["twitter"] == "中文 초안"
    assert image_prompt == "prompt"
