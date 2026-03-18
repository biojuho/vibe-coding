"""error_types.py 유닛 테스트."""
from __future__ import annotations

import pytest

from shorts_maker_v2.pipeline.error_types import (
    PipelineError,
    PipelineErrorType,
    classify_error,
)


class TestPipelineErrorType:
    def test_all_9_types_defined(self):
        types = {e.value for e in PipelineErrorType}
        assert types == {
            "network_error", "rate_limit", "auth_error", "server_error",
            "invalid_response", "content_filter", "context_length",
            "resource_error", "unknown",
        }

    def test_retryable_types(self):
        assert PipelineErrorType.NETWORK_ERROR.is_retryable is True
        assert PipelineErrorType.RATE_LIMIT.is_retryable is True
        assert PipelineErrorType.SERVER_ERROR.is_retryable is True
        assert PipelineErrorType.INVALID_RESPONSE.is_retryable is True

    def test_non_retryable_types(self):
        assert PipelineErrorType.AUTH_ERROR.is_retryable is False
        assert PipelineErrorType.CONTENT_FILTER.is_retryable is False
        assert PipelineErrorType.CONTEXT_LENGTH.is_retryable is False
        assert PipelineErrorType.RESOURCE_ERROR.is_retryable is False
        assert PipelineErrorType.UNKNOWN.is_retryable is False

    def test_suggested_wait_sec_rate_limit(self):
        assert PipelineErrorType.RATE_LIMIT.suggested_wait_sec == 15.0

    def test_suggested_wait_sec_network(self):
        assert PipelineErrorType.NETWORK_ERROR.suggested_wait_sec == 3.0

    def test_suggested_wait_sec_auth_zero(self):
        assert PipelineErrorType.AUTH_ERROR.suggested_wait_sec == 0.0

    def test_suggested_wait_sec_unknown_default(self):
        assert PipelineErrorType.UNKNOWN.suggested_wait_sec == 2.0

    def test_icons_defined_for_all_types(self):
        for t in PipelineErrorType:
            icon = t.icon
            assert isinstance(icon, str) and len(icon) > 0

    def test_is_str_enum(self):
        assert PipelineErrorType.RATE_LIMIT == "rate_limit"


class TestClassifyError:
    def test_timeout_is_network_error(self):
        assert classify_error(TimeoutError("Request timed out")) == PipelineErrorType.NETWORK_ERROR

    def test_connection_error_is_network(self):
        assert classify_error(ConnectionError("connection refused")) == PipelineErrorType.NETWORK_ERROR

    def test_rate_limit_429(self):
        assert classify_error(Exception("429 Too Many Requests")) == PipelineErrorType.RATE_LIMIT

    def test_rate_limit_keyword(self):
        assert classify_error(Exception("rate limit exceeded")) == PipelineErrorType.RATE_LIMIT

    def test_auth_error_invalid_api_key(self):
        assert classify_error(Exception("Invalid API key provided")) == PipelineErrorType.AUTH_ERROR

    def test_auth_error_unauthorized(self):
        assert classify_error(Exception("Unauthorized access")) == PipelineErrorType.AUTH_ERROR

    def test_auth_error_credit_balance(self):
        assert classify_error(Exception("credit balance is too low")) == PipelineErrorType.AUTH_ERROR

    def test_server_error_500(self):
        assert classify_error(Exception("500 Internal Server Error")) == PipelineErrorType.SERVER_ERROR

    def test_server_error_503(self):
        assert classify_error(Exception("503 Service Unavailable")) == PipelineErrorType.SERVER_ERROR

    def test_server_error_overloaded(self):
        assert classify_error(Exception("overloaded, please try again")) == PipelineErrorType.SERVER_ERROR

    def test_invalid_response_json(self):
        assert classify_error(ValueError("JSON parse error: expecting value")) == PipelineErrorType.INVALID_RESPONSE

    def test_invalid_response_decode(self):
        assert classify_error(Exception("decode error: malformed response")) == PipelineErrorType.INVALID_RESPONSE

    def test_content_filter_safety(self):
        assert classify_error(Exception("content policy violation: safety")) == PipelineErrorType.CONTENT_FILTER

    def test_content_filter_blocked(self):
        assert classify_error(Exception("your request was rejected due to policy")) == PipelineErrorType.CONTENT_FILTER

    def test_context_length(self):
        assert classify_error(Exception("context_length exceeded token limit")) == PipelineErrorType.CONTEXT_LENGTH

    def test_context_too_long(self):
        assert classify_error(Exception("Input is too long for context window")) == PipelineErrorType.CONTEXT_LENGTH

    def test_resource_error_disk(self):
        assert classify_error(OSError("No such file or directory")) == PipelineErrorType.RESOURCE_ERROR

    def test_resource_error_memory(self):
        assert classify_error(Exception("out of memory")) == PipelineErrorType.RESOURCE_ERROR

    def test_unknown_error(self):
        assert classify_error(Exception("some completely unexpected error xyz")) == PipelineErrorType.UNKNOWN

    def test_case_insensitive(self):
        assert classify_error(Exception("RATE LIMIT exceeded")) == PipelineErrorType.RATE_LIMIT

    # AUTH가 RATE_LIMIT보다 먼저 매칭되는지 확인 (classification rule 순서)
    def test_auth_takes_priority_over_unknown(self):
        result = classify_error(Exception("invalid_api_key"))
        assert result == PipelineErrorType.AUTH_ERROR


class TestPipelineError:
    def test_basic_construction(self):
        err = PipelineError(
            "test error",
            PipelineErrorType.RATE_LIMIT,
            step="script_step",
            provider="openai",
        )
        assert str(err) == "test error"
        assert err.error_type == PipelineErrorType.RATE_LIMIT
        assert err.step == "script_step"
        assert err.provider == "openai"
        assert err.cause is None
        assert err.context == {}

    def test_to_dict_keys(self):
        err = PipelineError("msg", PipelineErrorType.NETWORK_ERROR, step="media_step")
        d = err.to_dict()
        assert d["message"] == "msg"
        assert d["error_type"] == "network_error"
        assert d["step"] == "media_step"
        assert d["is_retryable"] is True
        assert d["cause_type"] == ""

    def test_to_dict_with_cause(self):
        cause = ValueError("original")
        err = PipelineError("wrapped", PipelineErrorType.INVALID_RESPONSE, cause=cause)
        d = err.to_dict()
        assert d["cause_type"] == "ValueError"
        assert d["is_retryable"] is True

    def test_to_dict_non_retryable(self):
        err = PipelineError("auth failed", PipelineErrorType.AUTH_ERROR)
        assert err.to_dict()["is_retryable"] is False

    def test_context_stored(self):
        err = PipelineError("err", PipelineErrorType.UNKNOWN, context={"attempt": 3})
        assert err.context["attempt"] == 3

    def test_from_exception_timeout(self):
        exc = TimeoutError("timed out")
        pe = PipelineError.from_exception(exc, step="tts_step", provider="edge_tts")
        assert pe.error_type == PipelineErrorType.NETWORK_ERROR
        assert pe.step == "tts_step"
        assert pe.provider == "edge_tts"
        assert pe.cause is exc

    def test_from_exception_unknown(self):
        exc = RuntimeError("unexpected problem")
        pe = PipelineError.from_exception(exc)
        assert pe.error_type == PipelineErrorType.UNKNOWN

    def test_is_exception_subclass(self):
        err = PipelineError("test", PipelineErrorType.UNKNOWN)
        assert isinstance(err, Exception)
        with pytest.raises(PipelineError):
            raise err
