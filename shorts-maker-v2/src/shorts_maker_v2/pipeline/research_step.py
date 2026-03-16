"""Research Step — 대본 생성 전 웹 검색 기반 팩트 수집.

Gemini Google Search Grounding을 사용하여 주제에 대한
검증 가능한 사실, 통계, 최신 정보를 수집합니다.

비용: $0 (Gemini 무료 tier)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from google.genai import types

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.providers.google_client import GoogleClient
from shorts_maker_v2.providers.llm_router import LLMRouter

logger = logging.getLogger(__name__)


@dataclass
class ResearchContext:
    """리서치 결과를 담는 컨테이너."""

    topic: str
    facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    key_data_points: list[str] = field(default_factory=list)
    summary: str = ""
    elapsed_sec: float = 0.0

    @property
    def has_content(self) -> bool:
        return bool(self.facts or self.key_data_points or self.summary)

    def to_prompt_block(self) -> str:
        """ScriptStep 프롬프트에 삽입할 리서치 블록 생성."""
        if not self.has_content:
            return ""

        lines = ["\n── Research Context (USE these verified facts in your script) ──"]
        if self.key_data_points:
            lines.append("Key Data Points:")
            for dp in self.key_data_points[:5]:
                lines.append(f"  • {dp}")
        if self.facts:
            lines.append("Verified Facts:")
            for fact in self.facts[:7]:
                lines.append(f"  • {fact}")
        if self.sources:
            lines.append(f"Sources: {', '.join(self.sources[:3])}")
        if self.summary:
            lines.append(f"Summary: {self.summary}")
        lines.append(
            "IMPORTANT: Prefer these researched facts over your parametric knowledge. "
            "Cite specific numbers and data points in the narration."
        )
        lines.append("── End Research Context ──\n")
        return "\n".join(lines)


_RESEARCH_SYSTEM_PROMPT = """\
You are a research assistant for a YouTube Shorts scriptwriter.
Given a topic, find and return VERIFIED, SPECIFIC facts that would make a compelling short video.

Focus on:
1. Specific numbers, statistics, dates (not vague claims)
2. Recent developments or surprising findings
3. Data that would make viewers stop scrolling ("hook-worthy" facts)
4. Cause-effect relationships that can be explained in 30-45 seconds

Output ONLY valid JSON:
{
  "facts": ["fact1", "fact2", ...],
  "key_data_points": ["stat or number with context", ...],
  "sources": ["source name 1", ...],
  "summary": "2-sentence overview of the most interesting angle"
}

Rules:
- Maximum 7 facts, 5 data points, 3 sources
- Each fact must be specific and verifiable (include numbers/dates when possible)
- Write facts in Korean (한국어) for direct use in the script
- If the topic is too niche or no reliable data exists, return fewer items rather than inventing
"""


class ResearchStep:
    """웹 검색 기반 리서치 스텝.

    Primary: Gemini + Google Search Grounding (무료)
    Fallback: LLM Router 지식 기반 리서치 (외부 검색 없음)
    """

    def __init__(
        self,
        config: AppConfig,
        google_client: GoogleClient | None = None,
        llm_router: LLMRouter | None = None,
    ):
        self.config = config
        self.google_client = google_client
        self.llm_router = llm_router

    def run(self, topic: str) -> ResearchContext:
        """주제에 대한 리서치 수행.

        Returns:
            ResearchContext with collected facts and data points.
        """
        start = time.monotonic()
        ctx = ResearchContext(topic=topic)

        # Primary: Gemini + Google Search Grounding
        if self.google_client:
            try:
                ctx = self._research_with_grounding(topic)
                ctx.elapsed_sec = round(time.monotonic() - start, 2)
                if ctx.has_content:
                    logger.info(
                        "[Research] grounding OK: %d facts, %d data_points (%.1fs)",
                        len(ctx.facts), len(ctx.key_data_points), ctx.elapsed_sec,
                    )
                    return ctx
            except Exception as exc:
                logger.warning("[Research] grounding failed: %s", exc)

        # Fallback: LLM Router (parametric knowledge only)
        if self.llm_router:
            try:
                ctx = self._research_with_llm(topic)
                ctx.elapsed_sec = round(time.monotonic() - start, 2)
                if ctx.has_content:
                    logger.info(
                        "[Research] LLM fallback OK: %d facts, %d data_points (%.1fs)",
                        len(ctx.facts), len(ctx.key_data_points), ctx.elapsed_sec,
                    )
                    return ctx
            except Exception as exc:
                logger.warning("[Research] LLM fallback failed: %s", exc)

        # 모두 실패 — 빈 컨텍스트 반환 (파이프라인 중단하지 않음)
        ctx.elapsed_sec = round(time.monotonic() - start, 2)
        logger.warning("[Research] all methods failed, proceeding without research context")
        return ctx

    def _research_with_grounding(self, topic: str) -> ResearchContext:
        """Gemini + Google Search Grounding으로 실시간 웹 검색."""
        user_prompt = (
            f"Topic: {topic}\n\n"
            "Search the web for the latest, most specific facts and statistics about this topic. "
            "Focus on numbers, dates, and surprising findings that would hook viewers."
        )

        response = self.google_client.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=_RESEARCH_SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
        )

        raw_text = response.text or ""
        data = self._parse_json(raw_text)

        # grounding metadata에서 소스 추출
        sources = data.get("sources", [])
        grounding_meta = getattr(response.candidates[0], "grounding_metadata", None)
        if grounding_meta and hasattr(grounding_meta, "grounding_chunks"):
            for chunk in (grounding_meta.grounding_chunks or []):
                web = getattr(chunk, "web", None)
                if web and hasattr(web, "title") and web.title:
                    source_name = web.title
                    if source_name not in sources:
                        sources.append(source_name)

        return ResearchContext(
            topic=topic,
            facts=data.get("facts", [])[:7],
            key_data_points=data.get("key_data_points", [])[:5],
            sources=sources[:5],
            summary=data.get("summary", ""),
        )

    def _research_with_llm(self, topic: str) -> ResearchContext:
        """LLM Router로 파라메트릭 지식 기반 리서치 (외부 검색 없음)."""
        user_prompt = (
            f"Topic: {topic}\n\n"
            "Based on your knowledge, provide the most specific and verifiable facts "
            "about this topic. Focus on well-known statistics and established findings."
        )

        result = self.llm_router.generate_json(
            system_prompt=_RESEARCH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        data = result if isinstance(result, dict) else {}
        return ResearchContext(
            topic=topic,
            facts=data.get("facts", [])[:7],
            key_data_points=data.get("key_data_points", [])[:5],
            sources=data.get("sources", [])[:3],
            summary=data.get("summary", ""),
        )

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """JSON 추출 (마크다운 코드블록 처리 포함)."""
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned.strip())
        except (json.JSONDecodeError, ValueError):
            return {}
