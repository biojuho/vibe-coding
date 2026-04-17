"""Multi-provider management and async LLM calls for draft generation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import aiohttp
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

PROVIDER_ALIASES: dict[str, str] = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "grok": "xai",
    "xai": "xai",
    "chatgpt": "openai",
    "openai": "openai",
    "ollama": "ollama",
}

DEFAULT_PROVIDER_ORDER: list[str] = ["anthropic", "gemini", "xai", "openai", "ollama"]


class DraftProvidersMixin:
    """Mixin providing multi-provider LLM management for TweetDraftGenerator.

    Expects the host class to set the following attributes in ``__init__``:
    ``self.config``, ``self.provider_order``, ``self.request_timeout_seconds``,
    ``self.anthropic_enabled``, ``self.openai_enabled``, ``self.gemini_enabled``,
    ``self.xai_enabled``, ``self.ollama_enabled``,
    ``self.anthropic_client``, ``self.openai_client``, ``self.xai_client``,
    ``self.ollama_client``,
    ``self.anthropic_model``, ``self.openai_model``, ``self.gemini_model``,
    ``self.xai_model``, ``self.ollama_model``,
    ``self.gemini_api_key``.
    """

    # ------------------------------------------------------------------
    # Provider order resolution
    # ------------------------------------------------------------------

    def _resolve_provider_order(self) -> list[str]:
        configured = self.config.get("llm.providers", None)
        if not configured:
            return list(DEFAULT_PROVIDER_ORDER)

        normalized: list[str] = []
        for provider in configured:
            provider_name = PROVIDER_ALIASES.get(str(provider).strip().lower())
            if provider_name and provider_name not in normalized:
                normalized.append(provider_name)
        return normalized or list(DEFAULT_PROVIDER_ORDER)

    # ------------------------------------------------------------------
    # Provider availability checks
    # ------------------------------------------------------------------

    def _provider_enabled(self, provider: str, api_key: str | None) -> bool:
        if provider == "openai":
            explicit = self.config.get("openai.chat_enabled", None)
            if explicit is None:
                explicit = self.config.get("openai.enabled", None)
        else:
            explicit = self.config.get(f"{provider}.enabled", None)
        if explicit is None:
            explicit = True
        return bool(explicit and api_key)

    def _check_ollama_enabled(self) -> bool:
        """Ollama 서비스가 로컬에서 실행 중인지 확인. 미실행 시 자동 비활성화."""
        explicit = self.config.get("ollama.enabled", None)
        if explicit is False:
            return False
        base_url = self.config.get("ollama.base_url", "http://localhost:11434/v1")
        # `/v1` 은 OpenAI-호환 경로 — health check 은 루트 `/api/tags` 사용
        host = base_url.rstrip("/").removesuffix("/v1")
        health_url = f"{host}/api/tags"
        try:
            import urllib.request

            req = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            logger.debug("Ollama not available at %s — disabled as fallback.", health_url)
            return False

    def _enabled_providers(self) -> list[str]:
        availability = {
            "anthropic": self.anthropic_enabled,
            "gemini": self.gemini_enabled,
            "xai": self.xai_enabled,
            "openai": self.openai_enabled,
            "ollama": self.ollama_enabled,
        }
        return [provider for provider in self.provider_order if availability.get(provider, False)]

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    def _timeout_for(self, provider: str) -> int:
        """프로바이더별 차등 타임아웃: 유료 45s, 무료/저렴 30s, Ollama(CPU) 90s."""
        if provider == "ollama":
            return 90  # CPU 추론은 느림 → 넉넉한 타임아웃
        if provider in {"anthropic", "openai"}:
            return self.request_timeout_seconds
        return min(30, self.request_timeout_seconds)

    # ------------------------------------------------------------------
    # Per-provider generation helpers
    # ------------------------------------------------------------------

    async def _generate_with_anthropic(self, prompt: str) -> tuple[str, int, int]:
        response = await self.anthropic_client.messages.create(
            model=self.anthropic_model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        input_tokens = getattr(response.usage, "input_tokens", 0)
        output_tokens = getattr(response.usage, "output_tokens", 0)
        return text, input_tokens, output_tokens

    async def _generate_with_openai(self, prompt: str) -> tuple[str, int, int]:
        response = await self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (response.choices[0].message.content or "") if response.choices else ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return text, input_tokens, output_tokens

    async def _generate_with_xai(self, prompt: str) -> tuple[str, int, int]:
        response = await self.xai_client.chat.completions.create(
            model=self.xai_model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return text, input_tokens, output_tokens

    async def _generate_with_ollama(self, prompt: str) -> tuple[str, int, int]:
        """Ollama 로컬 LLM으로 초안 생성 (OpenAI 호환 API, CPU 추론)."""
        response = await self.ollama_client.chat.completions.create(
            model=self.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        return text, input_tokens, output_tokens

    async def _generate_with_gemini(self, prompt: str) -> tuple[str, int, int]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7},
        }
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                params={"key": self.gemini_api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                text_body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"Gemini API error {response.status}: {text_body}")
                data = json.loads(text_body)

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if part.get("text"))
        usage = data.get("usageMetadata", {}) or {}
        input_tokens = int(usage.get("promptTokenCount", 0) or 0)
        output_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
        return text, input_tokens, output_tokens

    # ------------------------------------------------------------------
    # Unified generation dispatcher
    # ------------------------------------------------------------------

    async def _generate_once(self, provider: str, prompt: str) -> tuple[str, int, int]:
        timeout = self._timeout_for(provider)
        coro = None
        if provider == "anthropic":
            coro = self._generate_with_anthropic(prompt)
        elif provider == "openai":
            coro = self._generate_with_openai(prompt)
        elif provider == "gemini":
            coro = self._generate_with_gemini(prompt)
        elif provider == "xai":
            coro = self._generate_with_xai(prompt)
        elif provider == "ollama":
            coro = self._generate_with_ollama(prompt)
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")
        return await asyncio.wait_for(coro, timeout=timeout)


def init_provider_clients(instance: Any) -> None:
    """Helper called from ``TweetDraftGenerator.__init__`` to set up API keys,
    enabled flags, and async client objects on *instance*.

    This keeps the heavy setup logic close to the provider module while the
    main ``__init__`` stays short.
    """
    config = instance.config

    instance.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY") or config.get("anthropic.api_key")
    instance.openai_api_key = os.environ.get("OPENAI_API_KEY") or config.get("openai.api_key")
    instance.gemini_api_key = (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or config.get("gemini.api_key")
    )
    instance.xai_api_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or config.get("xai.api_key")

    instance.anthropic_model = config.get("anthropic.model", "claude-haiku-4-5-20251001")
    instance.openai_model = config.get("openai.chat_model", "gpt-4.1-mini")
    instance.gemini_model = config.get("gemini.model", "gemini-2.5-flash")
    instance.xai_model = config.get("xai.model", "grok-4-1-fast-reasoning")
    instance.ollama_model = config.get("ollama.model", "gemma3:4b")
    instance.ollama_base_url = config.get("ollama.base_url", "http://localhost:11434/v1")

    instance.anthropic_enabled = instance._provider_enabled("anthropic", instance.anthropic_api_key)
    instance.openai_enabled = instance._provider_enabled("openai", instance.openai_api_key)
    instance.gemini_enabled = instance._provider_enabled("gemini", instance.gemini_api_key)
    instance.xai_enabled = instance._provider_enabled("xai", instance.xai_api_key)
    instance.ollama_enabled = instance._check_ollama_enabled()

    instance.anthropic_client = (
        AsyncAnthropic(api_key=instance.anthropic_api_key) if instance.anthropic_enabled else None
    )
    instance.openai_client = AsyncOpenAI(api_key=instance.openai_api_key) if instance.openai_enabled else None
    instance.xai_client = (
        AsyncOpenAI(api_key=instance.xai_api_key, base_url="https://api.x.ai/v1") if instance.xai_enabled else None
    )
    instance.ollama_client = (
        AsyncOpenAI(api_key="ollama", base_url=instance.ollama_base_url) if instance.ollama_enabled else None
    )
