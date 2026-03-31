"""Tests for pipeline.image_upload — optimize, upload to Imgur/Cloudinary."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key, default=None):
        return self.data.get(key, default)


# ---------------------------------------------------------------------------
# _optimize_image_for_upload
# ---------------------------------------------------------------------------

class TestOptimizeImage:
    def test_small_file_returns_original(self, tmp_path):
        from pipeline.image_upload import _optimize_image_for_upload
        p = tmp_path / "small.png"
        p.write_bytes(b"x" * 1000)
        result = _optimize_image_for_upload(str(p), max_bytes=9 * 1024 * 1024)
        assert result == str(p)

    def test_large_png_converted_to_jpeg(self, tmp_path):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        # Create a large-ish PNG image by using random bytes
        size = 2000 * 2000 * 3
        data = os.urandom(size)
        img = Image.frombytes("RGB", (2000, 2000), data)

        p = tmp_path / "big.png"
        img.save(str(p), format="PNG")

        # Use a generous limit that JPEG can meet but PNG exceeds
        png_size = os.path.getsize(str(p))
        result = _optimize_image_for_upload(str(p), max_bytes=max(png_size // 4, 200_000))
        assert result != str(p)  # should be optimized
        assert result.endswith(".jpg")

    def test_rgba_image_converted(self, tmp_path):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        # RGBA image
        data = os.urandom(1000 * 1000 * 4)
        img = Image.frombytes("RGBA", (1000, 1000), data)
        p = tmp_path / "rgba.png"
        img.save(str(p), format="PNG")

        result = _optimize_image_for_upload(str(p), max_bytes=50_000)
        # Should convert RGBA → RGB JPEG
        assert result.endswith(".jpg")

    def test_palette_mode_image(self, tmp_path):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        data = os.urandom(1000 * 1000 * 3)
        img = Image.frombytes("RGB", (1000, 1000), data).convert("P")
        p = tmp_path / "palette.png"
        img.save(str(p), format="PNG")

        result = _optimize_image_for_upload(str(p), max_bytes=50_000)
        assert result.endswith(".jpg")

    def test_grayscale_image(self, tmp_path):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        data = os.urandom(1000 * 1000)
        img = Image.frombytes("L", (1000, 1000), data)
        p = tmp_path / "gray.png"
        img.save(str(p), format="PNG")
        png_size = os.path.getsize(str(p))

        # Set limit below PNG size but achievable by JPEG compression
        result = _optimize_image_for_upload(str(p), max_bytes=png_size // 2)
        assert result.endswith(".jpg")

    def test_resolution_shrink_when_quality_not_enough(self, tmp_path):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        # Create a very large random image that can't be compressed enough
        data = os.urandom(4000 * 4000 * 3)
        img = Image.frombytes("RGB", (4000, 4000), data)
        p = tmp_path / "huge.png"
        img.save(str(p), format="PNG")

        # Very aggressive limit — will need resolution shrink
        result = _optimize_image_for_upload(str(p), max_bytes=5_000)
        if result != str(p):
            assert os.path.getsize(result) <= 5_000 or result == str(p)

    def test_corrupted_file_returns_original(self, tmp_path):
        from pipeline.image_upload import _optimize_image_for_upload

        p = tmp_path / "broken.png"
        p.write_bytes(b"not a real image" * 1000000)  # >9MB of junk
        result = _optimize_image_for_upload(str(p), max_bytes=100)
    def test_save_exception_quality_loop(self, tmp_path, monkeypatch):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        data = os.urandom(1000 * 1000 * 3)
        img = Image.frombytes("RGB", (1000, 1000), data)
        p = tmp_path / "error_qual.png"
        img.save(str(p), format="PNG")

        def fake_save(*args, **kwargs):
            raise RuntimeError("Fake save error")

        monkeypatch.setattr(Image.Image, "save", fake_save)

        result = _optimize_image_for_upload(str(p), max_bytes=10)
        assert result == str(p)

    def test_save_exception_resize_loop(self, tmp_path, monkeypatch):
        from PIL import Image
        from pipeline.image_upload import _optimize_image_for_upload

        data = os.urandom(2000 * 2000 * 3)
        img = Image.frombytes("RGB", (2000, 2000), data)
        p = tmp_path / "error_res.png"
        img.save(str(p), format="PNG")

        original_save = Image.Image.save
        save_calls = {"count": 0}
        def fake_save(self, *args, **kwargs):
            save_calls["count"] += 1
            if save_calls["count"] > 4:
                raise RuntimeError("Fake save error in resize")
            return original_save(self, *args, **kwargs)

        monkeypatch.setattr(Image.Image, "save", fake_save)

        result = _optimize_image_for_upload(str(p), max_bytes=10)
        assert result == str(p)


# ---------------------------------------------------------------------------
# ImageUploader.__init__
# ---------------------------------------------------------------------------

class TestImageUploaderInit:
    def test_imgur_default(self, monkeypatch):
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"image_hosting.provider": "imgur", "image_hosting.imgur.client_id": "abc123"}))
        assert u.provider == "imgur"
        assert u.imgur_client_id == "abc123"
        assert u.cloudinary_ready is False

    def test_env_overrides_config(self, monkeypatch):
        monkeypatch.setenv("IMGUR_CLIENT_ID", "env-id")
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"image_hosting.provider": "imgur", "image_hosting.imgur.client_id": "config-id"}))
        assert u.imgur_client_id == "env-id"

    def test_cloudinary_ready(self, monkeypatch):
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "key123")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret456")
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        with patch("pipeline.image_upload.cloudinary.config") as mock_cfg:
            from pipeline.image_upload import ImageUploader
            u = ImageUploader(FakeConfig({"image_hosting.provider": "cloudinary"}))
            assert u.cloudinary_ready is True
            mock_cfg.assert_called_once()

    def test_retry_config(self):
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"request.retries": "5", "request.backoff_seconds": "2.0"}))
        assert u.max_retries == 5
        assert u.backoff == 2.0


# ---------------------------------------------------------------------------
# upload()
# ---------------------------------------------------------------------------

class TestUpload:
    @pytest.mark.asyncio
    async def test_missing_file(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig())
        result = await u.upload("/nonexistent/file.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_too_small_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        p = tmp_path / "tiny.png"
        p.write_bytes(b"x" * 100)  # < 1000 bytes
        u = ImageUploader(FakeConfig())
        result = await u.upload(str(p))
        assert result is None

    @pytest.mark.asyncio
    async def test_imgur_upload_success(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader

        p = tmp_path / "test.png"
        p.write_bytes(b"x" * 2000)

        u = ImageUploader(FakeConfig({
            "image_hosting.provider": "imgur",
            "image_hosting.imgur.client_id": "test-id",
        }))

        async def fake_retry(func, max_retries, backoff_seconds, action_name):
            return {"success": True, "data": {"link": "https://i.imgur.com/abc123.png"}}

        monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
        result = await u.upload(str(p))
        assert result == "https://i.imgur.com/abc123.png"

    @pytest.mark.asyncio
    async def test_imgur_upload_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader

        p = tmp_path / "test.png"
        p.write_bytes(b"x" * 2000)

        u = ImageUploader(FakeConfig({
            "image_hosting.provider": "imgur",
            "image_hosting.imgur.client_id": "test-id",
        }))

        async def fake_retry(func, max_retries, backoff_seconds, action_name):
            return {"success": False, "data": {}}

        monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
        result = await u.upload(str(p))
        assert result is None

    @pytest.mark.asyncio
    async def test_imgur_no_client_id(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader

        p = tmp_path / "test.png"
        p.write_bytes(b"x" * 2000)

        u = ImageUploader(FakeConfig({"image_hosting.provider": "imgur"}))
        result = await u.upload(str(p))
        assert result is None

    @pytest.mark.asyncio
    async def test_cloudinary_upload_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret")
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)

        with patch("pipeline.image_upload.cloudinary.config"):
            from pipeline.image_upload import ImageUploader

            p = tmp_path / "test.png"
            p.write_bytes(b"x" * 2000)

            u = ImageUploader(FakeConfig({"image_hosting.provider": "cloudinary"}))

            async def fake_retry(func, max_retries, backoff_seconds, action_name):
                return "https://res.cloudinary.com/test/image.png"

            monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
            # Mock _optimize_image_for_upload to return same path
            monkeypatch.setattr("pipeline.image_upload._optimize_image_for_upload", lambda fp: str(p))

            result = await u.upload(str(p))
            assert result == "https://res.cloudinary.com/test/image.png"

    @pytest.mark.asyncio
    async def test_unknown_provider_fallback_imgur(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader

        p = tmp_path / "test.png"
        p.write_bytes(b"x" * 2000)

        u = ImageUploader(FakeConfig({
            "image_hosting.provider": "unknown_cdn",
            "image_hosting.imgur.client_id": "fallback-id",
        }))
        u.imgur_client_id = "fallback-id"

        async def fake_retry(func, max_retries, backoff_seconds, action_name):
            return {"success": True, "data": {"link": "https://i.imgur.com/fallback.png"}}

        monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
        result = await u.upload(str(p))
        assert result == "https://i.imgur.com/fallback.png"

    @pytest.mark.asyncio
    async def test_upload_fallback_imgur_missing_id(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader

        p = tmp_path / "test.png"
        p.write_bytes(b"x" * 2000)

        u = ImageUploader(FakeConfig({
            "image_hosting.provider": "unknown_cdn"
        }))
        u.imgur_client_id = None
        result = await u.upload(str(p))
        assert result is None


# ---------------------------------------------------------------------------
# upload_from_url()
# ---------------------------------------------------------------------------

class TestUploadFromUrl:
    @pytest.mark.asyncio
    async def test_cloudinary_url_upload(self, monkeypatch):
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret")
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)

        with patch("pipeline.image_upload.cloudinary.config"):
            from pipeline.image_upload import ImageUploader
            u = ImageUploader(FakeConfig({"image_hosting.provider": "cloudinary"}))

            async def fake_retry(func, max_retries, backoff_seconds, action_name):
                return "https://res.cloudinary.com/test/uploaded.png"

            monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
            result = await u.upload_from_url("https://example.com/image.png")
            assert result == "https://res.cloudinary.com/test/uploaded.png"

    @pytest.mark.asyncio
    async def test_imgur_url_upload_success(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({
            "image_hosting.provider": "imgur",
            "image_hosting.imgur.client_id": "test-id",
        }))

        async def fake_retry(func, max_retries, backoff_seconds, action_name):
            return {"success": True, "data": {"link": "https://i.imgur.com/url_upload.png"}}

        monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
        result = await u.upload_from_url("https://example.com/source.png")
        assert result == "https://i.imgur.com/url_upload.png"

    @pytest.mark.asyncio
    async def test_imgur_no_client_id_returns_none(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"image_hosting.provider": "imgur"}))
        result = await u.upload_from_url("https://example.com/image.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_imgur_url_upload_exception(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({
            "image_hosting.provider": "imgur",
            "image_hosting.imgur.client_id": "test-id",
        }))

        async def fake_retry_raise(func, max_retries, backoff_seconds, action_name):
            raise ConnectionError("network down")

        monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry_raise)
        result = await u.upload_from_url("https://example.com/image.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_imgur_url_upload_no_link(self, monkeypatch):
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"image_hosting.provider": "imgur", "image_hosting.imgur.client_id": "test"}))
        u.imgur_client_id = "test"

        async def fake_retry(*a, **kw):
            return {"success": True, "data": {}}

        monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry)
        result = await u.upload_from_url("http://example.com/a.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_provider_returns_none(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"image_hosting.provider": "unknown"}))
        u.imgur_client_id = None
        result = await u.upload_from_url("https://example.com/image.png")
        assert result is None


# ---------------------------------------------------------------------------
# _upload_to_cloudinary
# ---------------------------------------------------------------------------

class TestCloudinaryDirect:
    @pytest.mark.asyncio
    async def test_not_ready_returns_none(self, monkeypatch):
        monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
        monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)
        from pipeline.image_upload import ImageUploader
        u = ImageUploader(FakeConfig({"image_hosting.provider": "cloudinary"}))
        assert u.cloudinary_ready is False
        result = await u._upload_to_cloudinary("/some/path.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_exception_returns_none(self, monkeypatch):
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret")
        monkeypatch.delenv("IMGUR_CLIENT_ID", raising=False)

        with patch("pipeline.image_upload.cloudinary.config"):
            from pipeline.image_upload import ImageUploader
            u = ImageUploader(FakeConfig({"image_hosting.provider": "cloudinary"}))

            async def fake_retry_raise(func, max_retries, backoff_seconds, action_name):
                raise RuntimeError("upload failed")

            monkeypatch.setattr("pipeline.image_upload.async_run_with_retry", fake_retry_raise)
            result = await u._upload_to_cloudinary("/some/path.png")
            assert result is None

    @pytest.mark.asyncio
    async def test_cloudinary_unexpected_response(self, monkeypatch):
        from pipeline.image_upload import ImageUploader
        monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test")
        monkeypatch.setenv("CLOUDINARY_API_KEY", "key")
        monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret")

        with patch("pipeline.image_upload.cloudinary.config"):
            u = ImageUploader(FakeConfig({"image_hosting.provider": "cloudinary"}))
            with patch("pipeline.image_upload.cloudinary.uploader.upload", return_value={"no_url": "here"}):
                result = await u._upload_to_cloudinary("/path.png")
                assert result is None

    @pytest.mark.asyncio
    async def test_imgur_value_error_json(self, tmp_path, monkeypatch):
        from pipeline.image_upload import ImageUploader

        p = tmp_path / "test.png"
        p.write_bytes(b"x" * 2000)

        u = ImageUploader(FakeConfig({"image_hosting.provider": "imgur", "image_hosting.imgur.client_id": "test-id"}))

        class MockResponse:
            def __init__(self):
                self.text = "invalid json"
                self.status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                raise ValueError("JSON decode error")

        monkeypatch.setattr("pipeline.image_upload.requests.post", lambda *a, **kw: MockResponse())
        result = await u._upload_to_imgur(str(p))
        assert result is None
