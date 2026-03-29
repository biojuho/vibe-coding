from __future__ import annotations

from pathlib import Path

from PIL import Image

from shorts_maker_v2.render.caption_pillow import (
    CAPTION_PRESETS,
    CaptionStyle,
    apply_preset,
    render_caption_image,
)


def _base_style(**overrides: object) -> CaptionStyle:
    fields: dict[str, object] = {
        "font_size": 40,
        "margin_x": 80,
        "bottom_offset": 220,
        "text_color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 3,
        "line_spacing": 8,
        "font_candidates": ("C:/Windows/Fonts/malgun.ttf",),
    }
    fields.update(overrides)
    return CaptionStyle(**fields)


def test_render_caption_image_outputs_png(tmp_path: Path) -> None:
    output_path = render_caption_image(
        text="Test caption sentence",
        canvas_width=1080,
        style=_base_style(),
        output_path=tmp_path / "caption.png",
    )

    assert output_path.exists()
    image = Image.open(output_path)
    assert image.mode == "RGBA"
    assert image.size[0] > 0 and image.size[1] > 0


def test_neon_preset_has_glow_enabled() -> None:
    neon = CAPTION_PRESETS["neon"]
    assert neon["glow_enabled"] is True
    assert neon["glow_color"] == "#00F0FF"
    assert neon["glow_radius"] > 0


def test_neon_preset_applied_caption_renders(tmp_path: Path) -> None:
    neon_style = apply_preset(_base_style(), "neon")
    assert neon_style.glow_enabled is True

    output_path = render_caption_image(
        text="AI changes daily life",
        canvas_width=1080,
        style=neon_style,
        output_path=tmp_path / "neon_caption.png",
    )

    assert output_path.exists()
    image = Image.open(output_path)
    assert image.mode == "RGBA"
    assert image.size[0] > 0 and image.size[1] > 0


def test_render_caption_image_draws_background_box_when_enabled(tmp_path: Path) -> None:
    output_path = render_caption_image(
        text="Hi",
        canvas_width=1080,
        style=_base_style(
            bg_color="#FF0000",
            bg_opacity=220,
            bg_radius=18,
            glow_enabled=False,
        ),
        output_path=tmp_path / "boxed_caption.png",
    )

    image = Image.open(output_path)
    sample = image.getpixel((max(10, image.width // 6), image.height // 2))
    assert sample[0] > sample[1]
    assert sample[0] > sample[2]
    assert sample[3] > 0
