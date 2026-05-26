from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)


def render_subtitle(
    engine: Any,
    text: str,
    *,
    keywords: list[str] | None = None,
    role: str = "body",
    output_path: Path | None = None,
) -> Path:
    """텍스트와 키워드 하이라이트를 적용한 자막 이미지를 생성합니다."""
    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    layout = engine._prepare_text_layout(text, role)
    style = layout["style"]
    hi_font = layout["hi_font"]
    scale = layout["scale"]
    lines = layout["lines"]
    line_text = layout["line_text"]
    img_w = layout["img_w"]
    img_h = layout["img_h"]
    tx = layout["tx"]
    ty = layout["ty"]

    image = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 배경 박스 (반투명)
    if style.bg_opacity > 0:
        bg_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_layer)
        bg_r, bg_g, bg_b = engine._hex_to_rgb(style.bg_color)
        bg_draw.rounded_rectangle(
            [(0, 0), (img_w, img_h)],
            radius=18 * scale,
            fill=(bg_r, bg_g, bg_b, style.bg_opacity),
        )
        image = Image.alpha_composite(image, bg_layer)
        draw = ImageDraw.Draw(image)

    # 키워드가 없으면 단색 텍스트
    if not keywords:
        # 드롭 섀도우
        draw.multiline_text(
            (tx + scale, ty + scale),
            line_text,
            font=hi_font,
            fill=(0, 0, 0, 160),
            spacing=style.line_spacing * scale,
            align="center",
        )
        draw.multiline_text(
            (tx, ty),
            line_text,
            font=hi_font,
            fill=style.text_color,
            stroke_width=style.stroke_width * scale,
            stroke_fill=style.stroke_color,
            spacing=style.line_spacing * scale,
            align="center",
        )
    else:
        # 키워드 하이라이트 적용 — 줄별로 처리
        engine._draw_highlighted_text(
            draw,
            lines,
            hi_font,
            tx,
            ty,
            style,
            scale,
            keywords,
            img_w,
        )

    # 다운샘플
    final_w = max(1, img_w // scale)
    final_h = max(1, img_h // scale)
    image = image.resize((final_w, final_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    logger.debug("[TextEngine] 자막 렌더: %s (%d×%d)", output_path.name, final_w, final_h)
    return output_path


def render_subtitle_with_glow(
    engine: Any,
    text: str,
    *,
    glow_color: str | None = None,
    glow_radius: int = 20,
    keywords: list[str] | None = None,
    role: str = "body",
    output_path: Path | None = None,
) -> Path:
    """네온 글로우 효과가 적용된 자막 이미지를 생성합니다."""
    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gc = glow_color or engine.palette.get("primary", "#00D4FF")
    gc_rgb = engine._hex_to_rgb(gc)

    scale = 2
    pad = glow_radius * scale
    layout = engine._prepare_text_layout(text, role, scale=scale, extra_pad=pad)
    style = layout["style"]
    hi_font = layout["hi_font"]
    line_text = layout["line_text"]
    img_w = layout["img_w"]
    img_h = layout["img_h"]
    tx = layout["tx"]
    ty = layout["ty"]

    # 1) 글로우 레이어 — 동일 텍스트를 글로우 색상으로, 블러 적용
    glow_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    glow_draw.multiline_text(
        (tx, ty),
        line_text,
        font=hi_font,
        fill=(*gc_rgb, 200),
        spacing=style.line_spacing * scale,
        align="center",
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_radius * scale))

    # 2) 메인 텍스트 레이어
    text_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.multiline_text(
        (tx, ty),
        line_text,
        font=hi_font,
        fill=style.text_color,
        stroke_width=style.stroke_width * scale,
        stroke_fill=style.stroke_color,
        spacing=style.line_spacing * scale,
        align="center",
    )

    # 3) 합성: 글로우 → 텍스트
    result = Image.alpha_composite(glow_layer, text_layer)

    # 다운샘플
    final_w = max(1, img_w // scale)
    final_h = max(1, img_h // scale)
    result = result.resize((final_w, final_h), Image.LANCZOS)
    result.save(output_path, format="PNG")
    logger.debug("[TextEngine] 글로우 자막 렌더: %s", output_path.name)
    return output_path
