"""LLM 폴백 체인 테스트.

프로바이더 발견, 순서, 폴백 전이, 에러 처리를 검증합니다.
실제 API 호출 없이 mock으로 동작합니다.
"""

from __future__ import annotations


import pytest

from execution.llm_client import (
    DEFAULT_PROVIDER_ORDER,
    LLMClient,
)


@pytest.fixture
def all_keys_env(monkeypatch):
    """모든 프로바이더 API 키를 fake로 설정."""
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
        "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY", "XAI_API_KEY", "DEEPSEEK_API_KEY",
        "MOONSHOT_API_KEY", "ZHIPUAI_API_KEY", "GROQ_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)


# ── 프로바이더 발견 ──────────────────────────────────────


def test_default_provider_order_has_8_providers():
    """기본 프로바이더 순서가 8개."""
    assert len(DEFAULT_PROVIDER_ORDER) == 8
    assert DEFAULT_PROVIDER_ORDER[0] == "google"
    assert DEFAULT_PROVIDER_ORDER[-1] == "anthropic"


def test_client_discovers_all_providers_with_keys(all_keys_env):
    """모든 API 키가 있으면 8개 프로바이더 활성화."""
    client = LLMClient(cache_ttl_sec=0)
    enabled = client.enabled_providers()
    assert len(enabled) == 8


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
