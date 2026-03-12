"""
color_engine.py — 컬러 그레이딩 엔진
=====================================
채널별 프리셋을 내장하여
영상 클립에 컬러 그레이딩을 적용합니다.

독립 사용:
    from ShortsFactory.engines.color_engine import ColorEngine
    engine = ColorEngine("neon_tech")
    graded_clip = engine.apply_grading(clip)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Built-in 프리셋 (이전 color_presets.yaml에서 마이그레이션) ──
_BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
    "neon_tech": {
        "brightness": 0.05, "contrast": 1.25, "saturation": 1.3,
        "hue_shift": 0, "gamma": 0.95, "vignette": 0.3,
        "tint": "#0A0E1A", "tint_opacity": 0.08,
    },
    "dreamy_purple": {
        "brightness": 0.02, "contrast": 1.1, "saturation": 1.15,
        "hue_shift": 10, "gamma": 1.05, "vignette": 0.25,
        "tint": "#1A0A2E", "tint_opacity": 0.1,
    },
    "vintage_sepia": {
        "brightness": 0.0, "contrast": 1.15, "saturation": 0.7,
        "hue_shift": 25, "gamma": 1.1, "vignette": 0.4,
        "tint": "#2B1810", "tint_opacity": 0.15,
    },
    "deep_space": {
        "brightness": -0.05, "contrast": 1.2, "saturation": 1.1,
        "hue_shift": -5, "gamma": 0.9, "vignette": 0.35,
        "tint": "#050520", "tint_opacity": 0.12,
    },
    "clean_medical": {
        "brightness": 0.03, "contrast": 1.05, "saturation": 0.95,
        "hue_shift": 0, "gamma": 1.0, "vignette": 0.15,
        "tint": "#F0FFF0", "tint_opacity": 0.05,
    },
}


def _load_presets() -> dict[str, Any]:
    """내장 프리셋을 반환합니다."""
    return dict(_BUILTIN_PRESETS)


class ColorPreset:
    """컬러 그레이딩 프리셋 데이터 클래스."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.brightness: float = data.get("brightness", 0.0)
        self.contrast: float = data.get("contrast", 1.0)
        self.saturation: float = data.get("saturation", 1.0)
        self.hue_shift: float = data.get("hue_shift", 0)
        self.gamma: float = data.get("gamma", 1.0)
        self.vignette: float = data.get("vignette", 0.0)
        self.tint: str = data.get("tint", "")
        self.tint_opacity: float = data.get("tint_opacity", 0.0)

    def __repr__(self) -> str:
        return (
            f"ColorPreset(brightness={self.brightness}, contrast={self.contrast}, "
            f"saturation={self.saturation}, gamma={self.gamma})"
        )


class ColorEngine:
    """컬러 그레이딩 엔진.

    Args:
        preset_name: 프리셋 이름 (neon_tech, dreamy_purple, vintage_sepia, deep_space, clean_medical).
    """

    def __init__(
        self,
        preset_name: str,
    ) -> None:
        self._presets = _load_presets()
        preset_data = self._presets.get(preset_name, {})
        if not preset_data:
            logger.warning(
                "[ColorEngine] 프리셋 '%s' 없음. 기본값 사용.", preset_name
            )
        self.preset = ColorPreset(preset_data)
        self.preset_name = preset_name

    # ── 공개 메서드 ─────────────────────────────────────────────────────

    def apply_grading(self, clip) -> Any:
        """moviepy 클립에 컬러 그레이딩을 적용합니다.

        numpy 배열 기반으로 brightness, contrast, saturation,
        gamma, vignette를 프레임 단위로 처리.

        Returns:
            그레이딩이 적용된 클립.
        """
        preset = self.preset
        w, h = clip.size if hasattr(clip, "size") else (1080, 1920)

        # 비네트 마스크 사전 계산
        vignette_mask = None
        if preset.vignette > 0:
            vignette_mask = self._make_vignette_mask(w, h, preset.vignette)

        # tint 색상
        tint_rgb = None
        if preset.tint and preset.tint_opacity > 0:
            tint_rgb = self._hex_to_rgb(preset.tint)

        def _grade_frame(get_frame, t):
            frame = get_frame(t).astype(np.float32)

            # 1. Brightness
            if preset.brightness != 0:
                frame = frame + preset.brightness * 255

            # 2. Contrast
            if preset.contrast != 1.0:
                mean = 127.5
                frame = (frame - mean) * preset.contrast + mean

            # 3. Gamma
            if preset.gamma != 1.0:
                frame = np.clip(frame, 0, 255)
                frame = 255 * (frame / 255) ** (1.0 / preset.gamma)

            # 4. Saturation
            if preset.saturation != 1.0:
                gray = 0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]
                gray = gray[:, :, np.newaxis]
                frame = gray + preset.saturation * (frame - gray)

            # 5. Tint overlay
            if tint_rgb is not None:
                tint_layer = np.array(tint_rgb, dtype=np.float32)
                frame = frame * (1 - preset.tint_opacity) + tint_layer * preset.tint_opacity * 255 / 255.0 * frame / 255.0 * 255

            # 6. Vignette
            if vignette_mask is not None:
                # 프레임 크기와 마스크 크기를 맞춤
                fh, fw = frame.shape[:2]
                if vignette_mask.shape[:2] != (fh, fw):
                    mask = self._make_vignette_mask(fw, fh, preset.vignette)
                else:
                    mask = vignette_mask
                frame = frame * mask

            return np.clip(frame, 0, 255).astype(np.uint8)

        return clip.transform(_grade_frame)

    def get_ffmpeg_filter(self) -> str:
        """FFmpeg CLI용 컬러 그레이딩 필터 문자열을 반환합니다.

        Returns:
            FFmpeg -vf 파라미터 문자열.
        """
        filters = []
        p = self.preset

        # brightness / contrast / saturation
        eq_parts = []
        if p.brightness != 0:
            eq_parts.append(f"brightness={p.brightness}")
        if p.contrast != 1.0:
            eq_parts.append(f"contrast={p.contrast}")
        if p.saturation != 1.0:
            eq_parts.append(f"saturation={p.saturation}")
        if p.gamma != 1.0:
            eq_parts.append(f"gamma={p.gamma}")
        if eq_parts:
            filters.append(f"eq={':'.join(eq_parts)}")

        # hue shift
        if p.hue_shift != 0:
            filters.append(f"hue=h={p.hue_shift}")

        # vignette
        if p.vignette > 0:
            angle = 0.3 + p.vignette * 0.7  # 0.3 ~ 1.0
            filters.append(f"vignette=angle={angle}")

        return ",".join(filters) if filters else "null"

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    @staticmethod
    def _make_vignette_mask(w: int, h: int, strength: float) -> np.ndarray:
        """비네트 마스크 (3채널, float32) 생성."""
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2, h / 2
        max_r = np.sqrt(cx ** 2 + cy ** 2)
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_r
        mask = 1.0 - strength * dist ** 2
        mask = np.clip(mask, 0.3, 1.0)
        return mask[:, :, np.newaxis]

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (128, 128, 128)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
