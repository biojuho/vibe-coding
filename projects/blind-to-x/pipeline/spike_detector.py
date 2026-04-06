"""실시간 바이럴 스파이크 감지기 (Viral Escalation Engine — Layer 1).

5분 간격으로 커뮤니티 인기글의 engagement velocity(좋아요/댓글 증가 가속도)를
모니터링하여, 골든타임(90분) 내 급상승 콘텐츠를 감지한다.

Architecture:
    SpikeDetector ──▶ EscalationQueue
    (이 모듈)            (escalation_queue.py)

Usage:
    detector = SpikeDetector(config_mgr)
    spikes = await detector.scan()
    # spikes: list[SpikeEvent] — velocity 임계치를 돌파한 이벤트들
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── 데이터 모델 ──────────────────────────────────────────────────────────────


@dataclass
class SpikeEvent:
    """에스컬레이션 큐에 전달되는 스파이크 이벤트."""

    url: str
    title: str
    source: str  # blind | ppomppu | fmkorea | jobplanet
    likes: int = 0
    comments: int = 0
    velocity_likes: float = 0.0  # 좋아요 증가율 (개/분)
    velocity_comments: float = 0.0  # 댓글 증가율 (개/분)
    velocity_score: float = 0.0  # 가중 합산 속도 점수
    detected_at: float = field(default_factory=time.time)
    category: str = "general"
    content_preview: str = ""  # 본문 첫 200자 (경량 초안용)
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def event_key(self) -> str:
        """중복 체크용 정규화 키 — URL에서 쿼리/프래그먼트 제거."""
        try:
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(self.url)
            clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))
            return clean
        except Exception:
            return self.url.split("?")[0].rstrip("/")


# ── 스냅샷 저장소 ────────────────────────────────────────────────────────────


class _EngagementSnapshot:
    """이전 스캔의 engagement를 기억하여 velocity를 계산하는 인메모리 저장소."""

    def __init__(self, max_entries: int = 500, ttl_seconds: int = 7200):
        self._store: dict[str, dict[str, Any]] = {}
        self._max_entries = max_entries
        self._ttl = ttl_seconds

    def record(self, key: str, likes: int, comments: int) -> dict[str, float] | None:
        """현재 값 기록 후, 이전 값과 비교하여 velocity 반환.

        Returns:
            None if no previous snapshot exists.
            {"velocity_likes": float, "velocity_comments": float, "elapsed_min": float}
        """
        now = time.time()
        self._evict_stale(now)

        prev = self._store.get(key)
        self._store[key] = {
            "likes": likes,
            "comments": comments,
            "ts": now,
        }

        if prev is None:
            return None

        elapsed_sec = now - prev["ts"]
        if elapsed_sec < 30:  # 너무 짧은 간격은 의미 없음
            return None

        elapsed_min = elapsed_sec / 60.0
        delta_likes = max(0, likes - prev["likes"])
        delta_comments = max(0, comments - prev["comments"])

        return {
            "velocity_likes": delta_likes / elapsed_min,
            "velocity_comments": delta_comments / elapsed_min,
            "elapsed_min": elapsed_min,
        }

    def _evict_stale(self, now: float) -> None:
        """TTL 초과 엔트리 정리 + 최대 크기 강제."""
        # TTL eviction
        stale_keys = [k for k, v in self._store.items() if now - v["ts"] > self._ttl]
        for k in stale_keys:
            del self._store[k]

        # Size cap (oldest first)
        if len(self._store) > self._max_entries:
            sorted_keys = sorted(
                self._store.keys(),
                key=lambda k: self._store[k]["ts"],
            )
            for k in sorted_keys[: len(self._store) - self._max_entries]:
                del self._store[k]


# ── 메인 디텍터 ──────────────────────────────────────────────────────────────


class SpikeDetector:
    """커뮤니티 게시글의 engagement velocity를 추적하여 스파이크를 감지.

    Args:
        config_mgr: ConfigManager 인스턴스.
        velocity_threshold: velocity_score 임계치 (기본 5.0 — 분당 좋아요+댓글×1.5 합산).
        min_absolute_likes: 최소 절대 좋아요 수 (노이즈 필터, 기본 20).
    """

    # 가중치: 댓글은 좋아요보다 더 강한 engagement 신호
    COMMENT_WEIGHT = 1.5

    def __init__(
        self,
        config_mgr: Any,
        velocity_threshold: float | None = None,
        min_absolute_likes: int | None = None,
    ):
        self.config = config_mgr
        self.velocity_threshold = velocity_threshold or float(config_mgr.get("escalation.velocity_threshold", 5.0))
        self.min_absolute_likes = min_absolute_likes or int(config_mgr.get("escalation.min_absolute_likes", 20))
        self._snapshots = _EngagementSnapshot(
            max_entries=int(config_mgr.get("escalation.snapshot_max_entries", 500)),
            ttl_seconds=int(config_mgr.get("escalation.snapshot_ttl_seconds", 7200)),
        )

    async def scan(self, candidates: list[dict[str, Any]] | None = None) -> list[SpikeEvent]:
        """후보 게시글 목록에서 스파이크를 감지.

        Args:
            candidates: 각 dict는 최소 {url, title, source, likes, comments}를 포함.
                        None이면 내부적으로 트렌드 모니터나 RSS에서 가져옴.

        Returns:
            velocity_threshold를 돌파한 SpikeEvent 리스트 (velocity_score 내림차순).
        """
        if candidates is None:
            candidates = await self._fetch_candidates()

        spikes: list[SpikeEvent] = []

        for item in candidates:
            url = item.get("url", "")
            if not url:
                continue

            likes = int(item.get("likes", 0) or 0)
            comments = int(item.get("comments", 0) or 0)

            # 절대 좋아요 수 미달이면 스킵 (노이즈)
            if likes < self.min_absolute_likes:
                continue

            # velocity 계산
            event_key = url.split("?")[0].rstrip("/")
            velocity = self._snapshots.record(event_key, likes, comments)

            if velocity is None:
                # 첫 스냅샷 — 다음 스캔에서 비교 가능
                continue

            v_likes = velocity["velocity_likes"]
            v_comments = velocity["velocity_comments"]
            v_score = v_likes + v_comments * self.COMMENT_WEIGHT

            if v_score >= self.velocity_threshold:
                spike = SpikeEvent(
                    url=url,
                    title=str(item.get("title", "")),
                    source=str(item.get("source", "unknown")),
                    likes=likes,
                    comments=comments,
                    velocity_likes=round(v_likes, 2),
                    velocity_comments=round(v_comments, 2),
                    velocity_score=round(v_score, 2),
                    category=str(item.get("category", "general")),
                    content_preview=str(item.get("content", ""))[:200],
                    raw_data=item,
                )
                spikes.append(spike)
                logger.info(
                    "🔥 SPIKE 감지: [%s] %s (v=%.2f, likes=%d, comments=%d)",
                    spike.source,
                    spike.title[:40],
                    v_score,
                    likes,
                    comments,
                )

        # velocity 높은 순으로 정렬
        spikes.sort(key=lambda s: s.velocity_score, reverse=True)
        return spikes

    async def _fetch_candidates(self) -> list[dict[str, Any]]:
        """내부 후보 수집 — TrendMonitor 연동 및 RSS 피드 확장.

        TrendMonitor의 트렌딩 아이템과 config에 정의된 RSS 피드(추후 구현)
        에서 초기 후보를 수집.
        """
        candidates = []

        # 1. TrendMonitor 연동
        try:
            from pipeline.trend_monitor import TrendMonitor

            monitor = TrendMonitor(self.config)

            # TrendMonitor가 제공하는 원시 데이터를 어떻게든 가져온다고 가정.
            # 지금은 mock 데이터를 추가해 dry-run이 동작함을 증명할 수 있다.
            keywords = await monitor.get_trending_keywords()
            logger.debug("SpikeDetector: %d trending keywords from TrendMonitor", len(keywords or []))

        except Exception as exc:
            logger.debug("SpikeDetector: TrendMonitor 연동 실패 (무시): %s", exc)

        # 2. RSS / 외부 API 수집 (config.yaml 활용)
        try:
            feeds = self.config.get("escalation.rss_feeds", [])
            for feed in feeds:
                # 여기서 aiohttp 또는 httpx로 비동기 피드 파싱
                # 본 POC에서는 생략.
                pass
        except Exception:
            pass

        # 3. Dry-run이나 E2E 테스트를 위해, 개발/테스트 환경이거나
        # candidates가 완전 비어있다면 가상의 스파이크 주입 (velocity 테스트용)
        # 프로덕션에서는 실제 RSS나 크롤러 DB에서 읽어옴.
        import os

        if os.environ.get("BTX_MOCK_SPIKE", "0") == "1":
            logger.info("SpikeDetector: MOCK 스파이크 주입 활성화 (BTX_MOCK_SPIKE=1)")
            import random

            candidates.append(
                {
                    "url": "https://www.teamblind.com/kr/s/MOCK_" + str(random.randint(1, 100)),
                    "title": f"MOCK: 폭등하는 블라인드 게시물 {random.randint(100, 999)}",
                    "source": "blind",
                    # 일부러 높게 줘서 velocity 발생
                    "likes": random.randint(50, 200),
                    "comments": random.randint(30, 80),
                    "content": "이것은 가짜 본문입니다. 에스컬레이션 큐 및 텔레그램 연동 E2E 테스트용.",
                    "category": "blabla",
                }
            )

        return candidates
