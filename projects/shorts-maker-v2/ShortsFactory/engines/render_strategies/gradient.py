from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def render_gradient_text(
    engine: Any,
    text: str,
    *,
    color_start: str | None = None,
    color_end: str | None = None,
    role: str = "hook",
    output_path: Path | None = None,
) -> Path:
    """두 색상 사이의 세로 그라데이션이 적용된 텍스트 이미지를 생성합니다."""
    if output_path is None:
        _fd, _tmp = tempfile.mkstemp(suffix=".png")
        os.close(_fd)
        output_path = Path(_tmp)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cs = engine._hex_to_rgb(color_start or engine.palette.get("accent", "#00FF88"))
    ce = engine._hex_to_rgb(color_end or engine.palette.get("primary", "#00D4FF"))

    layout = engine._prepare_text_layout(text, role)
    style = layout["style"]
    hi_font = layout["hi_font"]
    scale = layout["scale"]
    line_text = layout["line_text"]
    img_w = layout["img_w"]
    img_h = layout["img_h"]
    tx = layout["tx"]
    ty = layout["ty"]

    # 1) 텍스트를 흰색으로 먼저 렌더
    text_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    # 드롭 섀도우
    text_draw.multiline_text(
        (tx + scale, ty + scale),
        line_text,
        font=hi_font,
        fill=(0, 0, 0, 160),
        spacing=style.line_spacing * scale,
        align="center",
    )
    text_draw.multiline_text(
        (tx, ty),
        line_text,
        font=hi_font,
        fill=(255, 255, 255, 255),
        stroke_width=style.stroke_width * scale,
        stroke_fill=style.stroke_color,
        spacing=style.line_spacing * scale,
        align="center",
    )

    # 2) 세로 그라데이션 레이어 생성 (numpy 벡터화)
    ratios = np.linspace(0, 1, img_h).reshape(-1, 1)  # (H, 1)
    cs_arr = np.array(cs, dtype=np.float32)  # (3,)
    ce_arr = np.array(ce, dtype=np.float32)  # (3,)
    grad_row = (cs_arr * (1 - ratios) + ce_arr * ratios).astype(np.uint8)  # (H, 3)
    grad_arr = np.tile(grad_row[:, np.newaxis, :], (1, img_w, 1))  # (H, W, 3)
    alpha_ch = np.full((img_h, img_w, 1), 255, dtype=np.uint8)
    grad_rgba = np.concatenate([grad_arr, alpha_ch], axis=-1)  # (H, W, 4)
    gradient = Image.fromarray(grad_rgba)

    # 3) 텍스트 알파로 그라데이션 마스킹
    _, _, _, text_alpha = text_layer.split()
    gradient.putalpha(text_alpha)

    # 4) 스트로크 레이어 (검정 아웃라인)
    stroke_layer = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    stroke_draw = ImageDraw.Draw(stroke_layer)
    stroke_draw.multiline_text(
        (tx, ty),
        line_text,
        font=hi_font,
        fill=(0, 0, 0, 0),
        stroke_width=style.stroke_width * scale,
        stroke_fill=(0, 0, 0, 220),
        spacing=style.line_spacing * scale,
        align="center",
    )

    # 합성: 스트로크 위에 그라데이션 텍스트
    result = Image.alpha_composite(stroke_layer, gradient)

    # 다운샘플
    final_w = max(1, img_w // scale)
    final_h = max(1, img_h // scale)
    result = result.resize((final_w, final_h), Image.LANCZOS)
    result.save(output_path, format="PNG")
    logger.debug("[TextEngine] 그라데이션 텍스트: %s", output_path.name)
    return output_path
