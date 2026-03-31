"""Tests for shorts_maker_v2.providers.google_client — Google Gemini/Veo/Imagen wrapper.

All Google SDK calls are fully mocked so no real API calls or costs are incurred.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.providers import google_client

# ═══════════════════════════════════════════════════════════════════
# __init__
# ═══════════════════════════════════════════════════════════════════


class TestInit:
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_empty_api_key_raises(self, mock_genai):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            google_client.GoogleClient(api_key="")

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_creates_client(self, mock_genai):
        client = google_client.GoogleClient(api_key="fake-key")
        mock_genai.Client.assert_called_once_with(api_key="fake-key")
        assert client.request_timeout_sec == 180


# ═══════════════════════════════════════════════════════════════════
# generate_video
# ═══════════════════════════════════════════════════════════════════


class TestGenerateVideo:
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_cached_skips_api(self, mock_genai, tmp_path: Path):
        out = tmp_path / "video.mp4"
        out.write_bytes(b"existing-video")
        client = google_client.GoogleClient(api_key="k")
        result = client.generate_video(
            model="veo-2.0-generate-001",
            prompt="cat",
            aspect_ratio="9:16",
            duration_seconds=5,
            output_path=out,
        )
        assert result == out
        mock_genai.Client.return_value.models.generate_videos.assert_not_called()

    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_save_path(self, mock_genai, mock_time, tmp_path: Path):
        """When video_obj.save() works, output is returned."""
        out = tmp_path / "sub" / "video.mp4"
        mock_client = mock_genai.Client.return_value

        # Operation completes immediately
        operation = MagicMock()
        operation.done = True
        video_obj = MagicMock()
        video_obj.save.side_effect = lambda p: Path(p).write_bytes(b"video-data")
        operation.response.generated_videos = [MagicMock(video=video_obj)]
        mock_client.models.generate_videos.return_value = operation

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_video(
            model="veo-2.0-generate-001",
            prompt="cat",
            aspect_ratio="9:16",
            duration_seconds=5,
            output_path=out,
        )
        assert result == out
        assert out.read_bytes() == b"video-data"

    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_video_bytes_raw(self, mock_genai, mock_time, tmp_path: Path):
        """When video_obj has raw video_bytes."""
        out = tmp_path / "video.mp4"
        mock_client = mock_genai.Client.return_value

        operation = MagicMock()
        operation.done = True
        video_obj = MagicMock(spec=[])  # No save method
        video_obj.video_bytes = b"raw-video"
        video_obj.uri = None
        operation.response.generated_videos = [MagicMock(video=video_obj)]
        mock_client.models.generate_videos.return_value = operation

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_video(
            model="veo",
            prompt="dog",
            aspect_ratio="16:9",
            duration_seconds=5,
            output_path=out,
        )
        assert result == out
        assert out.read_bytes() == b"raw-video"

    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_video_bytes_base64(self, mock_genai, mock_time, tmp_path: Path):
        """When video_bytes is base64 string."""
        import base64

        out = tmp_path / "video.mp4"
        mock_client = mock_genai.Client.return_value

        operation = MagicMock()
        operation.done = True
        video_obj = MagicMock(spec=[])
        video_obj.video_bytes = base64.b64encode(b"decoded-video").decode()
        video_obj.uri = None
        operation.response.generated_videos = [MagicMock(video=video_obj)]
        mock_client.models.generate_videos.return_value = operation

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_video(
            model="veo",
            prompt="x",
            aspect_ratio="9:16",
            duration_seconds=5,
            output_path=out,
        )
        assert result == out
        assert out.read_bytes() == b"decoded-video"

    @patch("shorts_maker_v2.providers.google_client.requests.get")
    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_uri_download(self, mock_genai, mock_time, mock_get, tmp_path: Path):
        """When video_obj has a URI to download."""
        out = tmp_path / "video.mp4"
        mock_client = mock_genai.Client.return_value

        operation = MagicMock()
        operation.done = True
        video_obj = MagicMock(spec=[])
        video_obj.video_bytes = None
        video_obj.uri = "https://example.com/video.mp4"
        operation.response.generated_videos = [MagicMock(video=video_obj)]
        mock_client.models.generate_videos.return_value = operation

        dl_resp = MagicMock()
        dl_resp.content = b"downloaded-video"
        dl_resp.raise_for_status.return_value = None
        mock_get.return_value = dl_resp

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_video(
            model="veo",
            prompt="x",
            aspect_ratio="9:16",
            duration_seconds=5,
            output_path=out,
        )
        assert result == out
        assert out.read_bytes() == b"downloaded-video"

    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_timeout_raises(self, mock_genai, mock_time, tmp_path: Path):
        out = tmp_path / "video.mp4"
        mock_client = mock_genai.Client.return_value

        operation = MagicMock()
        operation.done = False
        mock_client.models.generate_videos.return_value = operation
        mock_client.operations.get.return_value = operation

        # Simulate time advancing past timeout
        mock_time.monotonic.side_effect = [0.0, 999.0]
        mock_time.sleep = MagicMock()

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(TimeoutError, match="Timed out"):
            client.generate_video(
                model="veo",
                prompt="x",
                aspect_ratio="9:16",
                duration_seconds=5,
                output_path=out,
                timeout_sec=10,
            )

    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_no_response_raises(self, mock_genai, mock_time, tmp_path: Path):
        out = tmp_path / "video.mp4"
        mock_client = mock_genai.Client.return_value

        operation = MagicMock()
        operation.done = True
        operation.response = None
        mock_client.models.generate_videos.return_value = operation

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="returned no videos"):
            client.generate_video(
                model="veo",
                prompt="x",
                aspect_ratio="9:16",
                duration_seconds=5,
                output_path=out,
            )

    @patch("shorts_maker_v2.providers.google_client.time")
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_unsaveable_video_raises(self, mock_genai, mock_time, tmp_path: Path):
        """Video object has no save, no video_bytes, no uri → RuntimeError."""
        out = tmp_path / "video.mp4"
        mock_client = mock_genai.Client.return_value

        operation = MagicMock()
        operation.done = True
        video_obj = MagicMock(spec=[])
        video_obj.video_bytes = None
        video_obj.uri = None
        operation.response.generated_videos = [MagicMock(video=video_obj)]
        mock_client.models.generate_videos.return_value = operation

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="could not be saved"):
            client.generate_video(
                model="veo",
                prompt="x",
                aspect_ratio="9:16",
                duration_seconds=5,
                output_path=out,
            )


# ═══════════════════════════════════════════════════════════════════
# generate_image
# ═══════════════════════════════════════════════════════════════════


class TestGenerateImage:
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_cached_skips_api(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        out.write_bytes(b"existing")
        client = google_client.GoogleClient(api_key="k")
        result = client.generate_image(prompt="cat", output_path=out)
        assert result == out

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_success(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        image_data = b"\x89PNG" * 500  # > 1000 bytes
        part = MagicMock()
        part.inline_data.data = image_data
        candidate = MagicMock()
        candidate.content.parts = [part]
        response = MagicMock()
        response.candidates = [candidate]
        mock_client.models.generate_content.return_value = response

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_image(prompt="cat", output_path=out)
        assert result == out
        assert out.read_bytes() == image_data

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_too_small_image_raises(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        part = MagicMock()
        part.inline_data.data = b"tiny"  # < 1000 bytes
        candidate = MagicMock()
        candidate.content.parts = [part]
        response = MagicMock()
        response.candidates = [candidate]
        mock_client.models.generate_content.return_value = response

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="too-small image"):
            client.generate_image(prompt="cat", output_path=out)

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_no_image_data_raises(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        part = MagicMock()
        part.inline_data = None
        candidate = MagicMock()
        candidate.content.parts = [part]
        response = MagicMock()
        response.candidates = [candidate]
        mock_client.models.generate_content.return_value = response

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="no image data"):
            client.generate_image(prompt="cat", output_path=out)


# ═══════════════════════════════════════════════════════════════════
# generate_image_imagen3
# ═══════════════════════════════════════════════════════════════════


class TestGenerateImageImagen3:
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_cached_skips_api(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        out.write_bytes(b"existing")
        client = google_client.GoogleClient(api_key="k")
        result = client.generate_image_imagen3(prompt="cat", output_path=out)
        assert result == out

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_first_model_succeeds(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        image_data = b"\x89PNG" * 500
        image_obj = MagicMock()
        image_obj.image_bytes = image_data
        response = MagicMock()
        response.generated_images = [MagicMock(image=image_obj)]
        mock_client.models.generate_images.return_value = response

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_image_imagen3(prompt="dog", output_path=out)
        assert result == out
        assert out.read_bytes() == image_data

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_fallback_to_second_model(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        image_data = b"\x89PNG" * 500
        image_obj = MagicMock()
        image_obj.image_bytes = image_data
        success_resp = MagicMock()
        success_resp.generated_images = [MagicMock(image=image_obj)]

        # First model fails, second succeeds
        mock_client.models.generate_images.side_effect = [
            RuntimeError("model 1 failed"),
            success_resp,
        ]

        client = google_client.GoogleClient(api_key="k")
        result = client.generate_image_imagen3(prompt="x", output_path=out)
        assert result == out

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_all_models_fail(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value
        mock_client.models.generate_images.side_effect = RuntimeError("fail")

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="All Imagen 3 models failed"):
            client.generate_image_imagen3(prompt="x", output_path=out)

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_no_generated_images_triggers_fallback(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        empty_resp = MagicMock()
        empty_resp.generated_images = []
        mock_client.models.generate_images.return_value = empty_resp

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="All Imagen 3 models failed"):
            client.generate_image_imagen3(prompt="x", output_path=out)

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_too_small_image_triggers_fallback(self, mock_genai, tmp_path: Path):
        out = tmp_path / "img.png"
        mock_client = mock_genai.Client.return_value

        image_obj = MagicMock()
        image_obj.image_bytes = b"tiny"
        response = MagicMock()
        response.generated_images = [MagicMock(image=image_obj)]
        mock_client.models.generate_images.return_value = response

        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(RuntimeError, match="All Imagen 3 models failed"):
            client.generate_image_imagen3(prompt="x", output_path=out)


# ═══════════════════════════════════════════════════════════════════
# embed_content
# ═══════════════════════════════════════════════════════════════════


class TestEmbedContent:
    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_text_embedding(self, mock_genai):
        mock_client = mock_genai.Client.return_value
        emb = MagicMock()
        emb.values = [0.1, 0.2, 0.3]
        mock_client.models.embed_content.return_value = MagicMock(embeddings=[emb])

        client = google_client.GoogleClient(api_key="k")
        result = client.embed_content(contents=["hello"])
        assert result == [[0.1, 0.2, 0.3]]

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_multimodal_embedding(self, mock_genai):
        mock_client = mock_genai.Client.return_value
        emb1 = MagicMock(values=[0.1, 0.2])
        emb2 = MagicMock(values=[0.3, 0.4])
        mock_client.models.embed_content.return_value = MagicMock(embeddings=[emb1, emb2])

        client = google_client.GoogleClient(api_key="k")
        result = client.embed_content(contents=["text", (b"\x89PNG", "image/png")])
        assert len(result) == 2

    @patch("shorts_maker_v2.providers.google_client.genai")
    def test_invalid_content_raises(self, mock_genai):
        client = google_client.GoogleClient(api_key="k")
        with pytest.raises(ValueError, match="Invalid content item"):
            client.embed_content(contents=[12345])


# ═══════════════════════════════════════════════════════════════════
# compute_similarity
# ═══════════════════════════════════════════════════════════════════


class TestComputeSimilarity:
    def test_identical_vectors(self):
        sim = google_client.GoogleClient.compute_similarity([1.0, 0.0], [1.0, 0.0])
        assert sim == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        sim = google_client.GoogleClient.compute_similarity([1.0, 0.0], [0.0, 1.0])
        assert sim == pytest.approx(0.0)

    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError, match="dimension mismatch"):
            google_client.GoogleClient.compute_similarity([1.0], [1.0, 2.0])

    def test_zero_norm_returns_zero(self):
        sim = google_client.GoogleClient.compute_similarity([0.0, 0.0], [1.0, 2.0])
        assert sim == 0.0
