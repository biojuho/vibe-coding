"""LLM 폴백 체인 테스트.

프로바이더 발견, 순서, 폴백 전이, 에러 처리를 검증합니다.
실제 API 호출 없이 mock으로 동작합니다.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from execution.llm_client import (
    DEFAULT_MODELS,
    DEFAULT_PROVIDER_ORDER,
    LLMClient,
)


@pytest.fixture
def all_keys_env(monkeypatch):
    """모든 프로바이더 API 키를 fake로 설정."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-google")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.setenv("XAI_API_KEY", "xai-fake")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-ds")
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-fake-ms")
    monkeypatch.setenv("ZHIPUAI_API_KEY", "fake-zhipu")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-fake")


@pytest.fixture
def no_keys_env(monkeypatch):
    """모든 API 키 제거."""
    for key in [
        "OLLAMA_BASE_URL",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "MOONSHOT_API_KEY",
        "ZHIPUAI_API_KEY",
        "GROQ_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)


# ── 프로바이더 발견 ──────────────────────────────────────


def test_default_provider_order_has_8_providers():
    """기본 프로바이더 순서가 현재 설정과 일치한다."""
    assert len(DEFAULT_PROVIDER_ORDER) == 9
    assert DEFAULT_PROVIDER_ORDER[0] == "ollama"
    assert DEFAULT_PROVIDER_ORDER[-1] == "anthropic"


def test_client_discovers_all_providers_with_keys(all_keys_env):
    """모든 API 키가 있으면 기본 순서 전체가 활성화된다."""
    client = LLMClient(cache_ttl_sec=0)
    enabled = client.enabled_providers()
    assert len(enabled) == len(DEFAULT_PROVIDER_ORDER)


def test_client_no_keys_returns_empty(no_keys_env):
    """API 키가 없으면 활성 프로바이더 0개."""
    client = LLMClient(cache_ttl_sec=0)
    assert len(client.enabled_providers()) == 0


def test_partial_keys(monkeypatch):
    """일부 키만 있으면 해당 프로바이더만 활성화."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    client = LLMClient(cache_ttl_sec=0)
    enabled = client.enabled_providers()
    assert "google" in enabled
    assert "openai" not in enabled


# ── 프로바이더 순서 ──────────────────────────────────────


def test_custom_provider_order(all_keys_env):
    """커스텀 프로바이더 순서가 존중됨."""
    client = LLMClient(providers=["anthropic", "openai", "google"], cache_ttl_sec=0)
    enabled = client.enabled_providers()
    assert enabled[0] == "anthropic"
    assert enabled[1] == "openai"
    assert enabled[2] == "google"


def test_provider_aliases(all_keys_env):
    """프로바이더 별명이 정규화됨."""
    client = LLMClient(providers=["chatgpt", "gemini", "claude"], cache_ttl_sec=0)
    enabled = client.enabled_providers()
    assert "openai" in enabled
    assert "google" in enabled
    assert "anthropic" in enabled


# ── 상태 보고 ──────────────────────────────────────


def test_all_provider_status(all_keys_env):
    """전체 프로바이더 상태 딕셔너리."""
    client = LLMClient(cache_ttl_sec=0)
    status = client.all_provider_status()
    assert isinstance(status, dict)
    assert all(isinstance(v, bool) for v in status.values())
    assert status["google"] is True


def test_all_provider_status_no_keys(no_keys_env):
    """키 없으면 모두 False."""
    client = LLMClient(cache_ttl_sec=0)
    status = client.all_provider_status()
    assert all(v is False for v in status.values())


# ── E2E 폴백 체인 테스트 ──────────────────────────────────


def _make_e2e_client(providers: list[str]) -> LLMClient:
    """테스트용 LLMClient 생성 (실제 API 호출 없이)."""
    client = LLMClient.__new__(LLMClient)
    client.provider_order = list(providers)
    client.models = dict(DEFAULT_MODELS)
    client.api_keys = {p: f"fake-{p}" for p in providers}
    client.max_retries = 2
    client.cache_ttl_sec = 0
    client.track_usage = False
    client._clients = {}
    client.caller_script = ""
    client.request_timeout_sec = 30
    return client


class TestFullCascadeFallback:
    """기본 프로바이더 전체 순차 폴백을 검증합니다."""

    def test_first_provider_succeeds_no_fallback(self):
        """첫 프로바이더 성공 시 나머지 호출 안 함."""
        client = _make_e2e_client(["google", "openai", "anthropic"])
        calls: list[str] = []

        def fake_gen(provider, *a, **kw):
            calls.append(provider)
            return '{"result": "ok"}', 10, 5, 0, 0

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            result = client.generate_json(system_prompt="s", user_prompt="u")

        assert result == {"result": "ok"}
        assert calls == ["google"]

    @patch("execution.llm_client.time.sleep")
    def test_cascade_7_fail_8th_succeeds(self, mock_sleep):
        """마지막 프로바이더만 성공해도 순차 폴백이 완주된다."""
        all_providers = list(DEFAULT_PROVIDER_ORDER)
        client = _make_e2e_client(all_providers)
        calls: list[str] = []
        last_provider = all_providers[-1]

        def fake_gen(provider, *a, **kw):
            calls.append(provider)
            if provider == last_provider:
                return '{"answer": "from last provider"}', 20, 10, 0, 0
            raise Exception(f"{provider} timeout")

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            result = client.generate_json(system_prompt="s", user_prompt="u")

        assert result == {"answer": "from last provider"}
        assert calls.count(last_provider) >= 1
        assert calls[0] == DEFAULT_PROVIDER_ORDER[0]

    @patch("execution.llm_client.time.sleep")
    def test_all_8_providers_exhausted_raises(self, mock_sleep):
        """기본 프로바이더 전체가 실패 시 RuntimeError."""
        all_providers = list(DEFAULT_PROVIDER_ORDER)
        client = _make_e2e_client(all_providers)

        def fake_gen(provider, *a, **kw):
            raise Exception(f"{provider} server error")

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            with pytest.raises(RuntimeError, match="모든 LLM 프로바이더 실패"):
                client.generate_json(system_prompt="s", user_prompt="u")

    @patch("execution.llm_client.time.sleep")
    def test_non_retryable_skips_retries_falls_to_next(self, mock_sleep):
        """non-retryable 에러는 재시도 없이 즉시 다음 프로바이더로."""
        client = _make_e2e_client(["google", "openai", "anthropic"])
        calls: list[str] = []

        def fake_gen(provider, *a, **kw):
            calls.append(provider)
            if provider == "google":
                raise Exception("invalid api key")  # non-retryable
            if provider == "openai":
                return '{"ok": true}', 5, 3, 0, 0
            raise Exception("should not reach")

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            result = client.generate_json(system_prompt="s", user_prompt="u")

        assert result == {"ok": True}
        # google: 1번만 (non-retryable → 재시도 안 함)
        assert calls.count("google") == 1
        assert calls.count("openai") == 1

    @patch("execution.llm_client.time.sleep")
    def test_generate_text_cascade(self, mock_sleep):
        """generate_text도 폴백 체인이 동작."""
        client = _make_e2e_client(["google", "openai"])
        calls: list[str] = []

        def fake_gen(provider, *a, **kw):
            calls.append(provider)
            if provider == "google":
                raise Exception("rate limit")
            return "success text", 5, 3, 0, 0

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            result = client.generate_text(system_prompt="s", user_prompt="u")

        assert result == "success text"
        assert "openai" in calls

    @patch("execution.llm_client.time.sleep")
    def test_cascade_order_preserved(self, mock_sleep):
        """프로바이더 시도 순서가 설정된 순서를 따름."""
        order = ["deepseek", "groq", "google", "anthropic"]
        client = _make_e2e_client(order)
        tried: list[str] = []

        def fake_gen(provider, *a, **kw):
            if provider not in tried:
                tried.append(provider)
            if provider == "anthropic":
                return '{"done": true}', 5, 3, 0, 0
            raise Exception("fail")

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            client.generate_json(system_prompt="s", user_prompt="u")

        assert tried == ["deepseek", "groq", "google", "anthropic"]

    @patch("execution.llm_client.time.sleep")
    def test_mixed_failure_modes(self, mock_sleep):
        """다양한 실패 유형 혼재 시에도 정상 폴백."""
        client = _make_e2e_client(["google", "deepseek", "openai", "anthropic"])
        calls: list[str] = []

        def fake_gen(provider, *a, **kw):
            calls.append(provider)
            if provider == "google":
                raise TimeoutError("connection timeout")
            if provider == "deepseek":
                raise Exception("insufficient_quota")  # non-retryable
            if provider == "openai":
                raise ConnectionError("network unreachable")
            return '{"result": "anthropic wins"}', 10, 5, 0, 0

        with patch.object(client, "_generate_once", side_effect=fake_gen):
            result = client.generate_json(system_prompt="s", user_prompt="u")

        assert result == {"result": "anthropic wins"}
        # deepseek는 non-retryable → 1번만
        assert calls.count("deepseek") == 1
        # google/openai는 retryable → max_retries(2)번
        assert calls.count("google") == 2
        assert calls.count("openai") == 2
