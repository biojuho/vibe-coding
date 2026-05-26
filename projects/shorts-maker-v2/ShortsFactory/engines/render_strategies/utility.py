from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def render_title(engine: Any, text: str, *, output_path: Path | None = None) -> Path:
    """타이틀 전용 렌더링 (font_title, 큰 폰트 사이즈)."""
    return engine.render_subtitle(
        text,
        role="hook",
        output_path=output_path,
    )


def render_watermark_number(
    engine: Any,
    number: int,
    *,
    font_size: int = 200,
    text_color: str = "#7C3AED",
    opacity: float = 0.5,
    canvas_w: int = 400,
    canvas_h: int = 300,
    output_path: Path | None = None,
) -> Path:
    """큰 워터마크 순번 이미지를 생성합니다."""
    from ShortsFactory.engines.text_engine import _resolve_font

    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scale = 2
    hi_w, hi_h = canvas_w * scale, canvas_h * scale
    hi_font_size = font_size * scale

    image = Image.new("RGBA", (hi_w, hi_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _resolve_font(engine.font_title, hi_font_size)

    num_str = str(number)
    rgb = engine._hex_to_rgb(text_color)
    alpha = int(255 * opacity)

    bbox = draw.textbbox((0, 0), num_str, font=font)
    tx = hi_w * 0.1  # 좌측 여백
    ty = (hi_h - (bbox[3] - bbox[1])) / 2 - bbox[1]

    draw.text(
        (tx, ty),
        num_str,
        font=font,
        fill=(*rgb, alpha),
    )

    image = image.resize((canvas_w, canvas_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    logger.debug("[TextEngine] 워터마크 순번: #%d (%dpx, %.0f%% opacity)", number, font_size, opacity * 100)
    return output_path


def render_progress_bar(
    engine: Any,
    progress: float,
    *,
    width: int = 800,
    height: int = 24,
    bar_color: str | None = None,
    bg_color: str = "#1A1A2E",
    label: str = "",
    output_path: Path | None = None,
) -> Path:
    """진행률 바 이미지를 생성합니다."""
    from ShortsFactory.engines.text_engine import _resolve_font

    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bc = engine._hex_to_rgb(bar_color or engine.palette.get("accent", "#00FF88"))
    bgc = engine._hex_to_rgb(bg_color)

    scale = 2
    total_w = width * scale
    total_h = (height + 30 if label else height) * scale
    bar_h = height * scale
    radius = bar_h // 2

    image = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 배경 바
    draw.rounded_rectangle(
        [(0, 0), (total_w, bar_h)],
        radius=radius,
        fill=(*bgc, 180),
    )

    # 진행 바
    fill_w = max(bar_h, int(total_w * min(1.0, max(0.0, progress))))
    draw.rounded_rectangle(
        [(0, 0), (fill_w, bar_h)],
        radius=radius,
        fill=(*bc, 220),
    )

    # 라벨
    if label:
        label_font = _resolve_font(engine.font_body, int(12 * scale))
        draw.text(
            (total_w - 10 * scale, bar_h + 5 * scale),
            label,
            font=label_font,
            fill=(200, 200, 200, 200),
            anchor="rt",
        )

    # 다운샘플
    final_w = max(1, total_w // scale)
    final_h = max(1, total_h // scale)
    image = image.resize((final_w, final_h), Image.LANCZOS)
    image.save(output_path, format="PNG")
    logger.debug("[TextEngine] 프로그레스 바: %.0f%%", progress * 100)
    return output_path
