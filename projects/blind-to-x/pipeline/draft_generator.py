"""Draft generation with multi-provider fallback support."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

import pipeline.draft_prompts as _draft_prompts_mod
from pipeline.draft_cache import DraftCache
from pipeline.draft_prompts import DraftPromptsMixin
from pipeline.draft_prompts import _load_draft_rules as _load_draft_rules  # noqa: F401 — re-export for tests
from pipeline.draft_providers import DEFAULT_PROVIDER_ORDER as DEFAULT_PROVIDER_ORDER  # noqa: F401 — re-export
from pipeline.draft_providers import PROVIDER_ALIASES as PROVIDER_ALIASES  # noqa: F401 — re-export
from pipeline.draft_providers import (
    DraftProvidersMixin,
    init_provider_clients,
)
from pipeline.draft_validation import DraftValidationMixin
from pipeline.regulation_checker import RegulationChecker

logger = logging.getLogger(__name__)


class TweetDraftGenerator(DraftPromptsMixin, DraftProvidersMixin, DraftValidationMixin):
    def __init__(self, config, cost_tracker=None):
        self.config = config
        self.cost_tracker = cost_tracker

        style = config.get("tweet_style", {})
        self.tone = style.get("tone", "위트 있고 공감 가는")
        self.max_length = style.get("max_length", 280)

        # Threads 스타일 설정
        threads_style = config.get("threads_style", {})
        self.threads_tone = threads_style.get("tone", "캐주얼하고 공감 가능한")
        self.threads_max_length = threads_style.get("max_length", 500)
        self.threads_hashtags_count = threads_style.get("hashtags_count", 3)

        # 네이버 블로그 스타일 설정
        blog_style = config.get("naver_blog_style", {})
        self.blog_tone = blog_style.get("tone", "정보성 있고 검색 친화적인")
        self.blog_min_length = blog_style.get("min_length", 1500)
        self.blog_max_length = blog_style.get("max_length", 3000)
        self.blog_seo_tags_count = blog_style.get("seo_tags_count", 15)

        self.provider_order = self._resolve_provider_order()
        self.provider_strategy = config.get("llm.strategy", "fallback")
        self.max_retries_per_provider = int(config.get("llm.max_retries_per_provider", 2))
        self.request_timeout_seconds = int(config.get("llm.request_timeout_seconds", 45))
        self.cache_db_path = config.get("llm.cache_db_path") or None

        # Provider clients (API keys, enabled flags, async clients)
        init_provider_clients(self)

        # P7: 규제 점검 시스템
        self.regulation_checker = RegulationChecker(config=config)
        self.draft_cache = DraftCache(db_path=self.cache_db_path)

    # ------------------------------------------------------------------
    # Cache key
    # ------------------------------------------------------------------

    def _make_cache_key(self, post_data: dict[str, Any], output_formats: list[str]) -> str:
        """Generate a stable cache key from post title + category + output formats."""
        title = str(post_data.get("title", ""))
        category = str(post_data.get("category", ""))
        source = str(post_data.get("source", ""))
        fmt_str = ",".join(sorted(output_formats))
        raw = f"{title}|{category}|{source}|{fmt_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def generate_drafts(
        self,
        post_data,
        top_tweets=None,
        output_formats=None,
        quality_feedback: list[dict[str, Any]] | None = None,
    ):
        if output_formats is None:
            output_formats = ["twitter"]

        # ── 드래프트 캐시 조회 (재생성 시에는 캐시 스킵) ───────────────
        cache_key = self._make_cache_key(post_data, output_formats)
        if not quality_feedback:
            try:
                cached = self.draft_cache.get(cache_key)
                if cached:
                    drafts, image_prompt = cached
                    logger.info(
                        "Draft cache HIT: %s (provider=%s)", cache_key[:12], drafts.get("_provider_used", "cached")
                    )
                    return drafts, image_prompt
            except Exception as exc:
                logger.debug("Draft cache lookup failed (ignored): %s", exc)

        prompt = self._build_prompt(post_data, top_tweets, output_formats)

        # B-5: 품질 피드백이 있으면 재생성 프롬프트에 반영
        if quality_feedback:
            prompt = self._build_retry_prompt(prompt, quality_feedback)
            logger.info("[B-5] Quality gate retry: incorporating %d platform feedback(s)", len(quality_feedback))
        providers = self._enabled_providers()

        # ── 실패 이력 기반 provider 스킵 ──────────────────────────────
        try:
            from pipeline.cost_db import get_cost_db

            _cost_db = get_cost_db()
            skipped = _cost_db.get_skipped_providers() if _cost_db else set()
            if skipped:
                before = len(providers)
                providers = [p for p in providers if p not in skipped]
                if len(providers) < before:
                    logger.info("Skipping providers with recent failures: %s", skipped)
        except Exception:
            pass

        if not providers:
            logger.error("No enabled LLM providers available for draft generation.")
            return {
                "_provider_used": "none",
                "_generation_failed": True,
                "_generation_error": "No enabled LLM providers available.",
            }, None

        provider_errors = []
        for provider in providers:
            for attempt in range(1, self.max_retries_per_provider + 1):
                try:
                    logger.info("Generating drafts via %s (%s/%s)...", provider, attempt, self.max_retries_per_provider)
                    response_text, input_tokens, output_tokens = await self._generate_once(provider, prompt)
                    if self.cost_tracker:
                        self.cost_tracker.add_text_generation_cost(
                            provider,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                        )
                    drafts_dict, image_prompt = self._parse_response(response_text, output_formats, provider)
                    validation_error = self._validate_provider_output(response_text, drafts_dict, output_formats)
                    if validation_error:
                        raise RuntimeError(f"invalid_draft_output:{validation_error}")
                    logger.info("Successfully generated drafts using %s.", provider)

                    # ── 캐시 저장 + circuit breaker close ─────────────
                    try:
                        self.draft_cache.set(cache_key, drafts_dict, image_prompt, provider=provider)
                    except Exception:
                        pass
                    try:
                        from pipeline.cost_db import get_cost_db

                        get_cost_db().record_provider_success(provider)
                    except Exception:
                        pass

                    return drafts_dict, image_prompt
                except Exception as exc:  # pragma: no cover - remote API dependent
                    provider_errors.append(f"{provider}: {exc}")
                    error_text = str(exc).lower()
                    non_retryable = any(
                        token in error_text
                        for token in (
                            "credit balance is too low",
                            "insufficient_quota",
                            "invalid api key",
                            "unauthorized",
                            "permission denied",
                        )
                    )
                    no_retry_only = "invalid_draft_output:" in error_text
                    should_retry = attempt < self.max_retries_per_provider
                    if non_retryable or no_retry_only:
                        should_retry = False
                    if non_retryable:
                        # circuit breaker: 비복구 에러 시 provider 스킵 등록
                        try:
                            from pipeline.cost_db import get_cost_db

                            _cdb = get_cost_db()
                            skip_h = _cdb.get_circuit_skip_hours(provider)
                            _cdb.record_provider_failure(provider, skip_hours=skip_h)
                        except Exception:
                            pass
                    wait_seconds = min(2**attempt, 10)
                    logger.warning(
                        "Draft generation failed via %s (%s/%s): %s",
                        provider,
                        attempt,
                        self.max_retries_per_provider,
                        exc,
                    )
                    if should_retry:
                        await asyncio.sleep(wait_seconds)
            logger.info("Provider %s exhausted. Trying next provider.", provider)

        error_text = " | ".join(provider_errors)
        logger.error("All providers failed for draft generation: %s", error_text)
        return {
            "_provider_used": "none",
            "_generation_failed": True,
            "_generation_error": error_text,
        }, None


# ---------------------------------------------------------------------------
# Cache access helper — tests that previously patched `dg._draft_rules_cache`
# should now patch `pipeline.draft_prompts._draft_rules_cache` directly.
# [QA 수정] @property는 모듈 수준에서 동작하지 않음 → 단순 모듈 참조 별칭으로 교체.
# ---------------------------------------------------------------------------

# 읽기 전용 별칭: draft_prompts 모듈의 캐시를 직접 가리킴.
# 테스트에서 캐시 패칭이 필요하면 pipeline.draft_prompts._draft_rules_cache 를 직접 패치하세요.
_draft_rules_cache = _draft_prompts_mod._draft_rules_cache
