"""영상 색보정·필터 시스템.

채널별 컬러 그레이딩 프로파일, 비네트 효과, 밝기/대비/채도 조정.
PIL ImageEnhance 기반 — 추가 의존성 없음.

성능 메모 (2026-05-20, T-333):
  컬러 그레이딩은 렌더 단계 wall time 의 ~40% 를 차지한다
  (bench_render.py A/B: 4s 영상에서 71.1s → 42.7s, 색보정 28.4s).
  `transform` 으로 프레임마다 호출되므로 핫패스다. 따라서:
    - 색보정 산술은 모두 in-place (큰 임시 배열 할당 제거)
    - `color_grade_clip` 의 프레임 함수는 색보정+비네트를 float32 한 번에
      융합 — 기존엔 색보정이 uint8 을 반환하고 비네트가 다시 float32 로
      변환하는 프레임당 왕복 변환이 있었다.
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

# Rec.601 luma 가중치 — 채도 조정의 그레이스케일 기준.
_LUMA_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def _resolve_profile(channel_key: str, role: str, override: dict | None) -> dict:
    """채널 프로파일 + 역할 보정 + override 를 병합한 최종 프로파일."""
    profile = dict(COLOR_PROFILES.get(channel_key, COLOR_PROFILES["default"]))
    role_adj = ROLE_ADJUSTMENTS.get(role, {})
    for k, v in role_adj.items():
        if k in profile and isinstance(profile[k], (int, float)):
            profile[k] = profile[k] * v
    if override:
        profile.update(override)
    return profile


def _grade_inplace(result: np.ndarray, profile: dict) -> None:
    """float32 프레임에 밝기/대비/채도/틴트를 in-place 적용.

    `result` 는 float32 (H, W, 3) 여야 하며 호출 후 덮어쓰여진다.

    핫패스 최적화 (T-333): 프레임당 비용은 거의 전부 전체 프레임을 훑는
    elementwise 패스 횟수에 비례한다 (micro-bench: 1080x1920 패스당 ~14ms).
    그래서 패스를 최소화한다:
      - 밝기+대비를 단일 affine `A*x + B` 로 융합 (4패스 → 2패스).
        대비 피벗은 밝기 적용 후 평균 = brightness * mean(x) 이므로
        A = contrast*brightness, B = brightness*mean(x)*(1-contrast).
      - 채도를 `sat*x + (1-sat)*luma(x)` 로 정리 (3패스 → 2패스).
      - 틴트를 채널별 strided 연산 3회 대신 길이-3 벡터 브로드캐스트 1회로.
    전체 프레임 패스가 ~10 → ~5 로 줄며 결과는 수학적으로 동일하다.
    """
    brightness = float(profile.get("brightness", 1.0))
    contrast = float(profile.get("contrast", 1.0))

    # 1+2) 밝기·대비 융합 — out = (contrast*brightness)*x + brightness*mean*(1-contrast)
    if brightness != 1.0 or contrast != 1.0:
        scale = contrast * brightness
        offset = 0.0
        if contrast != 1.0:
            mean0 = float(result.mean())
            offset = brightness * mean0 * (1.0 - contrast)
        if scale != 1.0:
            result *= scale
        if offset != 0.0:
            result += offset

    # 3) 채도 (luminance 기반) — out = saturation*x + (1-saturation)*luma(x)
    saturation = float(profile.get("saturation", 1.0))
    if saturation != 1.0:
        gray = result @ _LUMA_WEIGHTS  # (H, W) — BLAS 경로, 패스당 ~6ms
        gray *= 1.0 - saturation
        result *= saturation
        result += gray[:, :, np.newaxis]

    # 4) 색조 틴트 — 길이-3 벡터 브로드캐스트 (채널별 strided 연산 회피)
    tint = profile.get("tint", (0, 0, 0))
    if any(t != 0 for t in tint):
        result += np.asarray(tint, dtype=np.float32)


def apply_color_grade(
    frame: np.ndarray,
    channel_key: str = "",
    role: str = "body",
    *,
    override: dict | None = None,
) -> np.ndarray:
    """numpy 프레임에 컬러 그레이딩 적용 (pure-numpy, PIL 라운드트립 없음)."""
    profile = _resolve_profile(channel_key, role, override)
    result = frame.astype(np.float32)
    _grade_inplace(result, profile)
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
    """MoviePy 클립에 컬러 그레이딩 + 비네트 적용.

    프레임 함수는 색보정과 비네트를 단일 float32 패스로 융합한다 —
    프레임당 uint8↔float32 왕복 변환을 제거한다 (T-333).
    """
    profile = _resolve_profile(channel_key, role, None)
    vignette_strength = float(profile.get("vignette_strength", 0.2))
    vignette_key = round(vignette_strength, 2)

    def _grade_frame(get_frame, t):
        frame = get_frame(t)
        result = frame.astype(np.float32)
        _grade_inplace(result, profile)
        if vignette_strength > 0:
            h, w = result.shape[:2]
            result *= _build_vignette_mask(w, h, vignette_key)
        np.clip(result, 0, 255, out=result)
        return result.astype(np.uint8)

    return clip.transform(_grade_frame)
