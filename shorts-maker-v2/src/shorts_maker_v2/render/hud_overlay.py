"""AI/기술 채널 전용 HUD (Heads-Up Display) 오버레이.

Neon Cyberpunk 스타일의 기술적 UI 요소를 영상 위에 반투명 오버레이:
- 상단 스캔라인 + 코너 브래킷 프레임
- 좌하단 데이터 스트림 표시
- 우하단 분석 지표 표시
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# HUD 기본 색상 (Neon Cyan)
HUD_COLOR = (0, 240, 255)        # #00F0FF
HUD_COLOR_DIM = (0, 160, 180)    # 어두운 시안
HUD_COLOR_ACCENT = (255, 0, 170)  # #FF00AA (핑크 악센트)

# 데이터 스트림 텍스트 후보
_DATA_TEXTS = [
    "NEURAL LINK ACTIVE",
    "AI PROCESSING...",
    "DATA STREAM ONLINE",
    "QUANTUM SYNC ●",
    "ANALYZING DATA",
    "DEEP LEARNING MODE",
    "SYSTEM NOMINAL",
    "AI CORE ENGAGED",
]

# 지표 표시 후보
_METRIC_LABELS = [
    "ACCURACY",
    "PRECISION",
    "EFFICIENCY",
    "SYNC RATE",
    "CPU LOAD",
    "GPU UTIL",
]


def _load_hud_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """HUD용 고정폭 폰트 로드 (모노스페이스 우선)."""
    mono_candidates = [
        "C:/Windows/Fonts/consola.ttf",    # Consolas
        "C:/Windows/Fonts/cour.ttf",       # Courier New
        "C:/Windows/Fonts/lucon.ttf",      # Lucida Console
    ]
    for fp in mono_candidates:
        p = Path(fp)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_hud_overlay(
    target_width: int = 1080,
    target_height: int = 1920,
    output_path: Path | None = None,
    opacity: int = 100,
) -> Image.Image:
    """HUD 오버레이 이미지 생성.

    Args:
        target_width: 영상 가로 해상도
        target_height: 영상 세로 해상도
        output_path: 저장 경로 (None이면 저장하지 않음)
        opacity: 전체 오버레이 투명도 (0-255)

    Returns:
        RGBA 이미지
    """
    img = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── 코너 브래킷 ──────────────────────────────────
    bracket_len = 60
    bracket_width = 2
    margin = 30
    color = (*HUD_COLOR, opacity)
    accent = (*HUD_COLOR_ACCENT, opacity)

    # 좌상단
    draw.line([(margin, margin), (margin + bracket_len, margin)], fill=color, width=bracket_width)
    draw.line([(margin, margin), (margin, margin + bracket_len)], fill=color, width=bracket_width)
    # 우상단
    draw.line([(target_width - margin, margin), (target_width - margin - bracket_len, margin)], fill=color, width=bracket_width)
    draw.line([(target_width - margin, margin), (target_width - margin, margin + bracket_len)], fill=color, width=bracket_width)
    # 좌하단
    draw.line([(margin, target_height - margin), (margin + bracket_len, target_height - margin)], fill=accent, width=bracket_width)
    draw.line([(margin, target_height - margin), (margin, target_height - margin - bracket_len)], fill=accent, width=bracket_width)
    # 우하단
    draw.line([(target_width - margin, target_height - margin), (target_width - margin - bracket_len, target_height - margin)], fill=accent, width=bracket_width)
    draw.line([(target_width - margin, target_height - margin), (target_width - margin, target_height - margin - bracket_len)], fill=accent, width=bracket_width)

    # ── 상단 스캔라인 ─────────────────────────────────
    scanline_y = margin + 8
    for i in range(3):
        y = scanline_y + i * 4
        line_alpha = max(20, opacity // (i + 1))
        draw.line(
            [(margin + bracket_len + 10, y), (target_width - margin - bracket_len - 10, y)],
            fill=(*HUD_COLOR_DIM, line_alpha),
            width=1,
        )

    # ── 좌하단 데이터 스트림 ──────────────────────────
    font_sm = _load_hud_font(18)
    data_text = random.choice(_DATA_TEXTS)
    text_x = margin + 10
    text_y = target_height - margin - 100
    draw.text(
        (text_x, text_y),
        data_text,
        font=font_sm,
        fill=(*HUD_COLOR, min(255, opacity + 40)),
    )
    # 하단 타임스탬프 느낌
    timestamp = f"SYS.T {random.randint(1000, 9999)}.{random.randint(10, 99)}"
    draw.text(
        (text_x, text_y + 24),
        timestamp,
        font=font_sm,
        fill=(*HUD_COLOR_DIM, opacity),
    )

    # ── 우하단 분석 지표 ──────────────────────────────
    metric_label = random.choice(_METRIC_LABELS)
    metric_value = f"{random.randint(85, 99)}.{random.randint(0, 9)}%"
    metric_x = target_width - margin - 180
    metric_y = target_height - margin - 100
    draw.text(
        (metric_x, metric_y),
        metric_label,
        font=font_sm,
        fill=(*HUD_COLOR_DIM, opacity),
    )
    font_lg = _load_hud_font(28)
    draw.text(
        (metric_x, metric_y + 22),
        metric_value,
        font=font_lg,
        fill=(*HUD_COLOR, min(255, opacity + 60)),
    )

    # ── 작은 미니바 (우하단 지표 아래) ────────────────
    bar_x = metric_x
    bar_y = metric_y + 56
    bar_width = 140
    bar_height = 4
    fill_pct = random.uniform(0.75, 0.98)
    draw.rectangle(
        [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
        fill=(*HUD_COLOR_DIM, opacity // 2),
    )
    draw.rectangle(
        [(bar_x, bar_y), (bar_x + int(bar_width * fill_pct), bar_y + bar_height)],
        fill=(*HUD_COLOR, opacity),
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), format="PNG")

    return img
