"""Tests for pipeline.ab_feedback_loop — ABFeedbackLoop coverage uplift."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch


from pipeline.ab_feedback_loop import ABFeedbackLoop


# ── Helpers ──────────────────────────────────────────────────────────


class FakeConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


def _make_notion_page(
    *,
    ab_winner: str | None = None,
    topic_cluster: str | None = None,
    views: int | None = None,
    chosen_draft_type: str | None = None,
    recommended_draft_type: str | None = None,
):
    """Build a minimal Notion page dict for testing."""
    props: dict = {}
    if ab_winner:
        props["A/B 위너"] = {"type": "select", "select": {"name": ab_winner}}
    else:
        props["A/B 위너"] = {"type": "select", "select": None}
    if topic_cluster:
        props["토픽 클러스터"] = {"type": "select", "select": {"name": topic_cluster}}
    return {"properties": props}


def _make_record(
    topic_cluster: str = "연봉",
    views: int = 100,
    likes: int = 10,
    retweets: int = 5,
    chosen_draft_type: str = "공감형",
):
    return {
        "topic_cluster": topic_cluster,
        "views": views,
        "likes": likes,
        "retweets": retweets,
        "chosen_draft_type": chosen_draft_type,
    }


# ── ABFeedbackLoop.__init__ ──────────────────────────────────────


class TestABFeedbackLoopInit:
    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_init(self, mock_tester_cls):
        cfg = FakeConfig()
        notion = MagicMock()
        loop = ABFeedbackLoop(notion, cfg)
        assert loop.notion_uploader is notion
        assert loop.config is cfg
        mock_tester_cls.assert_called_once_with(config_mgr=cfg)


# ── fetch_manual_winners ─────────────────────────────────────────


class TestFetchManualWinners:
    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_empty_pages(self, _):
        loop = ABFeedbackLoop(MagicMock(), FakeConfig())
        result = asyncio.run(loop.fetch_manual_winners([]))
        assert result == {}

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_pages_with_manual_winner(self, _):
        page = _make_notion_page(ab_winner="논쟁형", topic_cluster="연봉")
        loop = ABFeedbackLoop(MagicMock(), FakeConfig())
        result = asyncio.run(loop.fetch_manual_winners([page]))
        assert result == {"연봉": "논쟁형"}

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_pages_without_winner(self, _):
        page = _make_notion_page(ab_winner=None, topic_cluster="연봉")
        loop = ABFeedbackLoop(MagicMock(), FakeConfig())
        result = asyncio.run(loop.fetch_manual_winners([page]))
        assert result == {}

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_pages_without_topic(self, _):
        """Winner selected but no topic → ignored."""
        page = {
            "properties": {
                "A/B 위너": {"type": "select", "select": {"name": "공감형"}},
                "토픽 클러스터": {"type": "select", "select": None},
            }
        }
        loop = ABFeedbackLoop(MagicMock(), FakeConfig())
        result = asyncio.run(loop.fetch_manual_winners([page]))
        assert result == {}

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_dict_style_ab_prop(self, _):
        """Non-standard dict format with 'name' key directly."""
        page = {
            "properties": {
                "A/B 위너": {"name": "유머형"},
                "토픽 클러스터": {"type": "select", "select": {"name": "야근"}},
            }
        }
        loop = ABFeedbackLoop(MagicMock(), FakeConfig())
        result = asyncio.run(loop.fetch_manual_winners([page]))
        assert result == {"야근": "유머형"}


# ── run_feedback_loop ────────────────────────────────────────────


class TestRunFeedbackLoop:
    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_fetch_notion_error_returns_empty(self, _):
        notion = MagicMock()
        notion.get_recent_pages = AsyncMock(side_effect=Exception("네트워크 오류"))
        loop = ABFeedbackLoop(notion, FakeConfig())
        result = asyncio.run(loop.run_feedback_loop(days=7))
        assert result == {}

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_no_valid_records_returns_cached(self, _, tmp_path, monkeypatch):
        # Patch CACHE_FILE to tmp
        cache_path = str(tmp_path / "tuned_image_styles.json")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", cache_path)

        notion = MagicMock()
        # Pages with zero views → no valid records
        pages = [_make_notion_page(topic_cluster="연봉")]
        notion.get_recent_pages = AsyncMock(return_value=pages)
        notion.extract_page_record = MagicMock(return_value={"views": 0, "topic_cluster": "연봉"})

        loop = ABFeedbackLoop(notion, FakeConfig())
        result = asyncio.run(loop.run_feedback_loop(days=7))
        # Should return cached (empty since file doesn't exist)
        assert isinstance(result, dict)

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_manual_winner_overrides_auto(self, mock_tester_cls, tmp_path, monkeypatch):
        cache_path = str(tmp_path / "tuned_image_styles.json")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", cache_path)

        manual_page = _make_notion_page(ab_winner="논쟁형", topic_cluster="연봉")
        notion = MagicMock()
        notion.get_recent_pages = AsyncMock(return_value=[manual_page])
        notion.extract_page_record = MagicMock(
            return_value={
                "views": 500,
                "likes": 30,
                "retweets": 10,
                "topic_cluster": "연봉",
                "chosen_draft_type": "공감형",
            }
        )

        loop = ABFeedbackLoop(notion, FakeConfig())
        result = asyncio.run(loop.run_feedback_loop(days=7))

        assert "연봉" in result
        assert result["연봉"]["winning_draft_type"] == "논쟁형"
        assert result["연봉"]["source"] == "manual"
        # 논쟁형 → "bold, dramatic, high contrast"
        assert "bold" in result["연봉"]["mood"]

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_auto_winner_with_clear_margin(self, mock_tester_cls, tmp_path, monkeypatch):
        cache_path = str(tmp_path / "tuned_image_styles.json")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", cache_path)

        # Two pages – same topic but different draft types
        p1 = _make_notion_page(topic_cluster="이직")
        p2 = _make_notion_page(topic_cluster="이직")
        notion = MagicMock()
        notion.get_recent_pages = AsyncMock(return_value=[p1, p2])

        # Two different draft types for same topic
        records = [
            {"views": 1000, "likes": 80, "retweets": 40, "topic_cluster": "이직", "chosen_draft_type": "공감형"},
            {"views": 1000, "likes": 20, "retweets": 5, "topic_cluster": "이직", "chosen_draft_type": "정보전달형"},
        ]
        notion.extract_page_record = MagicMock(side_effect=records)

        # Mock AB tester to return a winner
        from pipeline.image_ab_tester import ABTestResult

        mock_tester = MagicMock()
        mock_tester.compare_results.return_value = ABTestResult(
            test_id="test1",
            topic_cluster="이직",
            emotion_axis="공감",
            variants=[],
            winner="공감형",
            winner_reason="높은 참여율",
        )
        mock_tester_cls.return_value = mock_tester

        loop = ABFeedbackLoop(notion, FakeConfig())
        result = asyncio.run(loop.run_feedback_loop(days=14))

        assert "이직" in result
        assert result["이직"]["winning_draft_type"] == "공감형"
        assert result["이직"]["source"] == "auto"

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_single_variant_skipped(self, mock_tester_cls, tmp_path, monkeypatch):
        """Topic with only 1 variant should be skipped."""
        cache_path = str(tmp_path / "tuned_image_styles.json")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", cache_path)

        p1 = _make_notion_page(topic_cluster="야근")
        notion = MagicMock()
        notion.get_recent_pages = AsyncMock(return_value=[p1])
        notion.extract_page_record = MagicMock(
            return_value={
                "views": 500,
                "likes": 20,
                "retweets": 5,
                "topic_cluster": "야근",
                "chosen_draft_type": "공감형",
            }
        )

        loop = ABFeedbackLoop(notion, FakeConfig())
        result = asyncio.run(loop.run_feedback_loop(days=7))
        # Only 1 variant → no update
        assert "야근" not in result

    @patch("pipeline.ab_feedback_loop.ImageABTester")
    def test_no_winner_from_ab_tester(self, mock_tester_cls, tmp_path, monkeypatch):
        """compare_results returns no winner → no update."""
        cache_path = str(tmp_path / "tuned_image_styles.json")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", cache_path)

        p1 = _make_notion_page(topic_cluster="성과")
        p2 = _make_notion_page(topic_cluster="성과")
        notion = MagicMock()
        notion.get_recent_pages = AsyncMock(return_value=[p1, p2])
        records = [
            {"views": 500, "likes": 20, "retweets": 5, "topic_cluster": "성과", "chosen_draft_type": "공감형"},
            {"views": 500, "likes": 19, "retweets": 5, "topic_cluster": "성과", "chosen_draft_type": "논쟁형"},
        ]
        notion.extract_page_record = MagicMock(side_effect=records)

        from pipeline.image_ab_tester import ABTestResult

        mock_tester = MagicMock()
        mock_tester.compare_results.return_value = ABTestResult(
            test_id="test2",
            topic_cluster="",
            emotion_axis="",
            variants=[],
            winner=None,
            winner_reason="차이 미미",
        )
        mock_tester_cls.return_value = mock_tester

        loop = ABFeedbackLoop(notion, FakeConfig())
        result = asyncio.run(loop.run_feedback_loop(days=7))
        assert "성과" not in result


# ── load_tuned_styles / save_tuned_styles ────────────────────────


class TestTunedStylesIO:
    def test_load_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "pipeline.ab_feedback_loop.CACHE_FILE",
            str(tmp_path / "nonexistent.json"),
        )
        assert ABFeedbackLoop.load_tuned_styles() == {}

    def test_load_valid_file(self, tmp_path, monkeypatch):
        path = tmp_path / "styles.json"
        data = {"연봉": {"mood": "warm", "winning_draft_type": "공감형"}}
        path.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", str(path))
        assert ABFeedbackLoop.load_tuned_styles() == data

    def test_load_corrupt_file(self, tmp_path, monkeypatch):
        path = tmp_path / "bad.json"
        path.write_text("not-json!!!", encoding="utf-8")
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", str(path))
        assert ABFeedbackLoop.load_tuned_styles() == {}

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        path = tmp_path / "rt.json"
        monkeypatch.setattr("pipeline.ab_feedback_loop.CACHE_FILE", str(path))
        data = {"이직": {"mood": "bold", "source": "auto"}}
        ABFeedbackLoop.save_tuned_styles(data)
        assert ABFeedbackLoop.load_tuned_styles() == data

    def test_save_to_readonly_dir(self, tmp_path, monkeypatch):
        """save to invalid path should not raise (logged only)."""
        monkeypatch.setattr(
            "pipeline.ab_feedback_loop.CACHE_FILE",
            str(tmp_path / "no-exist-dir" / "deep" / "file.json"),
        )
        # Should not raise
        ABFeedbackLoop.save_tuned_styles({"k": {"v": "1"}})
