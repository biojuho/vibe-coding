"""performance_prompt_adapter.py
────────────────────────────────────────────────────────────────────────────
Performance-Aware Draft Rewriter — 성과 데이터 → 프롬프트 자동 반영 브릿지

아키텍처 위치:
    x_analytics.py (SQLite tweet_snapshots)
    performance_tracker.py (JSONL performance_records)
          ↓ (두 소스 데이터 정규화)
    PerformancePromptAdapter          ← 이 모듈
          ↓ (강화된 시스템 프롬프트 컨텍스트)
    express_draft.py / draft_prompts.py

설계 원칙:
    - 성과 데이터가 없어도 기존 프롬프트 그대로 동작 (fail-open)
    - PerformanceInsight 캐시 TTL 기반 (기본 6시간) — LLM 비용 최소화
    - 소스(blind/ppomppu/fmkorea)별로 독립 학습 — 크로스오염 방지
    - 모든 외부 I/O는 동기 래핑 → async 인터페이스로 노출

필요 라이브러리 (모두 stdlib + 기존 pipeline 모듈):
    - dataclasses, statistics, logging, datetime (stdlib)
    - pipeline.x_analytics (get_tracked_tweets, get_latest_snapshot)
    - pipeline.performance_tracker (PerformanceTracker, PerformanceRecord)
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────────────────────────

DEFAULT_CACHE_TTL_SECONDS: int = 6 * 60 * 60  # 6시간
MIN_SAMPLE_SIZE: int = 5  # 최소 샘플 수
TOP_N_PATTERNS: int = 3  # 프롬프트 인젝션 훅 패턴 수
PERFORMANCE_LOOKBACK_DAYS: int = 14  # 성과 학습 기간 (일)

# PerformanceTracker platform 키 → source 키 매핑
_PLATFORM_TO_SOURCE: dict[str, str] = {
    "twitter": "blind",  # X는 다중 소스에서 발행되므로 twitter 기록 전부 학습
    "threads": "blind",
}


# ── 데이터 모델 ───────────────────────────────────────────────────────────


@dataclass
class HookPattern:
    """성과가 높은 훅 패턴 하나.

    Attributes:
        pattern:              훅 텍스트 패턴 (앞 50자)
        avg_impression_rate:  평균 impression-to-follower 비율
        avg_engagement_rate:  평균 인게이지먼트 비율
        sample_count:         이 패턴으로 발행된 게시물 수
        source:               원본 커뮤니티 키
    """

    pattern: str
    avg_impression_rate: float
    avg_engagement_rate: float
    sample_count: int
    source: str


@dataclass
class PerformanceInsight:
    """프롬프트에 주입될 성과 인사이트 스냅샷. 소스별로 독립 캐시."""

    source: str
    top_hooks: list[HookPattern] = field(default_factory=list)
    best_posting_hours: list[int] = field(default_factory=list)  # 0-23 시
    avg_optimal_length: int = 280
    high_ctr_tone: str = "informative"
    fetched_at: float = field(default_factory=time.time)

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.fetched_at) > DEFAULT_CACHE_TTL_SECONDS

    @property
    def has_data(self) -> bool:
        return bool(self.top_hooks or self.best_posting_hours)

    def to_prompt_context(self) -> str:
        """인사이트를 LLM 시스템 프롬프트에 삽입할 텍스트 블록으로 변환.

        데이터가 없으면 빈 문자열 반환 → 기존 프롬프트 그대로.
        """
        if not self.has_data:
            return ""

        lines = [
            f"\n[성과 기반 가이드 — 최근 {PERFORMANCE_LOOKBACK_DAYS}일 실적 학습]",
            f"소스: {self.source} | 분석 기간: {PERFORMANCE_LOOKBACK_DAYS}일",
        ]

        if self.top_hooks:
            lines.append(f"▶ 고성과 훅 패턴 TOP {len(self.top_hooks)} (높은 순):")
            for i, hook in enumerate(self.top_hooks, 1):
                lines.append(
                    f"  {i}. '{hook.pattern}' "
                    f"(impression_rate {hook.avg_impression_rate:.1%}, "
                    f"engagement {hook.avg_engagement_rate:.1%}, n={hook.sample_count})"
                )

        if self.best_posting_hours:
            hours_str = ", ".join(f"{h:02d}시" for h in self.best_posting_hours[:3])
            lines.append(f"▶ 최적 발행 시간대: {hours_str}")

        lines.append(f"▶ 고성과 게시물 평균 길이: {self.avg_optimal_length}자 내외")
        lines.append(f"▶ 지배적 고성과 톤: {self.high_ctr_tone}")
        lines.append("위 패턴을 초안에 자연스럽게 반영하되, 강제 적용하지 말 것.")

        return "\n".join(lines)


# ── 내부 정규화 함수 ──────────────────────────────────────────────────────


def _normalize_x_analytics_row(tweet: dict, snapshot: dict | None) -> dict | None:
    """x_analytics tracked_tweet + snapshot → 공통 post dict.

    Returns None if snapshot is missing (no metrics yet).
    """
    if snapshot is None:
        return None

    impressions = snapshot.get("impressions", 0) or 0
    likes = snapshot.get("likes", 0) or 0
    retweets = snapshot.get("retweets", 0) or 0
    replies = snapshot.get("replies", 0) or 0

    # impression_rate: impressions per 1000 followers — 여기선 절댓값으로 근사
    # engagement_rate: (likes + retweets + replies) / max(impressions, 1)
    impression_rate = impressions / 1000.0  # 정규화 기준 (팔로워 데이터 없으므로 /1000 근사)
    engagement_rate = (likes + retweets + replies) / max(impressions, 1)

    # published_hour 추출
    published_hour: int | None = None
    pub_str = tweet.get("published_at", "")
    if pub_str:
        try:
            pub_dt = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S")
            published_hour = pub_dt.hour
        except (ValueError, IndexError):
            pass

    return {
        "content": tweet.get("text_preview", ""),
        "topic": tweet.get("topic", ""),
        "channel": tweet.get("channel", ""),
        "impression_rate": impression_rate,
        "engagement_rate": engagement_rate,
        "published_hour": published_hour,
        "source": "x_analytics",
    }


def _normalize_performance_record(rec: Any) -> dict:
    """PerformanceRecord → 공통 post dict."""
    metrics = getattr(rec, "metrics", {}) or {}
    platform = getattr(rec, "platform", "")
    engagement_score = getattr(rec, "engagement_score", 0.0) or 0.0

    # impression_rate 근사: twitter impressions / 1000, threads reach / 1000
    impressions = metrics.get("impressions", 0) or metrics.get("reach", 0) or 0
    impression_rate = impressions / 1000.0
    engagement_rate = engagement_score / max(impressions, 1)

    # published_hour: recorded_at에서 추출
    published_hour: int | None = None
    recorded_at = getattr(rec, "recorded_at", None)
    if recorded_at:
        try:
            dt = datetime.fromisoformat(str(recorded_at)[:19])
            published_hour = dt.hour
        except (ValueError, IndexError):
            pass

    # content 필드에 임의 텍스트 사용 → JSONL에는 content 없으므로 topic+platform 조합
    content_proxy = f"{getattr(rec, 'topic_cluster', '')} {platform}".strip()

    return {
        "content": content_proxy,
        "topic": getattr(rec, "topic_cluster", ""),
        "channel": platform,
        "impression_rate": impression_rate,
        "engagement_rate": engagement_rate,
        "published_hour": published_hour,
        "source": "performance_tracker",
    }


# ── 핵심 어댑터 클래스 ────────────────────────────────────────────────────


class PerformancePromptAdapter:
    """성과 데이터를 수집해 프롬프트 컨텍스트를 자동 강화하는 브릿지.

    사용 예시 (express_draft.py / draft_prompts.py):
    ──────────────────────────────────────────────
        adapter = get_performance_prompt_adapter()
        insight = await adapter.get_insight(source="blind")
        extra_ctx = insight.to_prompt_context()
        system_prompt = BASE_PROMPT + ("\\n\\n" + extra_ctx if extra_ctx else "")
    """

    def __init__(
        self,
        cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
        performance_data_dir: str | None = None,
    ) -> None:
        self._cache: dict[str, PerformanceInsight] = {}
        self._cache_ttl = cache_ttl
        self._performance_data_dir = performance_data_dir  # PerformanceTracker override

    # ── 공개 인터페이스 ────────────────────────────────────────────────

    async def get_insight(self, source: str = "blind") -> PerformanceInsight:
        """소스별 성과 인사이트 반환. 캐시가 신선하면 캐시 사용.

        Args:
            source: 원본 커뮤니티 키 (예: "blind", "ppomppu")

        Returns:
            PerformanceInsight — 데이터 없거나 오류 시 빈 인사이트 (fail-open)
        """
        cached = self._cache.get(source)
        if cached and not cached.is_stale:
            logger.debug("PerformanceInsight cache hit: source=%s", source)
            return cached

        try:
            insight = await asyncio.get_event_loop().run_in_executor(None, self._fetch_insight_sync, source)
        except Exception:
            logger.exception(
                "get_insight: executor level exception — source=%s, returning empty insight",
                source,
            )
            insight = PerformanceInsight(source=source)
        self._cache[source] = insight
        return insight

    def invalidate_cache(self, source: str | None = None) -> None:
        """캐시 강제 무효화. source가 None이면 전체 초기화."""
        if source:
            self._cache.pop(source, None)
        else:
            self._cache.clear()

    # ── 동기 내부 구현 (run_in_executor용) ───────────────────────────

    def _fetch_insight_sync(self, source: str) -> PerformanceInsight:
        """동기 방식으로 성과 데이터를 모아 PerformanceInsight 빌드."""
        try:
            posts = self._load_recent_posts_sync(source)
            if len(posts) < MIN_SAMPLE_SIZE:
                logger.info(
                    "Not enough data for insight: source=%s, n=%d (min=%d)",
                    source,
                    len(posts),
                    MIN_SAMPLE_SIZE,
                )
                return PerformanceInsight(source=source)

            top_hooks = self._extract_top_hooks(posts, source)
            best_hours = self._extract_best_hours(posts)
            avg_length = self._compute_optimal_length(posts)
            dominant_tone = self._infer_dominant_tone(posts)

            insight = PerformanceInsight(
                source=source,
                top_hooks=top_hooks,
                best_posting_hours=best_hours,
                avg_optimal_length=avg_length,
                high_ctr_tone=dominant_tone,
            )
            logger.info(
                "PerformanceInsight built: source=%s hooks=%d hours=%s tone=%s n=%d",
                source,
                len(top_hooks),
                best_hours[:3],
                dominant_tone,
                len(posts),
            )
            return insight

        except Exception:
            logger.exception(
                "Failed to build PerformanceInsight for source=%s — using empty insight",
                source,
            )
            return PerformanceInsight(source=source)

    def _load_recent_posts_sync(self, source: str) -> list[dict]:
        """XAnalytics + PerformanceTracker에서 최근 N일 데이터를 통합 로드.

        두 소스에서 공통 dict 포맷으로 정규화 후 합칩니다.
        """
        posts: list[dict] = []
        cutoff = datetime.now() - timedelta(days=PERFORMANCE_LOOKBACK_DAYS)

        # ── 소스 A: x_analytics SQLite DB ─────────────────────────────
        try:
            from pipeline.x_analytics import get_tracked_tweets, get_latest_snapshot

            tweets = get_tracked_tweets(limit=200)
            for tw in tweets:
                # 기간 필터
                pub_str = tw.get("published_at", "")
                if pub_str:
                    try:
                        pub_dt = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S")
                        if pub_dt < cutoff:
                            continue
                    except (ValueError, IndexError):
                        pass

                snapshot = get_latest_snapshot(tw["id"])
                normalized = _normalize_x_analytics_row(tw, snapshot)
                if normalized:
                    posts.append(normalized)
        except Exception as exc:
            logger.debug("x_analytics load failed (ignored): %s", exc)

        # ── 소스 B: performance_tracker JSONL ─────────────────────────
        try:
            from pipeline.performance_tracker import PerformanceTracker

            tracker = PerformanceTracker(data_dir=self._performance_data_dir)
            # twitter + threads 플랫폼 모두 수집 (소스 불문)
            for platform in ("twitter", "threads"):
                records = tracker.get_records(platform=platform, days=PERFORMANCE_LOOKBACK_DAYS)
                for rec in records:
                    posts.append(_normalize_performance_record(rec))
        except Exception as exc:
            logger.debug("performance_tracker load failed (ignored): %s", exc)

        logger.debug("_load_recent_posts_sync: source=%s total_posts=%d", source, len(posts))
        return posts

    # ── 분석 헬퍼 ──────────────────────────────────────────────────────

    def _extract_top_hooks(self, posts: list[dict], source: str) -> list[HookPattern]:
        """impression_rate 상위 게시물에서 훅 패턴 TOP N 추출."""
        if not posts:
            return []

        # impression_rate 내림차순 정렬
        sorted_posts = sorted(posts, key=lambda p: p.get("impression_rate", 0.0), reverse=True)
        top_posts = sorted_posts[: TOP_N_PATTERNS * 2]  # 여유 있게 수집 후 dedup

        patterns: list[HookPattern] = []
        seen_patterns: set[str] = set()

        for post in top_posts:
            content = (post.get("content") or "").strip()
            if not content:
                continue
            # 첫 50자 → 훅 패턴 대표값
            first_chunk = content[:50].split("\n")[0].strip()
            if not first_chunk or first_chunk in seen_patterns:
                continue
            seen_patterns.add(first_chunk)
            patterns.append(
                HookPattern(
                    pattern=first_chunk,
                    avg_impression_rate=float(post.get("impression_rate", 0.0)),
                    avg_engagement_rate=float(post.get("engagement_rate", 0.0)),
                    sample_count=1,
                    source=source,
                )
            )
            if len(patterns) >= TOP_N_PATTERNS:
                break

        return patterns

    def _extract_best_hours(self, posts: list[dict]) -> list[int]:
        """인게이지먼트 기준 최적 발행 시간대 추출."""
        hour_scores: dict[int, list[float]] = {}
        for post in posts:
            hour = post.get("published_hour")
            eng = float(post.get("engagement_rate", 0.0))
            if hour is not None and 0 <= int(hour) < 24:
                hour_scores.setdefault(int(hour), []).append(eng)

        if not hour_scores:
            return []

        avg_by_hour = {h: statistics.mean(scores) for h, scores in hour_scores.items() if scores}
        return sorted(avg_by_hour, key=lambda h: avg_by_hour[h], reverse=True)[:5]

    def _compute_optimal_length(self, posts: list[dict]) -> int:
        """impression_rate 상위 33% 게시물의 평균 본문 길이."""
        if not posts:
            return 280

        rates = [p.get("impression_rate", 0.0) for p in posts]
        try:
            threshold = statistics.quantiles(rates, n=3)[-1]
        except statistics.StatisticsError:
            threshold = 0.0

        high_perf = [p for p in posts if p.get("impression_rate", 0.0) >= threshold]
        lengths = [len(p.get("content") or "") for p in high_perf if p.get("content")]
        if not lengths:
            return 280
        avg = int(statistics.mean(lengths))
        # X 최대 280자, Threads 500자 범위로 클램핑
        return max(50, min(avg, 500))

    def _infer_dominant_tone(self, posts: list[dict]) -> str:
        """상위 33% 고성과 게시물에서 지배적 감성 톤 추론."""
        tone_keywords: dict[str, list[str]] = {
            "shocking": ["충격", "경악", "믿기지", "실화", "OMG", "대박"],
            "humorous": ["ㅋㅋ", "웃음", "웃긴", "개웃김", "ㅎㅎ", "빵터"],
            "empathetic": ["공감", "위로", "힘내", "같이", "우리", "맞아"],
            "informative": ["정보", "방법", "팁", "가이드", "정리", "알아두면"],
        }

        tone_counts: dict[str, int] = {t: 0 for t in tone_keywords}
        top_count = max(1, len(posts) // 3)
        high_perf = sorted(posts, key=lambda p: p.get("impression_rate", 0.0), reverse=True)[:top_count]

        for post in high_perf:
            content = post.get("content") or ""
            for tone, keywords in tone_keywords.items():
                if any(kw in content for kw in keywords):
                    tone_counts[tone] += 1

        dominant = max(tone_counts, key=lambda t: tone_counts[t])
        return dominant if tone_counts[dominant] > 0 else "informative"


# ── 팩토리 함수 (DI 진입점) ───────────────────────────────────────────────

_adapter_instance: PerformancePromptAdapter | None = None


def get_performance_prompt_adapter(
    performance_data_dir: str | None = None,
    _reset: bool = False,
) -> PerformancePromptAdapter:
    """어댑터 싱글톤 팩토리.

    express_draft.py, draft_prompts.py에서 호출:
        adapter = get_performance_prompt_adapter()
        insight = await adapter.get_insight(source=event.source)
        extra_ctx = insight.to_prompt_context()

    Args:
        performance_data_dir: PerformanceTracker 데이터 디렉터리 오버라이드 (주로 테스트용).
        _reset: True이면 싱글톤 강제 재생성 (테스트 격리용).
    """
    global _adapter_instance
    if _reset or _adapter_instance is None:
        _adapter_instance = PerformancePromptAdapter(
            performance_data_dir=performance_data_dir,
        )
    return _adapter_instance
