from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def render_badge(
    engine: Any,
    number: int,
    *,
    badge_color: str = "#7C3AED",
    text_color: str = "#FFFFFF",
    size: int = 80,
    output_path: Path | None = None,
) -> Path:
    """원형 순번 배지 이미지를 생성합니다."""
    from ShortsFactory.engines.text_engine import _resolve_font

    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scale = 2
    hi_size = size * scale
    image = Image.new("RGBA", (hi_size, hi_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    bg_rgb = engine._hex_to_rgb(badge_color)
    draw.ellipse(
        [0, 0, hi_size - 1, hi_size - 1],
        fill=(*bg_rgb, 255),
    )

    font = _resolve_font(engine.font_title, int(hi_size * 0.5))
    num_str = str(number)
    bbox = draw.textbbox((0, 0), num_str, font=font)
    tx = (hi_size - (bbox[2] - bbox[0])) / 2 - bbox[0]
    ty = (hi_size - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((tx, ty), num_str, font=font, fill=text_color)

    image = image.resize((size, size), Image.LANCZOS)
    image.save(output_path, format="PNG")
    logger.debug("[TextEngine] 배지 렌더: #%d (%dpx)", number, size)
    return output_path


def render_emoji_badge(
    engine: Any,
    emoji: str,
    label: str = "",
    *,
    size: int = 120,
    badge_color: str | None = None,
    output_path: Path | None = None,
) -> Path:
    """이모지 + 라벨 배지 이미지를 생성합니다."""
    from ShortsFactory.engines.text_engine import _resolve_font

    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bc = engine._hex_to_rgb(badge_color or engine.palette.get("accent", "#FF4444"))
    scale = 2
    hi_size = size * scale
    pad = 20 * scale if label else 0

    total_h = hi_size + pad
    image = Image.new("RGBA", (hi_size, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 원형 배경
    draw.ellipse(
        [0, 0, hi_size - 1, hi_size - 1],
        fill=(*bc, 220),
    )

    # 이모지 텍스트 (Segoe UI Emoji 또는 fallback)
    emoji_font = _resolve_font("Segoe UI Emoji", int(hi_size * 0.45))
    e_bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
    e_x = (hi_size - (e_bbox[2] - e_bbox[0])) / 2 - e_bbox[0]
    e_y = (hi_size - (e_bbox[3] - e_bbox[1])) / 2 - e_bbox[1]
    draw.text((e_x, e_y), emoji, font=emoji_font, fill=(255, 255, 255, 255))

    # 라벨
    if label and pad > 0:
        label_font = _resolve_font(engine.font_title, int(14 * scale))
        l_bbox = draw.textbbox((0, 0), label, font=label_font)
        l_x = (hi_size - (l_bbox[2] - l_bbox[0])) / 2 - l_bbox[0]
        draw.text((l_x, hi_size + 2), label, font=label_font, fill=(255, 255, 255, 200))

    # 다운샘플
    final_w = max(1, hi_size // scale)
    final_h = max(1, total_h // scale)
    image = image.resize((final_w, final_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    logger.debug("[TextEngine] 이모지 배지: %s %s", emoji, label)
    return output_path
