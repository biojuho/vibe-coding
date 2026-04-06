"""Tests for pipeline.feedback_loop — analyze_success_patterns, get_failure_patterns, etc."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.feedback_loop import FeedbackLoop


# ── Helpers ──────────────────────────────────────────────────────────


def _make_record(
    topic_cluster: str = "경제",
    hook_type: str = "공감형",
    emotion_axis: str = "분노",
    performance_grade: str = "S",
    final_rank_score: float = 85.0,
    views: int = 1000,
    likes: int = 50,
    retweets: int = 10,
    status: str = "승인됨",
    tweet_url: str = "https://x.com/...",
    chosen_draft_type: str = "공감형",
    title: str = "테스트 제목",
) -> dict:
    return {
        "topic_cluster": topic_cluster,
        "hook_type": hook_type,
        "emotion_axis": emotion_axis,
        "performance_grade": performance_grade,
        "final_rank_score": final_rank_score,
        "views": views,
        "likes": likes,
        "retweets": retweets,
        "status": status,
        "tweet_url": tweet_url,
        "chosen_draft_type": chosen_draft_type,
        "recommended_draft_type": chosen_draft_type,
        "title": title,
    }


# ── _pearson_corr ────────────────────────────────────────────────────


class TestPearsonCorr:
    def test_perfect_positive(self):
        corr = FeedbackLoop._pearson_corr([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert corr == pytest.approx(1.0, abs=0.01)

    def test_perfect_negative(self):
        corr = FeedbackLoop._pearson_corr([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        assert corr == pytest.approx(-1.0, abs=0.01)

    def test_zero_correlation(self):
        corr = FeedbackLoop._pearson_corr([1, 2, 3, 4, 5], [5, 5, 5, 5, 5])
        assert corr == 0.0

    def test_too_few_values(self):
        assert FeedbackLoop._pearson_corr([1, 2], [3, 4]) == 0.0
        assert FeedbackLoop._pearson_corr([], []) == 0.0

    def test_partial_correlation(self):
        corr = FeedbackLoop._pearson_corr([1, 2, 3, 4, 5], [1, 3, 2, 5, 4])
        assert -1.0 <= corr <= 1.0
        assert corr > 0  # broadly positive


# ── _load_yaml_golden_examples ───────────────────────────────────────


class TestLoadYamlGoldenExamples:
    def test_returns_list(self):
        result = FeedbackLoop._load_yaml_golden_examples(5)
        assert isinstance(result, list)

    def test_limit_respected(self):
        result = FeedbackLoop._load_yaml_golden_examples(1)
        assert len(result) <= 1


# ── analyze_success_patterns ─────────────────────────────────────────


class TestAnalyzeSuccessPatterns:
    def test_no_winners(self):
        records = [_make_record(performance_grade="D") for _ in range(5)]
        result = FeedbackLoop.analyze_success_patterns(records)
        assert result["count"] == 0
        assert "S/A등급 데이터 없음" in result["insights"][0]

    def test_empty_records(self):
        result = FeedbackLoop.analyze_success_patterns([])
        assert result["count"] == 0

    def test_with_winners(self):
        records = [
            _make_record(topic_cluster="경제", hook_type="공감형", performance_grade="S"),
            _make_record(topic_cluster="경제", hook_type="논쟁형", performance_grade="A"),
            _make_record(topic_cluster="IT", hook_type="공감형", performance_grade="S"),
            _make_record(topic_cluster="경제", hook_type="공감형", performance_grade="D"),
        ]
        result = FeedbackLoop.analyze_success_patterns(records)
        assert result["count"] == 3
        assert result["top_topics"][0][0] == "경제"
        assert result["top_topics"][0][1] == 2
        assert result["avg_rank_score"] > 0
        assert len(result["insights"]) >= 2

    def test_custom_grade_filter(self):
        records = [
            _make_record(performance_grade="S"),
            _make_record(performance_grade="A"),
            _make_record(performance_grade="B"),
        ]
        result = FeedbackLoop.analyze_success_patterns(records, grade_filter={"S"})
        assert result["count"] == 1


# ── get_failure_patterns ─────────────────────────────────────────────


class TestGetFailurePatterns:
    def test_no_losers(self):
        records = [_make_record(performance_grade="S") for _ in range(5)]
        result = FeedbackLoop.get_failure_patterns(records)
        assert result["count"] == 0
        assert result["risky_combos"] == []
        assert result["auto_filters"] == []

    def test_empty_records(self):
        result = FeedbackLoop.get_failure_patterns([])
        assert result["count"] == 0

    def test_with_repeated_failures(self):
        records = [_make_record(topic_cluster="경제", hook_type="논쟁형", performance_grade="D") for _ in range(5)]
        result = FeedbackLoop.get_failure_patterns(records, min_occurrences=3)
        assert result["count"] == 5
        assert len(result["risky_combos"]) >= 1
        assert result["risky_combos"][0][0] == "경제+논쟁형"
        assert result["risky_combos"][0][1] == 5
        # Auto filter should be generated
        assert len(result["auto_filters"]) >= 1

    def test_topic_risk_filter(self):
        """When 70%+ of a topic is D grade, a topic_risk filter is generated."""
        records = [_make_record(topic_cluster="위험토픽", performance_grade="D") for _ in range(7)] + [
            _make_record(topic_cluster="위험토픽", performance_grade="S") for _ in range(3)
        ]
        result = FeedbackLoop.get_failure_patterns(records, min_occurrences=3)
        topic_risk_filters = [f for f in result["auto_filters"] if f["type"] == "topic_risk"]
        assert len(topic_risk_filters) >= 1
        assert topic_risk_filters[0]["value"] == "위험토픽"

    def test_below_min_occurrences(self):
        """Failures below min_occurrences are not reported as risky."""
        records = [
            _make_record(topic_cluster="경제", hook_type="논쟁형", performance_grade="D"),
            _make_record(topic_cluster="경제", hook_type="논쟁형", performance_grade="D"),
        ]
        result = FeedbackLoop.get_failure_patterns(records, min_occurrences=3)
        assert result["count"] == 2
        assert result["risky_combos"] == []


# ── compute_adaptive_weights ─────────────────────────────────────────


class TestComputeAdaptiveWeights:
    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        mock_notion = MagicMock()
        mock_notion.get_top_performing_posts = AsyncMock(
            return_value=[
                {"views": 100, "scrape_quality_score": 70, "publishability_score": 80, "performance_score": 60},
            ]
        )  # Only 1 record, need 5

        fl = FeedbackLoop(mock_notion, {"analytics.lookback_days": 30})
        result = await fl.compute_adaptive_weights()
        assert result == {}

    @pytest.mark.asyncio
    async def test_sufficient_data(self):
        records = [
            {
                "views": v,
                "scrape_quality_score": 60 + i * 5,
                "publishability_score": 70 + i * 3,
                "performance_score": 50 + i * 4,
            }
            for i, v in enumerate([100, 200, 300, 400, 500, 600, 700])
        ]
        mock_notion = MagicMock()
        mock_notion.get_top_performing_posts = AsyncMock(return_value=records)

        fl = FeedbackLoop(mock_notion, {"analytics.lookback_days": 30})
        result = await fl.compute_adaptive_weights()
        assert "scrape_quality" in result
        assert "publishability" in result
        assert "performance" in result
        # Weights should sum to ~1.0
        total = sum(result.values())
        assert total == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_all_zero_correlations(self):
        """When all correlations are 0 or negative, returns empty dict."""
        records = [
            {
                "views": 100,
                "scrape_quality_score": 50,
                "publishability_score": 50,
                "performance_score": 50,
            }
            for _ in range(10)
        ]
        mock_notion = MagicMock()
        mock_notion.get_top_performing_posts = AsyncMock(return_value=records)

        fl = FeedbackLoop(mock_notion, {"analytics.lookback_days": 30})
        result = await fl.compute_adaptive_weights()
        assert result == {}


# ── get_few_shot_examples ────────────────────────────────────────────


class TestGetFewShotExamples:
    @pytest.mark.asyncio
    async def test_performance_examples_available(self):
        mock_notion = MagicMock()
        mock_notion.get_top_performing_posts = AsyncMock(return_value=[{"text": "ex1"}])

        fl = FeedbackLoop(
            mock_notion,
            {
                "analytics.lookback_days": 30,
                "analytics.top_examples_limit": 5,
                "analytics.minimum_posts_for_feedback": 20,
            },
        )
        result = await fl.get_few_shot_examples()
        assert result == [{"text": "ex1"}]

    @pytest.mark.asyncio
    async def test_fallback_to_approved(self):
        mock_notion = MagicMock()
        mock_notion.get_top_performing_posts = AsyncMock(return_value=[])
        mock_notion.get_recent_approved_posts = AsyncMock(return_value=[{"text": "approved1"}])

        fl = FeedbackLoop(
            mock_notion,
            {
                "analytics.lookback_days": 30,
                "analytics.top_examples_limit": 5,
                "analytics.minimum_posts_for_feedback": 20,
            },
        )
        result = await fl.get_few_shot_examples()
        assert result == [{"text": "approved1"}]

    @pytest.mark.asyncio
    async def test_fallback_to_yaml(self):
        mock_notion = MagicMock()
        mock_notion.get_top_performing_posts = AsyncMock(return_value=[])
        mock_notion.get_recent_approved_posts = AsyncMock(return_value=[])

        fl = FeedbackLoop(
            mock_notion,
            {
                "analytics.lookback_days": 30,
                "analytics.top_examples_limit": 5,
                "analytics.minimum_posts_for_feedback": 20,
            },
        )
        result = await fl.get_few_shot_examples()
        # Returns whatever YAML has (may be empty if no YAML golden examples)
        assert isinstance(result, list)


# ── build_weekly_report_payload ──────────────────────────────────────


class TestBuildWeeklyReportPayload:
    @pytest.mark.asyncio
    async def test_basic_report(self):
        pages = [
            {"id": "p1"},
            {"id": "p2"},
        ]
        records_data = [
            _make_record(
                topic_cluster="경제",
                hook_type="공감형",
                performance_grade="S",
                views=1000,
                likes=50,
                retweets=10,
                status="승인됨",
            ),
            _make_record(
                topic_cluster="IT",
                hook_type="논쟁형",
                performance_grade="D",
                views=0,
                likes=0,
                retweets=0,
                status="검토필요",
                tweet_url="",
            ),
        ]

        mock_notion = MagicMock()
        mock_notion.get_recent_pages = AsyncMock(return_value=pages)
        mock_notion.extract_page_record = MagicMock(side_effect=records_data)

        fl = FeedbackLoop(mock_notion, {})
        report = await fl.build_weekly_report_payload(days=7)

        assert report["totals"]["total"] == 2
        assert report["totals"]["review_queue"] == 1
        assert report["totals"]["approved"] == 1
        assert report["totals"]["published"] == 1
        assert len(report["top_topics"]) >= 1
        assert "success_patterns" in report
        assert "failure_patterns" in report
        assert "records" in report
