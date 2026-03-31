"""TrendDiscoveryStep — 채널별 트렌드 주제 자동 발굴.

3단계 소스 파이프라인 (비용 $0):
  1. YouTube RSS  — 경쟁 채널 최신 영상 제목 파싱
  2. Google Trends (pytrends) — 채널 키워드 관련 쿼리 수집
  3. LLM Brainstorm (fallback) — Gemini로 후보 30개 생성

Usage:
    step = TrendDiscoveryStep(config, llm_router=llm_router)
    candidates = step.run(channel_key="ai_tech", n=10)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.providers.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# YouTube RSS 채널 ID 매핑 (경쟁 채널 기준)
# ---------------------------------------------------------------------------
_CHANNEL_RSS_IDS: dict[str, list[str]] = {
    "ai_tech": [
        "UCupvZG-5ko_eiXAupbDfxWw",  # Google AI
        "UC0RhatS1pyxInC00YKjjBqQ",  # Marques Brownlee
    ],
    "psychology": [
        "UCfKUTn9O4ptjCCUn3ORIaTw",  # 심리학 채널 예시
    ],
    "history": [
        "UCpVm7bg6pXKo1Pr6k5kxG9A",  # National Geographic
    ],
    "space": [
        "UCLA_DiR1FfKNvjuUpBHmylQ",  # NASA
    ],
    "health": [
        "UCVHkiSFSvD0WFjhDpMpKijg",  # 건강 채널 예시
    ],
}

# ---------------------------------------------------------------------------
# 채널별 Google Trends 시드 키워드
# ---------------------------------------------------------------------------
_CHANNEL_TREND_SEEDS: dict[str, list[str]] = {
    "ai_tech": ["AI", "ChatGPT", "Claude", "Gemini", "딥러닝", "바이브코딩"],
    "psychology": ["인지 부조화", "자존감", "번아웃", "애착 유형", "마음챙김"],
    "history": ["한국 역사", "고대 이집트", "로마 제국", "역사 미스터리"],
    "space": ["블랙홀", "외계 생명체", "제임스 웹", "화성", "빅뱅"],
    "health": ["다이어트", "수면", "면역력", "당뇨", "스트레스"],
}


@dataclass
class TrendCandidate:
    """트렌드 주제 후보 단일 항목."""

    keyword: str               # 유저가 파이프라인에 넣을 주제 키워드
    source: str                # "youtube_rss" | "google_trends" | "llm_brainstorm"
    score: float               # 트렌드 강도 0.0-1.0
    channel: str               # ai_tech | psychology | history | space | health
    raw_title: str = ""        # YouTube RSS일 경우 원본 제목
    related_queries: list[str] = field(default_factory=list)  # Google Trends 관련 쿼리


class TrendDiscoveryStep:
    """채널별 트렌드 후보 자동 수집.

    Primary:   YouTube RSS 파싱 (httpx, 비용 $0)
    Secondary: Google Trends pytrends (비용 $0)
    Fallback:  LLM Brainstorm (Gemini/Claude)
    """

    _LLM_BRAINSTORM_SYSTEM = """\
You are a YouTube Shorts topic strategist for Korean content channels.
Given a channel category, generate trending topic ideas that would perform well as 30-45 second shorts.

Focus on:
- Topics with Cognitive Dissonance hook potential ("예상과 반대되는 결과 + 이유")
- Recent events or surprising findings (last 3-6 months)
- Specific, concrete topics (not vague categories)

Output ONLY valid JSON:
{
  "candidates": [
    {"keyword": "Korean topic keyword", "rationale": "why this is trending", "score": 0.85},
    ...
  ]
}

Rules:
- Generate exactly {n} candidates
- keyword: 한국어로 5-20자 (파이프라인 topic 입력으로 바로 사용 가능)
- score: 0.0-1.0 (예상 바이럴 강도)
- rationale: 한 줄 이유 (한국어)
- Do NOT generate vague topics like "AI의 미래" — be specific: "Claude가 승인창 없앤 진짜 이유"
"""

    def __init__(
        self,
        config: AppConfig,
        llm_router: LLMRouter | None = None,
    ):
        self.config = config
        self.llm_router = llm_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, channel_key: str, n: int = 10) -> list[TrendCandidate]:
        """채널별 트렌드 후보 수집.

        Args:
            channel_key: "ai_tech" | "psychology" | "history" | "space" | "health"
            n: 반환할 최대 후보 수

        Returns:
            score 내림차순 정렬된 TrendCandidate 리스트
        """
        start = time.monotonic()
        candidates: list[TrendCandidate] = []

        # 1. YouTube RSS
        try:
            rss_candidates = self._from_youtube_rss(channel_key)
            candidates.extend(rss_candidates)
            logger.info("[TrendDiscovery] RSS: %d candidates", len(rss_candidates))
        except Exception as exc:
            logger.warning("[TrendDiscovery] RSS failed: %s", exc)

        # 2. Google Trends (선택적 의존성)
        if len(candidates) < n:
            try:
                trend_candidates = self._from_google_trends(channel_key)
                candidates.extend(trend_candidates)
                logger.info("[TrendDiscovery] Google Trends: %d candidates", len(trend_candidates))
            except Exception as exc:
                logger.warning("[TrendDiscovery] Google Trends failed (pytrends 미설치?): %s", exc)

        # 3. LLM Brainstorm (fallback / 보충)
        if len(candidates) < n and self.llm_router:
            try:
                needed = n - len(candidates)
                llm_candidates = self._from_llm_brainstorm(channel_key, n=needed)
                candidates.extend(llm_candidates)
                logger.info("[TrendDiscovery] LLM brainstorm: %d candidates", len(llm_candidates))
            except Exception as exc:
                logger.warning("[TrendDiscovery] LLM brainstorm failed: %s", exc)

        # 중복 제거 + 점수 정렬
        seen: set[str] = set()
        unique: list[TrendCandidate] = []
        for c in sorted(candidates, key=lambda x: x.score, reverse=True):
            key = c.keyword.strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(c)

        result = unique[:n]
        elapsed = round(time.monotonic() - start, 2)
        logger.info(
            "[TrendDiscovery] done: %d candidates in %.1fs (channel=%s)",
            len(result),
            elapsed,
            channel_key,
        )
        return result

    # ------------------------------------------------------------------
    # Source 1: YouTube RSS
    # ------------------------------------------------------------------

    def _from_youtube_rss(self, channel_key: str) -> list[TrendCandidate]:
        """YouTube RSS 피드에서 최신 영상 제목 추출."""
        try:
            import httpx  # 선택적 의존성
        except ImportError as err:
            raise ImportError("httpx not installed. Run: pip install httpx") from err

        channel_ids = _CHANNEL_RSS_IDS.get(channel_key, [])
        if not channel_ids:
            return []

        candidates: list[TrendCandidate] = []
        for channel_id in channel_ids:
            url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            try:
                resp = httpx.get(url, timeout=10.0, follow_redirects=True)
                resp.raise_for_status()
                entries = self._parse_youtube_rss(resp.text)
                for i, entry in enumerate(entries[:10]):
                    title = entry.get("title", "").strip()
                    if not title:
                        continue
                    # 최신 영상일수록 점수 높음 (위치 기반 decay)
                    score = max(0.3, 1.0 - i * 0.07)
                    candidates.append(
                        TrendCandidate(
                            keyword=title,
                            source="youtube_rss",
                            score=round(score, 2),
                            channel=channel_key,
                            raw_title=title,
                        )
                    )
            except Exception as exc:
                logger.debug("[TrendDiscovery] RSS fetch failed for %s: %s", channel_id, exc)

        return candidates

    @staticmethod
    def _parse_youtube_rss(xml_text: str) -> list[dict[str, str]]:
        """YouTube Atom RSS XML 파싱 → [{title, link}, ...]"""
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        entries: list[dict[str, str]] = []
        try:
            try:
                from defusedxml import ElementTree as ET
            except ImportError:
                import xml.etree.ElementTree as ET  # noqa: S314 — defusedxml tried first; fallback parses trusted YouTube RSS only
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                title = title_el.text if title_el is not None else ""
                link = link_el.get("href", "") if link_el is not None else ""
                if title:
                    entries.append({"title": title, "link": link})
        except Exception as exc:
            logger.debug("[TrendDiscovery] RSS parse error: %s", exc)
        return entries

    # ------------------------------------------------------------------
    # Source 2: Google Trends
    # ------------------------------------------------------------------

    def _from_google_trends(self, channel_key: str) -> list[TrendCandidate]:
        """pytrends로 채널 시드 키워드 관련 쿼리 수집."""
        try:
            from pytrends.request import TrendReq  # 선택적 의존성
        except ImportError as err:
            raise ImportError("pytrends not installed. Run: pip install pytrends") from err

        seeds = _CHANNEL_TREND_SEEDS.get(channel_key, [])
        if not seeds:
            return []

        pytrends = TrendReq(hl="ko", tz=540)  # Korean, KST
        candidates: list[TrendCandidate] = []

        # 최대 3개 시드만 (pytrends 제한: 최대 5개 동시)
        for seed in seeds[:3]:
            try:
                pytrends.build_payload([seed], timeframe="now 7-d", geo="KR")
                related = pytrends.related_queries()
                top_queries = related.get(seed, {}).get("top")
                if top_queries is not None and not top_queries.empty:
                    for _, row in top_queries.iterrows():
                        query = str(row.get("query", "")).strip()
                        value = float(row.get("value", 50))
                        if query:
                            candidates.append(
                                TrendCandidate(
                                    keyword=query,
                                    source="google_trends",
                                    score=round(min(value / 100.0, 1.0), 2),
                                    channel=channel_key,
                                )
                            )
            except Exception as exc:
                logger.debug("[TrendDiscovery] pytrends failed for seed '%s': %s", seed, exc)

        return candidates

    # ------------------------------------------------------------------
    # Source 3: LLM Brainstorm (Fallback)
    # ------------------------------------------------------------------

    def _from_llm_brainstorm(
        self, channel_key: str, n: int = 10
    ) -> list[TrendCandidate]:
        """LLM으로 채널별 트렌드 후보 생성 (외부 API 미사용 fallback)."""
        if not self.llm_router:
            return []

        system_prompt = self._LLM_BRAINSTORM_SYSTEM.replace("{n}", str(n))
        channel_name_map = {
            "ai_tech": "AI/기술 (한국어 YouTube Shorts, 20-40대 테크 종사자 타겟)",
            "psychology": "심리학 (한국어 YouTube Shorts, 20-30대 자기계발 관심층 타겟)",
            "history": "역사/고고학 (한국어 YouTube Shorts, 반전 있는 역사 이야기)",
            "space": "우주/천문학 (한국어 YouTube Shorts, 경이로움과 스케일 강조)",
            "health": "의학/건강 (한국어 YouTube Shorts, 30-60대 건강 관심층 타겟)",
        }
        channel_desc = channel_name_map.get(channel_key, channel_key)

        user_prompt = (
            f"채널 카테고리: {channel_desc}\n"
            f"Generate {n} trending topic candidates for this channel.\n"
            "Focus on Cognitive Dissonance hooks: '예상과 반대되는 결과 + 이유' 패턴.\n"
            "Like: 'AI 도입했더니 오히려 야근이 늘어난 이유', 'Claude가 승인창 없앤 진짜 이유'"
        )

        try:
            result = self.llm_router.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.85,  # 창의성 높임
            )
            if not isinstance(result, dict):
                return []

            raw_list: list[Any] = result.get("candidates", [])
            candidates: list[TrendCandidate] = []
            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                kw = str(item.get("keyword", "")).strip()
                if not kw:
                    continue
                candidates.append(
                    TrendCandidate(
                        keyword=kw,
                        source="llm_brainstorm",
                        score=float(item.get("score", 0.5)),
                        channel=channel_key,
                    )
                )
            return candidates[:n]

        except Exception as exc:
            logger.warning("[TrendDiscovery] LLM brainstorm error: %s", exc)
            return []
