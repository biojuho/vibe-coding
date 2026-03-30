"""Real-time trend monitoring: Google Trends + Naver DataLab.

Provides trending keywords that boost trend_relevance_score in content_intelligence.py.
All data sources are free. Results are cached with configurable TTL.
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# ── Topic → Google Trends 검색 키워드 매핑 ─────────────────────────────
_DEFAULT_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "연봉": ["직장인 연봉", "연봉 인상", "성과급"],
    "이직": ["이직", "퇴사", "면접"],
    "회사문화": ["직장 문화", "야근", "워라밸"],
    "상사": ["직장 상사", "팀장"],
    "복지": ["직장 복지", "재택근무"],
    "재테크": ["주식", "부동산", "재테크"],
    "IT": ["개발자", "AI", "코딩"],
    "부동산": ["아파트", "전세", "청약"],
    "건강": ["직장인 건강", "번아웃"],
    "자기계발": ["자격증", "사이드프로젝트"],
}

# Naver DataLab API 엔드포인트 (공식 Open API)
_NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
# Naver 실시간 급상승 검색어 (비공식, HTML 스크래핑)
_NAVER_REALTIME_URL = "https://datalab.naver.com/keyword/realtimeList.naver"


class TrendMonitor:
    """Google Trends + Naver DataLab 통합 트렌드 모니터.

    Args:
        config: ConfigManager 또는 dict-like 설정 객체.
    """

    def __init__(self, config: Any = None):
        self._config = config or {}
        self.google_enabled: bool = self._get("trends.google_enabled", True)
        self.naver_enabled: bool = self._get("trends.naver_enabled", True)
        self.spike_threshold: float = float(self._get("trends.spike_threshold", 80.0))
        self._cache_ttl: int = int(self._get("trends.cache_ttl_minutes", 10)) * 60
        self._topic_keywords: dict[str, list[str]] = self._get("trends.topic_keywords", _DEFAULT_TOPIC_KEYWORDS)

        # Naver API 인증 (선택적 — 없으면 Naver 비활성화)
        import os

        self._naver_client_id = os.environ.get("NAVER_CLIENT_ID", "")
        self._naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
        if self.naver_enabled and not self._naver_client_id:
            logger.info("NAVER_CLIENT_ID 미설정 — Naver DataLab API 비활성화 (Google Trends만 사용)")
            self.naver_enabled = False

        # 캐시
        self._cache: dict[str, float] = {}
        self._cache_ts: float = 0.0

        # ThreadPoolExecutor for sync pytrends calls
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trend")

    def _get(self, key: str, default: Any = None) -> Any:
        """config에서 dot-notation 키 조회."""
        if hasattr(self._config, "get"):
            val = self._config.get(key, None)
            if val is not None:
                return val
        return default

    # ── Google Trends ──────────────────────────────────────────────────

    def _fetch_google_trends_sync(self) -> dict[str, float]:
        """pytrends로 한국 실시간 트렌딩 검색어 가져오기 (동기 함수, 재시도 내장)."""
        import time as _time

        result: dict[str, float] = {}
        _MAX_RETRIES = 3

        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="ko", tz=540, timeout=(5, 15))

            # 1. 실시간 트렌딩 검색어 (한국) — 재시도 포함
            for attempt in range(_MAX_RETRIES):
                try:
                    trending_df = pytrends.trending_searches(pn="south_korea")
                    if trending_df is not None and not trending_df.empty:
                        for idx, row in trending_df.iterrows():
                            keyword = str(row[0]).strip()
                            if keyword:
                                score = max(10.0, 100.0 - idx * 5)
                                result[keyword] = score
                    break  # 성공
                except Exception as exc:
                    if attempt < _MAX_RETRIES - 1:
                        backoff = 2 ** (attempt + 1)
                        logger.debug(
                            "Google Trends trending_searches 재시도 %d/%d (%.0fs): %s",
                            attempt + 1,
                            _MAX_RETRIES,
                            backoff,
                            exc,
                        )
                        _time.sleep(backoff)
                    else:
                        logger.debug("Google Trends trending_searches 최종 실패: %s", exc)

            # 2. 토픽 키워드 관심도 (지난 7일)
            all_keywords = []
            for kw_list in self._topic_keywords.values():
                all_keywords.extend(kw_list)

            # pytrends는 한 번에 5개까지만 조회 가능
            for i in range(0, len(all_keywords), 5):
                batch = all_keywords[i : i + 5]
                for attempt in range(_MAX_RETRIES):
                    try:
                        pytrends.build_payload(batch, timeframe="now 7-d", geo="KR")
                        interest = pytrends.interest_over_time()
                        if interest is not None and not interest.empty:
                            for kw in batch:
                                if kw in interest.columns:
                                    avg_score = float(interest[kw].mean())
                                    result[kw] = max(result.get(kw, 0), avg_score)
                        break  # 성공
                    except Exception as exc:
                        if attempt < _MAX_RETRIES - 1:
                            backoff = 2 ** (attempt + 1)
                            logger.debug(
                                "Google Trends interest_over_time 재시도 %d/%d (%s): %s",
                                attempt + 1,
                                _MAX_RETRIES,
                                batch,
                                exc,
                            )
                            _time.sleep(backoff)
                        else:
                            logger.debug("Google Trends interest_over_time 최종 실패 (%s): %s", batch, exc)

        except ImportError:
            logger.warning("pytrends 패키지 미설치 — Google Trends 비활성화. pip install pytrends")
        except Exception as exc:
            logger.warning("Google Trends 조회 실패: %s", exc)

        return result

    async def fetch_google_trends(self) -> dict[str, float]:
        """Google Trends 데이터 비동기 조회 (스레드 위임)."""
        if not self.google_enabled:
            return {}
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._fetch_google_trends_sync),
                timeout=30,
            )
        except asyncio.TimeoutError:
            logger.warning("Google Trends 조회 타임아웃 (30초)")
            return {}
        except Exception as exc:
            logger.warning("Google Trends 비동기 조회 실패: %s", exc)
            return {}

    # ── Naver DataLab ──────────────────────────────────────────────────

    async def fetch_naver_trends(self) -> dict[str, float]:
        """Naver DataLab API로 토픽 키워드 트렌드 조회.

        Returns:
            keyword → relative interest (0-100).
        """
        if not self.naver_enabled:
            return {}

        result: dict[str, float] = {}
        all_keywords = []
        for kw_list in self._topic_keywords.values():
            all_keywords.extend(kw_list)

        # Naver DataLab API는 한 번에 5개 키워드 그룹까지
        import datetime as _dt

        end_date = _dt.date.today().isoformat()
        start_date = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()

        for i in range(0, len(all_keywords), 5):
            batch = all_keywords[i : i + 5]
            keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in batch]
            payload = {
                "startDate": start_date,
                "endDate": end_date,
                "timeUnit": "date",
                "keywordGroups": keyword_groups,
            }
            headers = {
                "X-Naver-Client-Id": self._naver_client_id,
                "X-Naver-Client-Secret": self._naver_client_secret,
                "Content-Type": "application/json",
            }
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(_NAVER_DATALAB_URL, json=payload, headers=headers) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            logger.debug("Naver DataLab API %d: %s", resp.status, text[:200])
                            continue
                        data = await resp.json()
                        for group in data.get("results", []):
                            kw = group.get("title", "")
                            ratios = [float(d.get("ratio", 0)) for d in group.get("data", [])]
                            if ratios:
                                avg = sum(ratios) / len(ratios)
                                result[kw] = max(result.get(kw, 0), avg)
            except Exception as exc:
                logger.debug("Naver DataLab API 조회 실패 (%s): %s", batch, exc)

        return result

    # ── 통합 API ───────────────────────────────────────────────────────

    async def get_trending_keywords(self) -> dict[str, float]:
        """Google + Naver 통합 트렌딩 키워드 (캐시 적용).

        Returns:
            keyword → score (0-100). 캐시 TTL 내에는 캐시된 결과 반환.
        """
        now = time.time()
        if self._cache and (now - self._cache_ts) < self._cache_ttl:
            return self._cache

        # 병렬 조회
        google_task = self.fetch_google_trends()
        naver_task = self.fetch_naver_trends()

        google_result, naver_result = await asyncio.gather(google_task, naver_task, return_exceptions=True)

        merged: dict[str, float] = {}
        if isinstance(google_result, dict):
            merged.update(google_result)
        else:
            logger.debug("Google Trends 결과 오류: %s", google_result)

        if isinstance(naver_result, dict):
            for kw, score in naver_result.items():
                merged[kw] = max(merged.get(kw, 0), score)
        else:
            logger.debug("Naver DataLab 결과 오류: %s", naver_result)

        self._cache = merged
        self._cache_ts = now

        if merged:
            top_5 = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:5]
            logger.info(
                "트렌드 키워드 %d개 수집 (Top5: %s)",
                len(merged),
                ", ".join(f"{k}({v:.0f})" for k, v in top_5),
            )

        return merged

    def calculate_trend_boost(self, title: str, content: str) -> float:
        """콘텐츠와 트렌딩 키워드의 오버랩 기반 부스트 점수 (0-30).

        캐시된 트렌딩 키워드와 제목+본문의 매칭 정도를 계산합니다.
        동기 함수 — 캐시가 비어있으면 0.0 반환.
        """
        if not self._cache:
            return 0.0

        text = f"{title} {content}".lower()
        total_boost = 0.0
        match_count = 0

        for keyword, score in self._cache.items():
            kw_lower = keyword.lower()
            if kw_lower in text:
                # 점수 비례 부스트 (0-100 → 0-10 기여)
                total_boost += score * 0.1
                match_count += 1

        if match_count == 0:
            return 0.0

        # 다중 매칭 보너스 (최대 30점)
        boost = min(30.0, total_boost + match_count * 2.0)
        return round(boost, 2)

    async def detect_spikes(self) -> list[dict[str, Any]]:
        """급상승 키워드 감지 (threshold 초과).

        Returns:
            [{"keyword": str, "score": float, "source": "google"|"naver"}]
        """
        keywords = await self.get_trending_keywords()
        spikes = []
        for keyword, score in keywords.items():
            if score >= self.spike_threshold:
                spikes.append(
                    {
                        "keyword": keyword,
                        "score": score,
                        "source": "combined",
                    }
                )

        if spikes:
            logger.info(
                "트렌드 스파이크 %d개 감지 (threshold=%.0f): %s",
                len(spikes),
                self.spike_threshold,
                ", ".join(s["keyword"] for s in spikes[:5]),
            )

        return spikes

    def match_topic_cluster(self, keyword: str) -> str | None:
        """트렌딩 키워드가 어떤 topic_cluster에 해당하는지 매칭.

        Returns:
            매칭된 topic_cluster 이름 또는 None.
        """
        kw_lower = keyword.lower()
        for topic, kw_list in self._topic_keywords.items():
            for tk in kw_list:
                if tk.lower() in kw_lower or kw_lower in tk.lower():
                    return topic
        return None
