"""Tests for pipeline.publish_optimizer — PublishOptimizer and _extract_time_slot."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.publish_optimizer import (
    PublishOptimizer,
    TIME_SLOTS,
    _DEFAULT_OPTIMAL_SLOTS,
    _extract_time_slot,
)


# ── _extract_time_slot tests ─────────────────────────────────────────


class TestExtractTimeSlot:
    def test_morning(self):
        assert _extract_time_slot({"published_at": "2025-03-01T08:30:00+09:00"}) == "오전"

    def test_lunch(self):
        assert _extract_time_slot({"published_at": "2025-03-01T12:30:00+09:00"}) == "점심"

    def test_afternoon(self):
        assert _extract_time_slot({"published_at": "2025-03-01T15:00:00+09:00"}) == "오후"

    def test_evening(self):
        assert _extract_time_slot({"published_at": "2025-03-01T20:00:00+09:00"}) == "저녁"

    def test_late_night(self):
        assert _extract_time_slot({"published_at": "2025-03-01T23:00:00+09:00"}) == "심야"

    def test_early_morning_is_simya(self):
        assert _extract_time_slot({"published_at": "2025-03-01T03:00:00+09:00"}) == "심야"

    def test_missing_published_at(self):
        assert _extract_time_slot({}) is None

    def test_empty_published_at(self):
        assert _extract_time_slot({"published_at": ""}) is None

    def test_no_t_separator(self):
        assert _extract_time_slot({"published_at": "2025-03-01"}) is None

    def test_malformed_time(self):
        assert _extract_time_slot({"published_at": "2025-03-01TXX:YY"}) is None

    def test_boundary_6am(self):
        assert _extract_time_slot({"published_at": "2025-03-01T06:00:00+09:00"}) == "오전"

    def test_boundary_12pm(self):
        assert _extract_time_slot({"published_at": "2025-03-01T12:00:00+09:00"}) == "점심"

    def test_boundary_14pm(self):
        assert _extract_time_slot({"published_at": "2025-03-01T14:00:00+09:00"}) == "오후"

    def test_boundary_18pm(self):
        assert _extract_time_slot({"published_at": "2025-03-01T18:00:00+09:00"}) == "저녁"

    def test_boundary_22pm(self):
        assert _extract_time_slot({"published_at": "2025-03-01T22:00:00+09:00"}) == "심야"


# ── PublishOptimizer.get_hourly_performance ──────────────────────────


class TestGetHourlyPerformance:
    def test_empty_records(self):
        result = PublishOptimizer.get_hourly_performance([])
        for slot in TIME_SLOTS:
            assert result[slot]["count"] == 0
            assert result[slot]["avg_views"] == 0
            assert result[slot]["engagement_rate"] == 0

    def test_single_record(self):
        records = [
            {
                "published_at": "2025-03-01T13:00:00+09:00",
                "views": 1000,
                "likes": 50,
                "retweets": 10,
            }
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["점심"]["count"] == 1
        assert result["점심"]["avg_views"] == 1000.0
        assert result["점심"]["avg_likes"] == 50.0
        assert result["점심"]["avg_retweets"] == 10.0
        # engagement_rate: (50 + 10*2) / 1000 * 100 = 7.0
        assert result["점심"]["engagement_rate"] == 7.0

    def test_multiple_records_same_slot(self):
        records = [
            {"published_at": "2025-03-01T13:00:00+09:00", "views": 1000, "likes": 50, "retweets": 10},
            {"published_at": "2025-03-02T12:30:00+09:00", "views": 2000, "likes": 100, "retweets": 20},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["점심"]["count"] == 2
        assert result["점심"]["avg_views"] == 1500.0

    def test_zero_views_skipped(self):
        records = [
            {"published_at": "2025-03-01T13:00:00+09:00", "views": 0, "likes": 5, "retweets": 1},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["점심"]["count"] == 0

    def test_missing_metrics_default_to_zero(self):
        records = [
            {"published_at": "2025-03-01T13:00:00+09:00", "views": 500},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["점심"]["count"] == 1
        assert result["점심"]["avg_likes"] == 0.0
        assert result["점심"]["avg_retweets"] == 0.0

    def test_none_metrics_handled(self):
        records = [
            {"published_at": "2025-03-01T13:00:00+09:00", "views": 500, "likes": None, "retweets": None},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["점심"]["count"] == 1
        assert result["점심"]["avg_likes"] == 0.0

    def test_records_without_time_slot_skipped(self):
        records = [
            {"published_at": "", "views": 1000, "likes": 50, "retweets": 10},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        for slot in TIME_SLOTS:
            assert result[slot]["count"] == 0

    def test_multiple_slots(self):
        records = [
            {"published_at": "2025-03-01T08:00:00+09:00", "views": 100, "likes": 5, "retweets": 1},
            {"published_at": "2025-03-01T13:00:00+09:00", "views": 200, "likes": 10, "retweets": 2},
            {"published_at": "2025-03-01T20:00:00+09:00", "views": 300, "likes": 15, "retweets": 3},
        ]
        result = PublishOptimizer.get_hourly_performance(records)
        assert result["오전"]["count"] == 1
        assert result["점심"]["count"] == 1
        assert result["저녁"]["count"] == 1
        assert result["오후"]["count"] == 0


# ── PublishOptimizer.get_optimal_publish_time ────────────────────────


class TestGetOptimalPublishTime:
    def _make_records(self, slot_hour: int, count: int, views: int = 1000, likes: int = 50, retweets: int = 10):
        return [
            {
                "published_at": f"2025-03-{i + 1:02d}T{slot_hour:02d}:00:00+09:00",
                "views": views,
                "likes": likes,
                "retweets": retweets,
            }
            for i in range(count)
        ]

    def test_insufficient_data_returns_defaults(self):
        """When no slot has enough data points, returns default recommendations."""
        records = self._make_records(13, 2)  # only 2 records, min_data_points=5
        result = PublishOptimizer.get_optimal_publish_time(records, min_data_points=5)
        assert len(result) == len(_DEFAULT_OPTIMAL_SLOTS)
        for r in result:
            assert r["confidence"] == "default"
            assert r["score"] == 0

    def test_sufficient_data_returns_ranked(self):
        """With enough data, returns ranked candidates."""
        # 10 lunch records, 6 evening records
        lunch = self._make_records(13, 10, views=2000, likes=100, retweets=20)
        evening = self._make_records(20, 6, views=1000, likes=50, retweets=10)
        result = PublishOptimizer.get_optimal_publish_time(lunch + evening, min_data_points=5)
        assert len(result) == 2
        # Should be sorted by engagement_rate desc
        assert result[0]["slot"] in ("점심", "저녁")

    def test_top_candidate_has_trophy(self):
        """Top candidate should have trophy emoji in reason."""
        lunch = self._make_records(13, 10, views=2000, likes=100, retweets=20)
        result = PublishOptimizer.get_optimal_publish_time(lunch, min_data_points=5)
        assert len(result) >= 1
        assert "🏆" in result[0]["reason"]

    def test_confidence_levels(self):
        """10+ data points = high, 5-9 = medium."""
        lunch = self._make_records(13, 10)
        evening = self._make_records(20, 6)
        result = PublishOptimizer.get_optimal_publish_time(lunch + evening, min_data_points=5)
        confidences = {r["slot"]: r["confidence"] for r in result}
        assert confidences["점심"] == "high"
        assert confidences["저녁"] == "medium"

    def test_custom_metric(self):
        """Can sort by avg_views instead of engagement_rate."""
        lunch = self._make_records(13, 10, views=500, likes=100, retweets=50)
        evening = self._make_records(20, 10, views=2000, likes=10, retweets=5)
        result = PublishOptimizer.get_optimal_publish_time(lunch + evening, metric="avg_views", min_data_points=5)
        assert result[0]["slot"] == "저녁"  # higher avg_views

    def test_secondary_candidate_no_trophy(self):
        """Non-first candidates should not have trophy."""
        lunch = self._make_records(13, 10, views=2000, likes=100, retweets=20)
        evening = self._make_records(20, 10, views=1000, likes=50, retweets=10)
        result = PublishOptimizer.get_optimal_publish_time(lunch + evening, min_data_points=5)
        assert len(result) == 2
        assert "🏆" not in result[1]["reason"]

    def test_empty_records(self):
        result = PublishOptimizer.get_optimal_publish_time([])
        # No data → default recommendations
        assert len(result) == len(_DEFAULT_OPTIMAL_SLOTS)


# ── PublishOptimizer init ────────────────────────────────────────────


class TestPublishOptimizerInit:
    def test_default_init(self):
        opt = PublishOptimizer()
        assert opt.notion_uploader is None
        assert opt.config == {}

    def test_init_with_config(self):
        opt = PublishOptimizer(config={"key": "value"})
        assert opt.config["key"] == "value"
