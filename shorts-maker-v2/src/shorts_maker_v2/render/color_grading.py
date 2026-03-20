"""영상 색보정·필터 시스템.

채널별 컬러 그레이딩 프로파일, 비네트 효과, 밝기/대비/채도 조정.
PIL ImageEnhance 기반 — 추가 의존성 없음.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

# ── 채널별 컬러 그레이딩 프로파일 ─────────────────────────────────────────────
# brightness, contrast, saturation: 1.0 = 원본, >1 = 증가, <1 = 감소
# tint: (r_shift, g_shift, b_shift) — 각 채널에 더할 값 (-30~+30)
# vignette_strength: 0.0 = 없음, 1.0 = 강함

COLOR_PROFILES: dict[str, dict] = {
    "ai_tech": {
        "brightness": 0.95,
        "contrast": 1.12,
        "saturation": 0.90,
        "tint": (-5, 0, 12),  # cool blue shift
        "vignette_strength": 0.3,
    },
    "psychology": {
        "brightness": 1.02,
        "contrast": 1.05,
        "saturation": 1.08,
        "tint": (8, 2, -3),  # warm amber shift
        "vignette_strength": 0.25,
    },
    "history": {
        "brightness": 0.98,
        "contrast": 1.08,
        "saturation": 0.75,
        "tint": (12, 6, -8),  # sepia tone
        "vignette_strength": 0.4,
    },
    "medical": {
        "brightness": 1.05,
        "contrast": 1.03,
        "saturation": 0.95,
        "tint": (-2, 5, 0),  # slight green clinical tone
        "vignette_strength": 0.15,
    },
    "space": {
        "brightness": 0.92,
        "contrast": 1.15,
        "saturation": 1.10,
        "tint": (-3, -2, 15),  # deep blue/indigo
        "vignette_strength": 0.45,
    },
    "default": {
        "brightness": 1.0,
        "contrast": 1.05,
        "saturation": 1.02,
        "tint": (0, 0, 0),
        "vignette_strength": 0.2,
    },
}

# ── 역할별 미세 조정 ──────────────────────────────────────────────────────────
ROLE_ADJUSTMENTS: dict[str, dict] = {
    "hook": {"contrast": 1.08, "saturation": 1.05, "brightness": 0.97},
    "body": {},  # 프로파일 기본값 사용
    "cta": {"brightness": 1.05, "contrast": 1.03, "saturation": 1.02},
}


def apply_color_grade(
    frame: np.ndarray,
    channel_key: str = "",
    role: str = "body",
    *,
    override: dict | None = None,
) -> np.ndarray:
    """numpy 프레임에 컬러 그레이딩 적용 (pure-numpy, PIL 라운드트립 없음)."""
    profile = dict(COLOR_PROFILES.get(channel_key, COLOR_PROFILES["default"]))
    role_adj = ROLE_ADJUSTMENTS.get(role, {})
    for k, v in role_adj.items():
        if k in profile and isinstance(profile[k], (int, float)):
            profile[k] = profile[k] * v
    if override:
        profile.update(override)

    result = frame.astype(np.float32)

    # 1) 밝기
    brightness = float(profile.get("brightness", 1.0))
    if brightness != 1.0:
        result *= brightness

    # 2) 대비
    contrast = float(profile.get("contrast", 1.0))
    if contrast != 1.0:
        mean = result.mean()
        result = (result - mean) * contrast + mean

    # 3) 채도 (luminance 기반)
    saturation = float(profile.get("saturation", 1.0))
    if saturation != 1.0:
        gray = result[:, :, 0] * 0.299 + result[:, :, 1] * 0.587 + result[:, :, 2] * 0.114
        gray = gray[:, :, np.newaxis]
        result = gray + (result - gray) * saturation

    # 4) 색조 틴트
    tint = profile.get("tint", (0, 0, 0))
    if any(t != 0 for t in tint):
        result[:, :, 0] += tint[0]
        result[:, :, 1] += tint[1]
        result[:, :, 2] += tint[2]

    np.clip(result, 0, 255, out=result)
    return result.astype(np.uint8)


@lru_cache(maxsize=8)
def _build_vignette_mask(w: int, h: int, strength: float) -> np.ndarray:
    """비네트 마스크를 한 번 생성하고 캐시."""
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = w // 2, h // 2
    steps = 20
    for i in range(steps):
        ratio = 1.0 - (i / steps)
        alpha = int(255 * (1.0 - strength * ratio * ratio))
        rx = int(cx * (1.0 + ratio * 0.8))
        ry = int(cy * (1.0 + ratio * 0.8))
        draw.ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            fill=alpha,
        )
    mask_arr = np.array(mask, dtype=np.float32) / 255.0
    return mask_arr[:, :, np.newaxis]


def apply_vignette(
    frame: np.ndarray,
    strength: float = 0.3,
) -> np.ndarray:
    """비네트 효과 (가장자리 어둡게, 중앙 집중). 마스크는 캐시됨."""
    if strength <= 0:
        return frame

    h, w = frame.shape[:2]
    # 소수점 2자리 반올림으로 캐시 히트율 향상
    strength_key = round(strength, 2)
    mask_3d = _build_vignette_mask(w, h, strength_key)
    return (frame.astype(np.float32) * mask_3d).astype(np.uint8)


def color_grade_clip(clip, channel_key: str = "", role: str = "body"):
    """MoviePy 클립에 컬러 그레이딩 + 비네트 적용."""
    profile = COLOR_PROFILES.get(channel_key, COLOR_PROFILES["default"])
    vignette_strength = float(profile.get("vignette_strength", 0.2))

    def _grade_frame(get_frame, t):
        frame = get_frame(t)
        frame = apply_color_grade(frame, channel_key, role)
        if vignette_strength > 0:
            frame = apply_vignette(frame, vignette_strength)
        return frame

    return clip.transform(_grade_frame)
