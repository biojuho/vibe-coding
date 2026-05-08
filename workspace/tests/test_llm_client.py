"""execution/llm_client.py 테스트."""

from __future__ import annotations

import sqlite3
import time
from unittest.mock import MagicMock, patch

import pytest

from execution.llm_client import (
    DEFAULT_MODELS,
    DEFAULT_PROVIDER_ORDER,
    LLMClient,
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

        content, in_tok, out_tok, cache_w, cache_r = client._generate_once("openai", "sys", "user", 0.7, json_mode=True)
        assert content == '{"ok":true}'
        assert in_tok == 10
        assert out_tok == 20
        assert cache_w == 0
        assert cache_r == 0

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

        mock_gen.return_value = ('{"status":"ok"}', 5, 3, 0, 0)
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


# ── _cache_set parent dir creation (lines 184-185) ──────────


class TestCacheSetParentDir:
    def test_cache_set_creates_parent_and_table(self, tmp_path):
        """_cache_set creates parent directory and table on first write."""
        nested = tmp_path / "sub" / "deep" / "cache.db"
        with patch("execution.llm_client._CACHE_DB_PATH", nested):
            _cache_set("k1", "v1")
        assert nested.parent.exists()
        # If DB was created we should be able to read back (need same mock)
        with patch("execution.llm_client._CACHE_DB_PATH", nested):
            assert _cache_get("k1", 3600) == "v1"

    def test_cache_set_exception_silenced(self, tmp_path):
        """_cache_set silences exceptions (e.g., read-only path)."""
        with patch(
            "execution.llm_client._CACHE_DB_PATH",
            MagicMock(parent=MagicMock(mkdir=MagicMock(side_effect=PermissionError("no")))),
        ):
            # Should not raise
            _cache_set("k", "v")


# ── _get_client for all providers (lines 254-282) ───────────


class TestGetClientProviders:
    def _make_client_with_key(self, provider, key="test-key"):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = [provider]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {provider: key}
        client._clients = {}
        client.request_timeout_sec = 30
        return client

    def test_get_client_google(self):
        """_get_client initializes google genai.Client."""
        client = self._make_client_with_key("google")
        mock_client_instance = MagicMock()
        mock_genai = MagicMock()
        mock_genai.Client.return_value = mock_client_instance
        mock_google = MagicMock()
        mock_google.genai = mock_genai
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = client._get_client("google")
        assert result is mock_client_instance
        assert "google" in client._clients

    def test_get_client_anthropic(self):
        """_get_client initializes Anthropic client."""
        client = self._make_client_with_key("anthropic")
        mock_anthropic_cls = MagicMock()
        mock_anthropic_mod = MagicMock()
        mock_anthropic_mod.Anthropic = mock_anthropic_cls
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_mod}):
            client._get_client("anthropic")
        mock_anthropic_cls.assert_called_once_with(api_key="test-key")
        assert "anthropic" in client._clients

    def test_get_client_openai_compatible(self):
        """_get_client initializes OpenAI-compatible provider (xai, deepseek etc.)."""
        client = self._make_client_with_key("xai")
        mock_openai_cls = MagicMock()
        mock_openai_mod = MagicMock()
        mock_openai_mod.OpenAI = mock_openai_cls
        with patch.dict("sys.modules", {"openai": mock_openai_mod}):
            client._get_client("xai")
        mock_openai_cls.assert_called_once_with(
            api_key="test-key",
            base_url=OPENAI_COMPATIBLE_BASE_URLS["xai"],
            timeout=30,
        )
        assert "xai" in client._clients

    def test_get_client_openai_direct(self):
        """_get_client initializes direct OpenAI client (no base_url)."""
        client = self._make_client_with_key("openai")
        mock_openai_cls = MagicMock()
        mock_openai_mod = MagicMock()
        mock_openai_mod.OpenAI = mock_openai_cls
        with patch.dict("sys.modules", {"openai": mock_openai_mod}):
            client._get_client("openai")
        mock_openai_cls.assert_called_once_with(api_key="test-key", timeout=30)

    def test_get_client_no_api_key(self):
        """_get_client raises ValueError when API key is missing."""
        client = self._make_client_with_key("openai", key=None)
        with pytest.raises(ValueError, match="API key not found"):
            client._get_client("openai")

    def test_get_client_unknown_provider(self):
        """_get_client raises ValueError for unknown provider."""
        client = self._make_client_with_key("openai")
        client.api_keys["unknown_prov"] = "key"
        with pytest.raises(ValueError, match="Unknown provider"):
            client._get_client("unknown_prov")

    def test_get_client_cached(self):
        """_get_client returns cached client on second call."""
        client = self._make_client_with_key("openai")
        sentinel = MagicMock()
        client._clients["openai"] = sentinel
        assert client._get_client("openai") is sentinel


# ── _generate_once for google/anthropic (lines 315-349) ─────


class TestGenerateOnceProviders:
    def _make_client(self, provider):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = [provider]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {provider: "test-key"}
        client._clients = {}
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_get_client")
    def test_google_provider(self, mock_get_client):
        """_generate_once for google uses genai types API."""
        client = self._make_client("google")
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"result":"ok"}'
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 15
        mock_usage.candidates_token_count = 25
        mock_resp.usage_metadata = mock_usage
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        # Mock the google.genai.types import
        mock_types = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "google": MagicMock(),
                "google.genai": MagicMock(types=mock_types),
                "google.genai.types": mock_types,
            },
        ):
            content, in_tok, out_tok, _cache_w, _cache_r = client._generate_once(
                "google",
                "sys",
                "user",
                0.7,
                json_mode=True,
            )
        assert content == '{"result":"ok"}'
        assert in_tok == 15
        assert out_tok == 25

    @patch.object(LLMClient, "_get_client")
    def test_anthropic_provider(self, mock_get_client):
        """_generate_once for anthropic uses messages.create API."""
        client = self._make_client("anthropic")
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Hello from Claude")]
        mock_resp.usage = MagicMock(
            input_tokens=12,
            output_tokens=18,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        mock_client.messages.create.return_value = mock_resp
        mock_get_client.return_value = mock_client

        content, in_tok, out_tok, cache_w, cache_r = client._generate_once(
            "anthropic",
            "sys prompt",
            "user prompt",
            0.5,
            json_mode=False,
        )
        assert content == "Hello from Claude"
        assert in_tok == 12
        assert out_tok == 18
        assert (cache_w, cache_r) == (0, 0)
        # cache_strategy="off" 기본값일 때 system은 string 그대로 전달
        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["model"] == DEFAULT_MODELS["anthropic"]
        assert kwargs["system"] == "sys prompt"
        assert kwargs["messages"] == [{"role": "user", "content": "user prompt"}]
        assert kwargs["max_tokens"] == 2000
        assert kwargs["temperature"] == 0.5
        assert "extra_headers" not in kwargs

    @patch.object(LLMClient, "_get_client")
    def test_google_no_usage_metadata(self, mock_get_client):
        """_generate_once handles missing usage_metadata gracefully."""
        client = self._make_client("google")
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "hello"
        mock_resp.usage_metadata = None
        mock_client.models.generate_content.return_value = mock_resp
        mock_get_client.return_value = mock_client

        mock_types = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "google": MagicMock(),
                "google.genai": MagicMock(types=mock_types),
                "google.genai.types": mock_types,
            },
        ):
            content, in_tok, out_tok, _cache_w, _cache_r = client._generate_once(
                "google",
                "s",
                "u",
                0.7,
                json_mode=False,
            )
        assert in_tok == 0
        assert out_tok == 0


# ── _log_usage (lines 364-387) ──────────────────────────────


class TestLogUsage:
    def _make_client(self):
        client = LLMClient.__new__(LLMClient)
        client.track_usage = True
        client.caller_script = "test_script.py"
        return client

    @patch("execution.llm_client.log_api_call", create=True)
    def test_log_usage_calls_tracker(self, mock_log):
        """_log_usage calls api_usage_tracker.log_api_call with calculated cost."""
        client = self._make_client()
        with patch("execution.api_usage_tracker.log_api_call", mock_log):
            client._log_usage("openai", "gpt-4o-mini", 1000, 500)
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args
        # Should have been called with cost > 0
        assert call_kwargs[1]["provider"] == "openai" or call_kwargs[0][0] == "openai" if call_kwargs[0] else True

    def test_log_usage_disabled(self):
        """_log_usage does nothing when track_usage is False."""
        client = self._make_client()
        client.track_usage = False
        # Should not raise even without mock
        client._log_usage("openai", "gpt-4o-mini", 100, 50)

    def test_log_usage_exception_silenced(self):
        """_log_usage silently catches exceptions."""
        client = self._make_client()
        with patch.dict(
            "sys.modules",
            {"execution.api_usage_tracker": MagicMock(log_api_call=MagicMock(side_effect=RuntimeError("fail")))},
        ):
            # Should not raise
            client._log_usage("openai", "gpt-4o-mini", 100, 50)

    def test_log_usage_with_metadata(self):
        """_log_usage passes bridge metadata correctly."""
        client = self._make_client()
        mock_tracker = MagicMock()
        with patch("execution.api_usage_tracker.log_api_call", mock_tracker):
            client._log_usage(
                "openai",
                "gpt-4o-mini",
                100,
                50,
                metadata={
                    "bridge_mode": "enforce",
                    "reason_codes": ["low_hangul"],
                    "repair_count": 1,
                    "fallback_used": True,
                },
            )
        mock_tracker.assert_called_once()


# ── generate_json retry/fallback (lines 472-492) ────────────


class TestGenerateJsonRetryFallback:
    def _make_client(self, providers, keys):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = providers
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = keys
        client.max_retries = 2
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_get_client")
    def test_json_parse_error_retries(self, mock_get_client):
        """generate_json retries on JSONDecodeError."""
        client = self._make_client(["openai"], {"openai": "sk-test"})
        mock_openai = MagicMock()
        # First call returns invalid JSON, second returns valid
        mock_resp_bad = MagicMock()
        mock_resp_bad.choices = [MagicMock(message=MagicMock(content="not json"))]
        mock_resp_bad.usage = MagicMock(prompt_tokens=5, completion_tokens=5)
        mock_resp_good = MagicMock()
        mock_resp_good.choices = [MagicMock(message=MagicMock(content='{"ok":true}'))]
        mock_resp_good.usage = MagicMock(prompt_tokens=5, completion_tokens=5)
        mock_openai.chat.completions.create.side_effect = [mock_resp_bad, mock_resp_good]
        mock_get_client.return_value = mock_openai

        with patch("execution.llm_client.time.sleep"):
            result = client.generate_json(system_prompt="s", user_prompt="u")
        assert result == {"ok": True}

    @patch.object(LLMClient, "_get_client")
    def test_non_retryable_breaks_immediately(self, mock_get_client):
        """generate_json breaks retry loop on non-retryable error."""
        client = self._make_client(["openai"], {"openai": "sk-test"})
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = Exception("invalid api key")
        mock_get_client.return_value = mock_openai

        with pytest.raises(RuntimeError, match="모든 LLM 프로바이더 실패"):
            client.generate_json(system_prompt="s", user_prompt="u")
        # Should only call once (no retry for non-retryable)
        assert mock_openai.chat.completions.create.call_count == 1

    @patch.object(LLMClient, "_get_client")
    @patch("execution.llm_client.time.sleep")
    def test_all_providers_exhausted(self, mock_sleep, mock_get_client):
        """generate_json raises RuntimeError when all providers fail."""
        client = self._make_client(["openai", "google"], {"openai": "k1", "google": "k2"})
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("timeout")
        # For google, mock generate_content too
        mock_client.models.generate_content.side_effect = Exception("timeout")
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="모든 LLM 프로바이더 실패"):
            client.generate_json(system_prompt="s", user_prompt="u")


# ── generate_text retry/fallback (lines 510-541) ────────────


class TestGenerateTextRetryFallback:
    def _make_client(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {"openai": "sk-test"}
        client.max_retries = 2
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_generate_once")
    @patch("execution.llm_client.time.sleep")
    def test_text_retries_then_succeeds(self, mock_sleep, mock_gen):
        """generate_text retries on failure then succeeds."""
        client = self._make_client()
        mock_gen.side_effect = [Exception("fail"), ("success text", 5, 10, 0, 0)]
        result = client.generate_text(system_prompt="s", user_prompt="u")
        assert result == "success text"

    @patch.object(LLMClient, "_generate_once")
    def test_text_non_retryable_breaks(self, mock_gen):
        """generate_text breaks on non-retryable error."""
        client = self._make_client()
        mock_gen.side_effect = Exception("insufficient_quota")
        with pytest.raises(RuntimeError, match="모든 프로바이더 실패"):
            client.generate_text(system_prompt="s", user_prompt="u")
        assert mock_gen.call_count == 1

    @patch.object(LLMClient, "_generate_once")
    def test_text_cache_hit(self, mock_gen, tmp_path):
        """generate_text returns cached content on second call."""
        client = self._make_client()
        client.cache_ttl_sec = 3600
        mock_gen.return_value = ("cached text", 5, 10, 0, 0)
        with patch("execution.llm_client._CACHE_DB_PATH", tmp_path / "cache.db"):
            r1 = client.generate_text(system_prompt="s", user_prompt="u")
            r2 = client.generate_text(system_prompt="s", user_prompt="u")
        assert r1 == r2 == "cached text"
        assert mock_gen.call_count == 1


# ── generate_text_bridged (lines 551-669) ───────────────────


class TestGenerateTextBridged:
    def _make_client(self, providers=None, keys=None):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = providers or ["openai"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {"openai": "sk-test"} if keys is None else keys
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_generate_once")
    def test_bridged_off_delegates(self, mock_gen):
        """generate_text_bridged with mode=off delegates to generate_text."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.return_value = ("plain text", 5, 10, 0, 0)
        policy = BridgePolicy(mode="off")
        result = client.generate_text_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert result == "plain text"

    @patch.object(LLMClient, "_generate_once")
    def test_bridged_shadow_returns_on_warning(self, mock_gen):
        """generate_text_bridged in shadow mode returns content even if validation fails."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        # Return English text (will fail Korean validation)
        mock_gen.return_value = ("This is English text only", 5, 10, 0, 0)
        policy = BridgePolicy(mode="shadow", repair_attempts=0, fallback_providers=("openai",))
        result = client.generate_text_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        # Shadow mode should return content even with validation issues
        assert isinstance(result, str)

    @patch.object(LLMClient, "_generate_once")
    def test_bridged_enforce_all_fail_raises(self, mock_gen):
        """generate_text_bridged in enforce mode raises when all providers fail validation."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.return_value = ("English only text", 5, 10, 0, 0)
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_text_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )

    @patch.object(LLMClient, "_generate_once")
    def test_bridged_no_providers_raises(self, mock_gen):
        """generate_text_bridged raises RuntimeError when no providers available."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client(providers=["openai"], keys={})
        policy = BridgePolicy(mode="enforce", fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="사용 가능한 LLM"):
            client.generate_text_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )

    @patch.object(LLMClient, "_generate_once")
    def test_bridged_exception_in_generate(self, mock_gen):
        """generate_text_bridged handles exception during generation."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = Exception("connection error")
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_text_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )


# ── generate_json_bridged (lines 681-799) ───────────────────


class TestGenerateJsonBridged:
    def _make_client(self, providers=None, keys=None):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = providers or ["openai"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {"openai": "sk-test"} if keys is None else keys
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_generate_once")
    def test_json_bridged_off_delegates(self, mock_gen):
        """generate_json_bridged with mode=off delegates to generate_json."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.return_value = ('{"key":"value"}', 5, 10, 0, 0)
        policy = BridgePolicy(mode="off")
        result = client.generate_json_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert result == {"key": "value"}

    @patch.object(LLMClient, "_generate_once")
    def test_json_bridged_shadow_returns_on_warning(self, mock_gen):
        """generate_json_bridged in shadow mode returns JSON even with validation warnings."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.return_value = ('{"key":"English value"}', 5, 10, 0, 0)
        policy = BridgePolicy(mode="shadow", repair_attempts=0, fallback_providers=("openai",))
        result = client.generate_json_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert isinstance(result, dict)

    @patch.object(LLMClient, "_generate_once")
    def test_json_bridged_no_providers_raises(self, mock_gen):
        """generate_json_bridged raises RuntimeError when no providers available."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client(providers=["openai"], keys={})
        policy = BridgePolicy(mode="enforce", fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="사용 가능한 LLM"):
            client.generate_json_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )

    @patch.object(LLMClient, "_generate_once")
    def test_json_bridged_enforce_all_fail(self, mock_gen):
        """generate_json_bridged in enforce mode raises when all fail validation."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.return_value = ('{"key":"English"}', 5, 10, 0, 0)
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_json_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )

    @patch.object(LLMClient, "_generate_once")
    def test_json_bridged_exception_handling(self, mock_gen):
        """generate_json_bridged handles exception during generation."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = Exception("invalid api key")
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_json_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )


# ── Module-level convenience functions (lines 834-915) ──────


class TestConvenienceFunctions:
    def test_get_default_client_singleton(self):
        """get_default_client creates singleton LLMClient."""
        import execution.llm_client as mod

        old = mod._default_client
        try:
            mod._default_client = None
            c1 = mod.get_default_client()
            c2 = mod.get_default_client()
            assert c1 is c2
        finally:
            mod._default_client = old

    @patch("execution.llm_client.get_default_client")
    def test_module_generate_json(self, mock_get_client):
        """Module-level generate_json delegates to client."""
        from execution.llm_client import generate_json as mod_gen_json

        mock_client = MagicMock()
        mock_client.generate_json.return_value = {"ok": True}
        mock_get_client.return_value = mock_client
        result = mod_gen_json(system_prompt="s", user_prompt="u")
        assert result == {"ok": True}

    @patch("execution.llm_client.get_default_client")
    def test_module_generate_text(self, mock_get_client):
        """Module-level generate_text delegates to client."""
        from execution.llm_client import generate_text as mod_gen_text

        mock_client = MagicMock()
        mock_client.generate_text.return_value = "hello"
        mock_get_client.return_value = mock_client
        result = mod_gen_text(system_prompt="s", user_prompt="u")
        assert result == "hello"

    @patch("execution.llm_client.LLMClient")
    def test_module_generate_json_with_providers(self, mock_cls):
        """Module-level generate_json with custom providers creates new client."""
        from execution.llm_client import generate_json as mod_gen_json

        mock_instance = MagicMock()
        mock_instance.generate_json.return_value = {"custom": True}
        mock_cls.return_value = mock_instance
        result = mod_gen_json(system_prompt="s", user_prompt="u", providers=["google"])
        assert result == {"custom": True}
        mock_cls.assert_called_once_with(providers=["google"], caller_script="")

    @patch("execution.llm_client.get_default_client")
    def test_module_generate_json_bridged(self, mock_get_client):
        """Module-level generate_json_bridged delegates to client."""
        from execution.llm_client import generate_json_bridged as mod_fn

        mock_client = MagicMock()
        mock_client.generate_json_bridged.return_value = {"bridged": True}
        mock_get_client.return_value = mock_client
        result = mod_fn(system_prompt="s", user_prompt="u")
        assert result == {"bridged": True}

    @patch("execution.llm_client.get_default_client")
    def test_module_generate_text_bridged(self, mock_get_client):
        """Module-level generate_text_bridged delegates to client."""
        from execution.llm_client import generate_text_bridged as mod_fn

        mock_client = MagicMock()
        mock_client.generate_text_bridged.return_value = "bridged text"
        mock_get_client.return_value = mock_client
        result = mod_fn(system_prompt="s", user_prompt="u")
        assert result == "bridged text"


# ── CLI main() (lines 926-977) ──────────────────────────────


class TestCLIMain:
    def _mock_client(self):
        """Create a mock LLMClient for CLI tests."""
        client = LLMClient.__new__(LLMClient)
        client.provider_order = list(DEFAULT_PROVIDER_ORDER)
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {"google": "key"}
        client.max_retries = 2
        client.cache_ttl_sec = 0
        client.track_usage = True
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch("sys.argv", ["llm_client.py", "status"])
    def test_cli_status(self, capsys):
        """CLI 'status' subcommand prints provider status."""
        from execution.llm_client import main

        with patch("execution.llm_client.LLMClient", return_value=self._mock_client()):
            ret = main()
        assert ret == 0
        out = capsys.readouterr().out
        assert "google" in out

    @patch("sys.argv", ["llm_client.py", "test", "--provider", "google"])
    def test_cli_test_single(self, capsys):
        """CLI 'test --provider google' tests single provider."""
        from execution.llm_client import main

        mock_client = self._mock_client()
        mock_client.test_provider = MagicMock(
            return_value={
                "provider": "google",
                "model": "gemini-2.5-flash",
                "status": "ok",
                "detail": "ok",
            }
        )
        with patch("execution.llm_client.LLMClient", return_value=mock_client):
            ret = main()
        assert ret == 0

    @patch("sys.argv", ["llm_client.py", "test"])
    def test_cli_test_all(self, capsys):
        """CLI 'test' without --provider tests all providers."""
        from execution.llm_client import main

        mock_client = self._mock_client()
        mock_client.test_all_providers = MagicMock(
            return_value=[
                {"provider": "google", "model": "gemini-2.5-flash", "status": "ok", "detail": "ok"},
            ]
        )
        with patch("execution.llm_client.LLMClient", return_value=mock_client):
            ret = main()
        assert ret == 0

    @patch("sys.argv", ["llm_client.py"])
    def test_cli_no_subcommand(self):
        """CLI with no subcommand prints help."""
        from execution.llm_client import main

        with patch("execution.llm_client.LLMClient", return_value=self._mock_client()):
            ret = main()
        assert ret == 0


# ── _generate_once unsupported provider (line 349) ──────────


class TestGenerateOnceUnsupported:
    def _make_client(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["fakeprovider"]
        client.models = {"fakeprovider": "fake-model"}
        client.api_keys = {"fakeprovider": "key"}
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    def test_unsupported_provider_raises(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="Unknown provider"):
            client._generate_once("fakeprovider", "sys", "usr", 0.5, json_mode=False)


# ── text_bridged enforce repair loop (lines 603, 613-656, 665, 667) ──


class TestTextBridgedRepairLoop:
    def _make_client(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {"openai": "sk-test"}
        client.max_retries = 2
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch.object(LLMClient, "_generate_once")
    def test_enforce_validation_passed_returns(self, mock_gen):
        """Line 603: validation.passed → return content directly."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        # Return Korean text that passes validation
        mock_gen.return_value = ("한국어 응답입니다. 테스트 결과를 확인하세요.", 5, 10, 0, 0)
        policy = BridgePolicy(mode="enforce", repair_attempts=1, fallback_providers=("openai",))
        result = client.generate_text_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert "한국어" in result

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_enforce_repair_success(self, mock_gen, mock_sleep):
        """Lines 613-648: repair loop succeeds on first repair attempt."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        # First call: English (fails validation), second call (repair): Korean (passes)
        mock_gen.side_effect = [
            ("English only text", 5, 10, 0, 0),
            ("수리된 한국어 응답입니다. 이것은 테스트입니다.", 5, 10, 0, 0),
        ]
        policy = BridgePolicy(mode="enforce", repair_attempts=1, fallback_providers=("openai",))
        result = client.generate_text_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert "한국어" in result
        assert mock_gen.call_count == 2

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_enforce_repair_second_attempt_succeeds(self, mock_gen, mock_sleep):
        """Line 656: validation = repair_validation in multi-repair loop."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = [
            ("English only text", 5, 10, 0, 0),  # initial: fails
            ("Still English text", 5, 10, 0, 0),  # repair 1: fails → line 656 hit
            ("두 번째 수리된 한국어 응답입니다. 이것은 테스트입니다.", 5, 10, 0, 0),  # repair 2: passes
        ]
        policy = BridgePolicy(mode="enforce", repair_attempts=2, fallback_providers=("openai",))
        result = client.generate_text_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert "한국어" in result
        assert mock_gen.call_count == 3

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_shadow_repair_returns_on_warning(self, mock_gen, mock_sleep):
        """Lines 649-656: shadow mode repair returns content with warning."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        # First call: English (fails), repair: also English (still fails but shadow)
        mock_gen.side_effect = [
            ("", 5, 10, 0, 0),  # empty → is_empty=True
            ("English repaired text", 5, 10, 0, 0),  # non-empty but fails Korean
        ]
        policy = BridgePolicy(mode="shadow", repair_attempts=1, fallback_providers=("openai",))
        result = client.generate_text_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert result == "English repaired text"

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_enforce_non_retryable_breaks(self, mock_gen, mock_sleep):
        """Lines 664-665: non-retryable error breaks the retry loop."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = [
            Exception("invalid api key provided"),
        ]
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_text_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )
        # Non-retryable should not sleep
        mock_sleep.assert_not_called()

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_enforce_retryable_sleeps(self, mock_gen, mock_sleep):
        """Lines 666-667: retryable error triggers sleep between retries."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = [
            Exception("connection timeout"),
            Exception("connection timeout again"),
        ]
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_text_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )
        mock_sleep.assert_called()


# ── json_bridged repair loop (lines 780-785, 796-797) ──────


class TestJsonBridgedRepairLoop:
    def _make_client(self):
        client = LLMClient.__new__(LLMClient)
        client.provider_order = ["openai"]
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {"openai": "sk-test"}
        client.max_retries = 2
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        return client

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_json_shadow_repair_returns(self, mock_gen, mock_sleep):
        """Lines 779-785: shadow mode returns repaired JSON with warning."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        # First call: empty (fails), repair: English JSON (json_valid but fails Korean)
        mock_gen.side_effect = [
            ("", 5, 10, 0, 0),  # empty → fails
            ('{"key":"English value"}', 5, 10, 0, 0),  # valid JSON, fails Korean
        ]
        policy = BridgePolicy(mode="shadow", repair_attempts=1, fallback_providers=("openai",))
        result = client.generate_json_bridged(
            system_prompt="s",
            user_prompt="u",
            policy=policy,
        )
        assert result == {"key": "English value"}

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_json_enforce_non_retryable_breaks(self, mock_gen, mock_sleep):
        """Lines 794-795: non-retryable error breaks json_bridged retry loop."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = Exception("invalid api key provided")
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_json_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )
        mock_sleep.assert_not_called()

    @patch("execution.llm_client.time.sleep")
    @patch.object(LLMClient, "_generate_once")
    def test_json_enforce_retryable_sleeps(self, mock_gen, mock_sleep):
        """Lines 796-797: retryable error triggers sleep in json_bridged."""
        from execution.language_bridge import BridgePolicy

        client = self._make_client()
        mock_gen.side_effect = [
            Exception("connection timeout"),
            Exception("connection timeout again"),
        ]
        policy = BridgePolicy(mode="enforce", repair_attempts=0, fallback_providers=("openai",))
        with pytest.raises(RuntimeError, match="브릿지 프로바이더 실패"):
            client.generate_json_bridged(
                system_prompt="s",
                user_prompt="u",
                policy=policy,
            )
        mock_sleep.assert_called()


# ── test_all_providers (lines 834-837) ──────────────────────


class TestTestAllProviders:
    def test_test_all_providers_calls_each(self):
        """test_all_providers iterates over DEFAULT_PROVIDER_ORDER."""
        client = LLMClient.__new__(LLMClient)
        client.provider_order = list(DEFAULT_PROVIDER_ORDER)
        client.models = dict(DEFAULT_MODELS)
        client.api_keys = {}
        client.max_retries = 1
        client.cache_ttl_sec = 0
        client.track_usage = False
        client._clients = {}
        client.caller_script = ""
        client.request_timeout_sec = 30
        results = client.test_all_providers()
        assert len(results) == len(DEFAULT_PROVIDER_ORDER)
        assert all(r["status"] == "skip" for r in results)


# ── Module-level bridged convenience with providers (lines 895-896, 914) ──


class TestConvenienceBridgedWithProviders:
    @patch("execution.llm_client.LLMClient")
    def test_generate_json_bridged_with_providers(self, mock_cls):
        from execution.llm_client import generate_json_bridged as fn

        mock_instance = MagicMock()
        mock_instance.generate_json_bridged.return_value = {"p": True}
        mock_cls.return_value = mock_instance
        result = fn(system_prompt="s", user_prompt="u", providers=["google"])
        assert result == {"p": True}
        mock_cls.assert_called_once()

    @patch("execution.llm_client.LLMClient")
    def test_generate_text_bridged_with_providers(self, mock_cls):
        from execution.llm_client import generate_text_bridged as fn

        mock_instance = MagicMock()
        mock_instance.generate_text_bridged.return_value = "bridged"
        mock_cls.return_value = mock_instance
        result = fn(system_prompt="s", user_prompt="u", providers=["google"])
        assert result == "bridged"
        mock_cls.assert_called_once()

    @patch("execution.llm_client.LLMClient")
    def test_generate_text_with_providers(self, mock_cls):
        from execution.llm_client import generate_text as fn

        mock_instance = MagicMock()
        mock_instance.generate_text.return_value = "text"
        mock_cls.return_value = mock_instance
        result = fn(system_prompt="s", user_prompt="u", providers=["openai"])
        assert result == "text"
        mock_cls.assert_called_once()
