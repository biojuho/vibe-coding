from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from shorts_maker_v2.render.caption_pillow import (
    CAPTION_PRESETS,
    CaptionStyle,
    _load_font,
    _wrap_text,
    apply_preset,
    calculate_safe_position,
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


def test_wrap_text_breaks_long_single_token_by_character_width() -> None:
    style = _base_style()
    font = _load_font(style)
    image = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    lines = _wrap_text(draw, "A" * 36, font, max_width=80, stroke_width=style.stroke_width)

    assert len(lines) > 1
    for line in lines:
        left, _, right, _ = draw.textbbox((0, 0), line, font=font, stroke_width=style.stroke_width)
        assert right - left <= 80


def test_calculate_safe_position_centers_caption_inside_safe_zone() -> None:
    style = _base_style()

    y = calculate_safe_position(1920, 240, style, role="body")

    assert y == 792


def test_calculate_safe_position_clamps_to_top_for_oversized_caption() -> None:
    style = _base_style()

    y = calculate_safe_position(1920, 1400, style, role="body")

    assert y == 288


def test_render_caption_image_handles_tall_multiline_caption(tmp_path: Path) -> None:
    short_path = render_caption_image(
        text="Short line",
        canvas_width=420,
        style=_base_style(),
        output_path=tmp_path / "short.png",
    )
    tall_path = render_caption_image(
        text=(
            "This deliberately long caption block keeps wrapping so we can stress "
            "the multiline spacing and image height behavior in static mode."
        ),
        canvas_width=420,
        style=_base_style(min_lines=3, line_spacing=12, line_spacing_factor=1.6),
        output_path=tmp_path / "tall.png",
    )

    short_image = Image.open(short_path)
    tall_image = Image.open(tall_path)

    assert tall_image.height > short_image.height
