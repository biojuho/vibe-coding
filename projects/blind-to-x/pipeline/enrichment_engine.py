"""
Blind-to-X Dynamic Context Enrichment Engine (Phase 7 Scale-up)
================================================================
바이럴 큐에서 발생한 트렌드 키워드를 기반으로, Exa Search와 Perplexity API를 사용해
실시간 글로벌 레퍼런스, 반응, 심층 데이터를 보강(Enrichment)하는 미들웨어.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── 상수: Fallback 메시지 중복 제거 ──────────────────────────────
_FALLBACK_INSIGHT = "{topic}에 대한 심층 인사이트를 분석 중입니다 (Fallback Mode)."
_FALLBACK_SENTIMENT = "감정 분석 데이터 없음 (Deep Insights 참조)"
_ERROR_INSIGHT = "오류로 인해 {topic} 심도 분석에 실패했습니다."


class EnrichedContext(BaseModel):
    """보강된 최종 컨텍스트를 담는 데이터 클래스. Draft Generator의 입력으로 전달됨."""

    original_topic: str = Field(..., description="원본 바이럴 트렌드 주제")
    deep_insights: str = Field(..., description="Perplexity를 통해 분석된 심층 인사이트 요약")
    global_references: List[str] = Field(
        default_factory=list, description="Exa 검색을 통해 얻은 인용 가능한 URL/출처 목록"
    )
    sentiment_angle: str = Field(..., description="현재 트렌드의 주요 여론 및 감정 (작성 앵글 추천용)")

    def to_prompt_context(self) -> str:
        """프롬프트 주입용 포맷팅"""
        # [FIX-3] 불필요한 중간 리스트 제거 → 제너레이터
        refs = "\n".join(f"- {url}" for url in self.global_references)
        return f"""
[Enriched Deep Context]
* Original Topic: {self.original_topic}
* Key Sentiments/Angles: {self.sentiment_angle}
* Deep Insights:
{self.deep_insights}

* Global References:
{refs}
"""


class ContextEnrichmentEngine:
    def __init__(
        self,
        exa_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
        max_concurrency: int = 4,
    ):
        self.exa_api_key = exa_api_key or os.getenv("EXA_API_KEY")
        self.perplexity_api_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
        self.timeout = httpx.Timeout(5.0)
        # [FIX-2] 커넥션 풀 제한 명시 — 호스트당 최대 10, 전체 20
        self._limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        self.max_concurrency = max(1, int(max_concurrency))

    async def _fetch_exa_references(self, client: httpx.AsyncClient, topic: str) -> List[Dict]:
        """[내부] Exa API를 호출하여 고품질 레퍼런스 URL 및 스니펫을 검색합니다."""
        if not self.exa_api_key:
            logger.warning("EXA_API_KEY가 설정되지 않아 Exa 검색을 스킵합니다.")
            return []

        logger.info("[%s] 비동기 Exa API 검색 시작...", topic)
        try:
            headers = {"x-api-key": self.exa_api_key, "Content-Type": "application/json"}
            payload = {"query": topic, "numResults": 3, "useAutoprompt": True}
            res = await client.post("https://api.exa.ai/search", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

            results = data.get("results", [])
            return [{"title": r.get("title", ""), "url": r.get("url", "")} for r in results]
        except Exception as e:
            logger.error("Exa API 검색 중 오류 발생: %s", e)
            return []

    async def _fetch_perplexity_synthesis(
        self, client: httpx.AsyncClient, topic: str, references: List[Dict]
    ) -> str:
        """[내부] Perplexity API에 검색된 레퍼런스를 던져 심도 있는 전문가 수준의 인사이트를 합성합니다."""
        if not self.perplexity_api_key:
            logger.warning("PERPLEXITY_API_KEY 미설정 — Fallback Mode.")
            return _FALLBACK_INSIGHT.format(topic=topic)

        logger.info("[%s] Perplexity API 컨텍스트 합성 시작...", topic)

        # [FIX-3] .get()으로 통일 — _fetch_exa_references와 동일한 방어적 접근
        ref_text = "\n".join(
            f"- {r.get('title', '?')} ({r.get('url', '?')})" for r in references
        )
        prompt = f"""
You are an expert tech/business analyst.
Please provide deep strategic insights, current sentiment, and controversial angles for the following topic.
Topic: {topic}

Here are some relevant references found online:
{ref_text}

Provide:
1. Deep Insights (Why it matters, hidden context).
2. Key Sentiment & Angles (What people are arguing about).
"""

        try:
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "system", "content": "You are a top-tier C-level strategy analyst."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }

            res = await client.post(
                "https://api.perplexity.ai/chat/completions", headers=headers, json=payload
            )
            res.raise_for_status()
            data = res.json()

            choices = data.get("choices", [])
            if not choices:
                logger.warning("Perplexity 응답에 choices가 없습니다. Fallback 반환.")
                return _FALLBACK_INSIGHT.format(topic=topic)
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                logger.warning("Perplexity 응답 content가 비어 있습니다. Fallback 반환.")
                return _FALLBACK_INSIGHT.format(topic=topic)
            return content
        except Exception as e:
            logger.error("Perplexity API 합성 중 오류 발생: %s", e)
            return _ERROR_INSIGHT.format(topic=topic)

    # [FIX-2] client를 외부에서 주입받을 수 있도록 변경.
    # batch_process에서 공유 클라이언트를 넘기고, 단독 호출 시에는 자체 생성.
    async def process_topic(
        self,
        viral_topic: str,
        _client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[EnrichedContext]:
        """
        [Public API]
        단일 트렌드 토픽을 입력받아 데이터를 보강시킨 후 반환합니다.
        _client가 주어지면 재사용 (batch 모드), 없으면 자체 생성 (단건 모드).
        """

        async def _run(client: httpx.AsyncClient) -> Optional[EnrichedContext]:
            try:
                references = await self._fetch_exa_references(client, viral_topic)
                insights = await self._fetch_perplexity_synthesis(client, viral_topic, references)
                # [FIX-3] 하드코딩 제거 → 상수 사용
                sentiment = _FALLBACK_SENTIMENT

                enriched = EnrichedContext(
                    original_topic=viral_topic,
                    deep_insights=insights,
                    global_references=[ref["url"] for ref in references],
                    sentiment_angle=sentiment,
                )
                logger.info("Topic '%s' 컨텍스트 보강 완료.", viral_topic)
                return enriched
            except Exception as e:
                logger.error("컨텍스트 보강 실패 [%s]: %s", viral_topic, e)
                return None

        # [FIX-2] 외부 클라이언트가 있으면 그대로 사용 → TLS 핸드셰이크 1회로 수렴
        if _client is not None:
            return await _run(_client)

        # 단건 호출: 자체 클라이언트 생성 후 정리
        async with httpx.AsyncClient(timeout=self.timeout, limits=self._limits) as client:
            return await _run(client)

    async def batch_process(self, viral_topics: List[str]) -> Dict[str, EnrichedContext]:
        """다수의 큐 항목을 병렬로 보강하여 파이프라인 병목(Bottleneck) 현상을 없앱니다."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        # [FIX-2] 단일 공유 클라이언트 — 커넥션 풀 재사용, TLS 1회
        async with httpx.AsyncClient(timeout=self.timeout, limits=self._limits) as shared_client:

            async def _bounded_process(topic: str):
                async with semaphore:
                    return await self.process_topic(topic, _client=shared_client)

            tasks = [_bounded_process(topic) for topic in viral_topics]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # [FIX-1] 실패한 토픽을 명시적으로 로깅 — 디버깅 블랙홀 제거
        output: Dict[str, EnrichedContext] = {}
        for topic, res in zip(viral_topics, results):
            if isinstance(res, EnrichedContext):
                output[topic] = res
            elif isinstance(res, Exception):
                logger.error("batch_process 예외 [%s]: %s", topic, res)
            else:
                # process_topic이 None을 반환한 경우
                logger.warning("batch_process 보강 실패 (None) [%s]", topic)

        return output
