"""execution/llm_client.py 테스트."""
from __future__ import annotations

import json
import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from execution.llm_client import (
    DEFAULT_MODELS,
    DEFAULT_PROVIDER_ORDER,
    LLMClient,
    NON_RETRYABLE_KEYWORDS,
    OPENAI_COMPATIBLE_BASE_URLS,
    PRICING,
    PROVIDER_ALIASES,
    _cache_get,
    _cache_key,
    _cache_set,
)


# ── 상수 테스트 ───────────────────────────────────────────────


class TestConstants:
    def test_provider_aliases_cover_all_providers(self):
        for p in DEFAULT_PROVIDER_ORDER:
            assert p in PROVIDER_ALIASES.values()

    def test_default_models_for_all_providers(self):
        for p in DEFAULT_PROVIDER_ORDER:
            assert p in DEFAULT_MODELS

    def test_pricing_has_entries(self):
        assert len(PRICING) > 0
        for model, prices in PRICING.items():
            assert "input" in prices
            assert "output" in prices


# ── _cache_key 테스트 ─────────────────────────────────────────


class TestCacheKey:
    def test_deterministic(self):
        k1 = _cache_key(["google"], "sys", "user", 0.7)
        k2 = _cache_key(["google"], "sys", "user", 0.7)
        assert k1 == k2

    def test_different_inputs(self):
        k1 = _cache_key(["google"], "sys", "user1", 0.7)
        k2 = _cache_key(["google"], "sys", "user2", 0.7)
        assert k1 != k2

    def test_different_temperature(self):
        k1 = _cache_key(["google"], "sys", "user", 0.7)
        k2 = _cache_key(["google"], "sys", "user", 0.5)
        assert k1 != k2


# ── _cache_get / _cache_set 테스트 ────────────────────────────


class TestCache:
    def test_get_nonexistent(self, tmp_path):
        with patch("execution.llm_client._CACHE_DB_PATH", tmp_path / "cache.db"):
            result = _cache_get("nonexistent", 3600)
            assert result is None

    def test_set_and_get(self, tmp_path):
        db_path = tmp_path / "cache.db"
        with patch("execution.llm_client._CACHE_DB_PATH", db_path):
            _cache_set("testkey", "testvalue")
            result = _cache_get("testkey", 3600)
            assert result == "testvalue"

    def test_expired_cache(self, tmp_path):
        db_path = tmp_path / "cache.db"
        with patch("execution.llm_client._CACHE_DB_PATH", db_path):
            _cache_set("expkey", "value")
            # Manually set created_at to past
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute(
                    "UPDATE llm_cache SET created_at=? WHERE key=?",
                    (time.time() - 7200, "expkey"),
                )
            result = _cache_get("expkey", 3600)
            assert result is None


# ── LLMClient 초기화 테스트 ───────────────────────────────────


class TestLLMClientInit:
    @patch.dict("os.environ", {}, clear=False)
    def test_default_init(self):
        client = LLMClient()
        assert len(client.provider_order) > 0
        assert client.max_retries == 2

    def test_custom_providers(self):
        client = LLMClient(providers=["google", "openai"])
        assert client.provider_order == ["google", "openai"]

    def test_provider_alias_normalization(self):
        client = LLMClient(providers=["gemini", "chatgpt", "claude"])
        assert client.provider_order == ["google", "openai", "anthropic"]

    def test_dedup_providers(self):
        client = LLMClient(providers=["google", "gemini", "google"])
        assert client.provider_order == ["google"]

    def test_invalid_providers_fall_to_default(self):
        client = LLMClient(providers=["nonexistent"])
        assert client.provider_order == list(DEFAULT_PROVIDER_ORDER)

    def test_custom_models(self):
        client = LLMClient(models={"google": "gemini-2.0-flash"})
        assert client.models["google"] == "gemini-2.0-flash"

    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test123"}, clear=False)
    def test_api_key_loading(self):
        client = LLMClient()
        assert client.api_keys["openai"] == "sk-test123"


# ── enabled_providers 테스트 ──────────────────────────────────


class TestEnabledProviders:
    @patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test", "GEMINI_API_KEY": ""}, clear=False)
    def test_only_with_keys(self):
        client = LLMClient(providers=["openai", "google"])
        enabled = client.enabled_providers()
        assert "openai" in enabled
        # google may or may not be enabled depending on env

    @patch.dict("os.environ", {}, clear=False)
    def test_all_provider_status(self):
        client = LLMClient()
        status = client.all_provider_status()
        assert len(status) == len(DEFAULT_PROVIDER_ORDER)
        for p in DEFAULT_PROVIDER_ORDER:
            assert p in status


# ── _is_non_retryable 테스트 ──────────────────────────────────


class TestIsNonRetryable:
    def test_invalid_api_key(self):
        assert LLMClient._is_non_retryable(Exception("Invalid API key provided"))

    def test_insufficient_quota(self):
        assert LLMClient._is_non_retryable(Exception("insufficient_quota for this model"))

    def test_retryable_error(self):
        assert not LLMClient._is_non_retryable(Exception("Connection timeout"))

    def test_credit_balance(self):
        assert LLMClient._is_non_retryable(Exception("Credit balance is too low"))


# ── _clean_json 테스트 ────────────────────────────────────────


class TestCleanJson:
    def test_plain_json(self):
        assert LLMClient._clean_json('{"key": "value"}') == '{"key": "value"}'

    def test_markdown_json_block(self):
        result = LLMClient._clean_json('```json\n{"key": "value"}\n```')
        assert result == '{"key": "value"}'

    def test_markdown_block_no_lang(self):
        result = LLMClient._clean_json('```\n{"key": "value"}\n```')
        assert result == '{"key": "value"}'

    def test_whitespace_handling(self):
        result = LLMClient._clean_json('  {"key": "value"}  ')
        assert result == '{"key": "value"}'


# ── generate_json / generate_text 에러 경로 ───────────────────


class TestGenerateErrors:
    @patch.dict("os.environ", {}, clear=True)
    def test_no_providers_json(self):
        # Clear ALL api key env vars
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["google"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {}
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30

        with pytest.raises(RuntimeError, match="사용 가능한 LLM"):
            client.generate_json(system_prompt="test", user_prompt="test")

    def test_no_providers_text(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["google"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {}
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30

        with pytest.raises(RuntimeError, match="사용 가능한 LLM"):
            client.generate_text(system_prompt="test", user_prompt="test")


# ── _generate_once mock 테스트 ────────────────────────────────


class TestGenerateOnce:
    def _make_client(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = {"openai": "gpt-4o-mini"}
        client.api_keys = {"openai": "sk-test"}
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_get_client")
    def test_openai_compatible(self, mock_get_client):
        client = self._make_client()
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"ok":true}'))]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_openai.chat.completions.create.return_value = mock_resp
        mock_get_client.return_value = mock_openai

        content, in_tok, out_tok = client._generate_once(
            "openai", "sys", "user", 0.7, json_mode=True
        )
        assert content == '{"ok":true}'
        assert in_tok == 10
        assert out_tok == 20

    @patch.object(LLMClient, "_get_client")
    def test_generate_json_success(self, mock_get_client):
        client = self._make_client()
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"result":"ok"}'))]
        mock_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=10)
        mock_openai.chat.completions.create.return_value = mock_resp
        mock_get_client.return_value = mock_openai

        result = client.generate_json(system_prompt="sys", user_prompt="user")
        assert result == {"result": "ok"}

    @patch.object(LLMClient, "_get_client")
    def test_generate_text_success(self, mock_get_client):
        client = self._make_client()
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="Hello world"))]
        mock_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=10)
        mock_openai.chat.completions.create.return_value = mock_resp
        mock_get_client.return_value = mock_openai

        result = client.generate_text(system_prompt="sys", user_prompt="user")
        assert result == "Hello world"

    @patch.object(LLMClient, "_get_client")
    def test_json_cache_hit(self, mock_get_client, tmp_path):
        client = self._make_client()
        client.cache_ttl_sec = 3600

        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"cached":true}'))]
        mock_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=10)
        mock_openai.chat.completions.create.return_value = mock_resp
        mock_get_client.return_value = mock_openai

        with patch("execution.llm_client._CACHE_DB_PATH", tmp_path / "cache.db"):
            result1 = client.generate_json(system_prompt="sys", user_prompt="user")
            result2 = client.generate_json(system_prompt="sys", user_prompt="user")
            assert result1 == result2
            # Second call should use cache, not API
            assert mock_openai.chat.completions.create.call_count == 1


# ── test_provider 테스트 ──────────────────────────────────────


class TestTestProvider:
    def test_skip_no_key(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = {"openai": "gpt-4o-mini"}
        client.api_keys = {"openai": None}
        client._clients = {}
        client.request_timeout_sec = 30

        result = client.test_provider("openai")
        assert result["status"] == "skip"

    @patch.object(LLMClient, "_generate_once")
    def test_success(self, mock_gen):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = {"openai": "gpt-4o-mini"}
        client.api_keys = {"openai": "sk-test"}
        client._clients = {}
        client.request_timeout_sec = 30

        mock_gen.return_value = ('{"status":"ok"}', 5, 3)
        result = client.test_provider("openai")
        assert result["status"] == "ok"

    @patch.object(LLMClient, "_generate_once")
    def test_failure(self, mock_gen):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = {"openai": "gpt-4o-mini"}
        client.api_keys = {"openai": "sk-test"}
        client._clients = {}
        client.request_timeout_sec = 30

        mock_gen.side_effect = Exception("Connection refused")
        result = client.test_provider("openai")
        assert result["status"] == "fail"
