from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.config import CanvaSettings, ThumbnailSettings
from shorts_maker_v2.pipeline.thumbnail_step import (
    ThumbnailStep,
    _generate_pillow_thumbnail,
    _load_token,
    _pillow_gradient_bg,
    _sanitize_title,
    _wrap_text,
)

# ─── _sanitize_title ─────────────────────────────────────────────────────────


def test_sanitize_title_replaces_em_dash() -> None:
    assert _sanitize_title("A\u2014B") == "A-B"


def test_sanitize_title_replaces_en_dash() -> None:
    assert _sanitize_title("A\u2013B") == "A-B"


def test_sanitize_title_replaces_ellipsis() -> None:
    assert _sanitize_title("더보기\u2026") == "더보기..."


def test_sanitize_title_replaces_smart_quotes() -> None:
    assert _sanitize_title("\u201chello\u201d") == '"hello"'
    assert _sanitize_title("\u2018world\u2019") == "'world'"


def test_sanitize_title_passthrough_plain() -> None:
    assert _sanitize_title("일반 텍스트 123") == "일반 텍스트 123"


# ─── _pillow_gradient_bg ──────────────────────────────────────────────────────


def test_pillow_gradient_bg_returns_image_with_correct_size() -> None:
    from PIL import Image

    img = _pillow_gradient_bg(100, 200)
    assert isinstance(img, Image.Image)
    assert img.size == (100, 200)
    assert img.mode == "RGB"


# ─── _wrap_text ───────────────────────────────────────────────────────────────


def test_wrap_text_empty_input() -> None:
    """빈 문자열 입력 시 원본 반환."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (400, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    result = _wrap_text("", font, draw, max_width=200)
    assert result == [""]


def test_wrap_text_single_word_no_wrap() -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (600, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    result = _wrap_text("안녕", font, draw, max_width=600)
    assert len(result) >= 1
    assert "안녕" in " ".join(result)


def test_wrap_text_long_sentence_wraps() -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (200, 200))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # 매우 좁은 너비 → 여러 줄로 분리
    result = _wrap_text("hello world foo bar baz qux", font, draw, max_width=60)
    assert len(result) > 1


# ─── _generate_pillow_thumbnail ──────────────────────────────────────────────


def test_generate_pillow_thumbnail_creates_png(tmp_path: Path) -> None:
    """Pillow 썸네일이 PNG 파일로 생성되는지 확인."""
    output = tmp_path / "thumb.png"
    result = _generate_pillow_thumbnail("테스트 제목", output)
    assert result.exists()
    assert result.stat().st_size > 0
    with open(result, "rb") as f:
        assert f.read(4) == b"\x89PNG"


def test_generate_pillow_thumbnail_with_bg_image(tmp_path: Path) -> None:
    """배경 이미지 경로 제공 시 정상 생성."""
    from PIL import Image

    bg = Image.new("RGB", (200, 300), color=(100, 150, 200))
    bg_path = tmp_path / "bg.png"
    bg.save(str(bg_path))

    output = tmp_path / "thumb_bg.png"
    result = _generate_pillow_thumbnail("배경 테스트", output, bg_image_path=str(bg_path))
    assert result.exists()


def test_generate_pillow_thumbnail_with_missing_bg_falls_back(tmp_path: Path) -> None:
    """존재하지 않는 배경 이미지 → 그라디언트 폴백."""
    output = tmp_path / "thumb_fallback.png"
    result = _generate_pillow_thumbnail("폴백 테스트", output, bg_image_path="/nonexistent/bg.png")
    assert result.exists()


# ─── _load_token ─────────────────────────────────────────────────────────────


def test_load_token_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _load_token(tmp_path / "nonexistent.json")


def test_load_token_reads_json(tmp_path: Path) -> None:
    import json

    token_file = tmp_path / "token.json"
    token_file.write_text(json.dumps({"access_token": "abc123"}), encoding="utf-8")
    data = _load_token(token_file)
    assert data["access_token"] == "abc123"


# ─── ThumbnailStep helpers ────────────────────────────────────────────────────


def _make_step(
    mode: str = "pillow",
    openai_client=None,
    google_client=None,
    canva_enabled: bool = False,
    canva_design_id: str = "",
) -> ThumbnailStep:
    thumb_cfg = MagicMock(spec=ThumbnailSettings)
    thumb_cfg.mode = mode
    thumb_cfg.dalle_prompt_template = ""

    canva_cfg = MagicMock(spec=CanvaSettings)
    canva_cfg.enabled = canva_enabled
    canva_cfg.design_id = canva_design_id
    canva_cfg.token_file = ""

    return ThumbnailStep(
        thumbnail_config=thumb_cfg,
        canva_config=canva_cfg,
        openai_client=openai_client,
        google_client=google_client,
    )


# ─── ThumbnailStep._resolve_ai_prompt ────────────────────────────────────────


def test_resolve_ai_prompt_uses_config_template() -> None:
    result = ThumbnailStep._resolve_ai_prompt(
        topic="AI",
        title="AI의 미래",
        channel_key="ai_tech",
        config_template="Custom: {topic} / {title}",
    )
    assert result == "Custom: AI / AI의 미래"


def test_resolve_ai_prompt_uses_channel_template() -> None:
    result = ThumbnailStep._resolve_ai_prompt(
        topic="black hole",
        title="블랙홀의 비밀",
        channel_key="space",
        config_template="",
    )
    assert "space" in result.lower() or "cosmic" in result.lower() or "nebula" in result.lower()


def test_resolve_ai_prompt_unknown_channel_uses_default() -> None:
    result = ThumbnailStep._resolve_ai_prompt(
        topic="cooking",
        title="요리법",
        channel_key="unknown_channel",
        config_template="",
    )
    assert "cooking" in result or "요리법" in result


def test_resolve_ai_prompt_no_topic_uses_title_as_topic() -> None:
    result = ThumbnailStep._resolve_ai_prompt(
        topic="",
        title="제목으로 대체",
        channel_key="",
        config_template="Topic: {topic}",
    )
    assert "제목으로 대체" in result


# ─── ThumbnailStep.run() 모드 분기 ───────────────────────────────────────────


def test_run_mode_none_returns_none(tmp_path: Path) -> None:
    step = _make_step(mode="none")
    result = step.run("테스트", tmp_path)
    assert result is None


def test_run_mode_pillow_creates_file(tmp_path: Path) -> None:
    step = _make_step(mode="pillow")
    result = step.run("Pillow 테스트", tmp_path)
    assert result is not None
    assert Path(result).exists()


def test_run_mode_pillow_with_job_id_uses_unique_filename(tmp_path: Path) -> None:
    step = _make_step(mode="pillow")
    result = step.run("제목", tmp_path, job_id="job42")
    assert result is not None
    assert "job42" in result


def test_run_mode_dalle_no_client_falls_back_to_pillow(tmp_path: Path) -> None:
    """DALL-E 모드인데 openai_client 없으면 Pillow로 폴백."""
    step = _make_step(mode="dalle", openai_client=None)
    result = step.run("DALL-E 폴백", tmp_path)
    assert result is not None
    assert Path(result).exists()


def test_run_mode_gemini_no_client_falls_back_to_dalle_then_pillow(tmp_path: Path) -> None:
    """Gemini 모드인데 google_client 없으면 DALL-E → Pillow로 연쇄 폴백."""
    step = _make_step(mode="gemini", google_client=None, openai_client=None)
    result = step.run("Gemini 폴백", tmp_path)
    assert result is not None
    assert Path(result).exists()


def test_run_mode_canva_not_configured_falls_back_to_pillow(tmp_path: Path) -> None:
    """Canva 모드인데 enabled=False → Pillow 폴백."""
    step = _make_step(mode="canva", canva_enabled=False, canva_design_id="")
    result = step.run("Canva 폴백", tmp_path)
    assert result is not None
    assert Path(result).exists()


def test_run_unknown_mode_falls_back_to_pillow(tmp_path: Path) -> None:
    step = _make_step(mode="future_mode")
    result = step.run("알 수 없는 모드", tmp_path)
    assert result is not None
    assert Path(result).exists()


def test_run_exception_returns_none(tmp_path: Path) -> None:
    """내부 예외 발생 시 None 반환 (파이프라인 중단 없음)."""
    step = _make_step(mode="pillow")
    with patch(
        "shorts_maker_v2.pipeline.thumbnail_step._generate_pillow_thumbnail",
        side_effect=RuntimeError("disk full"),
    ):
        result = step.run("예외 테스트", tmp_path)
    assert result is None


# ─── ThumbnailStep._run_dalle (mocked openai_client) ────────────────────────


def test_run_dalle_with_client_calls_generate_image(tmp_path: Path) -> None:
    mock_openai = MagicMock()

    def fake_generate_image(*, model, prompt, size, quality, output_path):
        from PIL import Image

        img = Image.new("RGB", (100, 178), color=(50, 50, 50))
        img.save(str(output_path), "PNG")

    mock_openai.generate_image.side_effect = fake_generate_image

    step = _make_step(mode="dalle", openai_client=mock_openai)
    result = step.run("DALL-E 테스트", tmp_path, topic="AI", channel_key="ai_tech")

    assert result is not None
    mock_openai.generate_image.assert_called_once()
    kwargs = mock_openai.generate_image.call_args.kwargs
    assert kwargs["model"] == "dall-e-3"
    assert "AI" in kwargs["prompt"] or "tech" in kwargs["prompt"].lower()


# ─── ThumbnailStep._run_gemini (mocked google_client) ────────────────────────


def test_run_gemini_with_client_calls_generate_image(tmp_path: Path) -> None:
    mock_google = MagicMock()

    def fake_generate_image(*, prompt, output_path, aspect_ratio):
        from PIL import Image

        img = Image.new("RGB", (100, 178), color=(70, 100, 120))
        img.save(str(output_path), "PNG")

    mock_google.generate_image.side_effect = fake_generate_image

    step = _make_step(mode="gemini", google_client=mock_google)
    result = step.run("Gemini 테스트", tmp_path, topic="space", channel_key="space")

    assert result is not None
    mock_google.generate_image.assert_called_once()
    kwargs = mock_google.generate_image.call_args.kwargs
    assert kwargs["aspect_ratio"] == "9:16"


def test_run_gemini_client_failure_falls_back_to_pillow(tmp_path: Path) -> None:
    """Gemini generate_image 예외 → DALL-E 없으면 Pillow까지 폴백."""
    mock_google = MagicMock()
    mock_google.generate_image.side_effect = RuntimeError("quota exceeded")

    step = _make_step(mode="gemini", google_client=mock_google, openai_client=None)
    result = step.run("Gemini 실패 폴백", tmp_path, topic="space")

    assert result is not None
    assert Path(result).exists()


# ─── scene_assets background extraction ──────────────────────────────────────


def test_run_uses_first_image_scene_asset_as_bg(tmp_path: Path) -> None:
    from PIL import Image

    bg_img = Image.new("RGB", (200, 300), color=(80, 80, 80))
    bg_path = tmp_path / "scene1.png"
    bg_img.save(str(bg_path))

    mock_asset = MagicMock()
    mock_asset.visual_path = str(bg_path)

    step = _make_step(mode="pillow")
    with patch("shorts_maker_v2.pipeline.thumbnail_step._generate_pillow_thumbnail") as generate:
        generate.return_value = tmp_path / "thumbnail.png"
        result = step.run("배경 씬 테스트", tmp_path, scene_assets=[mock_asset])

    assert result is not None
    assert generate.call_args.kwargs["bg_image_path"] == str(bg_path)


def test_run_skips_missing_visual_path_asset(tmp_path: Path) -> None:
    mock_asset = MagicMock()
    mock_asset.visual_path = str(tmp_path / "nonexistent.png")

    step = _make_step(mode="pillow")
    with patch("shorts_maker_v2.pipeline.thumbnail_step._generate_pillow_thumbnail") as generate:
        generate.return_value = tmp_path / "thumbnail.png"
        result = step.run("누락 경로 테스트", tmp_path, scene_assets=[mock_asset])

    assert result is not None
    assert generate.call_args.kwargs["bg_image_path"] is None


def test_wrap_text_long_single_token_uses_char_level_wrap() -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (160, 200))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    result = _wrap_text("A" * 32, font, draw, max_width=20)

    assert len(result) > 1
    assert "".join(result) == "A" * 32


def test_run_dalle_cleans_up_unique_temp_bg(tmp_path: Path) -> None:
    mock_openai = MagicMock()

    def fake_generate_image(*, model, prompt, size, quality, output_path):
        from PIL import Image

        Image.new("RGB", (100, 178), color=(50, 50, 50)).save(str(output_path), "PNG")

    mock_openai.generate_image.side_effect = fake_generate_image

    step = _make_step(mode="dalle", openai_client=mock_openai)
    result = step.run("temp bg cleanup", tmp_path, topic="AI", channel_key="ai_tech", job_id="job42")

    assert result is not None
    assert not (tmp_path / "thumbnail_job42_dalle_bg.png").exists()


def test_run_gemini_cleans_up_unique_temp_bg(tmp_path: Path) -> None:
    mock_google = MagicMock()

    def fake_generate_image(*, prompt, output_path, aspect_ratio):
        from PIL import Image

        Image.new("RGB", (100, 178), color=(70, 100, 120)).save(str(output_path), "PNG")

    mock_google.generate_image.side_effect = fake_generate_image

    step = _make_step(mode="gemini", google_client=mock_google)
    result = step.run("temp bg cleanup", tmp_path, topic="space", channel_key="space", job_id="job42")

    assert result is not None
    assert not (tmp_path / "thumbnail_job42_gemini_bg.png").exists()


def test_run_canva_cleans_up_unique_temp_bg(tmp_path: Path) -> None:
    step = _make_step(mode="canva", canva_enabled=True, canva_design_id="design123")

    def fake_download(url: str, output_path: Path) -> Path:
        from PIL import Image

        Image.new("RGB", (100, 178), color=(90, 90, 90)).save(str(output_path), "PNG")
        return output_path

    with (
        patch("shorts_maker_v2.pipeline.thumbnail_step._get_access_token", return_value="token"),
        patch("shorts_maker_v2.pipeline.thumbnail_step._export_design", return_value="https://example.com/thumb.png"),
        patch("shorts_maker_v2.pipeline.thumbnail_step._http_download", side_effect=fake_download),
    ):
        result = step.run("temp bg cleanup", tmp_path, job_id="job42")

    assert result is not None
    assert not (tmp_path / "thumbnail_job42_canva_base.png").exists()
