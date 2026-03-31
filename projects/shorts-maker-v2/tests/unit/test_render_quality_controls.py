from __future__ import annotations

from types import SimpleNamespace

from shorts_maker_v2.pipeline.render_step import RenderStep


def _make_config(*, style_preset: str = "default") -> SimpleNamespace:
    return SimpleNamespace(
        video=SimpleNamespace(
            resolution=(1080, 1920),
            fps=30,
            transition_style="random",
            encoding_preset="fast",
            encoding_crf=23,
        ),
        captions=SimpleNamespace(
            mode="karaoke",
            font_size=72,
            margin_x=60,
            bottom_offset=280,
            text_color="#FFFFFF",
            stroke_color="#000000",
            stroke_width=0,
            line_spacing=12,
            font_candidates=("C:/Windows/Fonts/malgunbd.ttf",),
            words_per_chunk=3,
            bg_color="#000000",
            bg_opacity=185,
            bg_radius=18,
            style_preset=style_preset,
            hook_animation="random",
            highlight_color="#FFD700",
            highlight_mode="word",
            custom_styles=None,
            channel_style_map=None,
            outline_thickness="medium",
            safe_zone_enabled=True,
            center_hook=True,
            line_spacing_factor=1.0,
        ),
        audio=SimpleNamespace(
            bgm_dir="assets/bgm",
            bgm_volume=0.12,
            fade_duration=0.5,
            sfx_enabled=False,
            sfx_dir="assets/sfx",
            sfx_volume=0.35,
        ),
        intro_outro=SimpleNamespace(
            intro_path="",
            outro_path="",
            intro_duration=1.5,
            outro_duration=1.5,
        ),
        providers=SimpleNamespace(visual_styles=()),
    )


def test_style_preset_override_forces_single_caption_preset() -> None:
    step = RenderStep(config=_make_config(style_preset="neon"), channel_key="ai_tech")

    assert step.hook_style == step.body_style
    assert step.body_style == step.cta_style


def test_channel_keyword_map_uses_profile_highlight_color() -> None:
    step = RenderStep(config=_make_config(), channel_key="ai_tech")

    assert step._keyword_color_map is not None
    assert step._keyword_color_map["gpt"] == (0x00, 0xF0, 0xFF, 255)


def test_channel_specific_caption_tuning_raises_safe_area_for_psychology() -> None:
    baseline = RenderStep(config=_make_config(), channel_key="")
    psychology = RenderStep(config=_make_config(), channel_key="psychology")

    assert psychology.body_style.bottom_offset > baseline.body_style.bottom_offset
    assert psychology.body_style.line_spacing >= baseline.body_style.line_spacing
