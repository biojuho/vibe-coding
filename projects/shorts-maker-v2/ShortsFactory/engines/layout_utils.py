"""layout_utils.py — Typography wrap and highlighted rendering primitives.

Extracted from TextEngine to decouple typography metrics from styling decisions,
while keeping text layout reusable.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PIL import ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB 형식을 (R, G, B) 튜플로 변환."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def wrap_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    stroke_width: int,
) -> list[str]:
    """텍스트를 최대 너비에 맞게 줄바꿈합니다."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=stroke_width)
        w = bbox[2] - bbox[0]
        if w <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_highlighted_text(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    start_x: float,
    start_y: float,
    style: Any,
    scale: int,
    keywords: list[str],
    img_w: int,
    resolve_keyword_color_fn: Callable[[str], str | None],
) -> None:
    """키워드가 포함된 텍스트를 색상 하이라이트하여 그립니다."""
    y = start_y
    for line in lines:
        # 줄 전체 너비 계산
        line_bbox = draw.textbbox((0, 0), line, font=font, stroke_width=style.stroke_width * scale)
        line_w = line_bbox[2] - line_bbox[0]
        x = (img_w - line_w) / 2  # 중앙 정렬

        # 단어별로 나눠서 키워드 매칭
        remaining = line
        cursor_x = x
        while remaining:
            matched = False
            for kw in keywords:
                if remaining.startswith(kw):
                    # 키워드 색상으로 그리기
                    kw_color = resolve_keyword_color_fn(kw) or style.text_color
                    draw.text(
                        (cursor_x + scale, y + scale),
                        kw,
                        font=font,
                        fill=(0, 0, 0, 160),
                    )
                    draw.text(
                        (cursor_x, y),
                        kw,
                        font=font,
                        fill=kw_color,
                        stroke_width=style.stroke_width * scale,
                        stroke_fill=style.stroke_color,
                    )
                    kw_bbox = draw.textbbox((0, 0), kw, font=font, stroke_width=style.stroke_width * scale)
                    cursor_x += kw_bbox[2] - kw_bbox[0]
                    remaining = remaining[len(kw) :]
                    matched = True
                    break

            if not matched:
                # 일반 문자 그리기 (한 글자씩)
                char = remaining[0]
                draw.text(
                    (cursor_x + scale, y + scale),
                    char,
                    font=font,
                    fill=(0, 0, 0, 160),
                )
                draw.text(
                    (cursor_x, y),
                    char,
                    font=font,
                    fill=style.text_color,
                    stroke_width=style.stroke_width * scale,
                    stroke_fill=style.stroke_color,
                )
                char_bbox = draw.textbbox((0, 0), char, font=font, stroke_width=style.stroke_width * scale)
                cursor_x += char_bbox[2] - char_bbox[0]
                remaining = remaining[1:]

        # 다음 줄
        line_h = line_bbox[3] - line_bbox[1]
        y += line_h + style.line_spacing * scale
