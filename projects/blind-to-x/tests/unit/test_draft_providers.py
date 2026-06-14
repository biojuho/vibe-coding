"""Tests for pipeline.draft_providers pure helpers."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from pipeline.draft_generator import TweetDraftGenerator
from pipeline.draft_prompts import DraftPrompt
from pipeline.draft_providers import (
    DEFAULT_PROVIDER_ORDER,
    DraftProvidersMixin,
)


def _make_provider_instance(config: dict | None = None, timeout: int = 45) -> DraftProvidersMixin:
    """Create a minimal mixin instance with needed attributes."""
    obj = object.__new__(DraftProvidersMixin)
    obj.config = SimpleNamespace(get=lambda key, default=None: (config or {}).get(key, default))
    obj.request_timeout_seconds = timeout
    obj.provider_order = list(DEFAULT_PROVIDER_ORDER)
    obj.anthropic_enabled = True
    obj.gemini_enabled = True
    obj.xai_enabled = True
    obj.openai_enabled = True
    obj.ollama_enabled = False
    return obj


class FakeConfig:
    def __init__(self, data: dict):
        self.data = data

    def get(self, key, default=None):
        cur = self.data
        for part in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return default
        return default if cur is None else cur


def _generator_config() -> FakeConfig:
    return FakeConfig(
        {
            "llm": {
                "providers": ["anthropic", "gemini", "xai", "openai"],
                "request_timeout_seconds": 5,
            },
            "anthropic": {"enabled": True, "api_key": "anthropic-key", "model": "claude-sonnet-4-6"},
            "gemini": {"enabled": True, "api_key": "gemini-key", "model": "gemini-2.5-flash"},
            "xai": {"enabled": True, "api_key": "xai-key", "model": "grok-4-1-fast-reasoning"},
            "openai": {"chat_enabled": True, "api_key": "openai-key", "chat_model": "gpt-4.1-mini"},
            "tweet_style": {"tone": "casual", "max_length": 280},
        }
    )


# ── _resolve_provider_order ──────────────────────────────────────────────────


class TestResolveProviderOrder:
    def test_default_when_no_config(self):
        obj = _make_provider_instance()
        assert obj._resolve_provider_order() == list(DEFAULT_PROVIDER_ORDER)

    def test_alias_mapping(self):
        obj = _make_provider_instance({"llm.providers": ["claude", "chatgpt"]})
        result = obj._resolve_provider_order()
        assert result == ["anthropic", "openai"]

    def test_deduplication(self):
        obj = _make_provider_instance({"llm.providers": ["claude", "anthropic", "openai"]})
        result = obj._resolve_provider_order()
        assert result.count("anthropic") == 1

    def test_invalid_provider_filtered(self):
        obj = _make_provider_instance({"llm.providers": ["invalid_only"]})
        result = obj._resolve_provider_order()
        # Falls back to default when all invalid
        assert result == list(DEFAULT_PROVIDER_ORDER)

    def test_mixed_valid_invalid(self):
        obj = _make_provider_instance({"llm.providers": ["grok", "nonexistent"]})
        result = obj._resolve_provider_order()
        assert result == ["xai"]

    def test_case_insensitive(self):
        obj = _make_provider_instance({"llm.providers": ["Claude", "GEMINI"]})
        result = obj._resolve_provider_order()
        assert "anthropic" in result
        assert "gemini" in result


# ── _provider_enabled ────────────────────────────────────────────────────────


class TestProviderEnabled:
    def test_anthropic_enabled_with_key(self):
        obj = _make_provider_instance({"anthropic.enabled": True})
        assert obj._provider_enabled("anthropic", "sk-key") is True

    def test_anthropic_disabled_explicit(self):
        obj = _make_provider_instance({"anthropic.enabled": False})
        assert obj._provider_enabled("anthropic", "sk-key") is False

    def test_no_api_key(self):
        obj = _make_provider_instance({"anthropic.enabled": True})
        assert obj._provider_enabled("anthropic", None) is False

    def test_openai_chat_enabled_priority(self):
        obj = _make_provider_instance({"openai.chat_enabled": True, "openai.enabled": False})
        assert obj._provider_enabled("openai", "sk-key") is True

    def test_openai_fallback_to_enabled(self):
        obj = _make_provider_instance({"openai.enabled": True})
        assert obj._provider_enabled("openai", "sk-key") is True

    def test_default_enabled_with_key(self):
        obj = _make_provider_instance({})
        assert obj._provider_enabled("gemini", "key") is True

    def test_default_enabled_no_key(self):
        obj = _make_provider_instance({})
        assert obj._provider_enabled("gemini", None) is False


# ── _timeout_for ─────────────────────────────────────────────────────────────


class TestTimeoutFor:
    def test_ollama(self):
        obj = _make_provider_instance(timeout=45)
        assert obj._timeout_for("ollama") == 90

    def test_anthropic(self):
        obj = _make_provider_instance(timeout=45)
        assert obj._timeout_for("anthropic") == 45

    def test_openai(self):
        obj = _make_provider_instance(timeout=60)
        assert obj._timeout_for("openai") == 60

    def test_gemini_capped(self):
        obj = _make_provider_instance(timeout=45)
        assert obj._timeout_for("gemini") == 30

    def test_xai_capped(self):
        obj = _make_provider_instance(timeout=45)
        assert obj._timeout_for("xai") == 30

    def test_low_timeout_gemini(self):
        obj = _make_provider_instance(timeout=20)
        assert obj._timeout_for("gemini") == 20  # min(30, 20) = 20


# ── _enabled_providers ───────────────────────────────────────────────────────


class TestEnabledProviders:
    def test_filters_disabled(self):
        obj = _make_provider_instance()
        obj.ollama_enabled = False
        result = obj._enabled_providers()
        assert "ollama" not in result

    def test_all_enabled(self):
        obj = _make_provider_instance()
        obj.ollama_enabled = True
        result = obj._enabled_providers()
        assert len(result) == 5

    def test_respects_order(self):
        obj = _make_provider_instance()
        obj.provider_order = ["xai", "anthropic"]
        result = obj._enabled_providers()
        assert result[0] == "xai"
        assert result[1] == "anthropic"


class TestLazyProviderClients:
    def test_module_import_does_not_load_anthropic_sdk(self):
        project_root = Path(__file__).resolve().parents[2]
        code = (
            "import sys; "
            "import pipeline.draft_providers as draft_providers; "
            "print('anthropic' in sys.modules); "
            "print(draft_providers.AsyncAnthropic is None)"
        )

        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )

        assert result.stdout.splitlines() == ["False", "True"]

    def test_generator_init_defers_sdk_client_construction(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        with (
            patch("pipeline.draft_providers.AsyncAnthropic") as mock_anthropic_cls,
            patch("pipeline.draft_providers.AsyncOpenAI") as mock_openai_cls,
        ):
            generator = TweetDraftGenerator(_generator_config())

            mock_anthropic_cls.assert_not_called()
            mock_openai_cls.assert_not_called()
            assert generator._enabled_providers() == ["anthropic", "gemini", "xai", "openai"]

    def test_generator_init_skips_ollama_probe_when_order_excludes_ollama(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        with patch.object(DraftProvidersMixin, "_check_ollama_enabled", return_value=True) as mock_ollama:
            generator = TweetDraftGenerator(_generator_config())

        mock_ollama.assert_not_called()
        assert generator.ollama_enabled is False

    def test_generator_init_checks_ollama_when_default_order_includes_it(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        config = _generator_config()
        config.data["llm"].pop("providers")
        with patch.object(DraftProvidersMixin, "_check_ollama_enabled", return_value=True) as mock_ollama:
            generator = TweetDraftGenerator(config)

        mock_ollama.assert_called_once_with()
        assert generator.ollama_enabled is True

    def test_sdk_client_constructs_on_first_access(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        with (
            patch("pipeline.draft_providers.AsyncAnthropic") as mock_anthropic_cls,
            patch("pipeline.draft_providers.AsyncOpenAI") as mock_openai_cls,
        ):
            generator = TweetDraftGenerator(_generator_config())

            assert generator.anthropic_client is mock_anthropic_cls.return_value
            assert generator.openai_client is mock_openai_cls.return_value
            assert generator.xai_client is mock_openai_cls.return_value

        mock_anthropic_cls.assert_called_once_with(api_key="anthropic-key")
        assert mock_openai_cls.call_count == 2
        mock_openai_cls.assert_any_call(api_key="openai-key")
        mock_openai_cls.assert_any_call(api_key="xai-key", base_url="https://api.x.ai/v1")


class TestAnthropicPromptCaching:
    @staticmethod
    def _response(cache_creation: int = 0, cache_read: int = 0):
        return SimpleNamespace(
            content=[SimpleNamespace(text="draft")],
            usage=SimpleNamespace(
                input_tokens=120,
                output_tokens=30,
                cache_creation_input_tokens=cache_creation,
                cache_read_input_tokens=cache_read,
            ),
        )

    def _anthropic_instance(self, config: dict | None = None, cache_creation: int = 0, cache_read: int = 0):
        obj = _make_provider_instance(config)
        obj.anthropic_model = "claude-test"
        create = AsyncMock(return_value=self._response(cache_creation=cache_creation, cache_read=cache_read))
        obj.anthropic_client = SimpleNamespace(messages=SimpleNamespace(create=create))
        return obj, create

    def test_split_prompt_defaults_to_5m_cache_control(self):
        obj, create = self._anthropic_instance(cache_creation=900)
        prompt = DraftPrompt(
            "SYSTEM\n\nUSER",
            anthropic_system_prompt="SYSTEM",
            anthropic_user_prompt="USER",
        )

        result = asyncio.run(obj._generate_with_anthropic(prompt))

        assert result == ("draft", 120, 30, 900, 0)
        kwargs = create.await_args.kwargs
        assert kwargs["messages"] == [{"role": "user", "content": "USER"}]
        assert kwargs["system"][0]["text"] == "SYSTEM"
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}

    def test_split_prompt_supports_1h_cache_control(self):
        obj, create = self._anthropic_instance({"anthropic.cache_strategy": "1h"}, cache_creation=900)
        prompt = DraftPrompt(
            "SYSTEM\n\nUSER",
            anthropic_system_prompt="SYSTEM",
            anthropic_user_prompt="USER",
        )

        asyncio.run(obj._generate_with_anthropic(prompt))

        kwargs = create.await_args.kwargs
        assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}

    def test_plain_string_prompt_keeps_legacy_user_only_payload(self):
        obj, create = self._anthropic_instance()

        result = asyncio.run(obj._generate_with_anthropic("plain prompt"))

        assert result == ("draft", 120, 30, 0, 0)
        kwargs = create.await_args.kwargs
        assert "system" not in kwargs
        assert kwargs["messages"] == [{"role": "user", "content": "plain prompt"}]


class TestLangfuseTraceHook:
    def test_generate_once_emits_workspace_trace_when_enabled(self, monkeypatch):
        obj = _make_provider_instance()
        obj.gemini_model = "gemini-test"

        async def fake_gemini(prompt: str):
            assert prompt == "draft prompt"
            return "draft", 11, 7, 0, 0

        obj._generate_with_gemini = fake_gemini
        calls: list[dict] = []
        fake_execution = ModuleType("execution")
        fake_llm_client = ModuleType("execution.llm_client")
        fake_llm_client._emit_langfuse_trace = lambda **kwargs: calls.append(kwargs)

        monkeypatch.setenv("LANGFUSE_ENABLED", "1")
        monkeypatch.setitem(sys.modules, "execution", fake_execution)
        monkeypatch.setitem(sys.modules, "execution.llm_client", fake_llm_client)

        result = asyncio.run(obj._generate_once("gemini", "draft prompt"))

        assert result == ("draft", 11, 7, 0, 0)
        assert calls
        assert calls[0]["provider"] == "gemini"
        assert calls[0]["model"] == "gemini-test"
        assert calls[0]["endpoint"] == "blind-to-x.draft_provider"
        assert calls[0]["input_tokens"] == 11
        assert calls[0]["output_tokens"] == 7
        assert calls[0]["metadata"]["success"] is True

    def test_generate_once_disabled_trace_does_not_require_workspace_import(self, monkeypatch):
        obj = _make_provider_instance()

        async def fake_openai(prompt: str):
            assert prompt == "draft prompt"
            return "draft", 3, 4, 0, 0

        obj._generate_with_openai = fake_openai
        monkeypatch.setenv("LANGFUSE_ENABLED", "0")

        result = asyncio.run(obj._generate_once("openai", "draft prompt"))

        assert result == ("draft", 3, 4, 0, 0)


# ── _emit_workspace_langfuse_trace ──────────────────────────────────────────


class TestEmitWorkspaceLangfuseTrace:
    def test_disabled_env_is_noop(self, monkeypatch):
        monkeypatch.setenv("LANGFUSE_ENABLED", "0")
        from pipeline.draft_providers import _emit_workspace_langfuse_trace

        _emit_workspace_langfuse_trace(provider="openai", model="gpt-4o", input_tokens=10, output_tokens=5)

    def test_enabled_but_import_fails_is_silenced(self, monkeypatch):
        monkeypatch.setenv("LANGFUSE_ENABLED", "1")
        from unittest.mock import patch

        from pipeline.draft_providers import _emit_workspace_langfuse_trace

        with (
            patch("pipeline.draft_providers.Path.is_dir", return_value=True),
            patch.dict("sys.modules", {"execution.llm_client": None}),
        ):
            # None in sys.modules → AttributeError on `_emit_langfuse_trace` access → caught by except
            _emit_workspace_langfuse_trace(
                provider="anthropic", model="claude-3-5-haiku-20251001", input_tokens=8, output_tokens=4
            )

    def test_enabled_calls_emit_with_correct_args(self, monkeypatch):
        monkeypatch.setenv("LANGFUSE_ENABLED", "1")
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch

        from pipeline.draft_providers import _emit_workspace_langfuse_trace

        fake_client = MagicMock()
        fake_module = SimpleNamespace(_emit_langfuse_trace=fake_client)

        with (
            patch("pipeline.draft_providers.Path.is_dir", return_value=True),
            patch.dict("sys.modules", {"execution.llm_client": fake_module}),
        ):
            _emit_workspace_langfuse_trace(
                provider="openai",
                model="gpt-4o",
                input_tokens=20,
                output_tokens=10,
                cache_creation_tokens=2,
                cache_read_tokens=3,
                latency_ms=123.4,
                success=True,
                error="",
            )

        fake_client.assert_called_once()
        call_kwargs = fake_client.call_args.kwargs
        assert call_kwargs["provider"] == "openai"
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["input_tokens"] == 20
        assert call_kwargs["output_tokens"] == 10
