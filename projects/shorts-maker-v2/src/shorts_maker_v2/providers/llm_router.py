"""Multi-provider LLM router with fallback, retry, and cost-awareness.

Supported providers: openai, google (gemini), anthropic, xai (grok),
                     deepseek, moonshot (kimi), zhipuai (glm), groq (llama),
                     mimo (xiaomi).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from typing import Any


def _import_language_bridge():
    """Lazily import execution.language_bridge with dynamic sys.path fixup."""
    import sys as _sys
    from pathlib import Path as _Path

    _root = _Path(__file__).resolve().parent.parent.parent.parent.parent
    if str(_root) not in _sys.path:
        _sys.path.insert(0, str(_root))
    from execution.language_bridge import (  # type: ignore[import]
        BridgePolicy,
        build_bridge_system_prompt,
        build_repair_messages,
        normalize_json_payload,
        normalize_prompt_text,
        preferred_provider_order,
        validate_json_payload,
        validate_text_content,
    )

    return {
        "BridgePolicy": BridgePolicy,
        "build_bridge_system_prompt": build_bridge_system_prompt,
        "build_repair_messages": build_repair_messages,
        "normalize_json_payload": normalize_json_payload,
        "normalize_prompt_text": normalize_prompt_text,
        "preferred_provider_order": preferred_provider_order,
        "validate_json_payload": validate_json_payload,
        "validate_text_content": validate_text_content,
    }


_bridge_cache: dict | None = None
_bridge_lock = __import__("threading").Lock()


def _get_bridge():
    global _bridge_cache
    if _bridge_cache is None:
        with _bridge_lock:
            if _bridge_cache is None:
                _bridge_cache = _import_language_bridge()
    return _bridge_cache


logger = logging.getLogger(__name__)

PROVIDER_ALIASES = {
    "openai": "openai",
    "chatgpt": "openai",
    "gpt": "openai",
    "google": "google",
    "gemini": "google",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "xai": "xai",
    "grok": "xai",
    "deepseek": "deepseek",
    "moonshot": "moonshot",
    "kimi": "moonshot",
    "zhipuai": "zhipuai",
    "glm": "zhipuai",
    "zhipu": "zhipuai",
    "groq": "groq",
    "llama": "groq",
    "mimo": "mimo",
    "xiaomi": "mimo",
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "google": "gemini-3.1-flash-lite-preview",
    "anthropic": "claude-sonnet-4-6",
    "xai": "grok-3-mini-fast",
    "deepseek": "deepseek-chat",
    "moonshot": "moonshot-v1-8k",
    "zhipuai": "glm-4-flash",
    "groq": "llama-3.3-70b-versatile",
    "mimo": "mimo-v2-flash",
}

# Gemini 3.1 Thinking Levels (minimal → high)
VALID_THINKING_LEVELS = {"minimal", "low", "medium", "high"}

# OpenAI-compatible 프로바이더의 base_url
OPENAI_COMPATIBLE_BASE_URLS = {
    "xai": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipuai": "https://open.bigmodel.cn/api/paas/v4",
    "groq": "https://api.groq.com/openai/v1",
    "mimo": "https://api.xiaomimimo.com/v1",
}

NON_RETRYABLE_KEYWORDS = [
    "invalid api key",
    "unauthorized",
    "permission denied",
    "insufficient_quota",
    "credit balance is too low",
    "billing",
    "invalid_api_key",
    "authentication",
]


def _safe_console_print(message: str) -> None:
    """Print status lines without crashing on Windows console encodings."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    payload = f"{message}\n".encode(encoding, errors="replace")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(payload)
        sys.stdout.flush()
        return

    sys.stdout.write(payload.decode(encoding, errors="replace"))
    sys.stdout.flush()


def _bridge_reason_codes(validation: Any) -> str:
    return ",".join(getattr(validation, "reason_codes", []))


def _bridge_validation_error(provider: str, attempt: int, validation: Any) -> str:
    return f"{provider} attempt {attempt}: bridge validation failed - {_bridge_reason_codes(validation)}"


class LLMRouter:
    """Provider-agnostic LLM router with automatic fallback."""

    def __init__(
        self,
        *,
        providers: list[str] | None = None,
        models: dict[str, str] | None = None,
        max_retries: int = 2,
        request_timeout_sec: int = 120,
    ):
        self.provider_order = self._normalize_providers(providers or ["openai"])
        self.models = {**DEFAULT_MODELS, **(models or {})}
        self.max_retries = max_retries
        self.request_timeout_sec = request_timeout_sec

        # Load API keys from environment
        self.api_keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "google": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "xai": os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY"),
            "moonshot": os.getenv("MOONSHOT_API_KEY"),
            "zhipuai": os.getenv("ZHIPUAI_API_KEY"),
            "groq": os.getenv("GROQ_API_KEY"),
            "mimo": os.getenv("MIMO_API_KEY") or os.getenv("XIAOMI_API_KEY"),
        }

        self._clients: dict[str, Any] = {}
        self._client_lock = threading.Lock()

    @staticmethod
    def _normalize_providers(providers: list[str]) -> list[str]:
        seen: list[str] = []
        for p in providers:
            name = PROVIDER_ALIASES.get(str(p).strip().lower())
            if name and name not in seen:
                seen.append(name)
        return seen or ["openai"]

    def enabled_providers(self) -> list[str]:
        return [p for p in self.provider_order if self.api_keys.get(p)]

    def _enabled_from_order(self, providers: list[str] | None = None) -> list[str]:
        normalized = self._normalize_providers(providers or self.provider_order)
        return [p for p in normalized if self.api_keys.get(p)]

    def _get_client(self, provider: str) -> Any:
        if provider in self._clients:
            return self._clients[provider]

        with self._client_lock:
            # Double-check after acquiring lock
            if provider in self._clients:
                return self._clients[provider]

            api_key = self.api_keys.get(provider)
            if not api_key:
                raise ValueError(f"{provider} API key not found.")

            if provider == "google":
                from google import genai

                client = genai.Client(api_key=api_key)
            elif provider == "anthropic":
                from anthropic import Anthropic

                client = Anthropic(api_key=api_key)
            elif provider in OPENAI_COMPATIBLE_BASE_URLS:
                # xai, deepseek, moonshot, zhipuai → OpenAI-compatible
                from openai import OpenAI

                client = OpenAI(
                    api_key=api_key,
                    base_url=OPENAI_COMPATIBLE_BASE_URLS[provider],
                    timeout=self.request_timeout_sec,
                )
            elif provider == "openai":
                from openai import OpenAI

                client = OpenAI(api_key=api_key, timeout=self.request_timeout_sec)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            self._clients[provider] = client
            return client

    def _generate_once(
        self,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        json_mode: bool,
        thinking_level: str | None = None,
    ) -> str:
        client = self._get_client(provider)

        if provider in ("openai", "xai", "deepseek", "moonshot", "zhipuai", "groq", "mimo"):
            kwargs: dict[str, Any] = {
                "model": self.models[provider],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""

        elif provider == "google":
            from google.genai import types

            # Gemini 3.1: thinking_config 지원
            thinking_config = None
            if thinking_level and thinking_level in VALID_THINKING_LEVELS:
                thinking_config = types.ThinkingConfig(
                    thinking_level=thinking_level,
                )
                logger.info(
                    "[Gemini] Thinking level: %s (model: %s)",
                    thinking_level,
                    self.models[provider],
                )

            config_kwargs: dict[str, Any] = {
                "system_instruction": system_prompt,
                "temperature": temperature,
            }
            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"
            if thinking_config:
                config_kwargs["thinking_config"] = thinking_config

            config = types.GenerateContentConfig(**config_kwargs)
            resp = client.models.generate_content(
                model=self.models[provider],
                contents=user_prompt,
                config=config,
            )
            return resp.text

        elif provider == "anthropic":
            resp = client.messages.create(
                model=self.models[provider],
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=2000,
                temperature=temperature,
            )
            return resp.content[0].text

        raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def _is_non_retryable(error: Exception) -> bool:
        text = str(error).lower()
        return any(kw in text for kw in NON_RETRYABLE_KEYWORDS)

    @staticmethod
    def _clean_json(content: str) -> str:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        return json.loads(self._clean_json(content))

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        thinking_level: str | None = None,
    ) -> dict[str, Any]:
        """Generate JSON from LLM with automatic provider fallback.

        Args:
            thinking_level: Gemini 3.1 thinking depth (minimal/low/medium/high).
                           None = model default. Only affects Google provider.
        """
        providers = self.enabled_providers()
        if not providers:
            raise RuntimeError(
                "No LLM providers available. Check API keys: "
                "OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, "
                "DEEPSEEK_API_KEY, MOONSHOT_API_KEY, ZHIPUAI_API_KEY"
            )

        all_errors: list[str] = []

        for provider in providers:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "LLM request via %s (attempt %d/%d)",
                        provider,
                        attempt,
                        self.max_retries,
                    )
                    _safe_console_print(f"  🔄 [{provider}] LLM 요청 ({attempt}/{self.max_retries})...")

                    content = self._generate_once(
                        provider,
                        system_prompt,
                        user_prompt,
                        temperature,
                        json_mode=True,
                        thinking_level=thinking_level,
                    )
                    content = self._clean_json(content)
                    result = json.loads(content)

                    _safe_console_print(f"  ✅ [{provider}] 성공!")
                    return result

                except json.JSONDecodeError as e:
                    msg = f"{provider} attempt {attempt}: JSON parse error - {e}"
                    all_errors.append(msg)
                    logger.warning(msg)
                    _safe_console_print(f"  ⚠️ [{provider}] JSON 파싱 실패, 재시도...")

                except Exception as e:
                    msg = f"{provider} attempt {attempt}: {e}"
                    all_errors.append(msg)
                    logger.warning(msg)
                    _safe_console_print(f"  ⚠️ [{provider}] 실패: {e}")

                    if self._is_non_retryable(e):
                        _safe_console_print(f"  ❌ [{provider}] 복구 불가 에러 → 다음 provider")
                        break

                if attempt < self.max_retries:
                    wait = min(2**attempt, 10)
                    time.sleep(wait)

            logger.info("Provider %s exhausted. Moving to next.", provider)
            _safe_console_print(f"  ➡️ [{provider}] 실패, 다음 provider로 전환")

        raise RuntimeError(f"All LLM providers failed.\nErrors: {' | '.join(all_errors)}")

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        thinking_level: str | None = None,
    ) -> str:
        """Generate plain text (no JSON mode) with provider fallback."""
        providers = self.enabled_providers()
        if not providers:
            raise RuntimeError("No LLM providers available.")

        all_errors: list[str] = []
        for provider in providers:
            for attempt in range(1, self.max_retries + 1):
                try:
                    content = self._generate_once(
                        provider,
                        system_prompt,
                        user_prompt,
                        temperature,
                        json_mode=False,
                        thinking_level=thinking_level,
                    )
                    return content
                except Exception as e:
                    all_errors.append(f"{provider} #{attempt}: {e}")
                    if self._is_non_retryable(e):
                        break
                    if attempt < self.max_retries:
                        time.sleep(min(2**attempt, 10))

        raise RuntimeError(f"All providers failed: {' | '.join(all_errors)}")

    def _select_bridge_providers(self, preferred_provider_order: Any, policy: Any) -> list[str]:
        return (
            preferred_provider_order(
                self._enabled_from_order(list(policy.fallback_providers)),
                policy=policy,
            )
            or self.enabled_providers()
        )

    @staticmethod
    def _shadow_bridge_result(
        provider: str,
        validation: Any,
        content: Any,
        *,
        policy: Any,
        after_repair: bool = False,
    ) -> Any | None:
        if policy.mode != "shadow" or getattr(validation, "is_empty", False):
            return None
        suffix = " after repair" if after_repair else ""
        logger.warning(
            "LLMRouter bridge shadow warning%s [%s]: %s",
            suffix,
            provider,
            _bridge_reason_codes(validation),
        )
        return content

    def _repair_text_bridge_content(
        self,
        *,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        content: str,
        validation: Any,
        policy: Any,
        build_repair_messages: Any,
        validate_text_content: Any,
    ) -> tuple[str | None, Any]:
        for _repair_idx in range(policy.repair_attempts):
            repair_system, repair_user = build_repair_messages(
                original_system_prompt=system_prompt,
                original_user_prompt=user_prompt,
                raw_content=content,
                validation=validation,
                policy=policy,
                json_mode=False,
            )
            repaired = self._generate_once(
                provider,
                repair_system,
                repair_user,
                0.2,
                json_mode=False,
            )
            validation = validate_text_content(repaired, policy=policy, json_mode=False)
            if validation.passed:
                return repaired, validation
            shadow = self._shadow_bridge_result(
                provider,
                validation,
                repaired,
                policy=policy,
                after_repair=True,
            )
            if shadow is not None:
                return shadow, validation
        return None, validation

    def _try_text_bridge_provider(
        self,
        *,
        provider: str,
        bridge_system: str,
        bridge_user: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        policy: Any,
        build_repair_messages: Any,
        validate_text_content: Any,
        all_errors: list[str],
    ) -> str | None:
        for attempt in range(1, self.max_retries + 1):
            try:
                content = self._generate_once(
                    provider,
                    bridge_system,
                    bridge_user,
                    temperature,
                    json_mode=False,
                )
                validation = validate_text_content(content, policy=policy, json_mode=False)
                if validation.passed:
                    return content
                shadow = self._shadow_bridge_result(provider, validation, content, policy=policy)
                if shadow is not None:
                    return shadow

                repaired, validation = self._repair_text_bridge_content(
                    provider=provider,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    content=content,
                    validation=validation,
                    policy=policy,
                    build_repair_messages=build_repair_messages,
                    validate_text_content=validate_text_content,
                )
                if repaired is not None:
                    return repaired

                all_errors.append(_bridge_validation_error(provider, attempt, validation))
                break
            except Exception as e:
                all_errors.append(f"{provider} #{attempt}: {e}")
                if self._is_non_retryable(e):
                    break
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 10))
        return None

    def generate_text_bridged(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        policy: Any | None = None,
    ) -> str:
        bridge = _get_bridge()
        BridgePolicy = bridge["BridgePolicy"]  # noqa: N806
        preferred_provider_order = bridge["preferred_provider_order"]
        build_bridge_system_prompt = bridge["build_bridge_system_prompt"]
        normalize_prompt_text = bridge["normalize_prompt_text"]
        validate_text_content = bridge["validate_text_content"]
        build_repair_messages = bridge["build_repair_messages"]

        policy = policy or BridgePolicy.from_env()
        if policy.mode == "off":
            return self.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

        providers = self._select_bridge_providers(preferred_provider_order, policy)
        if not providers:
            raise RuntimeError("No LLM providers available.")

        bridge_system = build_bridge_system_prompt(system_prompt, policy=policy, json_mode=False)
        bridge_user = normalize_prompt_text(user_prompt, json_mode=False)
        all_errors: list[str] = []

        for provider in providers:
            result = self._try_text_bridge_provider(
                provider=provider,
                bridge_system=bridge_system,
                bridge_user=bridge_user,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                policy=policy,
                build_repair_messages=build_repair_messages,
                validate_text_content=validate_text_content,
                all_errors=all_errors,
            )
            if result is not None:
                return result

        raise RuntimeError(f"All bridge providers failed: {' | '.join(all_errors)}")

    def _validated_json_bridge_payload(
        self,
        *,
        provider: str,
        content: str,
        policy: Any,
        validate_text_content: Any,
        normalize_json_payload: Any,
        validate_json_payload: Any,
        after_repair: bool = False,
    ) -> tuple[dict[str, Any] | None, Any]:
        validation = validate_text_content(content, policy=policy, json_mode=True)
        if not validation.json_valid:
            return None, validation

        payload = normalize_json_payload(self._parse_json_response(content))
        payload_validation = validate_json_payload(payload, policy=policy)
        if payload_validation.passed:
            return payload, payload_validation

        shadow = self._shadow_bridge_result(
            provider,
            payload_validation,
            payload,
            policy=policy,
            after_repair=after_repair,
        )
        if shadow is not None:
            return shadow, payload_validation
        return None, payload_validation

    def _repair_json_bridge_payload(
        self,
        *,
        provider: str,
        system_prompt: str,
        user_prompt: str,
        content: str,
        validation: Any,
        policy: Any,
        build_repair_messages: Any,
        validate_text_content: Any,
        normalize_json_payload: Any,
        validate_json_payload: Any,
    ) -> tuple[dict[str, Any] | None, Any]:
        for _repair_idx in range(policy.repair_attempts):
            repair_system, repair_user = build_repair_messages(
                original_system_prompt=system_prompt,
                original_user_prompt=user_prompt,
                raw_content=content,
                validation=validation,
                policy=policy,
                json_mode=True,
            )
            repaired = self._generate_once(
                provider,
                repair_system,
                repair_user,
                0.2,
                json_mode=True,
            )
            payload, validation = self._validated_json_bridge_payload(
                provider=provider,
                content=repaired,
                policy=policy,
                validate_text_content=validate_text_content,
                normalize_json_payload=normalize_json_payload,
                validate_json_payload=validate_json_payload,
                after_repair=True,
            )
            if payload is not None:
                return payload, validation
        return None, validation

    def _try_json_bridge_provider(
        self,
        *,
        provider: str,
        bridge_system: str,
        bridge_user: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        policy: Any,
        build_repair_messages: Any,
        validate_text_content: Any,
        normalize_json_payload: Any,
        validate_json_payload: Any,
        all_errors: list[str],
    ) -> dict[str, Any] | None:
        for attempt in range(1, self.max_retries + 1):
            try:
                content = self._generate_once(
                    provider,
                    bridge_system,
                    bridge_user,
                    temperature,
                    json_mode=True,
                )
                payload, validation = self._validated_json_bridge_payload(
                    provider=provider,
                    content=content,
                    policy=policy,
                    validate_text_content=validate_text_content,
                    normalize_json_payload=normalize_json_payload,
                    validate_json_payload=validate_json_payload,
                )
                if payload is not None:
                    return payload

                payload, validation = self._repair_json_bridge_payload(
                    provider=provider,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    content=content,
                    validation=validation,
                    policy=policy,
                    build_repair_messages=build_repair_messages,
                    validate_text_content=validate_text_content,
                    normalize_json_payload=normalize_json_payload,
                    validate_json_payload=validate_json_payload,
                )
                if payload is not None:
                    return payload

                all_errors.append(_bridge_validation_error(provider, attempt, validation))
                break
            except Exception as e:
                all_errors.append(f"{provider} attempt {attempt}: {e}")
                if self._is_non_retryable(e):
                    break
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 10))
        return None

    def generate_json_bridged(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        policy: Any | None = None,
    ) -> dict[str, Any]:
        bridge = _get_bridge()
        BridgePolicy = bridge["BridgePolicy"]  # noqa: N806
        preferred_provider_order = bridge["preferred_provider_order"]
        build_bridge_system_prompt = bridge["build_bridge_system_prompt"]
        normalize_prompt_text = bridge["normalize_prompt_text"]
        validate_text_content = bridge["validate_text_content"]
        build_repair_messages = bridge["build_repair_messages"]
        normalize_json_payload = bridge["normalize_json_payload"]
        validate_json_payload = bridge["validate_json_payload"]

        policy = policy or BridgePolicy.from_env()
        if policy.mode == "off":
            return self.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

        providers = self._select_bridge_providers(preferred_provider_order, policy)
        if not providers:
            raise RuntimeError(
                "No LLM providers available. Check API keys: "
                "OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, "
                "DEEPSEEK_API_KEY, MOONSHOT_API_KEY, ZHIPUAI_API_KEY"
            )

        bridge_system = build_bridge_system_prompt(system_prompt, policy=policy, json_mode=True)
        bridge_user = normalize_prompt_text(user_prompt, json_mode=True)
        all_errors: list[str] = []

        for provider in providers:
            result = self._try_json_bridge_provider(
                provider=provider,
                bridge_system=bridge_system,
                bridge_user=bridge_user,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                policy=policy,
                build_repair_messages=build_repair_messages,
                validate_text_content=validate_text_content,
                normalize_json_payload=normalize_json_payload,
                validate_json_payload=validate_json_payload,
                all_errors=all_errors,
            )
            if result is not None:
                return result

        raise RuntimeError(f"All bridge providers failed: {' | '.join(all_errors)}")
