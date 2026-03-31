import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pipeline.commands.one_off import run_digest, run_sentiment_report


@pytest.mark.asyncio
async def test_run_digest():
    config = MagicMock()
    notion = AsyncMock()

    class MockDigest:
        total_collected = 10
        total_published = 5

    with patch("pipeline.daily_digest.generate_and_send", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = MockDigest()
        result = await run_digest(config, notion, date="2026-03-23")

        assert result.total_collected == 10
        assert result.total_published == 5
        mock_generate.assert_called_once_with(config, notion_uploader=notion, date="2026-03-23")


def test_run_sentiment_report(capsys):
    config = MagicMock()

    class MockTrend:
        keyword = "AI"
        direction = "rising"
        spike_ratio = 2.0
        current_count = 10

    class MockTrendFalling:
        keyword = "Old"
        direction = "falling"
        spike_ratio = 0.5
        current_count = 2

    class MockTrendFlat:
        keyword = "Flat"
        direction = "flat"
        spike_ratio = 1.0
        current_count = 5

    class MockSnapshot:
        from datetime import datetime

        timestamp = datetime(2026, 3, 23, 12, 0)
        total_posts = 100
        dominant_emotion = "Joy"
        top_emotions = [("Joy", 50), ("Sadness", 20)]
        trending_keywords = [MockTrend(), MockTrendFalling(), MockTrendFlat()]

    tracker = MagicMock()
    tracker.get_snapshot.return_value = MockSnapshot()

    with patch("pipeline.sentiment_tracker.get_sentiment_tracker", return_value=tracker):
        run_sentiment_report(config)

        captured = capsys.readouterr()

        assert "Sentiment Report" in captured.out
        assert "Posts analyzed: 100" in captured.out
        assert "Dominant emotion: Joy" in captured.out
        assert "Joy: 50" in captured.out
        assert "AI ^ (x2.0, count=10)" in captured.out
        assert "Old v (x0.5, count=2)" in captured.out
        assert "Flat = (x1.0, count=5)" in captured.out


def test_run_sentiment_report_empty_lists(capsys):
    config = MagicMock()

    class MockEmptySnapshot:
        from datetime import datetime

        timestamp = datetime(2026, 3, 23, 12, 0)
        total_posts = 100
        dominant_emotion = "Joy"
        top_emotions = []
        trending_keywords = []

    tracker = MagicMock()
    tracker.get_snapshot.return_value = MockEmptySnapshot()

    with patch("pipeline.sentiment_tracker.get_sentiment_tracker", return_value=tracker):
        run_sentiment_report(config)

        captured = capsys.readouterr()
        assert "Sentiment Report" in captured.out
        assert "Top emotions:" not in captured.out
        assert "Trending keywords:" not in captured.out
