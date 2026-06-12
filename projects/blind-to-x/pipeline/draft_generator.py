"""Draft generation with multi-provider fallback support."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

import pipeline.draft_prompts as _draft_prompts_mod
from pipeline.draft_cache import DraftCache
from pipeline.draft_contract import iter_publishable_drafts
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
from config import as_bool as _as_bool

logger = logging.getLogger(__name__)

_PROVIDER_FAILURE_PRIORITY = {
    "auth": 10,
    "quota_or_billing": 20,
    "invalid_output": 30,
    "rate_limit": 40,
    "overloaded": 50,
    "server_error": 60,
    "timeout": 70,
    "network_error": 80,
    "provider_error": 90,
}


def _compact_error_preview(error: Any, *, limit: int = 240) -> str:
    return " ".join(str(error or "").split())[:limit]


def classify_provider_failure(
    provider: str,
    model: str,
    error: Exception,
    *,
    attempt: int,
    max_attempts: int,
    latency_ms: float,
) -> dict[str, Any]:
    """Return an operator-friendly, JSON-safe LLM provider failure record."""
    error_text = str(error or "").lower()
    if isinstance(error, asyncio.TimeoutError) or "timeout" in error_text or "timed out" in error_text:
        category = "timeout"
        retryable = True
        action = "Retry with current fallback chain; if repeated, raise provider timeout or reduce prompt size."
    elif "invalid_draft_output:" in error_text:
        category = "invalid_output"
        retryable = False
        action = "Inspect prompt and parser contract; do not retry the same provider output blindly."
    elif any(token in error_text for token in ("invalid api key", "unauthorized", "permission denied", "401", "403")):
        category = "auth"
        retryable = False
        action = "Check provider API key, env wiring, and enabled flags before rerunning."
    elif any(
        token in error_text
        for token in (
            "credit balance is too low",
            "insufficient_quota",
            "current quota",
            "quota exceeded",
            "billing",
        )
    ):
        category = "quota_or_billing"
        retryable = False
        action = "Check provider quota, billing, or credits; keep fallback providers enabled."
    elif any(token in error_text for token in ("429", "rate limit", "too many requests", "resource_exhausted")):
        category = "rate_limit"
        retryable = True
        action = "Wait for provider rate-limit reset or reduce request volume before retrying."
    elif any(token in error_text for token in ("503", "529", "overloaded", "overloaded_error", "unavailable")):
        category = "overloaded"
        retryable = True
        action = "Retry with exponential backoff and fallback providers enabled; reduce burst traffic if repeated."
    elif any(token in error_text for token in ("500", "502", "504", "server error")):
        category = "server_error"
        retryable = True
        action = "Retry later with fallback providers enabled; provider service may be degraded."
    elif any(token in error_text for token in ("connection", "dns", "ssl", "read error", "network")):
        category = "network_error"
        retryable = True
        action = "Check network path and retry with the same fallback chain."
    else:
        category = "provider_error"
        retryable = True
        action = "Inspect provider response and fallback evidence before changing provider order."

    return {
        "provider": provider,
        "model": model,
        "attempt": int(attempt),
        "max_attempts": int(max_attempts),
        "category": category,
        "retryable": bool(retryable),
        "circuit_breaker_candidate": category in {"auth", "quota_or_billing"},
        "latency_ms": round(max(0.0, float(latency_ms)), 1),
        "error_preview": _compact_error_preview(error),
        "operator_action_required": True,
        "operator_action": action,
    }


def summarize_provider_failures(failures: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    providers: list[str] = []
    circuit_breaker_providers: list[str] = []
    retryable_count = 0
    non_retryable_count = 0
    primary_action = ""
    total_latency_ms = 0.0
    max_latency_ms = 0.0
    last_failure: dict[str, Any] = {}
    primary_failure: dict[str, Any] = {}
    primary_priority: tuple[int, int] | None = None
    for failure in failures:
        category = str(failure.get("category") or "provider_error")
        categories[category] = categories.get(category, 0) + 1
        provider = str(failure.get("provider") or "")
        if provider and provider not in providers:
            providers.append(provider)
        retryable = _as_bool(failure.get("retryable"))
        circuit_breaker_candidate = _as_bool(failure.get("circuit_breaker_candidate"))
        if provider and circuit_breaker_candidate and provider not in circuit_breaker_providers:
            circuit_breaker_providers.append(provider)
        if retryable:
            retryable_count += 1
        else:
            non_retryable_count += 1
        if not primary_action and failure.get("operator_action"):
            primary_action = str(failure["operator_action"])
        latency_ms = max(0.0, float(failure.get("latency_ms") or 0.0))
        total_latency_ms += latency_ms
        max_latency_ms = max(max_latency_ms, latency_ms)
        failure_brief = {
            "provider": provider,
            "model": str(failure.get("model") or ""),
            "category": category,
            "retryable": retryable,
            "circuit_breaker_candidate": circuit_breaker_candidate,
            "error_preview": str(failure.get("error_preview") or ""),
            "operator_action": str(failure.get("operator_action") or ""),
        }
        last_failure = failure_brief
        priority = (
            _PROVIDER_FAILURE_PRIORITY.get(category, _PROVIDER_FAILURE_PRIORITY["provider_error"]),
            len(providers),
        )
        if circuit_breaker_candidate:
            priority = (max(0, priority[0] - 5), priority[1])
        if primary_priority is None or priority < primary_priority:
            primary_priority = priority
            primary_failure = failure_brief
            if failure_brief["operator_action"]:
                primary_action = failure_brief["operator_action"]
    return {
        "total_failures": len(failures),
        "providers_attempted": providers,
        "categories": dict(sorted(categories.items())),
        "circuit_breaker_providers": circuit_breaker_providers,
        "retryable_count": retryable_count,
        "non_retryable_count": non_retryable_count,
        "total_latency_ms": round(total_latency_ms, 1),
        "max_latency_ms": round(max_latency_ms, 1),
        "last_failure": last_failure,
        "primary_failure": primary_failure,
        "operator_action_required": bool(failures),
        "primary_operator_action": primary_action,
    }


class ProviderFallbackError(RuntimeError):
    def __init__(self, message: str, failures: list[dict[str, Any]]):
        super().__init__(message)
        self.failures = failures
        self.summary = summarize_provider_failures(failures)


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

    def _cache_generated_drafts(
        self,
        cache_key: str,
        drafts_dict: dict[str, Any],
        image_prompt: str | None,
    ) -> None:
        try:
            self.draft_cache.set(cache_key, drafts_dict, image_prompt, provider=drafts_dict.get("_provider_used", ""))
        except Exception:
            pass

    @staticmethod
    def _generation_failure(
        error: str,
        *,
        provider_failures: list[dict[str, Any]] | None = None,
        provider_failure_summary: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], None]:
        payload = {
            "_provider_used": "none",
            "_generation_failed": True,
            "_generation_error": error,
        }
        if provider_failures is not None:
            payload["_provider_failures"] = provider_failures
        if provider_failure_summary is not None:
            payload["_provider_failure_summary"] = provider_failure_summary
        return payload, None

    def _available_providers_after_recent_failures(self) -> list[str]:
        providers = self._enabled_providers()
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
        return providers

    def _best_of_n_for_request(self, quality_feedback: list[dict[str, Any]] | None) -> int:
        # B-5 피드백 기반 재생성인 경우에는 비용 낭비 방지를 위해 1회만 단독 실행.
        if quality_feedback:
            return 1
        return int(self.config.get("llm.best_of_n", 1))

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def _generate_drafts_once(
        self,
        prompt: str,
        providers: list[str],
        output_formats: list[str],
        allow_partial: bool,
    ) -> tuple[dict[str, Any], str | None]:
        """주어진 프롬프트와 프로바이더 목록으로 초안 후보를 1회 성공적으로 생성하여 리턴합니다."""
        provider_errors = []
        provider_failures: list[dict[str, Any]] = []
        for provider in providers:
            for attempt in range(1, self.max_retries_per_provider + 1):
                attempt_started_at = time.monotonic()
                try:
                    logger.info(
                        "Generating drafts candidate via %s (%s/%s)...",
                        provider,
                        attempt,
                        self.max_retries_per_provider,
                    )
                    (
                        response_text,
                        input_tokens,
                        output_tokens,
                        cache_creation_tokens,
                        cache_read_tokens,
                    ) = await self._generate_once(provider, prompt)
                    if self.cost_tracker:
                        self.cost_tracker.add_text_generation_cost(
                            provider,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cache_creation_tokens=cache_creation_tokens,
                            cache_read_tokens=cache_read_tokens,
                            cache_creation_multiplier=self._cache_creation_multiplier_for(provider, prompt),
                        )
                    drafts_dict, image_prompt = self._parse_response(response_text, output_formats, provider)
                    validation_error = self._validate_provider_output(
                        response_text,
                        drafts_dict,
                        output_formats,
                        allow_partial=allow_partial,
                    )
                    if validation_error:
                        raise RuntimeError(f"invalid_draft_output:{validation_error}")

                    try:
                        from pipeline.cost_db import get_cost_db

                        get_cost_db().record_provider_success(provider)
                    except Exception:
                        pass

                    return drafts_dict, image_prompt
                except Exception as exc:
                    failure = classify_provider_failure(
                        provider,
                        self._model_for_provider(provider),
                        exc,
                        attempt=attempt,
                        max_attempts=self.max_retries_per_provider,
                        latency_ms=(time.monotonic() - attempt_started_at) * 1000,
                    )
                    provider_failures.append(failure)
                    provider_errors.append(f"{provider}: {exc}")
                    error_text = str(exc).lower()
                    non_retryable = failure["category"] in {"auth", "quota_or_billing"} or any(
                        token in error_text for token in ("invalid api key", "unauthorized", "permission denied")
                    )
                    no_retry_only = failure["category"] == "invalid_output"
                    should_retry = attempt < self.max_retries_per_provider
                    if non_retryable or no_retry_only:
                        should_retry = False
                    if non_retryable:
                        try:
                            from pipeline.cost_db import get_cost_db

                            _cdb = get_cost_db()
                            if _cdb:
                                skip_h = _cdb.get_circuit_skip_hours(provider)
                                _cdb.record_provider_failure(provider, skip_hours=skip_h)
                        except Exception:
                            pass
                    wait_seconds = min(2**attempt, 10)
                    logger.warning(
                        "Draft candidate generation failed via %s (%s/%s, category=%s, retryable=%s): %s",
                        provider,
                        attempt,
                        self.max_retries_per_provider,
                        failure["category"],
                        failure["retryable"],
                        exc,
                    )
                    if should_retry:
                        await asyncio.sleep(wait_seconds)
            logger.info("Provider %s exhausted for candidate. Trying next provider.", provider)

        error_text = " | ".join(provider_errors)
        raise ProviderFallbackError(
            f"All providers failed to generate candidate: {error_text}",
            provider_failures,
        )

    _DEFAULT_BEST_OF_N_COMMENT_WEIGHT = 0.5
    _DEFAULT_BEST_OF_N_QUALITY_WEIGHT = 0.35
    _COMMENT_TRIGGER_PLATFORMS = ("twitter", "threads")

    def _best_of_n_comment_weight(self) -> float:
        """Best-of-N 결합 점수에서 4축(comment_trigger) 평균이 차지할 가중치.

        twitter/threads 가 출력 포맷에 포함되고 EditorialReviewer 가 4축 평균을
        리턴한 경우에만 적용. 0.0 = 5축만, 1.0 = 4축만, 기본 0.5 = 50:50.
        """
        try:
            value = float(self.config.get("llm.best_of_n_comment_weight", self._DEFAULT_BEST_OF_N_COMMENT_WEIGHT))
        except (TypeError, ValueError):
            return self._DEFAULT_BEST_OF_N_COMMENT_WEIGHT
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    def _best_of_n_quality_weight(self) -> float:
        """Weight for deterministic publishability/novelty in Best-of-N selection.

        EditorialReviewer scores whether a draft is good writing. The local
        quality gate checks whether it is immediately usable: length, safety,
        cliches, source-copying, and recent-draft similarity.
        """
        try:
            value = float(self.config.get("llm.best_of_n_quality_weight", self._DEFAULT_BEST_OF_N_QUALITY_WEIGHT))
        except (TypeError, ValueError):
            return self._DEFAULT_BEST_OF_N_QUALITY_WEIGHT
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    def _combined_candidate_score(
        self,
        result: Any,
        output_formats: list[str] | None,
        *,
        comment_weight: float | None = None,
    ) -> tuple[float, dict[str, float]]:
        """5축 평균(avg_score) + 4축 평균(comment_trigger_scores) 결합.

        - 출력 포맷에 twitter/threads 가 없거나 4축 점수가 비어있으면 5축만 사용.
        - 결합식: combined = avg_score * (1 - w) + ct_avg * w.
        - 항상 (combined, breakdown_dict) 튜플을 반환. breakdown 은 로그/테스트용.
        """
        avg = float(getattr(result, "avg_score", 0.0) or 0.0)
        weight = self._best_of_n_comment_weight() if comment_weight is None else float(comment_weight)
        weight = max(0.0, min(1.0, weight))

        ct_scores: dict[str, float] = getattr(result, "comment_trigger_scores", {}) or {}
        formats = [f.lower() for f in (output_formats or []) if isinstance(f, str)]
        applicable = [
            float(ct_scores[plat])
            for plat in self._COMMENT_TRIGGER_PLATFORMS
            if plat in formats and plat in ct_scores and isinstance(ct_scores[plat], (int, float))
        ]

        if applicable:
            ct_avg = sum(applicable) / len(applicable)
            combined = avg * (1.0 - weight) + ct_avg * weight
        else:
            ct_avg = 0.0
            combined = avg

        breakdown = {
            "avg_score": avg,
            "comment_trigger_avg": ct_avg,
            "comment_weight": weight if applicable else 0.0,
        }
        return combined, breakdown

    def _candidate_publishability_score(
        self,
        drafts_dict: dict[str, Any],
        post_data: dict[str, Any],
        output_formats: list[str] | None,
    ) -> tuple[float, dict[str, float]]:
        """Score how ready the candidate is for direct publishing.

        Returns a 0-10 score so it can be blended with EditorialReviewer scores.
        A candidate with hard gate failures is penalized more strongly than the
        gate's raw 100-point score so Best-of-N prefers a slightly less flashy
        but directly usable draft.
        """
        from pipeline.quality_gate import QualityGate

        requested = {fmt.lower() for fmt in (output_formats or []) if isinstance(fmt, str)}
        publishable = [
            (platform, text)
            for platform, text in iter_publishable_drafts(drafts_dict)
            if not requested or platform.lower() in requested
        ]
        if not publishable:
            return 10.0, {
                "publishability_score": 10.0,
                "quality_failures": 0.0,
                "quality_warnings": 0.0,
                "max_semantic_similarity": 0.0,
            }

        gate = QualityGate()
        source_content = str((post_data or {}).get("content") or "")
        scores: list[float] = []
        failure_count = 0
        warning_count = 0
        max_similarity = 0.0

        for platform, text in publishable:
            result = gate.check(
                text,
                source_content=source_content,
                platform=platform,
                post_data=post_data,
            )
            failure_count += len(result.failures)
            warning_count += len(result.warnings)
            max_similarity = max(max_similarity, float(result.metrics.get("max_semantic_similarity", 0.0) or 0.0))
            normalized = float(result.score) / 10.0
            normalized -= min(6.0, len(result.failures) * 2.0 + len(result.warnings) * 0.5)
            scores.append(max(0.0, normalized))

        publishability_score = sum(scores) / len(scores)
        return publishability_score, {
            "publishability_score": publishability_score,
            "quality_failures": float(failure_count),
            "quality_warnings": float(warning_count),
            "max_semantic_similarity": max_similarity,
        }

    async def _generate_best_of_n_candidates(
        self,
        *,
        best_of_n: int,
        prompt: str,
        providers: list[str],
        output_formats: list[str],
        allow_partial: bool,
    ) -> list[tuple[dict[str, Any], str | None]]:
        candidates = []
        for i in range(best_of_n):
            try:
                drafts_dict, image_prompt = await self._generate_drafts_once(
                    prompt, providers, output_formats, allow_partial
                )
                candidates.append((drafts_dict, image_prompt))
            except Exception as exc:
                logger.warning("[Best-of-N] Candidate %d generation failed: %s", i + 1, exc)
        return candidates

    async def _select_best_of_n_candidate(
        self,
        candidates: list[tuple[dict[str, Any], str | None]],
        post_data: dict[str, Any],
        output_formats: list[str],
    ) -> tuple[dict[str, Any], str | None] | None:
        from pipeline.editorial_reviewer import EditorialReviewer

        reviewer = EditorialReviewer(config=self.config)
        best_candidate = None
        best_combined = -1.0
        best_breakdown: dict[str, float] | None = None
        comment_weight = self._best_of_n_comment_weight()
        quality_weight = self._best_of_n_quality_weight()

        for idx, (drafts_dict, image_prompt) in enumerate(candidates, start=1):
            result = await reviewer.review_and_polish(drafts_dict, post_data)
            editorial_score, breakdown = self._combined_candidate_score(
                result,
                output_formats,
                comment_weight=comment_weight,
            )
            publishability_score, quality_breakdown = self._candidate_publishability_score(
                result.polished_drafts,
                post_data,
                output_formats,
            )
            combined = editorial_score * (1.0 - quality_weight) + publishability_score * quality_weight
            breakdown.update(quality_breakdown)
            breakdown["editorial_combined"] = editorial_score
            breakdown["quality_weight"] = quality_weight
            breakdown["selection_score"] = combined
            logger.info(
                "[Best-of-N] Candidate %d: selection=%.2f (editorial=%.2f, publishability=%.2f, "
                "avg=%.2f, ct_avg=%.2f, comment_w=%.2f, quality_w=%.2f)",
                idx,
                combined,
                breakdown.get("editorial_combined", 0.0),
                breakdown.get("publishability_score", 0.0),
                breakdown.get("avg_score", 0.0),
                breakdown.get("comment_trigger_avg", 0.0),
                breakdown.get("comment_weight", 0.0),
                breakdown.get("quality_weight", 0.0),
            )
            if combined > best_combined:
                best_combined = combined
                best_breakdown = breakdown
                best_candidate = (result.polished_drafts, image_prompt)

        if not best_candidate:
            return None

        drafts_dict, image_prompt = best_candidate
        logger.info(
            "[Best-of-N] Selected best candidate combined=%.2f (avg=%.2f, ct_avg=%.2f)",
            best_combined,
            (best_breakdown or {}).get("avg_score", 0.0),
            (best_breakdown or {}).get("comment_trigger_avg", 0.0),
        )
        # T-1107: tune_best_of_n_weight.py sweep 데이터 소스로 영속화.
        # persist_stage 가 이 키를 읽어 record_draft_event 에 전달.
        if isinstance(drafts_dict, dict):
            try:
                drafts_dict["_comment_trigger_avg"] = float((best_breakdown or {}).get("comment_trigger_avg", 0.0))
                drafts_dict["_quality_gate_score"] = float((best_breakdown or {}).get("publishability_score", 0.0))
                drafts_dict["_quality_gate_failures"] = int((best_breakdown or {}).get("quality_failures", 0.0))
                drafts_dict["_quality_gate_warnings"] = int((best_breakdown or {}).get("quality_warnings", 0.0))
                drafts_dict["_max_semantic_similarity"] = float(
                    (best_breakdown or {}).get("max_semantic_similarity", 0.0)
                )
                drafts_dict["_best_of_n_selection_score"] = float(
                    (best_breakdown or {}).get("selection_score", best_combined)
                )
            except (TypeError, ValueError):
                pass
        return drafts_dict, image_prompt

    async def generate_drafts(
        self,
        post_data,
        top_tweets=None,
        output_formats=None,
        quality_feedback: list[dict[str, Any]] | None = None,
        allow_partial: bool = False,
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
        providers = self._available_providers_after_recent_failures()

        if not providers:
            logger.error("No enabled LLM providers available for draft generation.")
            return self._generation_failure("No enabled LLM providers available.")

        best_of_n = self._best_of_n_for_request(quality_feedback)

        if best_of_n <= 1:
            try:
                drafts_dict, image_prompt = await self._generate_drafts_once(
                    prompt, providers, output_formats, allow_partial
                )
                self._cache_generated_drafts(cache_key, drafts_dict, image_prompt)
                return drafts_dict, image_prompt
            except ProviderFallbackError as exc:
                logger.error("Draft generation failed: %s", exc)
                return self._generation_failure(
                    str(exc),
                    provider_failures=exc.failures,
                    provider_failure_summary=exc.summary,
                )
            except Exception as exc:
                logger.error("Draft generation failed: %s", exc)
                return self._generation_failure(str(exc))

        # Best-of-N 루프 실행
        logger.info("[Best-of-N] Generating %d candidates for comparison...", best_of_n)
        candidates = await self._generate_best_of_n_candidates(
            best_of_n=best_of_n,
            prompt=prompt,
            providers=providers,
            output_formats=output_formats,
            allow_partial=allow_partial,
        )

        if not candidates:
            logger.error("[Best-of-N] All candidate generations failed.")
            return self._generation_failure("All candidates failed to generate.")

        if len(candidates) == 1:
            drafts_dict, image_prompt = candidates[0]
            self._cache_generated_drafts(cache_key, drafts_dict, image_prompt)
            return drafts_dict, image_prompt

        # N개 중 EditorialReviewer를 사용해 최선 책정
        logger.info("[Best-of-N] Comparing %d candidates using EditorialReviewer...", len(candidates))
        try:
            selected = await self._select_best_of_n_candidate(candidates, post_data, output_formats)
            if selected:
                drafts_dict, image_prompt = selected
                self._cache_generated_drafts(cache_key, drafts_dict, image_prompt)
                return drafts_dict, image_prompt
        except Exception as exc:
            logger.warning("[Best-of-N] Editorial evaluation failed (falling back to first candidate): %s", exc)

        drafts_dict, image_prompt = candidates[0]
        self._cache_generated_drafts(cache_key, drafts_dict, image_prompt)
        return drafts_dict, image_prompt

    async def _call_llm_with_fallback(self, prompt: str, *, platform: str = "twitter") -> str:
        """Return the best-effort text for a single platform using the provider chain."""
        output_formats = [platform]
        provider_errors = []
        for provider in self._enabled_providers():
            for attempt in range(1, self.max_retries_per_provider + 1):
                try:
                    (
                        response_text,
                        input_tokens,
                        output_tokens,
                        cache_creation_tokens,
                        cache_read_tokens,
                    ) = await self._generate_once(provider, prompt)
                    if self.cost_tracker:
                        self.cost_tracker.add_text_generation_cost(
                            provider,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cache_creation_tokens=cache_creation_tokens,
                            cache_read_tokens=cache_read_tokens,
                            cache_creation_multiplier=self._cache_creation_multiplier_for(provider, prompt),
                        )
                    drafts_dict, _image_prompt = self._parse_response(response_text, output_formats, provider)
                    draft_text = str(drafts_dict.get(platform, "") or "").strip()
                    if draft_text:
                        return draft_text
                    raise RuntimeError(f"empty_retry_output:{platform}")
                except Exception as exc:  # pragma: no cover - remote API dependent
                    provider_errors.append(f"{provider}: {exc}")
                    logger.warning(
                        "Retry draft generation failed via %s (%s/%s): %s",
                        provider,
                        attempt,
                        self.max_retries_per_provider,
                        exc,
                    )
                    if attempt < self.max_retries_per_provider:
                        await asyncio.sleep(min(2**attempt, 10))
            logger.info("Retry provider %s exhausted. Trying next provider.", provider)
        raise RuntimeError(" | ".join(provider_errors) or "No enabled LLM providers available.")


# ---------------------------------------------------------------------------
# Cache access helper — tests that previously patched `dg._draft_rules_cache`
# should now patch `pipeline.draft_prompts._draft_rules_cache` directly.
# [QA 수정] @property는 모듈 수준에서 동작하지 않음 → 단순 모듈 참조 별칭으로 교체.
# ---------------------------------------------------------------------------

# 읽기 전용 별칭: draft_prompts 모듈의 캐시를 직접 가리킴.
# 테스트에서 캐시 패칭이 필요하면 pipeline.draft_prompts._draft_rules_cache 를 직접 패치하세요.
_draft_rules_cache = _draft_prompts_mod._draft_rules_cache
