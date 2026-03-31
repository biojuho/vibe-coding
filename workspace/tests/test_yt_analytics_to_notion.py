"""execution/yt_analytics_to_notion.py 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from execution.yt_analytics_to_notion import (
    _cli,
    _fetch_yt_stats,
    _get_uploaded_pages,
    _notion_headers,
    _notion_request,
    _update_notion_page,
    run,
)


# ── _notion_headers 테스트 ────────────────────────────────────


class TestNotionHeaders:
    @patch.dict("os.environ", {"NOTION_API_KEY": "ntn_test123"})
    def test_returns_auth_header(self):
        headers = _notion_headers()
        assert headers["Authorization"] == "Bearer ntn_test123"
        assert "Notion-Version" in headers
        assert headers["Content-Type"] == "application/json"


# ── _fetch_yt_stats 테스트 ────────────────────────────────────


class TestFetchYtStats:
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": ""})
    def test_no_api_key_raises(self):
        with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
            _fetch_yt_stats(["vid1"])

    @patch("execution.yt_analytics_to_notion.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "AIza_test"})
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "items": [
                {
                    "id": "vid1",
                    "statistics": {
                        "viewCount": "100",
                        "likeCount": "10",
                        "commentCount": "5",
                    },
                }
            ]
        }
        mock_get.return_value = mock_resp

        stats = _fetch_yt_stats(["vid1"])
        assert stats["vid1"]["views"] == 100
        assert stats["vid1"]["likes"] == 10
        assert stats["vid1"]["comments"] == 5

    @patch("execution.yt_analytics_to_notion.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "AIza_test"})
    def test_api_error_raises(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_get.return_value = mock_resp

        with pytest.raises(RuntimeError, match="YouTube API"):
            _fetch_yt_stats(["vid1"])

    @patch("execution.yt_analytics_to_notion.requests.get")
    @patch.dict("os.environ", {"YOUTUBE_API_KEY": "AIza_test"})
    def test_batching_over_50(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        mock_get.return_value = mock_resp

        _fetch_yt_stats([f"vid{i}" for i in range(75)])
        assert mock_get.call_count == 2  # 50 + 25


# ── _update_notion_page 테스트 ────────────────────────────────


class TestUpdateNotionPage:
    @patch("execution.yt_analytics_to_notion._notion_request")
    def test_success(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_request.return_value = mock_resp

        result = _update_notion_page(
            "page-123",
            {"views": 100, "likes": 10, "comments": 5},
            video_id="vid1",
        )
        assert result is True
        mock_request.assert_called_once()

    @patch("execution.yt_analytics_to_notion._notion_request")
    def test_failure(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_request.return_value = mock_resp

        result = _update_notion_page("page-123", {"views": 0, "likes": 0, "comments": 0})
        assert result is False


# ── _get_uploaded_pages 테스트 ────────────────────────────────


class TestGetUploadedPages:
    @patch.dict("os.environ", {"NOTION_TRACKING_DB_ID": ""})
    def test_no_db_id_raises(self):
        with pytest.raises(ValueError, match="NOTION_TRACKING_DB_ID"):
            _get_uploaded_pages()

    @patch("execution.yt_analytics_to_notion._notion_request")
    @patch.dict("os.environ", {"NOTION_TRACKING_DB_ID": "db_test"})
    def test_single_page(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{"id": "page1"}],
            "has_more": False,
        }
        mock_request.return_value = mock_resp

        pages = _get_uploaded_pages()
        assert len(pages) == 1
        assert pages[0]["id"] == "page1"

    @patch("execution.yt_analytics_to_notion._notion_request")
    @patch.dict("os.environ", {"NOTION_TRACKING_DB_ID": "db_test"})
    def test_with_channel_filter(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [], "has_more": False}
        mock_request.return_value = mock_resp

        _get_uploaded_pages(channel="AI/테크")
        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json"]
        # Should have "and" filter with channel
        assert "and" in payload["filter"]


# ── run 테스트 ────────────────────────────────────────────────


class TestRun:
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_no_pages(self, mock_pages):
        mock_pages.return_value = []
        result = run()
        assert result["updated"] == 0
        assert result["skipped"] == 0

    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_no_video_ids(self, mock_pages):
        mock_pages.return_value = [{"id": "p1", "properties": {}}]
        result = run()
        assert result["skipped"] == 1

    @patch("execution.yt_analytics_to_notion._fetch_yt_stats")
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_dry_run(self, mock_pages, mock_stats):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtu.be/abc123"},
                    "YouTube Video ID": {"rich_text": []},
                },
            }
        ]
        result = run(dry_run=True)
        assert result["skipped"] == 1
        mock_stats.assert_not_called()

    @patch("execution.yt_analytics_to_notion._update_notion_page")
    @patch("execution.yt_analytics_to_notion._fetch_yt_stats")
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_full_run(self, mock_pages, mock_stats, mock_update):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtu.be/abc123"},
                    "YouTube Video ID": {"rich_text": []},
                },
            }
        ]
        mock_stats.return_value = {"abc123": {"views": 500, "likes": 50, "comments": 10}}
        mock_update.return_value = True

        result = run()
        assert result["updated"] == 1
        assert result["errors"] == []

    @patch("execution.yt_analytics_to_notion._update_notion_page")
    @patch("execution.yt_analytics_to_notion._fetch_yt_stats")
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_video_not_in_stats(self, mock_pages, mock_stats, mock_update):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtu.be/abc123"},
                    "YouTube Video ID": {"rich_text": []},
                },
            }
        ]
        mock_stats.return_value = {}  # video not found
        result = run()
        assert result["skipped"] == 1
        mock_update.assert_not_called()

    @patch("execution.yt_analytics_to_notion._fetch_yt_stats")
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_yt_api_key_error(self, mock_pages, mock_stats):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtu.be/abc123"},
                    "YouTube Video ID": {"rich_text": []},
                },
            }
        ]
        mock_stats.side_effect = ValueError("YOUTUBE_API_KEY 환경변수가 없습니다.")
        result = run()
        assert len(result["errors"]) == 1

    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_url_parsing_shorts(self, mock_pages):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtube.com/shorts/xyz789"},
                    "YouTube Video ID": {"rich_text": []},
                },
            }
        ]
        result = run(dry_run=True)
        assert result["skipped"] == 1  # has video id so enters dry_run path

    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_existing_video_id_priority(self, mock_pages):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtu.be/url_id"},
                    "YouTube Video ID": {"rich_text": [{"plain_text": "existing_id"}]},
                },
            }
        ]
        result = run(dry_run=True)
        assert result["skipped"] == 1


# ── _notion_request 테스트 ────────────────────────────────────


class TestNotionRequest:
    @patch("execution.yt_analytics_to_notion.time.sleep")
    @patch("execution.yt_analytics_to_notion.requests.request")
    @patch.dict("os.environ", {"NOTION_API_KEY": "ntn_test"})
    def test_makes_request_with_headers(self, mock_req, mock_sleep):
        mock_resp = MagicMock()
        mock_req.return_value = mock_resp
        result = _notion_request("POST", "/databases/db1/query", json={"page_size": 10})
        assert result is mock_resp
        mock_req.assert_called_once()
        mock_sleep.assert_called_once()


# ── 추가 _get_uploaded_pages 테스트 ──────────────────────────


class TestGetUploadedPagesExtra:
    @patch("execution.yt_analytics_to_notion._notion_request")
    @patch.dict("os.environ", {"NOTION_TRACKING_DB_ID": "db_test"})
    def test_with_days_filter(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": [], "has_more": False}
        mock_request.return_value = mock_resp
        _get_uploaded_pages(days=7)
        call_kwargs = mock_request.call_args[1]
        assert "and" in call_kwargs["json"]["filter"]

    @patch("execution.yt_analytics_to_notion._notion_request")
    @patch.dict("os.environ", {"NOTION_TRACKING_DB_ID": "db_test"})
    def test_api_error_breaks(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_request.return_value = mock_resp
        pages = _get_uploaded_pages()
        assert pages == []

    @patch("execution.yt_analytics_to_notion._notion_request")
    @patch.dict("os.environ", {"NOTION_TRACKING_DB_ID": "db_test"})
    def test_pagination(self, mock_request):
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {"results": [{"id": "p1"}], "has_more": True, "next_cursor": "c1"}
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {"results": [{"id": "p2"}], "has_more": False}
        mock_request.side_effect = [resp1, resp2]
        pages = _get_uploaded_pages()
        assert len(pages) == 2


# ── run 추가 테스트 ──────────────────────────────────────────


class TestRunExtra:
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_v_param_url(self, mock_pages):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {
                    "유튜브 URL": {"url": "https://youtube.com/watch?v=qwerty"},
                    "YouTube Video ID": {"rich_text": []},
                },
            }
        ]
        result = run(dry_run=True)
        assert result["skipped"] == 1

    @patch("execution.yt_analytics_to_notion._update_notion_page")
    @patch("execution.yt_analytics_to_notion._fetch_yt_stats")
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_update_failure(self, mock_pages, mock_stats, mock_update):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {"유튜브 URL": {"url": "https://youtu.be/abc"}, "YouTube Video ID": {"rich_text": []}},
            }
        ]
        mock_stats.return_value = {"abc": {"views": 1, "likes": 0, "comments": 0}}
        mock_update.return_value = False
        result = run()
        assert len(result["errors"]) == 1

    @patch("execution.yt_analytics_to_notion._fetch_yt_stats")
    @patch("execution.yt_analytics_to_notion._get_uploaded_pages")
    def test_generic_exception(self, mock_pages, mock_stats):
        mock_pages.return_value = [
            {
                "id": "p1",
                "properties": {"유튜브 URL": {"url": "https://youtu.be/abc"}, "YouTube Video ID": {"rich_text": []}},
            }
        ]
        mock_stats.side_effect = RuntimeError("Network error")
        result = run()
        assert len(result["errors"]) == 1


# ── _cli 테스트 ──────────────────────────────────────────────


class TestCli:
    @patch("execution.yt_analytics_to_notion.run")
    @patch("sys.argv", ["prog", "--dry-run"])
    def test_cli_dry_run(self, mock_run):
        mock_run.return_value = {"updated": 0, "skipped": 5, "errors": []}
        _cli()
        mock_run.assert_called_once_with(channel=None, days=None, dry_run=True)

    @patch("execution.yt_analytics_to_notion.run")
    @patch("sys.argv", ["prog", "--channel", "AI", "--days", "7"])
    def test_cli_with_args(self, mock_run):
        mock_run.return_value = {"updated": 3, "skipped": 1, "errors": ["err1"]}
        _cli()
        mock_run.assert_called_once_with(channel="AI", days=7, dry_run=False)
