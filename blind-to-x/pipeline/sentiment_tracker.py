"""Sentiment trend tracker -- detects rising emotion keywords over time.

Stores emotion signals in SQLite, computes rolling trends, and surfaces
"hot emotion keywords" that are spiking compared to their baseline.
Integrates with the existing ContentProfile emotion_axis classification.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "sentiment_tracker.db")

_KST = timezone(timedelta(hours=9))


@dataclass
class EmotionTrend:
    """A single emotion keyword trend."""

    keyword: str
    current_count: int
    baseline_count: float
    spike_ratio: float  # current / baseline (>1.0 = trending up)
    direction: str  # "rising" | "stable" | "falling"


@dataclass
class SentimentSnapshot:
    """Aggregated sentiment state at a point in time."""

    dominant_emotion: str
    top_emotions: list[tuple[str, int]]  # (emotion, count) sorted desc
    trending_keywords: list[EmotionTrend]
    timestamp: datetime
    total_posts: int


# ── Emotion keyword lexicon (Korean workplace context) ─────────────────
EMOTION_LEXICON: dict[str, list[str]] = {
    "분노": ["빡치", "열받", "화나", "분노", "짜증", "억까", "어이없", "미친", "빡세"],
    "허탈": ["허탈", "허무", "현타", "공허", "멘붕", "한심", "황당", "어처구니"],
    "공감": ["공감", "이해", "맞말", "다들", "나만", "저만", "인정", "격공", "팩트"],
    "웃김": ["웃김", "개웃", "현웃", "웃겨", "유머", "짤", "ㅋㅋ", "웃프", "코미디"],
    "경악": ["충격", "미쳤", "실화", "레전드", "소름", "헐", "대박", "경악", "ㄷㄷ"],
    "현타": ["현타", "퇴사각", "퇴사 마렵", "현실", "지친", "번아웃", "힘들", "피곤"],
    "불안": ["불안", "걱정", "고민", "두렵", "막막", "초조", "스트레스", "압박"],
    "희망": ["희망", "기대", "설렘", "좋겠", "드디어", "성장", "합격", "축하"],
    "분석": ["분석", "정리", "비교", "종합", "트렌드", "팁", "방법", "가이드"],
    "연대": ["응원", "힘내", "파이팅", "함께", "우리", "같이", "동료", "선배"],
}


class SentimentTracker:
    """Tracks emotion keywords over time in SQLite and detects trends."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or _DB_PATH
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS emotion_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        source TEXT DEFAULT '',
                        emotion TEXT NOT NULL,
                        keywords TEXT DEFAULT '',
                        score REAL DEFAULT 0.0,
                        created_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_emotion_created
                    ON emotion_signals(emotion, created_at)
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS keyword_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT NOT NULL,
                        emotion TEXT NOT NULL,
                        url TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_kw_created
                    ON keyword_signals(keyword, created_at)
                """)
                conn.commit()
            finally:
                conn.close()

    def record(self, url: str, title: str, content: str, emotion_axis: str, source: str = "") -> dict[str, int]:
        """Record emotion signals from a post. Returns matched keyword counts."""
        text = f"{title} {content}".lower()
        matched: dict[str, int] = {}

        for emotion, keywords in EMOTION_LEXICON.items():
            for kw in keywords:
                if kw in text:
                    matched[kw] = matched.get(kw, 0) + text.count(kw)

        now = datetime.now(_KST).strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            conn = self._get_conn()
            try:
                # Record overall emotion
                matched_kws = ",".join(sorted(matched.keys()))
                conn.execute(
                    "INSERT INTO emotion_signals (url, source, emotion, keywords, score, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (url, source, emotion_axis, matched_kws, sum(matched.values()), now),
                )
                # Record individual keywords
                for kw, count in matched.items():
                    emotion_label = self._keyword_to_emotion(kw)
                    for _ in range(min(count, 5)):  # cap at 5 per keyword per post
                        conn.execute(
                            "INSERT INTO keyword_signals (keyword, emotion, url, created_at) VALUES (?, ?, ?, ?)",
                            (kw, emotion_label, url, now),
                        )
                conn.commit()
            finally:
                conn.close()

        return matched

    def _keyword_to_emotion(self, keyword: str) -> str:
        for emotion, keywords in EMOTION_LEXICON.items():
            if keyword in keywords:
                return emotion
        return "unknown"

    def get_trending_emotions(
        self,
        window_hours: int = 6,
        baseline_days: int = 7,
        min_count: int = 3,
        top_n: int = 5,
    ) -> list[EmotionTrend]:
        """Detect emotion keywords that are spiking vs their baseline.

        Args:
            window_hours: Recent window to measure current frequency.
            baseline_days: Days of history for baseline average.
            min_count: Minimum occurrences in window to consider.
            top_n: Number of top trending keywords to return.
        """
        now = datetime.now(_KST)
        window_start = (now - timedelta(hours=window_hours)).strftime("%Y-%m-%d %H:%M:%S")
        baseline_start = (now - timedelta(days=baseline_days)).strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            conn = self._get_conn()
            try:
                # Current window counts
                rows = conn.execute(
                    "SELECT keyword, COUNT(*) as cnt FROM keyword_signals "
                    "WHERE created_at >= ? GROUP BY keyword HAVING cnt >= ?",
                    (window_start, min_count),
                ).fetchall()
                current = {row[0]: row[1] for row in rows}

                if not current:
                    return []

                # Baseline daily average
                baseline_rows = conn.execute(
                    "SELECT keyword, COUNT(*) as cnt FROM keyword_signals "
                    "WHERE created_at >= ? AND created_at < ? GROUP BY keyword",
                    (baseline_start, window_start),
                ).fetchall()

                baseline_total_hours = max(1, (baseline_days * 24) - window_hours)
                baseline_per_window: dict[str, float] = {}
                for row in baseline_rows:
                    kw, cnt = row
                    baseline_per_window[kw] = (cnt / baseline_total_hours) * window_hours

                trends: list[EmotionTrend] = []
                for kw, cnt in current.items():
                    baseline = baseline_per_window.get(kw, 0.5)  # smoothing
                    ratio = cnt / max(baseline, 0.5)
                    if ratio > 1.2:
                        direction = "rising"
                    elif ratio < 0.8:
                        direction = "falling"
                    else:
                        direction = "stable"

                    trends.append(
                        EmotionTrend(
                            keyword=kw,
                            current_count=cnt,
                            baseline_count=round(baseline, 2),
                            spike_ratio=round(ratio, 2),
                            direction=direction,
                        )
                    )

                trends.sort(key=lambda t: t.spike_ratio, reverse=True)
                return trends[:top_n]
            finally:
                conn.close()

    def get_snapshot(self, hours: int = 24) -> SentimentSnapshot:
        """Get aggregated sentiment snapshot for the given time window."""
        now = datetime.now(_KST)
        cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

        # Fetch trending BEFORE acquiring lock to avoid deadlock
        # (get_trending_emotions also acquires self._lock)
        trending = self.get_trending_emotions()

        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT emotion, COUNT(*) as cnt FROM emotion_signals "
                    "WHERE created_at >= ? GROUP BY emotion ORDER BY cnt DESC",
                    (cutoff,),
                ).fetchall()

                total = conn.execute(
                    "SELECT COUNT(DISTINCT url) FROM emotion_signals WHERE created_at >= ?",
                    (cutoff,),
                ).fetchone()[0]

                top_emotions = [(row[0], row[1]) for row in rows]
                dominant = top_emotions[0][0] if top_emotions else "unknown"

                return SentimentSnapshot(
                    dominant_emotion=dominant,
                    top_emotions=top_emotions,
                    trending_keywords=trending,
                    timestamp=now,
                    total_posts=total,
                )
            finally:
                conn.close()

    def get_emotion_history(self, days: int = 7) -> dict[str, list[tuple[str, int]]]:
        """Get daily emotion counts for the past N days.

        Returns:
            Dict mapping emotion to list of (date_str, count) tuples.
        """
        cutoff = (datetime.now(_KST) - timedelta(days=days)).strftime("%Y-%m-%d")

        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT emotion, DATE(created_at) as dt, COUNT(*) as cnt "
                    "FROM emotion_signals WHERE DATE(created_at) >= ? "
                    "GROUP BY emotion, dt ORDER BY dt",
                    (cutoff,),
                ).fetchall()

                history: dict[str, list[tuple[str, int]]] = {}
                for emotion, dt, cnt in rows:
                    history.setdefault(emotion, []).append((dt, cnt))
                return history
            finally:
                conn.close()

    def cleanup(self, retention_days: int = 30):
        """Delete emotion signals older than retention_days."""
        cutoff = (datetime.now(_KST) - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM emotion_signals WHERE created_at < ?", (cutoff,))
                conn.execute("DELETE FROM keyword_signals WHERE created_at < ?", (cutoff,))
                conn.commit()
            finally:
                conn.close()


# ── Module-level singleton ─────────────────────────────────────────────
_instance: SentimentTracker | None = None
_instance_lock = threading.Lock()


def get_sentiment_tracker(db_path: str | None = None) -> SentimentTracker:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = SentimentTracker(db_path=db_path)
    return _instance
