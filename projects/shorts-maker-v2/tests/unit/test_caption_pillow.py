from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from shorts_maker_v2.render.caption_pillow import (
    CAPTION_PRESETS,
    CaptionStyle,
    _char_level_wrap,
    _hex_to_rgb,
    _load_font,
    _render_glow_layer,
    _wrap_text,
    apply_preset,
    auto_font_size,
    calculate_safe_position,
    complementary_color,
    register_custom_styles,
    render_caption_image,
    resolve_channel_style,
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


# ---------------------------------------------------------------------------
# 기존 테스트
# ---------------------------------------------------------------------------


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


def test_calculate_safe_position_keeps_hook_centered_when_enabled() -> None:
    style = _base_style(center_hook=True)

    y = calculate_safe_position(1920, 240, style, role="hook")

    assert y == 792


def test_calculate_safe_position_uses_safe_lower_third_for_non_centered_hook() -> None:
    style = _base_style(center_hook=False, bottom_offset=220)

    y = calculate_safe_position(1920, 240, style, role="hook")

    assert y == 1296


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


# ---------------------------------------------------------------------------
# T-082: 새 테스트 — 미커버 분기 채우기
# ---------------------------------------------------------------------------


class TestComplementaryColor:
    def test_valid_hex_returns_complementary(self) -> None:
        # #FFFFFF → complement is #000000
        result = complementary_color("#FFFFFF")
        assert result == "#000000"

    def test_valid_hex_without_hash(self) -> None:
        result = complementary_color("000000")
        assert result == "#FFFFFF"

    def test_invalid_hex_too_short_returns_white(self) -> None:
        # 6자 미만 → 기본값 #FFFFFF
        result = complementary_color("#FFF")
        assert result == "#FFFFFF"

    def test_empty_string_returns_white(self) -> None:
        result = complementary_color("")
        assert result == "#FFFFFF"

    def test_midpoint_color(self) -> None:
        # #808080 → #7F7F7F (255-128=127)
        result = complementary_color("#808080")
        assert result == "#7F7F7F"


class TestHexToRgb:
    def test_valid_hex_parses_correctly(self) -> None:
        assert _hex_to_rgb("#FF8040") == (255, 128, 64)

    def test_without_hash(self) -> None:
        assert _hex_to_rgb("00FFAA") == (0, 255, 170)

    def test_too_short_returns_black(self) -> None:
        # 6자 미만이면 (0, 0, 0) 반환
        result = _hex_to_rgb("#FFF")
        assert result == (0, 0, 0)

    def test_empty_returns_black(self) -> None:
        result = _hex_to_rgb("")
        assert result == (0, 0, 0)


class TestAutoFontSize:
    def test_body_role_short_text_unchanged(self) -> None:
        # 30자 이하, body role → multiplier 1.0, length_factor 1.0
        size = auto_font_size(72, 10, role="body")
        assert size == 72

    def test_hook_role_increases_size(self) -> None:
        size = auto_font_size(72, 10, role="hook")
        assert size == int(72 * 1.25)

    def test_cta_role_increases_size(self) -> None:
        size = auto_font_size(72, 10, role="cta")
        assert size == int(72 * 1.15)

    def test_closing_role_slightly_increases(self) -> None:
        size = auto_font_size(72, 10, role="closing")
        assert size == int(72 * 1.05)

    def test_medium_text_30_to_50_chars_reduces_slightly(self) -> None:
        # 30 < length <= 50 → length_factor 0.92
        size = auto_font_size(72, 40, role="body")
        assert size == int(72 * 1.0 * 0.92)

    def test_long_text_over_50_chars_reduces_more(self) -> None:
        # length > 50 → length_factor 0.85
        size = auto_font_size(72, 60, role="body")
        assert size == int(72 * 1.0 * 0.85)

    def test_minimum_size_enforced(self) -> None:
        # 매우 작은 base_size + long text 도 최소 32
        size = auto_font_size(10, 100, role="body")
        assert size == 32

    def test_unknown_role_treated_as_body(self) -> None:
        size = auto_font_size(72, 10, role="unknown_role")
        assert size == 72  # 1.0 multiplier


class TestResolveChannelStyle:
    def test_no_map_returns_none(self) -> None:
        result = resolve_channel_style("ai", "hook", None)
        assert result is None

    def test_no_channel_key_returns_none(self) -> None:
        result = resolve_channel_style("", "hook", {"ai": "neon_tech"})
        assert result is None

    def test_channel_not_in_map_returns_none(self) -> None:
        result = resolve_channel_style("history", "hook", {"ai": "neon_tech"})
        assert result is None

    def test_hook_role_returns_highlight_variant_if_available(self) -> None:
        # "neon_tech" + hook → "neon_tech_highlight" (존재)
        result = resolve_channel_style("ai", "hook", {"ai": "neon_tech"})
        assert result == "neon_tech_highlight"

    def test_hook_role_falls_back_to_base_if_no_highlight(self) -> None:
        # "subtitle" 프리셋은 _highlight 변형 없음
        result = resolve_channel_style("ai", "hook", {"ai": "subtitle"})
        assert result == "subtitle"

    def test_non_hook_role_returns_base_style(self) -> None:
        result = resolve_channel_style("ai", "body", {"ai": "neon_tech"})
        assert result == "neon_tech"


class TestRegisterCustomStyles:
    def setup_method(self) -> None:
        # 각 테스트 전에 추가된 커스텀 키 제거
        self._added: list[str] = []

    def teardown_method(self) -> None:
        for key in self._added:
            CAPTION_PRESETS.pop(key, None)

    def test_registers_new_style(self) -> None:
        key = "_test_custom_style_new"
        self._added.append(key)
        register_custom_styles({key: {"text_color": "#AABBCC"}})
        assert key in CAPTION_PRESETS
        assert CAPTION_PRESETS[key]["text_color"] == "#AABBCC"

    def test_does_not_overwrite_existing_style(self) -> None:
        # "neon" 은 이미 존재 → 덮어쓰지 않아야 함
        original_glow_color = CAPTION_PRESETS["neon"]["glow_color"]
        register_custom_styles({"neon": {"glow_color": "#DEADBE"}})
        assert CAPTION_PRESETS["neon"]["glow_color"] == original_glow_color

    def test_skips_none_input(self) -> None:
        # None 입력 시 오류 없음
        register_custom_styles(None)

    def test_skips_non_dict_values(self) -> None:
        key = "_test_bad_value"
        self._added.append(key)
        # dict 가 아닌 값은 등록 안 됨
        register_custom_styles({key: "invalid_value"})
        assert key not in CAPTION_PRESETS


class TestRenderGlowLayer:
    def test_returns_rgba_image_same_size(self) -> None:
        size = (200, 100)
        base = Image.new("RGBA", size, (255, 255, 255, 200))
        result = _render_glow_layer(base, "#00F0FF", glow_radius=8)
        assert result.mode == "RGBA"
        assert result.size == size

    def test_glow_color_applied(self) -> None:
        size = (100, 50)
        # 완전히 불투명한 텍스트 이미지 → 글로우 레이어에 색이 들어감
        base = Image.new("RGBA", size, (255, 255, 255, 255))
        result = _render_glow_layer(base, "#FF0000", glow_radius=4)
        # 결과 이미지가 완전 투명은 아니어야 함
        pixels = list(result.getdata())
        assert any(p[3] > 0 for p in pixels)


class TestCharLevelWrap:
    def test_wraps_cjk_text_by_pixel(self) -> None:
        image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        style = _base_style()
        font = _load_font(style)
        lines = _char_level_wrap(draw, "가나다라마바사아자차카타파하" * 3, font, max_width=100, stroke_width=2)
        assert len(lines) > 1

    def test_single_char_always_returned(self) -> None:
        image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        style = _base_style()
        font = _load_font(style)
        # 1글자는 어떤 max_width 에도 1줄 반환
        lines = _char_level_wrap(draw, "A", font, max_width=1, stroke_width=0)
        assert lines == ["A"]

    def test_empty_string_fallback(self) -> None:
        image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        style = _base_style()
        font = _load_font(style)
        lines = _char_level_wrap(draw, "", font, max_width=100, stroke_width=0)
        assert lines == [""]


class TestRenderCaptionImageEdgeCases:
    def test_empty_text_renders_without_error(self, tmp_path: Path) -> None:
        output_path = render_caption_image(
            text="",
            canvas_width=1080,
            style=_base_style(),
            output_path=tmp_path / "empty.png",
        )
        assert output_path.exists()

    def test_no_glow_no_bg_renders_text_only(self, tmp_path: Path) -> None:
        style = _base_style(glow_enabled=False, bg_opacity=0)
        output_path = render_caption_image(
            text="Simple text",
            canvas_width=1080,
            style=style,
            output_path=tmp_path / "simple.png",
        )
        assert output_path.exists()
        img = Image.open(output_path)
        assert img.mode == "RGBA"

    def test_glow_and_bg_together(self, tmp_path: Path) -> None:
        style = _base_style(
            glow_enabled=True,
            glow_color="#00F0FF",
            glow_radius=10,
            bg_color="#000000",
            bg_opacity=180,
            bg_radius=12,
        )
        output_path = render_caption_image(
            text="Glow + BG",
            canvas_width=1080,
            style=style,
            output_path=tmp_path / "glow_bg.png",
        )
        assert output_path.exists()

    def test_very_narrow_canvas_does_not_crash(self, tmp_path: Path) -> None:
        output_path = render_caption_image(
            text="Narrow canvas test",
            canvas_width=200,
            style=_base_style(),
            output_path=tmp_path / "narrow.png",
        )
        assert output_path.exists()

    def test_min_lines_pads_output(self, tmp_path: Path) -> None:
        path1 = render_caption_image(
            text="Hi",
            canvas_width=1080,
            style=_base_style(min_lines=1),
            output_path=tmp_path / "min1.png",
        )
        path3 = render_caption_image(
            text="Hi",
            canvas_width=1080,
            style=_base_style(min_lines=3),
            output_path=tmp_path / "min3.png",
        )
        img1 = Image.open(path1)
        img3 = Image.open(path3)
        assert img3.height >= img1.height
