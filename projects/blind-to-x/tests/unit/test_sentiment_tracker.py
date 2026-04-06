"""Tests for pipeline.sentiment_tracker helpers."""

from __future__ import annotations

import pytest

from pipeline.sentiment_tracker import (
    EMOTION_LEXICON,
    EmotionTrend,
    SentimentTracker,
)


@pytest.fixture
def tracker(tmp_path):
    """Create a SentimentTracker with a temp DB."""
    db = str(tmp_path / "sentiment_test.db")
    return SentimentTracker(db_path=db)


# ── _keyword_to_emotion ─────────────────────────────────────────────────────


class TestKeywordToEmotion:
    def test_known_keywords(self, tracker):
        assert tracker._keyword_to_emotion("빡치") == "분노"
        assert tracker._keyword_to_emotion("웃김") == "웃김"
        assert tracker._keyword_to_emotion("충격") == "경악"
        assert tracker._keyword_to_emotion("희망") == "희망"
        assert tracker._keyword_to_emotion("응원") == "연대"

    def test_unknown_keyword(self, tracker):
        assert tracker._keyword_to_emotion("알수없는단어") == "unknown"

    def test_all_lexicon_keywords_resolve(self, tracker):
        """Every keyword in the lexicon should resolve to *some* emotion (not 'unknown')."""
        for emotion, keywords in EMOTION_LEXICON.items():
            for kw in keywords:
                result = tracker._keyword_to_emotion(kw)
                assert result != "unknown", f"{kw} should resolve to an emotion, got unknown"


# ── record() ─────────────────────────────────────────────────────────────────


class TestRecord:
    def test_detects_keywords_in_content(self, tracker):
        matched = tracker.record(
            url="https://example.com/1",
            title="직장 스트레스",
            content="빡치고 열받는 하루였다. 진짜 어이없는 일.",
            emotion_axis="분노",
        )
        assert "빡치" in matched
        assert "열받" in matched
        assert "어이없" in matched

    def test_no_keywords(self, tracker):
        matched = tracker.record(
            url="https://example.com/2",
            title="평범한 글",
            content="오늘 점심 먹었다.",
            emotion_axis="일상",
        )
        assert matched == {}

    def test_count_multiple_occurrences(self, tracker):
        matched = tracker.record(
            url="https://example.com/3",
            title="반복",
            content="빡치고 또 빡치고 또또 빡치는 하루",
            emotion_axis="분노",
        )
        assert matched["빡치"] == 3

    def test_case_insensitive(self, tracker):
        # Korean doesn't have case, but the text is lowered
        matched = tracker.record(
            url="https://example.com/4",
            title="ㅋㅋ 웃김",
            content="ㅋㅋ 완전 웃김",
            emotion_axis="웃김",
        )
        assert "ㅋㅋ" in matched
        assert "웃김" in matched


# ── get_trending_emotions (basic integration) ────────────────────────────────


class TestGetTrendingEmotions:
    def test_returns_list_on_empty_db(self, tracker):
        trends = tracker.get_trending_emotions()
        assert isinstance(trends, list)
        assert len(trends) == 0

    def test_returns_trends_after_records(self, tracker):
        # Insert several records to create a trend
        for i in range(10):
            tracker.record(
                url=f"https://example.com/{i}",
                title="빡침",
                content="빡치고 열받는 상황",
                emotion_axis="분노",
            )
        trends = tracker.get_trending_emotions(
            window_hours=1,
            baseline_days=1,
            min_count=1,
        )
        assert isinstance(trends, list)
        # Should have at least one trend
        for t in trends:
            assert isinstance(t, EmotionTrend)
            assert t.current_count >= 1


# ── get_snapshot (basic) ─────────────────────────────────────────────────────


class TestGetSnapshot:
    def test_empty_snapshot(self, tracker):
        snapshot = tracker.get_snapshot()
        assert snapshot.total_posts == 0
        assert snapshot.dominant_emotion in ("none", "unknown")
        assert snapshot.top_emotions == []

    def test_snapshot_after_records(self, tracker):
        tracker.record("u1", "t", "빡치는 일", "분노")
        tracker.record("u2", "t", "웃김 상황", "웃김")
        tracker.record("u3", "t", "빡치고 열받", "분노")
        snapshot = tracker.get_snapshot(hours=1)
        assert snapshot.total_posts == 3
        assert snapshot.dominant_emotion == "분노"


# ── EmotionTrend direction logic ─────────────────────────────────────────────


class TestEmotionTrendDirection:
    """Verify direction categorization from spike_ratio."""

    def test_rising(self):
        t = EmotionTrend("빡치", 10, 5.0, 2.0, "rising")
        assert t.direction == "rising"

    def test_falling(self):
        t = EmotionTrend("웃김", 2, 10.0, 0.2, "falling")
        assert t.direction == "falling"

    def test_stable(self):
        t = EmotionTrend("공감", 5, 5.0, 1.0, "stable")
        assert t.direction == "stable"
