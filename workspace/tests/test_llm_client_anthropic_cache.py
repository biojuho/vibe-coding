"""execution/llm_client.py — Anthropic prompt caching (cache_strategy) 회귀 테스트.

T-255: directives/anthropic_prompt_caching.md 의 cache_strategy 인터페이스를 고정한다.

검증 항목:
  - cache_strategy="off" (default) 호출은 system을 string으로 전달, cache_control 미주입
  - cache_strategy="5m" 호출은 system을 list[block] 형태 + cache_control{"type":"ephemeral"} 주입
  - cache_strategy="1h" 호출은 ttl="1h" 주입
  - 응답의 cache_creation_input_tokens / cache_read_input_tokens 값이 _generate_once 5-tuple로 흘러나옴
  - 비-anthropic provider 분기는 cache_strategy를 무시하고 0/0 반환
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from execution.llm_client import LLMClient


def _make_client(provider: str = "anthropic"):
    client = LLMClient.__new__(LLMClient)
    client.provider_order = [provider]
    client.models = {provider: "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o-mini"}
    client.api_keys = {provider: "test-key"}
    client.max_retries = 1
    client.cache_ttl_sec = 0
    client.track_usage = False
    client._clients = {}
    client.caller_script = ""
    client.request_timeout_sec = 30
    return client


def _make_anthropic_response(*, cache_creation: int = 0, cache_read: int = 0) -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text='{"ok": true}')]
    resp.usage = MagicMock(
        input_tokens=120,
        output_tokens=30,
        cache_creation_input_tokens=cache_creation,
        cache_read_input_tokens=cache_read,
    )
    return resp


class TestCacheStrategyOff:
    @patch.object(LLMClient, "_get_client")
    def test_default_passes_system_as_string(self, mock_get_client):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response()
        mock_get_client.return_value = mock_anthropic

        content, in_tok, out_tok, cache_w, cache_r = client._generate_once(
            "anthropic", "SYS", "USER", 0.7, json_mode=False
        )

        assert content == '{"ok": true}'
        assert (in_tok, out_tok, cache_w, cache_r) == (120, 30, 0, 0)
        kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert kwargs["system"] == "SYS"  # string, not a list
        assert "extra_headers" not in kwargs

    @patch.object(LLMClient, "_get_client")
    def test_explicit_off_matches_default(self, mock_get_client):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response()
        mock_get_client.return_value = mock_anthropic

        client._generate_once("anthropic", "SYS", "USER", 0.7, json_mode=False, cache_strategy="off")

        kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert kwargs["system"] == "SYS"
        assert "extra_headers" not in kwargs


class TestCacheStrategy5m:
    @patch.object(LLMClient, "_get_client")
    def test_5m_injects_ephemeral_cache_control(self, mock_get_client):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response(cache_creation=900, cache_read=0)
        mock_get_client.return_value = mock_anthropic

        content, in_tok, out_tok, cache_w, cache_r = client._generate_once(
            "anthropic", "LARGE_SYS_PROMPT", "USER", 0.7, json_mode=False, cache_strategy="5m"
        )

        assert (cache_w, cache_r) == (900, 0)
        kwargs = mock_anthropic.messages.create.call_args.kwargs
        assert isinstance(kwargs["system"], list)
        block = kwargs["system"][0]
        assert block["type"] == "text"
        assert block["text"] == "LARGE_SYS_PROMPT"
        assert block["cache_control"] == {"type": "ephemeral"}
        # 5m TTL은 default — ttl 키가 추가되지 않아야 함
        assert "ttl" not in block["cache_control"]
        assert "extra_headers" not in kwargs

    @patch.object(LLMClient, "_get_client")
    def test_5m_captures_cache_read_tokens(self, mock_get_client):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response(cache_creation=0, cache_read=900)
        mock_get_client.return_value = mock_anthropic

        _, _, _, cache_w, cache_r = client._generate_once(
            "anthropic", "SYS", "USER", 0.7, json_mode=False, cache_strategy="5m"
        )
        assert (cache_w, cache_r) == (0, 900)


class TestCacheStrategy1h:
    @patch.object(LLMClient, "_get_client")
    def test_1h_adds_ttl_without_extra_headers(self, mock_get_client):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response()
        mock_get_client.return_value = mock_anthropic

        client._generate_once("anthropic", "SYS", "USER", 0.7, json_mode=False, cache_strategy="1h")

        kwargs = mock_anthropic.messages.create.call_args.kwargs
        block = kwargs["system"][0]
        assert block["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
        assert "extra_headers" not in kwargs


class TestNonAnthropicIgnoresCacheStrategy:
    @patch.object(LLMClient, "_get_client")
    def test_openai_ignores_cache_strategy(self, mock_get_client):
        client = _make_client("openai")
        mock_openai = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content='{"ok":true}'))]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_openai.chat.completions.create.return_value = mock_resp
        mock_get_client.return_value = mock_openai

        content, in_tok, out_tok, cache_w, cache_r = client._generate_once(
            "openai", "SYS", "USER", 0.7, json_mode=True, cache_strategy="5m"
        )

        assert (in_tok, out_tok, cache_w, cache_r) == (10, 20, 0, 0)
        # OpenAI-compatible 페이로드는 변하지 않아야 함 (system은 messages 안의 일반 string)
        kwargs = mock_openai.chat.completions.create.call_args.kwargs
        sys_msg = next(m for m in kwargs["messages"] if m["role"] == "system")
        assert sys_msg["content"] == "SYS"


class TestGenerateJsonPropagatesCacheStrategy:
    @patch.object(LLMClient, "_log_usage")
    @patch.object(LLMClient, "_get_client")
    def test_generate_json_routes_cache_tokens_to_log_usage(self, mock_get_client, mock_log_usage):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response(cache_creation=0, cache_read=750)
        mock_get_client.return_value = mock_anthropic

        result = client.generate_json(system_prompt="SYS", user_prompt="USER", cache_strategy="5m")

        assert result == {"ok": True}
        mock_log_usage.assert_called_once()
        kwargs = mock_log_usage.call_args.kwargs
        assert kwargs["cache_creation_tokens"] == 0
        assert kwargs["cache_read_tokens"] == 750
        assert kwargs["cache_creation_multiplier"] == 1.25

    @patch.object(LLMClient, "_log_usage")
    @patch.object(LLMClient, "_get_client")
    def test_generate_json_routes_1h_cache_write_multiplier(self, mock_get_client, mock_log_usage):
        client = _make_client("anthropic")
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = _make_anthropic_response(cache_creation=1000, cache_read=0)
        mock_get_client.return_value = mock_anthropic

        result = client.generate_json(system_prompt="SYS", user_prompt="USER", cache_strategy="1h")

        assert result == {"ok": True}
        kwargs = mock_log_usage.call_args.kwargs
        assert kwargs["cache_creation_tokens"] == 1000
        assert kwargs["cache_creation_multiplier"] == 2.0
