"""execution/llm_client.py — Langfuse opt-in trace 회귀 테스트.

T-253: directives/llm_observability_langfuse.md 의 _emit_langfuse_trace 후크를
opt-in 플래그(LANGFUSE_ENABLED=1) 없이 호출 시 100% no-op 인지 고정한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from execution.llm_client import _emit_langfuse_trace


class TestEmitLangfuseTraceDisabled:
    @patch.dict("os.environ", {"LANGFUSE_ENABLED": "0"}, clear=False)
    def test_disabled_does_not_import_sdk(self):
        # langfuse SDK 미설치 환경에서도 절대 import 시도하지 않아야 한다.
        # 검증: LANGFUSE_ENABLED=0 일 때 어떤 부수효과도 없음 (예외 없이 즉시 return).
        with patch("builtins.__import__", side_effect=AssertionError("SDK should not be imported")):
            _emit_langfuse_trace(
                provider="anthropic",
                model="claude-sonnet-4",
                endpoint="chat.completions",
                input_tokens=100,
                output_tokens=50,
            )

    @patch.dict("os.environ", {}, clear=True)
    def test_unset_env_treated_as_disabled(self):
        with patch("builtins.__import__", side_effect=AssertionError("SDK should not be imported")):
            _emit_langfuse_trace(
                provider="anthropic",
                model="claude-sonnet-4",
                endpoint="chat.completions",
                input_tokens=100,
                output_tokens=50,
            )

    @patch.dict(
        "os.environ",
        {"LANGFUSE_ENABLED": "1", "LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": ""},
        clear=False,
    )
    def test_enabled_but_missing_keys_no_op(self):
        # 키 미설정이면 enabled 라도 SDK import 시도 금지.
        with patch("builtins.__import__", side_effect=AssertionError("SDK should not be imported")):
            _emit_langfuse_trace(
                provider="anthropic",
                model="claude-sonnet-4",
                endpoint="chat.completions",
                input_tokens=100,
                output_tokens=50,
            )


class TestEmitLangfuseTraceEnabled:
    @patch.dict(
        "os.environ",
        {
            "LANGFUSE_ENABLED": "1",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LANGFUSE_HOST": "http://127.0.0.1:3030",
        },
        clear=False,
    )
    def test_enabled_sends_trace_and_generation(self):
        fake_observation = MagicMock()
        fake_client = MagicMock()
        fake_client.start_observation.return_value = fake_observation
        fake_module = MagicMock(get_client=MagicMock(return_value=fake_client))

        with patch.dict("sys.modules", {"langfuse": fake_module}):
            _emit_langfuse_trace(
                provider="anthropic",
                model="claude-sonnet-4",
                endpoint="chat.completions",
                input_tokens=120,
                output_tokens=30,
                cache_creation_tokens=900,
                cache_read_tokens=0,
                cost_usd=0.0042,
                caller_script="test_script",
                metadata={"bridge_mode": "off"},
            )

        # 최신 Langfuse SDK는 환경 변수 기반 get_client + manual observation을 사용한다.
        fake_module.get_client.assert_called_once_with()
        fake_client.start_observation.assert_called_once()
        gen_kwargs = fake_client.start_observation.call_args.kwargs
        assert gen_kwargs["name"] == "chat.completions"
        assert gen_kwargs["as_type"] == "generation"
        assert gen_kwargs["model"] == "claude-sonnet-4"
        assert gen_kwargs["usage_details"]["input"] == 120
        assert gen_kwargs["usage_details"]["output"] == 30
        assert gen_kwargs["usage_details"]["input_cache_creation"] == 900
        assert gen_kwargs["usage_details"]["input_cache_read"] == 0
        assert gen_kwargs["metadata"]["provider"] == "anthropic"
        assert gen_kwargs["metadata"]["bridge_mode"] == "off"
        fake_observation.end.assert_called_once_with()

    @patch.dict(
        "os.environ",
        {
            "LANGFUSE_ENABLED": "1",
            "LANGFUSE_PUBLIC_KEY": "pk",
            "LANGFUSE_SECRET_KEY": "sk",
        },
        clear=False,
    )
    def test_sdk_import_failure_silent(self):
        # SDK import 자체가 실패해도 LLM 호출 차단 금지 (silent drop).
        with patch.dict("sys.modules", {"langfuse": None}):
            # 정상 종료 (예외 던지지 않음)
            _emit_langfuse_trace(
                provider="anthropic",
                model="claude-sonnet-4",
                endpoint="chat.completions",
                input_tokens=100,
                output_tokens=50,
            )
