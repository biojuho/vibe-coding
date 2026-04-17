"""경량 급행 초안 생성기 (Viral Escalation Engine — Layer 3).

기존 TweetDraftGenerator를 래핑하되, Surge 전용으로 최적화:
- 경량 프롬프트 (시스템 프롬프트 축소)
- 60초 SLA 강제 (타임아웃)
- X + Threads 2채널만 생성 (블로그/뉴스레터 생략)
- 비용 추적 자동 연동
- [Phase 8] PerformancePromptAdapter로 성과 기반 프롬프트 자동 강화

Architecture:
    EscalationQueue ──▶ ExpressDraftPipeline ──▶ Notification (텔레그램)
    (escalation_queue.py)   (이 모듈)               (notification.py)
    PerformancePromptAdapter ↗ (성과 학습 컨텍스트 주입)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from pipeline.enrichment_engine import ContextEnrichmentEngine, EnrichedContext
from pipeline.performance_prompt_adapter import (
    PerformanceInsight,
    get_performance_prompt_adapter,
)

logger = logging.getLogger(__name__)


@dataclass
class ExpressDraftResult:
    """급행 초안 생성 결과."""

    success: bool = False
    draft_x: str = ""
    draft_threads: str = ""
    generation_time_sec: float = 0.0
    provider_used: str = ""
    error: str = ""
    cost_usd: float = 0.0


# ── 경량 프롬프트 ────────────────────────────────────────────────────────────

_SURGE_SYSTEM_PROMPT = """너는 한국 직장인 커뮤니티 트렌드를 실시간으로 전달하는 소셜미디어 에디터야.
지금 커뮤니티에서 급상승 중인 글감을 받으면, 즉시 소셜미디어 초안을 만들어.

규칙:
- X(트위터): 280자 이내, 위트 + 핵심만, 링크/해시태그 없음
- Threads: 500자 이내, 좀 더 캐주얼하고 대화체
- "🔥 지금 블라인드에서 터지는 중" 같은 실시간감을 살려
- 편집 없이 바로 게시 가능한 자연스러움이 최우선

반드시 아래 JSON 포맷으로만 응답:
{"x": "트윗 초안", "threads": "스레드 초안"}"""


# ── 메인 파이프라인 ──────────────────────────────────────────────────────────


class ExpressDraftPipeline:
    """Surge 전용 경량 초안 생성 파이프라인.

    Args:
        config_mgr: ConfigManager 인스턴스.
        draft_generator: 기존 TweetDraftGenerator (재사용).
        cost_tracker: CostTracker (비용 추적 연동).
        timeout_seconds: 초안 생성 최대 허용 시간 (기본 60초).
    """

    def __init__(
        self,
        config_mgr: Any,
        draft_generator: Any | None = None,
        cost_tracker: Any | None = None,
        timeout_seconds: int = 60,
    ):
        self.config = config_mgr
        self._draft_generator = draft_generator
        self._cost_tracker = cost_tracker
        self._timeout = timeout_seconds

        # [Phase 7] 실시간 RAG 인리치먼트 엔진 초기화
        self._enrichment_engine = ContextEnrichmentEngine()

        # [Phase 8] 성과 기반 프롬프트 강화 어댑터
        self._perf_adapter = get_performance_prompt_adapter()

    async def generate(
        self,
        title: str,
        content_preview: str,
        source: str = "blind",
        velocity_score: float = 0.0,
    ) -> ExpressDraftResult:
        """급행 X + Threads 초안 생성.

        Args:
            title: 원문 제목.
            content_preview: 원문 본문 미리보기 (최대 200자).
            source: 출처.
            velocity_score: 스파이크 속도 점수 (프롬프트 컨텍스트용).

        Returns:
            ExpressDraftResult — 성공 여부 및 초안.
        """
        start = time.time()
        result = ExpressDraftResult()

        # [Phase 8] 성과 인사이트 선제 조회 (fail-open — 실패해도 빈 인사이트)
        try:
            perf_insight: PerformanceInsight = await asyncio.wait_for(
                self._perf_adapter.get_insight(source=source),
                timeout=3.0,  # 인사이트 조회는 최대 3초만 허용 (SLA 보호)
            )
        except Exception:
            logger.debug("ExpressDraft: 성과 인사이트 조회 실패 (무시) — source=%s", source)
            from pipeline.performance_prompt_adapter import PerformanceInsight

            perf_insight = PerformanceInsight(source=source)

        # [Phase 7] 0단계: 실시간 외부 컨텍스트 보강 (Exa + Perplexity RAG)
        try:

            async def _generate_with_deadline():
                enriched = await self._enrichment_engine.process_topic(title)
                user_prompt = self._build_user_prompt(
                    title,
                    content_preview,
                    source,
                    velocity_score,
                    enriched=enriched,
                    perf_insight=perf_insight,
                )
                return await self._call_llm(user_prompt)

            raw_response = await asyncio.wait_for(_generate_with_deadline(), timeout=self._timeout)
            parsed = self._parse_response(raw_response)
            result.draft_x = parsed.get("x", "")
            result.draft_threads = parsed.get("threads", "")
            result.success = bool(result.draft_x)
            result.generation_time_sec = round(time.time() - start, 2)
            result.provider_used = raw_response.get("_provider", "unknown")
            result.cost_usd = float(raw_response.get("_cost", 0.0))

            logger.info(
                "ExpressDraft: 생성 완료 (%.1f초, provider=%s, perf_insight=%s)",
                result.generation_time_sec,
                result.provider_used,
                "있음" if perf_insight.has_data else "없음",
            )

        except asyncio.TimeoutError:
            result.error = f"타임아웃 ({self._timeout}초 초과)"
            result.generation_time_sec = round(time.time() - start, 2)
            logger.warning("ExpressDraft: 타임아웃 — %s", title[:40])

        except Exception as exc:
            result.error = str(exc)
            result.generation_time_sec = round(time.time() - start, 2)
            logger.error("ExpressDraft: 생성 실패 — %s: %s", title[:40], exc)

        return result

    def _build_user_prompt(
        self,
        title: str,
        content_preview: str,
        source: str,
        velocity_score: float,
        enriched: EnrichedContext | None = None,
        perf_insight: "PerformanceInsight | None" = None,
    ) -> str:
        """급행 사용자 프롬프트 구성.

        [Phase 8] perf_insight가 있으면 성과 기반 가이드를 시스템 프롬프트 뒤에 주입.
        데이터가 없으면 기존 동작 그대로 (fail-open).
        """
        source_label = {
            "blind": "블라인드",
            "ppomppu": "뽐뿌",
            "fmkorea": "에펨코리아",
            "jobplanet": "잡플래닛",
        }.get(source, source)

        base_prompt = (
            f"🔥 지금 {source_label}에서 급상승 중인 글 (속도점수: {velocity_score:.1f})\n\n"
            f"제목: {title}\n"
            f"내용 미리보기: {content_preview}\n\n"
        )

        if enriched:
            logger.info("보강된 컨텍스트(Enriched Context)를 프롬프트에 주입합니다.")
            base_prompt += enriched.to_prompt_context()

        # [Phase 8] 성과 기반 가이드 인젝션
        if perf_insight is not None:
            perf_ctx = perf_insight.to_prompt_context()
            if perf_ctx:
                logger.info("성과 인사이트를 프롬프트에 주입합니다 (source=%s).", source)
                base_prompt += perf_ctx

        base_prompt += "\n이 글로 X(트위터)와 Threads 초안을 즉시 만들어."
        return base_prompt

    async def _call_llm(self, user_prompt: str) -> dict[str, Any]:
        """LLM 호출 — 기존 draft_generator 재사용 또는 직접 호출.

        Returns:
            {"response": str, "_provider": str, "_cost": float}
        """
        # 기존 DraftGenerator의 LLM 호출 인프라 재사용
        if self._draft_generator is not None:
            try:
                # draft_generator의 내부 provider 체인 활용
                providers = getattr(self._draft_generator, "providers", None)
                if providers:
                    for provider in providers:
                        try:
                            response = await provider.generate(
                                system_prompt=_SURGE_SYSTEM_PROMPT,
                                user_prompt=user_prompt,
                                max_tokens=600,
                            )
                            if response:
                                return {
                                    "response": str(response),
                                    "_provider": getattr(provider, "name", "unknown"),
                                    "_cost": 0.0,
                                }
                        except Exception as exc:
                            logger.debug(
                                "ExpressDraft: provider %s 실패: %s",
                                getattr(provider, "name", "?"),
                                exc,
                            )
                            continue

                enabled_providers = getattr(self._draft_generator, "_enabled_providers", None)
                generate_once = getattr(self._draft_generator, "_generate_once", None)
                if callable(enabled_providers) and callable(generate_once):
                    combined_prompt = f"{_SURGE_SYSTEM_PROMPT}\n\n{user_prompt}"
                    for provider_name in enabled_providers():
                        try:
                            response_text, input_tokens, output_tokens = await generate_once(
                                provider_name,
                                combined_prompt,
                            )
                            cost_tracker = getattr(self._draft_generator, "cost_tracker", None)
                            if cost_tracker is not None:
                                cost_tracker.add_text_generation_cost(
                                    provider_name,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                )
                            return {
                                "response": str(response_text),
                                "_provider": str(provider_name),
                                "_cost": 0.0,
                            }
                        except Exception as exc:
                            logger.debug("ExpressDraft: provider %s 실패: %s", provider_name, exc)
                            continue
            except Exception as exc:
                logger.warning("ExpressDraft: draft_generator 연동 실패: %s", exc)

        # Fallback: 직접 API 호출 (TODO: 구현)
        raise RuntimeError("사용 가능한 LLM provider 없음")

    @staticmethod
    def _parse_response(raw: dict[str, Any]) -> dict[str, str]:
        """LLM 응답에서 JSON 파싱 시도."""
        import json
        import re

        text = str(raw.get("response", ""))

        # JSON 블록 추출
        json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 파싱 실패 시 전체 텍스트를 X 초안으로 사용
        cleaned = text.strip()
        if cleaned:
            x_draft = cleaned[:280]
            threads_draft = cleaned[:500]
            return {"x": x_draft, "threads": threads_draft}

        return {"x": "", "threads": ""}
