from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from shorts_maker_v2.pipeline.render_step import RenderStep


def _make_render_step(
    transition_style: str = "random",
    *,
    channel_key: str = "",
    video_renderer_backend: str | None = None,
) -> RenderStep:
    config = MagicMock()

    config.video.resolution = (1080, 1920)
    config.video.fps = 30
    config.video.transition_style = transition_style

    config.captions.mode = "karaoke"
    config.captions.font_size = 72
    config.captions.margin_x = 60
    config.captions.bottom_offset = 280
    config.captions.text_color = "#FFFFFF"
    config.captions.stroke_color = "#000000"
    config.captions.stroke_width = 0
    config.captions.line_spacing = 12
    config.captions.bg_color = "#000000"
    config.captions.bg_opacity = 185
    config.captions.bg_radius = 18
    config.captions.style_preset = "default"
    config.captions.words_per_chunk = 3
    config.captions.font_candidates = ("C:/Windows/Fonts/malgunbd.ttf",)
    config.captions.outline_thickness = "medium"
    config.captions.custom_styles = {}
    config.captions.safe_zone_enabled = True
    config.captions.center_hook = False
    config.captions.line_spacing_factor = 1.0
    config.captions.channel_style_map = {}
    config.captions.highlight_color = "#00FFAA"

    config.audio.bgm_dir = "assets/bgm"
    config.audio.bgm_volume = 0.12
    config.audio.fade_duration = 0.5
    config.audio.sfx_enabled = False
    config.audio.sfx_dir = "assets/sfx"
    config.audio.sfx_volume = 0.35

    config.intro_outro.intro_path = ""
    config.intro_outro.outro_path = ""
    config.intro_outro.intro_duration = 2.0
    config.intro_outro.outro_duration = 2.0

    config.providers.visual_styles = ()

    return RenderStep(
        config=config,
        openai_client=MagicMock(),
        job_index=0,
        channel_key=channel_key,
        video_renderer_backend=video_renderer_backend,
    )


def test_load_video_clip_uses_native_renderer_even_with_ffmpeg_backend() -> None:
    step = _make_render_step(video_renderer_backend="ffmpeg")
    native_video = object()
    step._native_renderer.load_video = MagicMock(return_value=MagicMock(native=native_video))
    step._output_renderer.load_video = MagicMock(return_value=MagicMock(native="unused"))

    result = step._load_video_clip("sample.mp4", audio=False)

    assert result is native_video
    step._native_renderer.load_video.assert_called_once_with("sample.mp4", audio=False)
    step._output_renderer.load_video.assert_not_called()


def test_load_image_clip_uses_native_renderer_even_with_ffmpeg_backend() -> None:
    step = _make_render_step(video_renderer_backend="ffmpeg")
    native_image = object()
    step._native_renderer.load_image = MagicMock(return_value=MagicMock(native=native_image))
    step._output_renderer.load_image = MagicMock(return_value=MagicMock(native="unused"))

    result = step._load_image_clip("sample.png", duration=3.5)

    assert result is native_image
    step._native_renderer.load_image.assert_called_once_with("sample.png", duration=3.5)
    step._output_renderer.load_image.assert_not_called()


def test_build_keyword_color_map_uses_channel_keywords_and_default_color() -> None:
    step = _make_render_step()
    step._channel_profile = {"highlight_keywords": ["AI", "GPU"]}

    with patch(
        "shorts_maker_v2.pipeline.render_step.build_keyword_color_map",
        return_value={"AI": (0, 255, 170, 255)},
    ) as build:
        result = step._build_keyword_color_map()

    assert result == {"AI": (0, 255, 170, 255)}
    build.assert_called_once_with(["AI", "GPU"], "#00FFAA")


def test_resolve_style_override_returns_blank_for_default() -> None:
    step = _make_render_step()
    step.config.captions.style_preset = " default "

    assert step._resolve_style_override() == ""


def test_resolve_style_override_trims_custom_value() -> None:
    step = _make_render_step()
    step.config.captions.style_preset = " neon "

    assert step._resolve_style_override() == "neon"


def test_resolve_caption_combo_prefers_channel_profile() -> None:
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter.get_profile",
        return_value={"caption_combo": ["hook_plus", "body_plus", "cta_plus"]},
    ):
        result = RenderStep._resolve_caption_combo("ai_tech", job_index=99)

    assert result == ("hook_plus", "body_plus", "cta_plus", "closing")


def test_resolve_caption_combo_falls_back_to_rotation_for_invalid_profile() -> None:
    with patch(
        "shorts_maker_v2.utils.channel_router.ChannelRouter.get_profile",
        return_value={"caption_combo": ["hook_only", "body_only"]},
    ):
        result = RenderStep._resolve_caption_combo("ai_tech", job_index=1)

    assert result == RenderStep._CAPTION_COMBOS[1]


def test_apply_named_effect_falls_back_to_random_for_unknown_effect() -> None:
    step = _make_render_step()
    clip = object()

    with (
        patch.object(step, "_build_effect_map", return_value={}),
        patch.object(step, "_apply_random_effect", return_value=("fallback_clip", "drift")) as fallback,
    ):
        result = step._apply_named_effect("unknown", clip, 1080, 1920)

    assert result == ("fallback_clip", "drift")
    fallback.assert_called_once_with(clip, 1080, 1920)


def test_apply_channel_image_motion_uses_explicit_channel_hook_motion() -> None:
    step = _make_render_step(channel_key="ai_tech")
    clip = object()

    with patch.object(step, "_apply_named_effect", return_value=("hook_clip", "dramatic_ken_burns")) as named:
        result = step._apply_channel_image_motion(
            clip,
            role="hook",
            target_width=1080,
            target_height=1920,
        )

    assert result == ("hook_clip", "dramatic_ken_burns")
    named.assert_called_once_with("dramatic_ken_burns", clip, 1080, 1920)


def test_apply_channel_image_motion_uses_list_motion_without_excluded_value() -> None:
    step = _make_render_step(channel_key="ai_tech")
    clip = object()

    with (
        patch("shorts_maker_v2.pipeline.render_effects.random.choice", return_value="pan_right") as chooser,
        patch.object(step, "_apply_named_effect", return_value=("body_clip", "pan_right")) as named,
    ):
        result = step._apply_channel_image_motion(
            clip,
            role="body",
            target_width=1080,
            target_height=1920,
            exclude="pan_left",
        )

    assert result == ("body_clip", "pan_right")
    chooser.assert_called_once()
    named.assert_called_once_with("pan_right", clip, 1080, 1920)


def test_apply_channel_image_motion_uses_random_fallback_for_non_hook_without_profile() -> None:
    step = _make_render_step(channel_key="unknown")
    clip = object()

    with patch.object(step, "_apply_random_effect", return_value=("fallback_clip", "zoom_out")) as fallback:
        result = step._apply_channel_image_motion(
            clip,
            role="body",
            target_width=1080,
            target_height=1920,
            exclude="ken_burns",
        )

    assert result == ("fallback_clip", "zoom_out")
    fallback.assert_called_once_with(clip, 1080, 1920, exclude="ken_burns")


def test_caption_y_uses_safe_zone_calculation() -> None:
    clip = MagicMock(h=220)
    style = MagicMock(safe_zone_enabled=True)

    with patch("shorts_maker_v2.pipeline.render_captions.calculate_safe_position", return_value=777) as calc:
        result = RenderStep._caption_y(clip, target_height=1920, style=style, role="hook")

    assert result == 777
    calc.assert_called_once_with(1920, 220, style, "hook")


def test_caption_y_uses_bottom_offset_without_safe_zone() -> None:
    clip = MagicMock(h=320)
    style = MagicMock(safe_zone_enabled=False, bottom_offset=280)

    assert RenderStep._caption_y(clip, target_height=1920, style=style) == 1320


def _ensure_fake_shorts_factory():
    """ShortsFactory가 sys.path에 없을 때 가짜 모듈을 sys.modules에 주입."""
    import sys

    if "ShortsFactory" not in sys.modules:
        fake_sf = MagicMock()
        sys.modules["ShortsFactory"] = fake_sf
    fake_sf = sys.modules["ShortsFactory"]
    if "ShortsFactory.engines" not in sys.modules:
        sys.modules["ShortsFactory.engines"] = fake_sf.engines
    if "ShortsFactory.engines.text_engine" not in sys.modules:
        sys.modules["ShortsFactory.engines.text_engine"] = fake_sf.engines.text_engine


def test_render_static_caption_hook_uses_glow_fallback_when_gradient_fails(tmp_path: Path) -> None:
    _ensure_fake_shorts_factory()
    step = _make_render_step(channel_key="ai_tech")
    step._channel_profile = {"theme": "tech"}
    output = tmp_path / "hook.png"
    engine = MagicMock()
    engine.render_gradient_text.side_effect = RuntimeError("gradient failed")
    engine.render_subtitle_with_glow.return_value = output

    with patch("ShortsFactory.engines.text_engine.TextEngine", return_value=engine):
        result = step._render_static_caption("Hook", 1080, step.hook_style, output, "hook")

    assert result == output
    engine.render_gradient_text.assert_called_once()
    engine.render_subtitle_with_glow.assert_called_once_with("Hook", role="hook", output_path=output)


def test_render_static_caption_falls_back_to_render_caption_image_when_text_engine_fails(tmp_path: Path) -> None:
    _ensure_fake_shorts_factory()
    step = _make_render_step(channel_key="ai_tech")
    output = tmp_path / "fallback.png"

    with (
        patch("ShortsFactory.engines.text_engine.TextEngine", side_effect=RuntimeError("boom")),
        patch("shorts_maker_v2.pipeline.render_captions.render_caption_image", return_value=output) as renderer,
    ):
        result = step._render_static_caption("Fallback", 1080, step.hook_style, output, "hook")

    assert result == output
    renderer.assert_called_once_with("Fallback", 1080, step.hook_style, output)


def test_build_bookend_clip_uses_video_loader_for_video_assets(tmp_path: Path) -> None:
    step = _make_render_step()
    intro = tmp_path / "intro.mp4"
    intro.write_bytes(b"video")
    loaded_clip = MagicMock(duration=7.0)
    clipped_clip = MagicMock()
    loaded_clip.subclipped.return_value = clipped_clip
    step._load_video_clip = MagicMock(return_value=loaded_clip)
    step._fit_vertical = MagicMock(return_value="fit_video")

    result = step._build_bookend_clip(str(intro), duration=2.5, target_width=1080, target_height=1920)

    assert result == "fit_video"
    step._load_video_clip.assert_called_once_with(intro, audio=False)
    loaded_clip.subclipped.assert_called_once_with(0, 2.5)
    step._fit_vertical.assert_called_once_with(clipped_clip, 1080, 1920)


def test_build_bookend_clip_uses_image_loader_for_image_assets(tmp_path: Path) -> None:
    step = _make_render_step()
    outro = tmp_path / "outro.png"
    outro.write_bytes(b"image")
    image_clip = MagicMock()
    step._load_image_clip = MagicMock(return_value=image_clip)
    step._fit_vertical = MagicMock(return_value="fit_image")

    result = step._build_bookend_clip(str(outro), duration=3.0, target_width=1080, target_height=1920)

    assert result == "fit_image"
    step._load_image_clip.assert_called_once_with(outro, duration=3.0)
    step._fit_vertical.assert_called_once_with(image_clip, 1080, 1920)


def test_build_bookend_clip_returns_none_for_unsupported_extension(tmp_path: Path) -> None:
    step = _make_render_step()
    note = tmp_path / "note.txt"
    note.write_text("ignore", encoding="utf-8")

    assert step._build_bookend_clip(str(note), duration=1.0, target_width=1080, target_height=1920) is None
