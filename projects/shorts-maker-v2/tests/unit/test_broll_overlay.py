"""Tests for shorts_maker_v2.render.broll_overlay — B-Roll PIP overlay.

HTTP calls are fully mocked; MoviePy ImageClip is mocked to avoid real rendering.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.render import broll_overlay

# ── helpers ────────────────────────────────────────────────────────


def _fake_response(status_code: int = 200, content: bytes = b"\x89PNG" * 500, json_data=None):
    """Create a minimal requests.Response-like mock."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


# ═══════════════════════════════════════════════════════════════════
# _fetch_pexels_image
# ═══════════════════════════════════════════════════════════════════


class TestFetchPexelsImage:
    def test_no_api_key_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("PEXELS_API_KEY", raising=False)
        result = broll_overlay._fetch_pexels_image("test", tmp_path / "img.png")
        assert result is None

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    def test_success(self, mock_get, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PEXELS_API_KEY", "fake-key")

        search_resp = _fake_response(json_data={"photos": [{"src": {"medium": "https://example.com/photo.jpg"}}]})
        img_content = b"\xff\xd8\xff" + b"\x00" * 2000  # > 1000 bytes
        img_resp = _fake_response(content=img_content)
        mock_get.side_effect = [search_resp, img_resp]

        out = tmp_path / "pexels.png"
        result = broll_overlay._fetch_pexels_image("sunset", out)
        assert result == out
        assert out.exists()
        assert out.read_bytes() == img_content

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    def test_bad_status_returns_none(self, mock_get, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PEXELS_API_KEY", "k")
        mock_get.return_value = _fake_response(status_code=403)
        assert broll_overlay._fetch_pexels_image("q", tmp_path / "x.png") is None

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    def test_no_photos_returns_none(self, mock_get, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PEXELS_API_KEY", "k")
        mock_get.return_value = _fake_response(json_data={"photos": []})
        assert broll_overlay._fetch_pexels_image("q", tmp_path / "x.png") is None

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    def test_no_medium_url_returns_none(self, mock_get, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PEXELS_API_KEY", "k")
        mock_get.return_value = _fake_response(json_data={"photos": [{"src": {}}]})
        assert broll_overlay._fetch_pexels_image("q", tmp_path / "x.png") is None

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    def test_small_image_returns_none(self, mock_get, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PEXELS_API_KEY", "k")
        search_resp = _fake_response(json_data={"photos": [{"src": {"medium": "http://x"}}]})
        img_resp = _fake_response(content=b"tiny")  # < 1000 bytes
        mock_get.side_effect = [search_resp, img_resp]
        assert broll_overlay._fetch_pexels_image("q", tmp_path / "x.png") is None

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    def test_network_error_returns_none(self, mock_get, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PEXELS_API_KEY", "k")
        mock_get.side_effect = ConnectionError("network down")
        assert broll_overlay._fetch_pexels_image("q", tmp_path / "x.png") is None


# ═══════════════════════════════════════════════════════════════════
# _ensure_broll_image
# ═══════════════════════════════════════════════════════════════════


class TestEnsureBrollImage:
    def test_cached_file_reused(self, tmp_path: Path):
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        # Pre-create a cached file matching the expected name pattern
        import urllib.parse

        safe = urllib.parse.quote_plus("test_prompt"[:50])
        cached = cache_dir / f"broll_{safe}.png"
        cached.write_bytes(b"cached-img-data")

        result = broll_overlay._ensure_broll_image(cache_dir, "test_prompt")
        assert result == cached
        assert result.read_bytes() == b"cached-img-data"

    @patch("shorts_maker_v2.render.broll_overlay._fetch_pexels_image")
    def test_pexels_hit(self, mock_pexels, tmp_path: Path):
        def fake_pexels(query, path):
            path.write_bytes(b"pexels-data")
            return path

        mock_pexels.side_effect = fake_pexels
        result = broll_overlay._ensure_broll_image(tmp_path / "cache", "sunset")
        assert result is not None
        assert result.exists()

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    @patch("shorts_maker_v2.render.broll_overlay._fetch_pexels_image", return_value=None)
    def test_pollinations_fallback(self, mock_pexels, mock_get, tmp_path: Path):
        img_data = b"\x89PNG" * 500  # > 1000 bytes
        mock_get.return_value = _fake_response(content=img_data)
        result = broll_overlay._ensure_broll_image(tmp_path / "cache", "mountain")
        assert result is not None
        assert result.exists()

    @patch("shorts_maker_v2.render.broll_overlay.requests.get")
    @patch("shorts_maker_v2.render.broll_overlay._fetch_pexels_image", return_value=None)
    def test_all_sources_fail(self, mock_pexels, mock_get, tmp_path: Path):
        mock_get.side_effect = ConnectionError("fail")
        result = broll_overlay._ensure_broll_image(tmp_path / "cache", "nothing")
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# create_broll_pip
# ═══════════════════════════════════════════════════════════════════


class TestCreateBrollPip:
    @patch("shorts_maker_v2.render.broll_overlay._ensure_broll_image")
    @patch("shorts_maker_v2.render.broll_overlay.ImageClip")
    def test_success(self, MockImageClip, mock_ensure, tmp_path: Path):
        broll_path = tmp_path / "broll.png"
        broll_path.write_bytes(b"img")
        mock_ensure.return_value = broll_path

        pip_clip = MagicMock()
        pip_clip.w = 100
        pip_clip.h = 100
        pip_clip.with_duration.return_value = pip_clip
        pip_clip.with_start.return_value = pip_clip
        pip_clip.resized.return_value = pip_clip
        pip_clip.with_position.return_value = pip_clip
        MockImageClip.return_value = pip_clip

        base_clip = MagicMock()
        base_clip.duration = 5.0

        result = broll_overlay.create_broll_pip(base_clip, tmp_path, "space", 1080, 1920, start_time=1.0, duration=3.0)
        assert result is not None

    @patch("shorts_maker_v2.render.broll_overlay._ensure_broll_image", return_value=None)
    def test_no_image_returns_none(self, mock_ensure, tmp_path: Path):
        result = broll_overlay.create_broll_pip(MagicMock(), tmp_path, "q", 1080, 1920)
        assert result is None

    @patch("shorts_maker_v2.render.broll_overlay._ensure_broll_image")
    @patch("shorts_maker_v2.render.broll_overlay.ImageClip", side_effect=Exception("load error"))
    def test_load_error_returns_none(self, MockImageClip, mock_ensure, tmp_path: Path):
        mock_ensure.return_value = tmp_path / "exists.png"
        (tmp_path / "exists.png").write_bytes(b"x")
        result = broll_overlay.create_broll_pip(MagicMock(), tmp_path, "q", 1080, 1920)
        assert result is None

    @patch("shorts_maker_v2.render.broll_overlay._ensure_broll_image")
    @patch("shorts_maker_v2.render.broll_overlay.ImageClip")
    def test_opacity_fallback_without_with_opacity(self, MockImageClip, mock_ensure, tmp_path: Path):
        broll_path = tmp_path / "broll.png"
        broll_path.write_bytes(b"img")
        mock_ensure.return_value = broll_path

        pip_clip = MagicMock()
        pip_clip.w = 200
        pip_clip.h = 200
        pip_clip.with_duration.return_value = pip_clip
        pip_clip.with_start.return_value = pip_clip
        pip_clip.resized.return_value = pip_clip
        pip_clip.with_position.return_value = pip_clip
        # Remove with_opacity so the fallback mask path is triggered
        del pip_clip.with_opacity
        pip_clip.with_mask.return_value = pip_clip
        MockImageClip.return_value = pip_clip

        result = broll_overlay.create_broll_pip(MagicMock(duration=5.0), tmp_path, "icon", 1080, 1920)
        assert result is not None

    @patch("shorts_maker_v2.render.broll_overlay._ensure_broll_image")
    @patch("shorts_maker_v2.render.broll_overlay.ImageClip")
    def test_opacity_exception_is_swallowed(self, MockImageClip, mock_ensure, tmp_path: Path):
        """When both with_opacity and numpy mask fallback fail, the except passes silently."""
        broll_path = tmp_path / "broll.png"
        broll_path.write_bytes(b"img")
        mock_ensure.return_value = broll_path

        pip_clip = MagicMock()
        pip_clip.w = 200
        pip_clip.h = 200
        pip_clip.with_duration.return_value = pip_clip
        pip_clip.with_start.return_value = pip_clip
        pip_clip.resized.return_value = pip_clip
        pip_clip.with_position.return_value = pip_clip
        # with_opacity raises → enters except block
        pip_clip.with_opacity.side_effect = RuntimeError("opacity unsupported")
        MockImageClip.return_value = pip_clip

        result = broll_overlay.create_broll_pip(MagicMock(duration=5.0), tmp_path, "icon", 1080, 1920)
        assert result is not None
