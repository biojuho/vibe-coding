"""
통합 LLM 클라이언트 - 7개 프로바이더 자동 fallback.

모든 프로젝트에서 공통으로 사용할 수 있는 LLM 호출 인터페이스.
프로바이더 우선순위에 따라 자동 fallback하며, API 사용량을 추적합니다.

지원 프로바이더:
  - openai   : OpenAI GPT (gpt-4o-mini 등)
  - google   : Google Gemini (gemini-2.5-flash 등)
  - anthropic: Anthropic Claude (claude-sonnet-4 등)
  - xai      : xAI Grok (grok-3-mini-fast 등)
  - deepseek : DeepSeek (deepseek-chat 등)
  - moonshot : Moonshot Kimi (moonshot-v1-8k 등)
  - zhipuai  : ZhipuAI GLM (glm-4-flash 등)

Usage (library):
    from execution.llm_client import LLMClient
    client = LLMClient()                          # 기본 설정
    client = LLMClient(providers=["google", "deepseek", "openai"])  # 우선순위 지정
    result = client.generate_json(system_prompt="...", user_prompt="...")
    text   = client.generate_text(system_prompt="...", user_prompt="...")

Usage (CLI - 연결 테스트):
    python workspace/execution/llm_client.py test            # 전체 프로바이더 연결 테스트
    python workspace/execution/llm_client.py test --provider google  # 특정 프로바이더만
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import REPO_ROOT, resolve_project_dir
from execution.language_bridge import (
    BridgePolicy,
    BridgeValidationResult,
    build_bridge_system_prompt,
    build_execution_metadata,
    build_repair_messages,
    normalize_json_payload,
    normalize_prompt_text,
    preferred_provider_order,
    validate_json_payload,
    validate_text_content,
)

load_dotenv(REPO_ROOT / ".env")
load_dotenv(resolve_project_dir("shorts-maker-v2", required_paths=("config.yaml",)) / ".env", override=False)

from execution._logging import logger  # noqa: E402

# ── 프로바이더 설정 ──────────────────────────────────────────

PROVIDER_ALIASES: dict[str, str] = {
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
    "ollama": "ollama",
    "local": "ollama",
    "qwen": "ollama",
}

# 비용 효율 순 기본 우선순위 (무료/저가 → 고가)
DEFAULT_PROVIDER_ORDER = [
    "ollama",  # Ollama - 로컬, 비용 제로, 프라이버시 최고
    "google",  # Gemini - 무료 tier 넉넉
    "groq",  # Groq - 무료 tier, 세계 최고속 추론
    "deepseek",  # DeepSeek - 매우 저렴
    "moonshot",  # Moonshot Kimi - 저렴
    "zhipuai",  # ZhipuAI GLM - glm-4-flash 무료
    "openai",  # OpenAI - 중간 비용
    "xai",  # xAI Grok - 중간 비용
    "anthropic",  # Anthropic - 상대적 고비용
]

DEFAULT_MODELS: dict[str, str] = {
    "ollama": "qwen3-coder:30b-a3b-q4_K_M",
    "openai": "gpt-4o-mini",
    "google": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-4-20250514",
    "xai": "grok-3-mini-fast",
    "deepseek": "deepseek-chat",
    "moonshot": "moonshot-v1-8k",
    "zhipuai": "glm-4-flash",
    "groq": "llama-3.3-70b-versatile",
}

# OpenAI-compatible 프로바이더의 base_url
OPENAI_COMPATIBLE_BASE_URLS: dict[str, str] = {
    "xai": "https://api.x.ai/v1",
    "deepseek": "https://api.deepseek.com",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipuai": "https://open.bigmodel.cn/api/paas/v4",
    "groq": "https://api.groq.com/openai/v1",
}

# API 키 환경 변수 매핑
# Ollama는 API 키 불필요 — OLLAMA_BASE_URL 존재 여부로 활성화 판단
API_KEY_ENV_VARS: dict[str, list[str]] = {
    "ollama": ["OLLAMA_BASE_URL"],
    "openai": ["OPENAI_API_KEY"],
    "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "moonshot": ["MOONSHOT_API_KEY"],
    "zhipuai": ["ZHIPUAI_API_KEY"],
    "groq": ["GROQ_API_KEY"],
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

# 토큰당 비용 (USD per 1K tokens) - 비용 추적용
PRICING: dict[str, dict[str, float]] = {
    "qwen3-coder:30b-a3b-q4_K_M": {"input": 0.0, "output": 0.0},  # Ollama 로컬 무료
    "qwen3-coder:8b": {"input": 0.0, "output": 0.0},  # Ollama 로컬 무료
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},  # 무료 tier
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "grok-3-mini-fast": {"input": 0.0003, "output": 0.0005},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "moonshot-v1-8k": {"input": 0.00085, "output": 0.00085},
    "glm-4-flash": {"input": 0.0, "output": 0.0},  # 무료
    "llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},  # Groq 무료 tier
}


_CACHE_DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "llm_cache.db"


def _emit_langfuse_trace(
    *,
    provider: str,
    model: str,
    endpoint: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    cost_usd: float = 0.0,
    caller_script: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Send one trace+observation to a self-hosted Langfuse if opt-in.

    Activated only when `LANGFUSE_ENABLED=1` and both `LANGFUSE_PUBLIC_KEY` /
    `LANGFUSE_SECRET_KEY` are set. Any failure (SDK missing, network, etc.)
    is silently dropped — LLM calls must never be blocked by observability.
    See `directives/llm_observability_langfuse.md` for the operational SOP.
    """
    if os.getenv("LANGFUSE_ENABLED", "0").strip() != "1":
        return
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return
    try:
        from langfuse import get_client  # type: ignore[import-not-found]

        os.environ.setdefault("LANGFUSE_HOST", "http://127.0.0.1:3030")
        client = get_client()
        observation = client.start_observation(
            name=endpoint,
            as_type="generation",
            model=model,
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
                "input_cache_creation": cache_creation_tokens,
                "input_cache_read": cache_read_tokens,
            },
            metadata={
                "provider": provider,
                "cost_usd": cost_usd,
                "caller_script": caller_script,
                **(metadata or {}),
            },
        )
        observation.end()
    except Exception:
        # Any failure (SDK not installed, network, wrong keys) — silent.
        return


def _cache_key(providers: list[str], system_prompt: str, user_prompt: str, temperature: float) -> str:
    raw = json.dumps([providers, system_prompt, user_prompt, round(temperature, 4)], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str, ttl_sec: int) -> str | None:
    """캐시에서 응답 조회. 없거나 만료면 None."""
    try:
        with sqlite3.connect(str(_CACHE_DB_PATH)) as conn:
            row = conn.execute("SELECT content, created_at FROM llm_cache WHERE key=?", (key,)).fetchone()
        if row and (time.time() - row[1]) < ttl_sec:
            return row[0]
    except Exception:
        pass
    return None


def _cache_set(key: str, content: str) -> None:
    """캐시에 응답 저장."""
    try:
        _CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(_CACHE_DB_PATH)) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS llm_cache (key TEXT PRIMARY KEY, content TEXT, created_at REAL)")
            conn.execute(
                "INSERT OR REPLACE INTO llm_cache VALUES (?,?,?)",
                (key, content, time.time()),
            )
    except Exception:
        pass


def cache_cleanup(ttl_sec: int = 259200) -> int:
    """만료된 캐시 항목 삭제. 삭제 건수 반환."""
    try:
        with sqlite3.connect(str(_CACHE_DB_PATH)) as conn:
            cutoff = time.time() - ttl_sec
            cursor = conn.execute("DELETE FROM llm_cache WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
            if deleted > 0:
                conn.execute("PRAGMA optimize")
            return deleted
    except Exception:
        return 0


class LLMClient:
    """7개 프로바이더 자동 fallback LLM 클라이언트.

    사용 가능한 API 키가 있는 프로바이더만 활성화되며,
    호출 실패 시 다음 프로바이더로 자동 전환됩니다.

    cache_ttl_sec > 0 이면 동일 프롬프트 재호출 시 캐시 반환 (기본값: 259200 = 72시간).
    """

    def __init__(
        self,
        *,
        providers: list[str] | None = None,
        models: dict[str, str] | None = None,
        max_retries: int = 2,
        request_timeout_sec: int = 120,
        track_usage: bool = True,
        caller_script: str = "",
        cache_ttl_sec: int = 259200,
    ):
        self.provider_order = self._normalize_providers(providers or DEFAULT_PROVIDER_ORDER)
        self.models = {**DEFAULT_MODELS, **(models or {})}
        self.cache_ttl_sec = cache_ttl_sec
        self.max_retries = max_retries
        self.request_timeout_sec = request_timeout_sec
        self.track_usage = track_usage
        self.caller_script = caller_script

        # API 키 로드
        self.api_keys: dict[str, str | None] = {}
        for provider, env_vars in API_KEY_ENV_VARS.items():
            key = None
            for env_var in env_vars:
                key = os.getenv(env_var, "").strip() or None
                if key:
                    break
            self.api_keys[provider] = key

        self._clients: dict[str, Any] = {}

    @staticmethod
    def _normalize_providers(providers: list[str]) -> list[str]:
        """프로바이더 이름을 정규화하고 중복 제거."""
        seen: list[str] = []
        for p in providers:
            name = PROVIDER_ALIASES.get(str(p).strip().lower())
            if name and name not in seen:
                seen.append(name)
        return seen or list(DEFAULT_PROVIDER_ORDER)

    def enabled_providers(self) -> list[str]:
        """API 키가 설정된 활성 프로바이더 목록."""
        return [p for p in self.provider_order if self.api_keys.get(p)]

    def _enabled_from_order(self, providers: list[str] | None = None) -> list[str]:
        normalized = self._normalize_providers(providers or self.provider_order)
        return [p for p in normalized if self.api_keys.get(p)]

    def all_provider_status(self) -> dict[str, bool]:
        """모든 프로바이더의 활성화 상태."""
        return {p: bool(self.api_keys.get(p)) for p in DEFAULT_PROVIDER_ORDER}

    def _get_client(self, provider: str) -> Any:
        """프로바이더별 클라이언트 lazy 초기화."""
        if provider in self._clients:
            return self._clients[provider]

        if provider == "ollama":
            from execution.local_inference import OllamaClient

            client = OllamaClient()
            if not client.is_available():
                raise ConnectionError("Ollama 서버 연결 불가")
            self._clients[provider] = client
            return client

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
        cache_strategy: str = "off",
    ) -> tuple[str, int, int, int, int]:
        """단일 프로바이더로 1회 생성.

        Returns:
            content, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        """
        client = self._get_client(provider)
        model = self.models.get(provider, DEFAULT_MODELS.get(provider, ""))

        if provider == "ollama":
            # Ollama 로컬 추론
            content, input_tokens, output_tokens = client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                json_mode=json_mode,
            )
            return content, input_tokens, output_tokens, 0, 0

        elif provider in ("openai", "xai", "deepseek", "moonshot", "zhipuai", "groq"):
            # OpenAI-compatible API
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            return content, input_tokens, output_tokens, 0, 0

        elif provider == "google":
            from google.genai import types

            config_kwargs: dict[str, Any] = {
                "system_instruction": system_prompt,
                "temperature": temperature,
            }
            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"
            config = types.GenerateContentConfig(**config_kwargs)
            resp = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=config,
            )
            content = resp.text
            # Gemini usage metadata
            usage_meta = getattr(resp, "usage_metadata", None)
            input_tokens = getattr(usage_meta, "prompt_token_count", 0) if usage_meta else 0
            output_tokens = getattr(usage_meta, "candidates_token_count", 0) if usage_meta else 0
            return content, input_tokens, output_tokens, 0, 0

        elif provider == "anthropic":
            create_kwargs: dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": 2000,
                "temperature": temperature,
            }
            if cache_strategy in ("5m", "1h"):
                cache_control: dict[str, Any] = {"type": "ephemeral"}
                if cache_strategy == "1h":
                    cache_control["ttl"] = "1h"
                create_kwargs["system"] = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": cache_control,
                    }
                ]
            else:
                create_kwargs["system"] = system_prompt

            resp = client.messages.create(**create_kwargs)
            content = resp.content[0].text
            input_tokens = getattr(resp.usage, "input_tokens", 0)
            output_tokens = getattr(resp.usage, "output_tokens", 0)
            cache_creation_tokens = getattr(resp.usage, "cache_creation_input_tokens", 0) or 0
            cache_read_tokens = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
            return content, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens

        raise ValueError(f"Unsupported provider: {provider}")  # pragma: no cover — _get_client raises first

    def _log_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        *,
        endpoint: str = "chat.completions",
        metadata: dict[str, Any] | None = None,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_creation_multiplier: float = 1.25,
    ) -> None:
        """API 사용량 추적 (api_usage_tracker 연동)."""
        if not self.track_usage:
            return
        cost = 0.0
        try:
            from execution.api_usage_tracker import log_api_call

            pricing = PRICING.get(model, {})
            input_price = pricing.get("input", 0)
            cost = (
                (input_tokens / 1000 * input_price)
                + (output_tokens / 1000 * pricing.get("output", 0))
                + (cache_creation_tokens / 1000 * input_price * cache_creation_multiplier)
                + (cache_read_tokens / 1000 * input_price * 0.10)
            )
            log_api_call(
                provider=provider,
                model=model,
                endpoint=endpoint,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                cost_usd=cost,
                caller_script=self.caller_script,
                bridge_mode=str((metadata or {}).get("bridge_mode", "")),
                reason_codes=list((metadata or {}).get("reason_codes", [])),
                repair_count=int((metadata or {}).get("repair_count", 0)),
                fallback_used=bool((metadata or {}).get("fallback_used", False)),
                language_score=(metadata or {}).get("language_score"),
                provider_used=str((metadata or {}).get("provider_used", provider)),
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_creation_multiplier=cache_creation_multiplier,
            )
        except Exception:
            pass  # 추적 실패는 무시

        # JSONL 메트릭 수집 (llm_metrics 레이어)
        try:
            from execution.llm_metrics import record_llm_call

            record_llm_call(
                step=endpoint,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                metadata=metadata,
            )
        except Exception:
            pass  # 메트릭 기록 실패는 무시

        # Langfuse 셀프호스트 trace 송신 (T-253, opt-in via LANGFUSE_ENABLED=1).
        # 비활성/SDK 미설치/네트워크 실패 시 silent drop, LLM 호출 자체는 영향 없음.
        _emit_langfuse_trace(
            provider=provider,
            model=model,
            endpoint=endpoint,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens,
            cost_usd=cost,
            caller_script=self.caller_script,
            metadata=metadata,
        )

    @staticmethod
    def _is_non_retryable(error: Exception) -> bool:
        text = str(error).lower()
        return any(kw in text for kw in NON_RETRYABLE_KEYWORDS)

    @staticmethod
    def _clean_json(content: str) -> str:
        """LLM 응답에서 markdown 코드블록 제거."""
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

    def _validate_json_candidate(
        self,
        content: str,
        *,
        policy: BridgePolicy,
    ) -> tuple[BridgeValidationResult, dict[str, Any] | None]:
        raw_validation = validate_text_content(content, policy=policy, json_mode=True)
        if not raw_validation.json_valid:
            return raw_validation, None

        payload = normalize_json_payload(self._parse_json_response(content))
        payload_validation = validate_json_payload(payload, policy=policy)
        return payload_validation, payload

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        cache_strategy: str = "off",
    ) -> dict[str, Any]:
        """JSON 응답 생성 (자동 fallback + 재시도).

        모든 프로바이더 실패 시 RuntimeError 발생.
        """
        providers = self.enabled_providers()
        if not providers:
            raise RuntimeError(
                "사용 가능한 LLM 프로바이더가 없습니다. API 키를 확인하세요: "
                + ", ".join(f"{v[0]}" for v in API_KEY_ENV_VARS.values())
            )

        # 캐시 조회
        if self.cache_ttl_sec > 0:
            key = _cache_key(providers, system_prompt, user_prompt, temperature)
            cached = _cache_get(key, self.cache_ttl_sec)
            if cached is not None:
                logger.info("LLM 캐시 히트 (JSON)")
                return json.loads(cached)

        all_errors: list[str] = []

        for provider in providers:
            model = self.models.get(provider, DEFAULT_MODELS.get(provider, ""))
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "LLM JSON 요청: %s/%s (attempt %d/%d)",
                        provider,
                        model,
                        attempt,
                        self.max_retries,
                    )
                    content, in_tok, out_tok, cache_w, cache_r = self._generate_once(
                        provider,
                        system_prompt,
                        user_prompt,
                        temperature,
                        json_mode=True,
                        cache_strategy=cache_strategy,
                    )
                    content = self._clean_json(content)
                    result = json.loads(content)

                    self._log_usage(
                        provider,
                        model,
                        in_tok,
                        out_tok,
                        cache_creation_tokens=cache_w,
                        cache_read_tokens=cache_r,
                        cache_creation_multiplier=2.0 if cache_strategy == "1h" else 1.25,
                    )
                    logger.info("LLM 성공: %s (in=%d, out=%d)", provider, in_tok, out_tok)
                    if self.cache_ttl_sec > 0:
                        _cache_set(key, json.dumps(result, ensure_ascii=False))
                    return result

                except json.JSONDecodeError as e:
                    msg = f"{provider} attempt {attempt}: JSON parse error - {e}"
                    all_errors.append(msg)
                    logger.warning(msg)

                except Exception as e:
                    msg = f"{provider} attempt {attempt}: {e}"
                    all_errors.append(msg)
                    logger.warning(msg)

                    if self._is_non_retryable(e):
                        logger.info("%s: 복구 불가 에러 → 다음 provider", provider)
                        break

                if attempt < self.max_retries:
                    wait = min(2**attempt, 10)
                    time.sleep(wait)

            logger.info("Provider %s 소진 → 다음 provider", provider)

        raise RuntimeError(f"모든 LLM 프로바이더 실패.\nErrors: {' | '.join(all_errors)}")

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        cache_strategy: str = "off",
    ) -> str:
        """텍스트 응답 생성 (자동 fallback + 재시도)."""
        providers = self.enabled_providers()
        if not providers:
            raise RuntimeError("사용 가능한 LLM 프로바이더가 없습니다.")

        # 캐시 조회
        if self.cache_ttl_sec > 0:
            key = _cache_key(providers, system_prompt, user_prompt, temperature)
            cached = _cache_get(key, self.cache_ttl_sec)
            if cached is not None:
                logger.info("LLM 캐시 히트 (텍스트)")
                return cached

        all_errors: list[str] = []
        for provider in providers:
            model = self.models.get(provider, DEFAULT_MODELS.get(provider, ""))
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "LLM 텍스트 요청: %s/%s (attempt %d/%d)",
                        provider,
                        model,
                        attempt,
                        self.max_retries,
                    )
                    content, in_tok, out_tok, cache_w, cache_r = self._generate_once(
                        provider,
                        system_prompt,
                        user_prompt,
                        temperature,
                        json_mode=False,
                        cache_strategy=cache_strategy,
                    )
                    self._log_usage(
                        provider,
                        model,
                        in_tok,
                        out_tok,
                        cache_creation_tokens=cache_w,
                        cache_read_tokens=cache_r,
                        cache_creation_multiplier=2.0 if cache_strategy == "1h" else 1.25,
                    )
                    if self.cache_ttl_sec > 0:
                        _cache_set(key, content)
                    return content

                except Exception as e:
                    all_errors.append(f"{provider} #{attempt}: {e}")
                    if self._is_non_retryable(e):
                        break
                    if attempt < self.max_retries:
                        time.sleep(min(2**attempt, 10))

        raise RuntimeError(f"모든 프로바이더 실패: {' | '.join(all_errors)}")

    def _bridged_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        json_mode: bool,
        policy: BridgePolicy,
    ) -> str | dict[str, Any]:
        """Shared bridged generation loop for both text and JSON modes."""
        providers = (
            preferred_provider_order(
                self._enabled_from_order(list(policy.fallback_providers)),
                policy=policy,
            )
            or self.enabled_providers()
        )
        if not providers:
            raise RuntimeError(
                "사용 가능한 LLM 프로바이더가 없습니다. API 키를 확인하세요: "
                + ", ".join(f"{v[0]}" for v in API_KEY_ENV_VARS.values())
            )

        bridge_system = build_bridge_system_prompt(system_prompt, policy=policy, json_mode=json_mode)
        bridge_user = normalize_prompt_text(user_prompt, json_mode=json_mode)
        all_errors: list[str] = []
        first_provider = providers[0]

        for provider_index, provider in enumerate(providers):
            model = self.models.get(provider, DEFAULT_MODELS.get(provider, ""))
            fallback_used = provider != first_provider or provider_index > 0

            result = self._bridged_attempt_provider(
                provider=provider,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                bridge_system=bridge_system,
                bridge_user=bridge_user,
                temperature=temperature,
                json_mode=json_mode,
                policy=policy,
                fallback_used=fallback_used,
                all_errors=all_errors,
            )
            if result is not None:
                return result

        raise RuntimeError(f"모든 브릿지 프로바이더 실패: {' | '.join(all_errors)}")

    def _bridged_attempt_provider(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        bridge_system: str,
        bridge_user: str,
        temperature: float,
        json_mode: bool,
        policy: BridgePolicy,
        fallback_used: bool,
        all_errors: list[str],
    ) -> str | dict[str, Any] | None:
        """Try one provider with retries and repair loop. Returns result or None."""
        for attempt in range(1, self.max_retries + 1):
            try:
                content, in_tok, out_tok, _cache_w, _cache_r = self._generate_once(
                    provider,
                    bridge_system,
                    bridge_user,
                    temperature,
                    json_mode=json_mode,
                )
                validation, payload = self._validate_bridged_content(content, json_mode, policy)
                self._log_bridged_usage(provider, model, in_tok, out_tok, 0, fallback_used, policy, validation)

                if self._is_bridged_accepted(validation, payload, json_mode, policy, provider, ""):
                    return payload if json_mode else content

                # Repair loop
                repaired_result = self._bridged_repair_loop(
                    provider=provider,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    content=content,
                    validation=validation,
                    json_mode=json_mode,
                    policy=policy,
                    fallback_used=fallback_used,
                )
                if repaired_result is not None:
                    return repaired_result

                all_errors.append(
                    f"{provider} attempt {attempt}: bridge validation failed - {','.join(validation.reason_codes)}"
                )
                break
            except Exception as e:
                all_errors.append(f"{provider} #{attempt}: {e}")
                if self._is_non_retryable(e):
                    break
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 10))
        return None

    def _validate_bridged_content(
        self,
        content: str,
        json_mode: bool,
        policy: BridgePolicy,
    ) -> tuple[BridgeValidationResult, dict | None]:
        """Validate bridged content based on mode."""
        if json_mode:
            return self._validate_json_candidate(content, policy=policy)
        return validate_text_content(content, policy=policy, json_mode=False), None

    def _log_bridged_usage(
        self,
        provider: str,
        model: str,
        in_tok: int,
        out_tok: int,
        repair_count: int,
        fallback_used: bool,
        policy: BridgePolicy,
        validation: BridgeValidationResult,
    ) -> None:
        metadata = build_execution_metadata(
            provider_used=provider,
            repair_count=repair_count,
            fallback_used=fallback_used,
            policy=policy,
            validation=validation,
        )
        self._log_usage(provider, model, in_tok, out_tok, metadata=metadata.as_usage_metadata())

    def _is_bridged_accepted(
        self,
        validation: BridgeValidationResult,
        payload: dict | None,
        json_mode: bool,
        policy: BridgePolicy,
        provider: str,
        phase: str,
    ) -> bool:
        """Check if bridged result should be accepted."""
        if json_mode:
            if validation.passed and payload is not None:
                return True
            if policy.mode == "shadow" and validation.json_valid and payload is not None:
                logger.warning(
                    "LLM bridge shadow warning%s [%s]: %s", phase, provider, ",".join(validation.reason_codes)
                )
                return True
        else:
            if validation.passed:
                return True
            if policy.mode == "shadow" and not validation.is_empty:
                logger.warning(
                    "LLM bridge shadow warning%s [%s]: %s", phase, provider, ",".join(validation.reason_codes)
                )
                return True
        return False

    def _bridged_repair_loop(
        self,
        *,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        content: str,
        validation: BridgeValidationResult,
        json_mode: bool,
        policy: BridgePolicy,
        fallback_used: bool,
    ) -> str | dict[str, Any] | None:
        """Run repair attempts for a bridged generation."""
        for repair_idx in range(policy.repair_attempts):
            repair_system, repair_user = build_repair_messages(
                original_system_prompt=system_prompt,
                original_user_prompt=user_prompt,
                raw_content=content,
                validation=validation,
                policy=policy,
                json_mode=json_mode,
            )
            repaired, repair_in, repair_out, _cache_w, _cache_r = self._generate_once(
                provider,
                repair_system,
                repair_user,
                0.2,
                json_mode=json_mode,
            )
            repair_validation, repaired_payload = self._validate_bridged_content(repaired, json_mode, policy)
            self._log_bridged_usage(
                provider,
                model,
                repair_in,
                repair_out,
                repair_idx + 1,
                fallback_used,
                policy,
                repair_validation,
            )
            if self._is_bridged_accepted(
                repair_validation,
                repaired_payload,
                json_mode,
                policy,
                provider,
                " after repair",
            ):
                return repaired_payload if json_mode else repaired
            validation = repair_validation
        return None

    def generate_text_bridged(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        policy: BridgePolicy | None = None,
    ) -> str:
        policy = policy or BridgePolicy.from_env()
        if policy.mode == "off":
            return self.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
        result = self._bridged_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            json_mode=False,
            policy=policy,
        )
        return result

    def generate_json_bridged(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        policy: BridgePolicy | None = None,
    ) -> dict[str, Any]:
        policy = policy or BridgePolicy.from_env()
        if policy.mode == "off":
            return self.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
        result = self._bridged_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            json_mode=True,
            policy=policy,
        )
        return result

    def test_provider(self, provider: str) -> dict[str, Any]:
        """특정 프로바이더 연결 테스트. 간단한 프롬프트로 실제 API 호출."""
        result: dict[str, Any] = {
            "provider": provider,
            "model": self.models.get(provider, "unknown"),
            "api_key_set": bool(self.api_keys.get(provider)),
        }
        if not result["api_key_set"]:
            result["status"] = "skip"
            result["detail"] = "API key not set"
            return result

        try:
            content, in_tok, out_tok, _cache_w, _cache_r = self._generate_once(
                provider,
                system_prompt="You are a test bot.",
                user_prompt='Respond with exactly: {"status":"ok"}',
                temperature=0.0,
                json_mode=True,
            )
            result["status"] = "ok"
            result["detail"] = f"응답 수신 (in={in_tok}, out={out_tok})"
            result["response_preview"] = content[:100]
        except Exception as e:
            result["status"] = "fail"
            result["detail"] = str(e)[:200]

        return result

    def test_all_providers(self) -> list[dict[str, Any]]:
        """모든 프로바이더 연결 테스트."""
        results = []
        for provider in DEFAULT_PROVIDER_ORDER:
            results.append(self.test_provider(provider))
        return results


# ── 편의 함수 (모듈 레벨) ─────────────────────────────────────

_default_client: LLMClient | None = None


def get_default_client(**kwargs: Any) -> LLMClient:
    """기본 LLMClient 싱글톤. 여러 모듈에서 공유 사용."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient(**kwargs)
    return _default_client


def generate_json(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    providers: list[str] | None = None,
    caller_script: str = "",
    cache_strategy: str = "off",
) -> dict[str, Any]:
    """간편 JSON 생성 함수. 매번 새 클라이언트 생성 없이 사용."""
    client = (
        LLMClient(providers=providers, caller_script=caller_script)
        if providers
        else get_default_client(caller_script=caller_script)
    )
    return client.generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        cache_strategy=cache_strategy,
    )


def generate_text(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    providers: list[str] | None = None,
    caller_script: str = "",
    cache_strategy: str = "off",
) -> str:
    """간편 텍스트 생성 함수."""
    client = (
        LLMClient(providers=providers, caller_script=caller_script)
        if providers
        else get_default_client(caller_script=caller_script)
    )
    return client.generate_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        cache_strategy=cache_strategy,
    )


def generate_json_bridged(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    providers: list[str] | None = None,
    caller_script: str = "",
    policy: BridgePolicy | None = None,
) -> dict[str, Any]:
    client = (
        LLMClient(providers=providers, caller_script=caller_script)
        if providers
        else get_default_client(caller_script=caller_script)
    )
    return client.generate_json_bridged(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        policy=policy,
    )


def generate_text_bridged(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    providers: list[str] | None = None,
    caller_script: str = "",
    policy: BridgePolicy | None = None,
) -> str:
    client = (
        LLMClient(providers=providers, caller_script=caller_script)
        if providers
        else get_default_client(caller_script=caller_script)
    )
    return client.generate_text_bridged(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        policy=policy,
    )


# ── CLI ───────────────────────────────────────────────────────


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="통합 LLM 클라이언트 - 연결 테스트")
    sub = parser.add_subparsers(dest="cmd")

    p_test = sub.add_parser("test", help="프로바이더 연결 테스트")
    p_test.add_argument("--provider", type=str, help="특정 프로바이더만 테스트")

    sub.add_parser("status", help="프로바이더 활성화 상태 확인")

    args = parser.parse_args()

    # loguru setup already applied via execution._logging import
    client = LLMClient()

    ICONS = {"ok": "✅", "fail": "❌", "skip": "⏭️"}

    if args.cmd == "test":
        if args.provider:
            name = PROVIDER_ALIASES.get(args.provider.lower(), args.provider.lower())
            result = client.test_provider(name)
            icon = ICONS.get(result["status"], "?")
            print(f"{icon} {result['provider']} ({result['model']}): {result['detail']}")
        else:
            print("🔍 전체 프로바이더 연결 테스트...\n")
            results = client.test_all_providers()
            for r in results:
                icon = ICONS.get(r["status"], "?")
                print(f"  {icon} {r['provider']:10s} ({r['model']:25s}): {r['detail']}")
            ok_count = sum(1 for r in results if r["status"] == "ok")
            total = len(results)
            print(f"\n  결과: {ok_count}/{total} 프로바이더 정상")

    elif args.cmd == "status":
        status = client.all_provider_status()
        enabled = client.enabled_providers()
        print("📊 프로바이더 상태:\n")
        for provider, has_key in status.items():
            icon = "✅" if has_key else "❌"
            model = DEFAULT_MODELS.get(provider, "?")
            order_str = f" (#{enabled.index(provider) + 1})" if provider in enabled else ""
            print(f"  {icon} {provider:10s} | {model:25s}{order_str}")
        print(f"\n  활성 프로바이더 순서: {' → '.join(enabled)}")

    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
