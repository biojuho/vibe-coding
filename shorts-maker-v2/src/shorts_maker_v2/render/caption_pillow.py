from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


@dataclass(frozen=True)
class CaptionStyle:
    font_size: int
    margin_x: int
    bottom_offset: int
    text_color: str
    stroke_color: str
    stroke_width: int
    line_spacing: int
    font_candidates: tuple[str, ...]
    padding_y: int = 16
    min_lines: int = 1
    mode: str = "karaoke"       # "static" | "karaoke"
    words_per_chunk: int = 3
    bg_color: str = "#000000"
    bg_opacity: int = 185
    bg_radius: int = 18
    glow_enabled: bool = False
    glow_color: str = "#00F0FF"
    glow_radius: int = 12


# ---------------------------------------------------------------------------
# 자막 스타일 프리셋
# ---------------------------------------------------------------------------
CAPTION_PRESETS: dict[str, dict[str, Any]] = {
    "default": {},
    "neon": {
        "text_color": "#00F0FF",
        "stroke_color": "#FF00AA",
        "stroke_width": 5,
        "bg_opacity": 0,
        "bg_radius": 0,
        "glow_enabled": True,
        "glow_color": "#00F0FF",
        "glow_radius": 14,
    },
    "subtitle": {
        "text_color": "#FFFFFF",
        "stroke_color": "#000000",
        "stroke_width": 2,
        "bg_color": "#000000",
        "bg_opacity": 160,
        "bg_radius": 0,
        "bottom_offset": 120,
    },
    "bold": {
        "text_color": "#FFDD00",
        "stroke_color": "#000000",
        "stroke_width": 8,
        "font_size": 88,
        "bg_opacity": 0,
    },
    "cta": {
        "text_color": "#FFD700",
        "stroke_color": "#7B3F00",
        "stroke_width": 6,
        "font_size": 76,
        "bg_opacity": 0,
        "bg_radius": 0,
    },
}


def complementary_color(hex_color: str) -> str:
    """Return the complementary (opposite hue) hex color for maximum contrast."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "#FFFFFF"
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"#{255 - r:02X}{255 - g:02X}{255 - b:02X}"


def auto_font_size(base_size: int, text_length: int, role: str = "body") -> int:
    """Dynamically adjust font size based on text length and scene role.

    Hook/CTA get larger text for emphasis; long text gets scaled down
    to avoid overflow.
    """
    role_multiplier = {"hook": 1.25, "cta": 1.15, "body": 1.0}.get(role, 1.0)
    # Scale down for long text (>30 chars)
    length_factor = 1.0
    if text_length > 50:
        length_factor = 0.85
    elif text_length > 30:
        length_factor = 0.92
    return max(32, int(base_size * role_multiplier * length_factor))


def apply_preset(style: CaptionStyle, preset_name: str) -> CaptionStyle:
    """프리셋 오버라이드를 적용한 새 CaptionStyle 반환."""
    overrides = CAPTION_PRESETS.get(preset_name, {})
    if not overrides:
        return style
    fields = {f.name: getattr(style, f.name) for f in dataclasses.fields(style)}
    fields.update(overrides)
    return CaptionStyle(**fields)


def _load_font(style: CaptionStyle) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in style.font_candidates:
        path = Path(font_path)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), style.font_size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, stroke_width: int) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return int(max(0, round(right - left)))


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    stroke_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word]).strip()
        if not candidate:
            continue
        if _text_width(draw, candidate, font, stroke_width) <= max_width or not current:
            current.append(word)
            continue
        lines.append(" ".join(current))
        current = [word]
    if current:
        lines.append(" ".join(current))

    widened: list[str] = []
    for line in lines:
        if _text_width(draw, line, font, stroke_width) <= max_width:
            widened.append(line)
            continue
        wrapped = textwrap.wrap(line, width=max(6, int(len(line) * (max_width / max(_text_width(draw, line, font, stroke_width), 1)))))
        widened.extend(wrapped or [line])
    return widened


def _render_glow_layer(
    text_image: Image.Image,
    glow_color: str,
    glow_radius: int,
) -> Image.Image:
    """텍스트 이미지에서 네온 글로우 레이어 생성 (Gaussian blur 기반)."""
    # 텍스트 영역의 알파 채널을 추출하여 글로우 마스크 생성
    alpha = text_image.split()[3]
    glow = Image.new("RGBA", text_image.size, (0, 0, 0, 0))
    # 글로우 색상으로 채운 레이어 생성
    hex_color = glow_color.lstrip("#")
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    color_layer = Image.new("RGBA", text_image.size, (r, g, b, 180))
    glow = Image.composite(color_layer, glow, alpha)
    # Gaussian blur로 글로우 확산
    glow = glow.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    return glow


def render_caption_image(
    text: str,
    canvas_width: int,
    style: CaptionStyle,
    output_path: Path,
) -> Path:
    """
    정적 자막 이미지 렌더링.
    2x 해상도로 렌더링 후 다운샘플하여 안티앨리어싱 품질 향상.
    텍스트 드롭 섀도우 추가. 네온 프리셋 시 글로우 효과 적용.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = 2  # 2x 슈퍼샘플링

    # 2x 스타일로 폰트/간격 스케일링
    hi_style = CaptionStyle(
        font_size=style.font_size * scale,
        margin_x=style.margin_x * scale,
        bottom_offset=style.bottom_offset * scale,
        text_color=style.text_color,
        stroke_color=style.stroke_color,
        stroke_width=style.stroke_width * scale,
        line_spacing=style.line_spacing * scale,
        font_candidates=style.font_candidates,
        padding_y=style.padding_y * scale,
        min_lines=style.min_lines,
        mode=style.mode,
        words_per_chunk=style.words_per_chunk,
        bg_color=style.bg_color,
        bg_opacity=style.bg_opacity,
        bg_radius=style.bg_radius * scale,
        glow_enabled=style.glow_enabled,
        glow_color=style.glow_color,
        glow_radius=style.glow_radius * scale,
    )
    hi_width = canvas_width * scale
    font = _load_font(hi_style)
    probe_image = Image.new("RGBA", (hi_width, hi_width), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe_image)

    text_width_limit = max(120 * scale, hi_width - (hi_style.margin_x * 2))
    lines = _wrap_text(draw, text.strip(), font, text_width_limit, hi_style.stroke_width)
    while len(lines) < hi_style.min_lines:
        lines.append("")
    line_text = "\n".join(lines)

    left, top, right, bottom = draw.multiline_textbbox(
        (0, 0),
        line_text,
        font=font,
        spacing=hi_style.line_spacing,
        stroke_width=hi_style.stroke_width,
        align="center",
    )
    text_w = int(max(1, round(right - left)))
    text_h = int(max(1, round(bottom - top)))
    # 글로우 효과 시 여백 확대 (블러가 번질 공간 확보)
    glow_pad = hi_style.glow_radius * 2 if hi_style.glow_enabled else 0
    image_w = int(min(hi_width, text_w + hi_style.padding_y * 4 + glow_pad * 2))
    image_h = int(text_h + hi_style.padding_y * 2 + glow_pad * 2)
    image = Image.new("RGBA", (image_w, image_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    tx = (image_w - text_w) / 2
    ty = hi_style.padding_y + glow_pad - top

    # 드롭 섀도우 (오프셋 2px @2x = 1px @1x)
    shadow_offset = max(2, scale)
    draw.multiline_text(
        (tx + shadow_offset, ty + shadow_offset),
        line_text,
        font=font,
        fill=(0, 0, 0, 160),
        stroke_width=0,
        spacing=hi_style.line_spacing,
        align="center",
    )

    # 본문 텍스트
    draw.multiline_text(
        (tx, ty),
        line_text,
        font=font,
        fill=style.text_color,
        stroke_width=hi_style.stroke_width,
        stroke_fill=style.stroke_color,
        spacing=hi_style.line_spacing,
        align="center",
    )

    # 네온 글로우 효과 (glow_enabled 시)
    if hi_style.glow_enabled:
        glow_layer = _render_glow_layer(image, hi_style.glow_color, hi_style.glow_radius)
        # 글로우를 텍스트 아래에 합성
        result = Image.new("RGBA", image.size, (0, 0, 0, 0))
        result = Image.alpha_composite(result, glow_layer)
        result = Image.alpha_composite(result, image)
        image = result

    # 다운샘플 (LANCZOS)
    final_w = max(1, image_w // scale)
    final_h = max(1, image_h // scale)
    image = image.resize((final_w, final_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    return output_path
