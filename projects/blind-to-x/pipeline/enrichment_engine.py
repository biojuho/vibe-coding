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
from pydantic import BaseModel, Field

import httpx

logger = logging.getLogger(__name__)


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
        refs = "\n".join([f"- {url}" for url in self.global_references])
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
        # 타임아웃을 강제하여 파이프라인 전체 딜레이를 방지 (최대 5초)
        # [QA 수정] 15초 → 5초: 실패 시 파이프라인 블로킹 최소화
        self.timeout = httpx.Timeout(5.0)
        self.max_concurrency = max(1, int(max_concurrency))

    async def _fetch_exa_references(self, client: httpx.AsyncClient, topic: str) -> List[Dict]:
        """[내부] Exa API를 호출하여 고품질 레퍼런스 URL 및 스니펫을 검색합니다."""
        if not self.exa_api_key:
            logger.warning("EXA_API_KEY가 설정되지 않아 Exa 검색을 스킵합니다.")
            return []

        logger.info(f"[{topic}] 비동기 Exa API 검색 시작...")
        try:
            # Exa Search API Endpoint
            headers = {"x-api-key": self.exa_api_key, "Content-Type": "application/json"}
            payload = {"query": topic, "numResults": 3, "useAutoprompt": True}
            res = await client.post("https://api.exa.ai/search", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

            results = data.get("results", [])
            return [{"title": r.get("title", ""), "url": r.get("url", "")} for r in results]
        except Exception as e:
            logger.error(f"Exa API 검색 중 오류 발생: {e}")
            return []

    async def _fetch_perplexity_synthesis(self, client: httpx.AsyncClient, topic: str, references: List[Dict]) -> str:
        """[내부] Perplexity API에 검색된 레퍼런스를 던져 심도 있는 전문가 수준의 인사이트를 합성합니다."""
        if not self.perplexity_api_key:
            logger.warning("PERPLEXITY_API_KEY가 설정되지 않아 Perplexity 합성을 스킵합니다 (Fallback Mode).")
            # NOTE: sleep 제거 — 테스트 환경에서 불필요한 지연의 원인이었음 (T-BUG-SLOW-TEST)
            return f"{topic}에 대한 심층 인사이트를 분석 중입니다 (Fallback Mode)."

        logger.info(f"[{topic}] Perplexity API 컨텍스트 합성 시작...")

        # Build prompt from topic and references
        ref_text = "\n".join([f"- {r['title']} ({r['url']})" for r in references])
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
            headers = {"Authorization": f"Bearer {self.perplexity_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "sonar-pro",  # Perplexity's primary model
                "messages": [
                    {"role": "system", "content": "You are a top-tier C-level strategy analyst."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }

            res = await client.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

            # [QA 수정] 응답 형식 방어: choices가 비어있거나 키가 없을 경우 Fallback
            choices = data.get("choices", [])
            if not choices:
                logger.warning("Perplexity 응답에 choices가 없습니다. Fallback 반환.")
                return f"{topic}에 대한 심층 인사이트를 분석 중입니다 (Fallback Mode)."
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                logger.warning("Perplexity 응답 content가 비어 있습니다. Fallback 반환.")
                return f"{topic}에 대한 심층 인사이트를 분석 중입니다 (Fallback Mode)."
            return content
        except Exception as e:
            logger.error(f"Perplexity API 합성 중 오류 발생: {e}")
            return f"오류로 인해 {topic} 심도 분석에 실패했습니다."

    async def process_topic(self, viral_topic: str) -> Optional[EnrichedContext]:
        """
        [Public API]
        단일 트렌드 토픽을 입력받아 데이터를 보강시킨 후 반환합니다.
        성능 확보를 위해 비동기 I/O로 처리되며 실패 시 Graceful Degradation(원본만 반환)을 수행.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # 1단계: 고품질 출처 실시간 검색
                references = await self._fetch_exa_references(client, viral_topic)

                # 2단계: 검색 데이터를 기반으로 한 심층 분석 (RAG)
                insights = await self._fetch_perplexity_synthesis(client, viral_topic, references)

                # 3단계: 최종 데이터 취합 후 반환
                # Note: 실제로 감정(Sentiment)은 Perplexity에서 함께 추출 가능
                sentiment = "강한 찬반 양론 (Deep Insights 참조)"

                enriched = EnrichedContext(
                    original_topic=viral_topic,
                    deep_insights=insights,
                    global_references=[ref["url"] for ref in references],
                    sentiment_angle=sentiment,
                )
                logger.info(f"✅ Topic '{viral_topic}' 컨텍스트 보강 완료.")
                return enriched

            except Exception as e:
                logger.error(f"❌ 컨텍스트 보강 실패, 로컬 정보를 사용합니다. ({str(e)})")
                return None

    async def batch_process(self, viral_topics: List[str]) -> Dict[str, EnrichedContext]:
        """다수의 큐 항목을 병렬로 보강하여 파이프라인 병목(Bottleneck) 현상을 없앱니다."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _bounded_process(topic: str):
            async with semaphore:
                return await self.process_topic(topic)

        tasks = [_bounded_process(topic) for topic in viral_topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {topic: res for topic, res in zip(viral_topics, results) if isinstance(res, EnrichedContext)}
