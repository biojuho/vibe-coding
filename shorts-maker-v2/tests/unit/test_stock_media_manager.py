"""StockMediaManager + Pexels/Unsplash 클라이언트 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.providers.pexels_client import PexelsClient
from shorts_maker_v2.providers.unsplash_client import UnsplashClient
from shorts_maker_v2.providers.stock_media_manager import StockMediaManager


# ════════════════════════════════════════════════════════════
# PexelsClient
# ════════════════════════════════════════════════════════════


class TestPexelsClientInit:
    def test_raises_without_api_key(self):
        with pytest.raises(ValueError, match="PEXELS_API_KEY"):
            PexelsClient(api_key="")

    def test_init_success(self):
        client = PexelsClient(api_key="test_key")
        assert client.api_key == "test_key"


class TestPexelsSearchVideos:
    @patch("shorts_maker_v2.providers.pexels_client.requests.get")
    def test_returns_video_list(self, mock_get):
        mock_get.return_value.json.return_value = {
            "videos": [{"id": 1, "video_files": []}]
        }
        mock_get.return_value.raise_for_status = lambda: None

        client = PexelsClient(api_key="key")
        result = client.search_videos(query="technology")
        assert len(result) == 1
        assert result[0]["id"] == 1

    @patch("shorts_maker_v2.providers.pexels_client.requests.get")
    def test_empty_results(self, mock_get):
        mock_get.return_value.json.return_value = {"videos": []}
        mock_get.return_value.raise_for_status = lambda: None

        client = PexelsClient(api_key="key")
        result = client.search_videos(query="xyz_no_result")
        assert result == []


class TestPexelsSearchPhotos:
    @patch("shorts_maker_v2.providers.pexels_client.requests.get")
    def test_returns_photo_list(self, mock_get):
        mock_get.return_value.json.return_value = {
            "photos": [{"id": 10, "src": {"large2x": "https://example.com/img.jpg"}}]
        }
        mock_get.return_value.raise_for_status = lambda: None

        client = PexelsClient(api_key="key")
        result = client.search_photos(query="nature")
        assert len(result) == 1
        assert result[0]["id"] == 10


class TestPickBestVideoFile:
    def test_picks_closest_resolution(self):
        entry = {
            "video_files": [
                {"width": 720, "height": 1280, "link": "url_720"},
                {"width": 1080, "height": 1920, "link": "url_1080"},
            ]
        }
        url = PexelsClient._pick_best_video_file(entry, 1080, 1920)
        assert url == "url_1080"

    def test_returns_none_for_empty_files(self):
        assert PexelsClient._pick_best_video_file({"video_files": []}) is None

    def test_returns_none_for_no_key(self):
        assert PexelsClient._pick_best_video_file({}) is None


# ════════════════════════════════════════════════════════════
# UnsplashClient
# ════════════════════════════════════════════════════════════


class TestUnsplashClientInit:
    def test_raises_without_key(self):
        with pytest.raises(ValueError, match="UNSPLASH_API_KEY"):
            UnsplashClient(access_key="")

    def test_init_success(self):
        client = UnsplashClient(access_key="test_key")
        assert "Client-ID test_key" in client._headers["Authorization"]


class TestUnsplashSearchPhotos:
    @patch("shorts_maker_v2.providers.unsplash_client.requests.get")
    def test_returns_results_list(self, mock_get):
        mock_get.return_value.json.return_value = {
            "results": [
                {"id": "abc", "urls": {"full": "https://unsplash.com/abc.jpg"}, "width": 800, "height": 1200}
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None

        client = UnsplashClient(access_key="key")
        result = client.search_photos(query="space")
        assert len(result) == 1
        assert result[0]["id"] == "abc"

    @patch("shorts_maker_v2.providers.unsplash_client.requests.get")
    def test_limits_per_page_to_30(self, mock_get):
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status = lambda: None

        client = UnsplashClient(access_key="key")
        client.search_photos(query="test", per_page=100)

        call_kwargs = mock_get.call_args[1]["params"]
        assert call_kwargs["per_page"] == 30  # 최대 30으로 제한


# ════════════════════════════════════════════════════════════
# StockMediaManager
# ════════════════════════════════════════════════════════════


class TestStockMediaManagerQueryBuild:
    def _make_manager(self) -> StockMediaManager:
        pexels = MagicMock(spec=PexelsClient)
        unsplash = MagicMock(spec=UnsplashClient)
        return StockMediaManager(pexels, unsplash)

    def test_query_contains_channel_keyword(self):
        manager = self._make_manager()
        query = manager.get_search_query("ai_tech", "body", "neural network brain")
        assert "neural network brain" in query
        assert "artificial intelligence" in query

    def test_query_for_unknown_channel_uses_default(self):
        manager = self._make_manager()
        query = manager.get_search_query("unknown_ch", "body", "some visual")
        assert len(query) > 0

    def test_query_max_length(self):
        manager = self._make_manager()
        long_prompt = "word " * 50
        query = manager.get_search_query("psychology", "hook", long_prompt)
        assert len(query) <= 100


class TestStockMediaManagerFallback:
    def _make_manager(
        self,
        pexels_video_ok: bool = True,
        pexels_photo_ok: bool = True,
        unsplash_ok: bool = True,
    ) -> StockMediaManager:
        pexels = MagicMock(spec=PexelsClient)
        unsplash = MagicMock(spec=UnsplashClient)

        if not pexels_video_ok:
            pexels.download_video.side_effect = RuntimeError("Pexels video fail")
        else:
            pexels.download_video.side_effect = lambda **kw: kw["output_path"]

        if not pexels_photo_ok:
            pexels.download_photo.side_effect = RuntimeError("Pexels photo fail")
        else:
            pexels.download_photo.side_effect = lambda **kw: kw["output_path"]

        if not unsplash_ok:
            unsplash.download_photo.side_effect = RuntimeError("Unsplash fail")
        else:
            unsplash.download_photo.side_effect = lambda **kw: kw["output_path"]

        return StockMediaManager(pexels, unsplash)

    def test_returns_pexels_video_on_success(self, tmp_path):
        manager = self._make_manager(pexels_video_ok=True)
        result = manager.get_media_for_scene(
            channel="ai_tech",
            scene_role="body",
            visual_prompt="AI technology",
            output_path=tmp_path / "scene.mp4",
        )
        assert str(result).endswith(".mp4")

    def test_fallback_to_pexels_photo_when_video_fails(self, tmp_path):
        manager = self._make_manager(pexels_video_ok=False, pexels_photo_ok=True)
        result = manager.get_media_for_scene(
            channel="history",
            scene_role="body",
            visual_prompt="ancient ruins",
            output_path=tmp_path / "scene.mp4",
        )
        # 이미지 폴백이므로 .jpg 확장자
        assert str(result).endswith(".jpg")

    def test_fallback_to_unsplash_when_pexels_fails(self, tmp_path):
        manager = self._make_manager(pexels_video_ok=False, pexels_photo_ok=False, unsplash_ok=True)
        result = manager.get_media_for_scene(
            channel="space",
            scene_role="hook",
            visual_prompt="galaxy stars",
            output_path=tmp_path / "scene.mp4",
        )
        assert str(result).endswith(".jpg")

    def test_raises_when_all_sources_fail(self, tmp_path):
        manager = self._make_manager(
            pexels_video_ok=False,
            pexels_photo_ok=False,
            unsplash_ok=False,
        )
        with pytest.raises(RuntimeError, match="모든 소스"):
            manager.get_media_for_scene(
                channel="health",
                scene_role="body",
                visual_prompt="medical health",
                output_path=tmp_path / "scene.mp4",
            )

    def test_no_unsplash_two_pexels_fallbacks(self, tmp_path):
        """UnsplashClient 없이도 Pexels 폴백 체인 동작."""
        pexels = MagicMock(spec=PexelsClient)
        pexels.download_video.side_effect = RuntimeError("video fail")
        pexels.download_photo.side_effect = lambda **kw: kw["output_path"]

        manager = StockMediaManager(pexels, unsplash_client=None)
        result = manager.get_media_for_scene(
            channel="psychology",
            scene_role="body",
            visual_prompt="calm emotion",
            output_path=tmp_path / "scene.mp4",
        )
        assert str(result).endswith(".jpg")


class TestStockMediaManagerFromEnv:
    @patch.dict(
        "os.environ",
        {"PEXELS_API_KEY": "pexels_test", "UNSPLASH_API_KEY": "unsplash_test"},
    )
    def test_from_env_creates_both_clients(self):
        manager = StockMediaManager.from_env()
        assert isinstance(manager.pexels, PexelsClient)
        assert isinstance(manager.unsplash, UnsplashClient)

    @patch.dict("os.environ", {"PEXELS_API_KEY": "", "UNSPLASH_API_KEY": ""})
    def test_from_env_raises_without_pexels_key(self):
        with pytest.raises(EnvironmentError, match="PEXELS_API_KEY"):
            StockMediaManager.from_env()

    @patch.dict("os.environ", {"PEXELS_API_KEY": "only_pexels"}, clear=False)
    def test_from_env_without_unsplash_is_ok(self):
        import os
        os.environ.pop("UNSPLASH_API_KEY", None)
        manager = StockMediaManager.from_env()
        assert manager.unsplash is None
