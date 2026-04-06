"""Tests for pipeline.draft_providers pure helpers."""

from __future__ import annotations

from types import SimpleNamespace


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
