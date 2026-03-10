from __future__ import annotations

from pathlib import Path

from PIL import Image

from shorts_maker_v2.render.caption_pillow import (
    CAPTION_PRESETS,
    CaptionStyle,
    apply_preset,
    render_caption_image,
)


def test_render_caption_image_outputs_png(tmp_path: Path) -> None:
    style = CaptionStyle(
        font_size=40,
        margin_x=80,
        bottom_offset=220,
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=3,
        line_spacing=8,
        font_candidates=("C:/Windows/Fonts/malgun.ttf",),
    )
    output_path = render_caption_image(
        text="테스트 자막 문장입니다.",
        canvas_width=1080,
        style=style,
        output_path=tmp_path / "caption.png",
    )
    assert output_path.exists()
    image = Image.open(output_path)
    assert image.mode == "RGBA"
    assert image.size[0] > 0 and image.size[1] > 0


def test_neon_preset_has_glow_enabled() -> None:
    """네온 프리셋에 glow_enabled=True 포함 확인."""
    neon = CAPTION_PRESETS["neon"]
    assert neon["glow_enabled"] is True
    assert neon["glow_color"] == "#00F0FF"
    assert neon["glow_radius"] > 0


def test_neon_preset_applied_caption_renders(tmp_path: Path) -> None:
    """네온 프리셋 적용 후 캡션 이미지가 정상 생성되는지 확인."""
    base_style = CaptionStyle(
        font_size=40,
        margin_x=80,
        bottom_offset=220,
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=3,
        line_spacing=8,
        font_candidates=("C:/Windows/Fonts/malgun.ttf",),
    )
    neon_style = apply_preset(base_style, "neon")
    assert neon_style.glow_enabled is True

    output_path = render_caption_image(
        text="AI가 세상을 바꾼다",
        canvas_width=1080,
        style=neon_style,
        output_path=tmp_path / "neon_caption.png",
    )
    assert output_path.exists()
    image = Image.open(output_path)
    assert image.mode == "RGBA"
    # 글로우 여백으로 인해 non-glow 캡션보다 이미지가 더 클 수 있음
    assert image.size[0] > 0 and image.size[1] > 0
