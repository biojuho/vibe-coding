"""Tests for pipeline.image_generator — prompt building, validation, and async generation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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
# _env_flag
# ---------------------------------------------------------------------------


class TestEnvFlag:
    def test_none_returns_none(self, monkeypatch):
        monkeypatch.delenv("TEST_FLAG_XYZ", raising=False)
        from pipeline.image_generator import _env_flag

        assert _env_flag("TEST_FLAG_XYZ") is None

    @pytest.mark.parametrize(
        "val,expected",
        [
            ("1", True),
            ("true", True),
            ("yes", True),
            ("on", True),
            ("TRUE", True),
            ("  Yes  ", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("off", False),
            ("random", False),
        ],
    )
    def test_truthy_falsy(self, monkeypatch, val, expected):
        monkeypatch.setenv("TEST_FLAG_XYZ", val)
        from pipeline.image_generator import _env_flag

        assert _env_flag("TEST_FLAG_XYZ") is expected


# ---------------------------------------------------------------------------
# build_image_prompt (static, pure)
# ---------------------------------------------------------------------------


class TestBuildImagePrompt:
    def _call(self, **kw):
        from pipeline.image_generator import ImageGenerator

        return ImageGenerator.build_image_prompt(**kw)

    def test_blind_source_uses_anime_style(self):
        prompt = self._call(topic_cluster="연봉", emotion_axis="분노", source="blind")
        assert "Pixar" in prompt
        assert "no text" in prompt.lower()

    def test_blind_korean_source(self):
        prompt = self._call(source="블라인드", topic_cluster="이직")
        assert "Pixar" in prompt

    def test_ppomppu_source(self):
        prompt = self._call(source="ppomppu", topic_cluster="재테크", emotion_axis="웃김")
        assert "shopping" in prompt.lower() or "deal" in prompt.lower()
        assert "no text" in prompt.lower()

    def test_fmkorea_source(self):
        prompt = self._call(source="fmkorea")
        assert "forum" in prompt.lower() or "internet" in prompt.lower()

    def test_jobplanet_source(self):
        prompt = self._call(source="잡플래닛")
        assert "review" in prompt.lower() or "dashboard" in prompt.lower()

    def test_generic_source_uses_topic_style(self):
        prompt = self._call(topic_cluster="연봉")
        assert "infographic" in prompt.lower() or "blue" in prompt.lower()
        assert "no text" in prompt.lower()

    def test_unknown_topic_uses_default(self):
        prompt = self._call(topic_cluster="알수없음")
        assert "modern illustration" in prompt.lower()

    def test_emotion_override(self):
        prompt = self._call(topic_cluster="복지", emotion_axis="분노")
        assert "intense" in prompt.lower() or "frustrated" in prompt.lower()

    def test_none_source_safe(self):
        # source=None should not raise
        prompt = self._call(source=None, topic_cluster="IT")
        assert isinstance(prompt, str)
        assert len(prompt) > 10

    def test_empty_everything(self):
        prompt = self._call()
        assert isinstance(prompt, str)
        assert "no text" in prompt.lower()


# ---------------------------------------------------------------------------
# _build_blind_anime_prompt (static, pure)
# ---------------------------------------------------------------------------


class TestBuildBlindAnimePrompt:
    def _call(self, **kw):
        from pipeline.image_generator import ImageGenerator

        return ImageGenerator._build_blind_anime_prompt(**kw)

    def test_semantic_scene_matched(self):
        prompt = self._call(topic_cluster="연봉", emotion_axis="분노")
        assert "paycheck" in prompt.lower() or "angrily" in prompt.lower()
        assert "Pixar" in prompt

    def test_topic_scene_fallback(self):
        # emotion not in _SEMANTIC_SCENES for this topic
        prompt = self._call(topic_cluster="정치", emotion_axis="기대감")
        assert "news" in prompt.lower() or "phone" in prompt.lower()

    def test_default_pool_fallback(self):
        prompt = self._call(topic_cluster="미분류", emotion_axis="unknown")
        assert "Pixar" in prompt
        # expression should be the default
        assert "expressive and relatable" in prompt.lower()

    def test_emotion_expression_mapping(self):
        prompt = self._call(topic_cluster="이직", emotion_axis="경악")
        assert "shocked" in prompt.lower() or "wide-eyed" in prompt.lower()

    def test_constraints_present(self):
        prompt = self._call(topic_cluster="IT", emotion_axis="웃김")
        assert "no text" in prompt.lower()
        assert "16:9" in prompt


# ---------------------------------------------------------------------------
# _validate_image (static)
# ---------------------------------------------------------------------------


class TestValidateImage:
    def _call(self, path):
        from pipeline.image_generator import ImageGenerator

        return ImageGenerator._validate_image(path)

    def test_valid_image(self, tmp_path):
        from PIL import Image
        import numpy as np

        img = Image.fromarray(np.random.randint(0, 255, (512, 512, 3), dtype="uint8"))
        p = tmp_path / "ok.png"
        img.save(str(p))
        valid, reason = self._call(str(p))
        assert valid is True
        assert reason == ""

    def test_too_small(self, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        p = tmp_path / "tiny.png"
        img.save(str(p))
        valid, reason = self._call(str(p))
        assert valid is False
        assert "too_small" in reason

    def test_uniform_image(self, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (512, 512), color=(128, 128, 128))
        p = tmp_path / "flat.png"
        img.save(str(p))
        valid, reason = self._call(str(p))
        assert valid is False
        assert "too_uniform" in reason

    def test_nonexistent_file(self):
        valid, reason = self._call("/nonexistent/path.png")
        assert valid is False
        assert "open_failed" in reason


# ---------------------------------------------------------------------------
# ImageGenerator.__init__
# ---------------------------------------------------------------------------


class TestImageGeneratorInit:
    def test_gemini_provider_with_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
        fake_genai = MagicMock()
        fake_client = MagicMock()
        fake_genai.Client.return_value = fake_client
        with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": fake_genai}):
            from pipeline.image_generator import ImageGenerator

            gen = ImageGenerator(FakeConfig({"image.provider": "gemini"}))
            assert gen.provider == "gemini"
            assert gen._gemini_client is not None

    def test_gemini_no_key_falls_to_pollinations(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "gemini"}))
        assert gen.provider == "pollinations"

    def test_pollinations_provider(self):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        assert gen.provider == "pollinations"

    def test_dalle_disabled_falls_to_pollinations(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_IMAGE_ENABLED", raising=False)
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "dalle", "openai.enabled": False}))
        assert gen.provider == "pollinations"

    def test_dalle_enabled(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        monkeypatch.setenv("OPENAI_IMAGE_ENABLED", "true")
        mock_client = MagicMock()
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            from pipeline.image_generator import ImageGenerator

            gen = ImageGenerator(FakeConfig({"image.provider": "dalle"}))
            assert gen.provider == "dalle"
            assert gen.client is not None


# ---------------------------------------------------------------------------
# generate_image (async)
# ---------------------------------------------------------------------------


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_empty_prompt_returns_none(self):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        result = await gen.generate_image("")
        assert result is None

    @pytest.mark.asyncio
    async def test_short_prompt_returns_none(self):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        result = await gen.generate_image("too short")
        assert result is None

    @pytest.mark.asyncio
    async def test_pollinations_success(self, tmp_path, monkeypatch):
        from PIL import Image
        import numpy as np

        # Create a valid image file to return
        img_path = str(tmp_path / "poll.png")
        img = Image.fromarray(np.random.randint(0, 255, (512, 512, 3), dtype="uint8"))
        img.save(img_path)
        img_bytes = open(img_path, "rb").read()

        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))

        # Mock aiohttp to return valid image bytes
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=img_bytes)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_session_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr("pipeline.image_generator.aiohttp.ClientSession", lambda **kw: mock_session)

        # Mock ImageCache to avoid side effects
        monkeypatch.setattr(
            "pipeline.image_generator.ImageGenerator._validate_image", staticmethod(lambda p: (True, ""))
        )

        prompt = "A beautiful modern office illustration with warm colors and detailed scenery"
        result = await gen.generate_image(prompt)
        assert result is not None

    @pytest.mark.asyncio
    async def test_gemini_fallback_to_pollinations(self, monkeypatch):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        gen.provider = "gemini"
        gen._gemini_client = None  # no client → _generate_gemini returns None

        # Mock _generate_pollinations
        gen._generate_pollinations = AsyncMock(return_value="/fake/path.png")
        monkeypatch.setattr(ImageGenerator, "_validate_image", staticmethod(lambda p: (True, "")))

        prompt = "A colorful illustration of a Korean office worker at desk with coffee"
        result = await gen.generate_image(prompt)
        assert result == "/fake/path.png"
        gen._generate_pollinations.assert_called_once()

    @pytest.mark.asyncio
    async def test_dalle_no_client_returns_none(self):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        result = await gen._generate_dalle("some prompt here with enough words for testing")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self, monkeypatch):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))

        fake_cache = MagicMock()
        fake_cache.get.return_value = "/cached/image.png"

        from pipeline import image_cache as _ic

        monkeypatch.setattr(_ic, "ImageCache", lambda: fake_cache)

        prompt = "A modern office scene with professional lighting and warm tones"
        result = await gen.generate_image(prompt, topic_cluster="연봉", emotion_axis="공감")
        assert result == "/cached/image.png"


# ---------------------------------------------------------------------------
# _generate_gemini
# ---------------------------------------------------------------------------


class TestGenerateGemini:
    @pytest.mark.asyncio
    async def test_no_client_returns_none(self):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        gen._gemini_client = None
        result = await gen._generate_gemini("test prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_too_small_image_skipped(self, monkeypatch):
        from pipeline.image_generator import ImageGenerator

        fake_part = SimpleNamespace(inline_data=SimpleNamespace(data=b"tiny"))
        fake_candidate = SimpleNamespace(content=SimpleNamespace(parts=[fake_part]))
        fake_response = SimpleNamespace(candidates=[fake_candidate])

        fake_client = MagicMock()
        fake_client.models.generate_content = MagicMock(return_value=fake_response)

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))
        gen.provider = "gemini"
        gen._gemini_client = fake_client

        # Mock asyncio.to_thread to call synchronously
        monkeypatch.setattr("pipeline.image_generator.asyncio.to_thread", AsyncMock(return_value=fake_response))

        # Mock google.genai.types
        fake_types = MagicMock()
        monkeypatch.setattr("pipeline.image_generator.types", fake_types, raising=False)
        with patch.dict("sys.modules", {"google.genai": MagicMock(types=fake_types), "google.genai.types": fake_types}):
            result = await gen._generate_gemini("test prompt with enough words")
        assert result is None


# ---------------------------------------------------------------------------
# _generate_pollinations
# ---------------------------------------------------------------------------


class TestGeneratePollinations:
    @pytest.mark.asyncio
    async def test_http_error(self, monkeypatch):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))

        mock_resp = AsyncMock()
        mock_resp.status = 500

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr("pipeline.image_generator.aiohttp.ClientSession", lambda **kw: mock_session)

        result = await gen._generate_pollinations("a test prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_too_small_response(self, monkeypatch):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b"tiny")

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_ctx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        monkeypatch.setattr("pipeline.image_generator.aiohttp.ClientSession", lambda **kw: mock_session)

        result = await gen._generate_pollinations("a test prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_network_exception(self, monkeypatch):
        from pipeline.image_generator import ImageGenerator

        gen = ImageGenerator(FakeConfig({"image.provider": "pollinations"}))

        def raise_err(**kw):
            raise ConnectionError("network down")

        monkeypatch.setattr("pipeline.image_generator.aiohttp.ClientSession", raise_err)
        result = await gen._generate_pollinations("a test prompt")
        assert result is None
