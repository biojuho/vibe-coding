"""
result_tracker_db 유닛 테스트.
QA/QC STEP 2: 기능성, 보안, 안정성, 코드 품질 검증.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """모든 테스트에서 임시 DB 사용."""
    temp_db = tmp_path / "test_result_tracker.db"
    monkeypatch.setattr("execution.result_tracker_db.DB_PATH", temp_db)
    from execution.result_tracker_db import init_db
    init_db()
    yield


class TestInitDB:
    """DB 초기화 테스트."""

    def test_init_creates_tables(self, tmp_path, monkeypatch):
        temp_db = tmp_path / "new_test.db"
        monkeypatch.setattr("execution.result_tracker_db.DB_PATH", temp_db)
        from execution.result_tracker_db import _conn, init_db
        init_db()
        conn = _conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        conn.close()
        assert "published_content" in table_names
        assert "stats_history" in table_names

    def test_init_idempotent(self):
        """init_db를 여러 번 호출해도 에러 없음."""
        from execution.result_tracker_db import init_db
        init_db()
        init_db()
        init_db()


class TestExtractVideoId:
    """YouTube URL 파싱 테스트."""

    def test_standard_url(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("https://youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("https://example.com/video") == ""

    def test_empty_url(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("") == ""

    def test_url_with_params(self):
        from execution.result_tracker_db import extract_youtube_video_id
        assert extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s") == "dQw4w9WgXcQ"


class TestCRUD:
    """CRUD 기능 테스트."""

    def test_add_and_get_all(self):
        from execution.result_tracker_db import add_content, get_all
        row_id = add_content(
            platform="youtube",
            url="https://youtu.be/abc12345678",
            title="테스트 영상",
            channel="AI/기술",
        )
        assert row_id > 0
        items = get_all()
        assert len(items) == 1
        assert items[0]["title"] == "테스트 영상"
        assert items[0]["video_id"] == "abc12345678"

    def test_add_x_content(self):
        from execution.result_tracker_db import add_content, get_all
        add_content(
            platform="x",
            url="https://x.com/user/status/123",
            title="X 게시물",
        )
        items = get_all(platform="x")
        assert len(items) == 1
        assert items[0]["video_id"] == ""  # X는 video_id 없음

    def test_filter_by_platform(self):
        from execution.result_tracker_db import add_content, get_all
        add_content(platform="youtube", url="https://youtu.be/a", title="YT1")
        add_content(platform="x", url="https://x.com/1", title="X1")
        assert len(get_all(platform="youtube")) == 1
        assert len(get_all(platform="x")) == 1
        assert len(get_all()) == 2

    def test_filter_by_channel(self):
        from execution.result_tracker_db import add_content, get_all
        add_content(platform="youtube", url="u1", title="T1", channel="AI/기술")
        add_content(platform="youtube", url="u2", title="T2", channel="심리학")
        assert len(get_all(channel="AI/기술")) == 1

    def test_get_by_id(self):
        from execution.result_tracker_db import add_content, get_by_id
        row_id = add_content(platform="youtube", url="u1", title="T1")
        item = get_by_id(row_id)
        assert item is not None
        assert item["title"] == "T1"

    def test_get_by_id_nonexistent(self):
        from execution.result_tracker_db import get_by_id
        assert get_by_id(99999) is None

    def test_delete_content(self):
        from execution.result_tracker_db import add_content, delete_content, get_all
        row_id = add_content(platform="youtube", url="u1", title="삭제대상")
        assert len(get_all()) == 1
        delete_content(row_id)
        assert len(get_all()) == 0

    def test_delete_cascades_history(self):
        from execution.result_tracker_db import (
            add_content, delete_content, get_stats_history, update_stats,
        )
        row_id = add_content(platform="youtube", url="u1", title="T1")
        update_stats(row_id, views=100, likes=10)
        assert len(get_stats_history(row_id)) == 1
        delete_content(row_id)
        assert len(get_stats_history(row_id)) == 0

    def test_add_strips_whitespace(self):
        from execution.result_tracker_db import add_content, get_all
        add_content(
            platform="youtube",
            url="  https://youtu.be/abc  ",
            title="  제목  ",
            channel="  AI  ",
        )
        item = get_all()[0]
        assert item["url"] == "https://youtu.be/abc"
        assert item["title"] == "제목"
        assert item["channel"] == "AI"

    def test_duplicate_url_returns_existing_id(self):
        """[QA 수정 검증] 같은 URL 중복 등록 시 기존 ID 반환."""
        from execution.result_tracker_db import add_content, get_all
        id1 = add_content(platform="youtube", url="https://youtu.be/dup1", title="첫등록")
        id2 = add_content(platform="youtube", url="https://youtu.be/dup1", title="중복등록")
        assert id1 == id2
        assert len(get_all()) == 1  # 1건만 존재

    def test_same_url_different_platform_ok(self):
        """같은 URL이라도 플랫폼이 다르면 별개 등록."""
        from execution.result_tracker_db import add_content, get_all
        add_content(platform="youtube", url="https://example.com/1", title="YT")
        add_content(platform="x", url="https://example.com/1", title="X")
        assert len(get_all()) == 2


class TestStats:
    """통계 업데이트 테스트."""

    def test_update_stats(self):
        from execution.result_tracker_db import add_content, get_by_id, update_stats
        row_id = add_content(platform="youtube", url="u1", title="T1")
        update_stats(row_id, views=1000, likes=50, comments=5)
        item = get_by_id(row_id)
        assert item["views"] == 1000
        assert item["likes"] == 50
        assert item["comments"] == 5
        assert item["stats_updated"] != ""

    def test_update_creates_history(self):
        from execution.result_tracker_db import (
            add_content, get_stats_history, update_stats,
        )
        row_id = add_content(platform="youtube", url="u1", title="T1")
        update_stats(row_id, views=100)
        update_stats(row_id, views=200)
        history = get_stats_history(row_id)
        assert len(history) == 2
        assert history[0]["views"] == 100
        assert history[1]["views"] == 200

    def test_update_manual_stats(self):
        from execution.result_tracker_db import add_content, get_by_id, update_manual_stats
        row_id = add_content(platform="x", url="u1", title="X1")
        update_manual_stats(row_id, impressions=5000, likes=100, retweets=20)
        item = get_by_id(row_id)
        assert item["impressions"] == 5000
        assert item["likes"] == 100
        assert item["retweets"] == 20

    def test_update_manual_stats_nonexistent(self):
        """존재하지 않는 ID에 대한 수동 통계 업데이트는 무시."""
        from execution.result_tracker_db import update_manual_stats
        update_manual_stats(99999, views=100)  # 에러 없이 pass

    def test_update_manual_stats_ignores_invalid_keys(self):
        from execution.result_tracker_db import add_content, get_by_id, update_manual_stats
        row_id = add_content(platform="x", url="u1", title="X1")
        update_manual_stats(row_id, invalid_key=999, likes=10)
        item = get_by_id(row_id)
        assert item["likes"] == 10


class TestAggregates:
    """집계 함수 테스트."""

    def test_platform_summary(self):
        from execution.result_tracker_db import (
            add_content, get_platform_summary, update_stats,
        )
        id1 = add_content(platform="youtube", url="u1", title="Y1")
        add_content(platform="x", url="u2", title="X1")
        update_stats(id1, views=1000)
        summary = get_platform_summary()
        assert len(summary) == 2

    def test_channel_summary(self):
        from execution.result_tracker_db import (
            add_content, get_channel_summary, update_stats,
        )
        id1 = add_content(platform="youtube", url="u1", title="Y1", channel="AI/기술")
        update_stats(id1, views=500)
        summary = get_channel_summary()
        assert len(summary) == 1
        assert summary[0]["channel"] == "AI/기술"

    def test_top_content(self):
        from execution.result_tracker_db import add_content, get_top_content, update_stats
        id1 = add_content(platform="youtube", url="u1", title="높은조회수")
        id2 = add_content(platform="youtube", url="u2", title="낮은조회수")
        update_stats(id1, views=10000)
        update_stats(id2, views=100)
        top = get_top_content(1)
        assert len(top) == 1
        assert top[0]["title"] == "높은조회수"

    def test_top_content_excludes_zero_views(self):
        from execution.result_tracker_db import add_content, get_top_content
        add_content(platform="youtube", url="u1", title="조회수없음")
        top = get_top_content(10)
        assert len(top) == 0

    def test_daily_trend(self):
        from execution.result_tracker_db import add_content, get_daily_trend
        add_content(platform="youtube", url="u1", title="T1")
        trend = get_daily_trend(30)
        assert len(trend) >= 1

    def test_empty_aggregates(self):
        from execution.result_tracker_db import (
            get_channel_summary, get_daily_trend, get_platform_summary, get_top_content,
        )
        assert get_platform_summary() == []
        assert get_channel_summary() == []
        assert get_top_content() == []
        assert get_daily_trend() == []


class TestYouTubeCollector:
    """YouTube 통계 수집 테스트."""

    def test_collect_no_api_key(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        from execution.result_tracker_db import collect_youtube_stats
        result = collect_youtube_stats()
        assert "error" in result

    def test_collect_no_items(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key")
        from execution.result_tracker_db import collect_youtube_stats
        result = collect_youtube_stats()
        assert result["updated"] == 0

    @patch("execution.result_tracker_db.requests.get")
    def test_collect_success(self, mock_get, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key")
        from execution.result_tracker_db import add_content, collect_youtube_stats, get_by_id

        row_id = add_content(
            platform="youtube",
            url="https://youtu.be/abc12345678",
            title="테스트",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "items": [
                {
                    "id": "abc12345678",
                    "statistics": {
                        "viewCount": "1500",
                        "likeCount": "75",
                        "commentCount": "12",
                    },
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = collect_youtube_stats()
        assert result["updated"] == 1
        item = get_by_id(row_id)
        assert item["views"] == 1500
        assert item["likes"] == 75
        assert item["comments"] == 12

    @patch("execution.result_tracker_db.requests.get")
    def test_collect_api_error(self, mock_get, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key")
        from execution.result_tracker_db import add_content, collect_youtube_stats

        add_content(
            platform="youtube",
            url="https://youtu.be/abc12345678",
            title="테스트",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_get.return_value = mock_resp

        result = collect_youtube_stats()
        assert result["updated"] == 0

    @patch("execution.result_tracker_db.requests.get")
    def test_collect_network_error(self, mock_get, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "test_key")
        from execution.result_tracker_db import add_content, collect_youtube_stats

        add_content(
            platform="youtube",
            url="https://youtu.be/abc12345678",
            title="테스트",
        )
        mock_get.side_effect = ConnectionError("timeout")

        result = collect_youtube_stats()
        assert result["updated"] == 0


class TestPlatformConfig:
    """플랫폼 설정 테스트."""

    def test_platforms_have_required_keys(self):
        from execution.result_tracker_db import PLATFORMS
        for key, cfg in PLATFORMS.items():
            assert "display" in cfg
            assert "emoji" in cfg
            assert "auto_stats" in cfg

    def test_only_youtube_has_auto_stats(self):
        from execution.result_tracker_db import PLATFORMS
        auto = [k for k, v in PLATFORMS.items() if v["auto_stats"]]
        assert auto == ["youtube"]
