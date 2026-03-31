"""Unit tests for karaoke rendering functions."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image

from shorts_maker_v2.render.caption_pillow import CaptionStyle
from shorts_maker_v2.render.karaoke import (
    _auto_scale_font,
    _hex_to_rgb,
    _render_word_glow,
    build_keyword_color_map,
    render_karaoke_highlight_image,
    render_karaoke_image,
)


@pytest.fixture
def base_style():
    return CaptionStyle(
        font_size=60,
        margin_x=50,
        bottom_offset=100,
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=2,
        line_spacing=5,
        font_candidates=["MaruBuri-Bold", "malgun"],
        mode="karaoke",
        words_per_chunk=3,
        bg_color="#1A1A1A",
        bg_opacity=180,
        bg_radius=20,
    )

def test_hex_to_rgb():
    assert _hex_to_rgb("#FFAA00") == (255, 170, 0)
    assert _hex_to_rgb("FFAA00") == (255, 170, 0)

def test_build_keyword_color_map():
    keywords = ["테스트", "인지 부조화", "ai"]
    color_map = build_keyword_color_map(keywords, "#FF0000")
    expected_color = (255, 0, 0, 255)

    assert "테스트" in color_map
    assert color_map["테스트"] == expected_color
    assert "인지" in color_map
    assert "부조화" in color_map
    assert "인지 부조화" in color_map
    assert "ai" in color_map

def test_auto_scale_font(base_style):
    from unittest.mock import patch

    class MockFont:
        def __init__(self, size):
            self.size = size

    def fake_draw(img, *args, **kwargs):
        class FakeDraw:
            def textbbox(self, xy, text, font=None, **kwargs):
                font_size = getattr(font, "size", 60)
                width = len(text) * font_size
                return (0, 0, width, font_size)
            def text(self, *args, **kwargs): pass
            def rounded_rectangle(self, *args, **kwargs): pass
        return FakeDraw()

    with patch("PIL.ImageDraw.Draw", new=fake_draw), patch("shorts_maker_v2.render.karaoke._load_font", side_effect=lambda style: MockFont(style.font_size)):
        # Test text that fits comfortably within max width
        style_out = _auto_scale_font(base_style, "짧은 텍스트", 2000)
        assert style_out.font_size == base_style.font_size

        # Test long text that requires scaling down
        long_text = "이것은 캔버스 너비를 초과할 가능성이 매우 높은 아주 길고 긴 텍스트입니다. 폰트 크기가 줄어들어야 합니다." # 55 chars. width at size 60 = 3300.
        style_out_scaled = _auto_scale_font(base_style, long_text, 800)
        assert style_out_scaled.font_size < base_style.font_size

def test_render_karaoke_image(base_style):
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_karaoke.png"
        result_path = render_karaoke_image("테스트 자막입니다", 1080, base_style, output_path)

        assert result_path.exists()
        with Image.open(result_path) as img:
            assert img.format in ["PNG", "MPO", "JPEG", None]  # PIL handles these

def test_render_karaoke_highlight_image(base_style):
    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_karaoke_highlight.png"
        words = ["테스트", "하이라이트", "자막입니다"]
        keyword_colors = build_keyword_color_map(["하이라이트"], "#FF0000")

        result_path = render_karaoke_highlight_image(
            words=words,
            active_word_index=1,
            canvas_width=1080,
            style=base_style,
            highlight_color="#00FF00",
            output_path=output_path,
            keyword_colors=keyword_colors,
        )

        assert result_path.exists()
        with Image.open(result_path) as img:
            assert img.format in ["PNG", "MPO", "JPEG", None]

def test_render_word_glow():
    from PIL import ImageFont
    # Mock font simply using default load since actual font rendering is handled by PIL
    image = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    # Create an empty dummy font if needed, or fallback to default
    try:
        from PIL import ImageFont
        font = ImageFont.load_default()
    except Exception:
        font = None

    result = _render_word_glow(
        image=image,
        position=(10, 10),
        word="glow",
        font=font,
        glow_color="#FF0000",
        glow_radius=2,
    )
    assert result is not None
    assert result.size == (200, 100)
