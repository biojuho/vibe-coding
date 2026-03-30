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
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ── Built-in 프리셋 (이전 color_presets.yaml에서 마이그레이션) ──
_BUILTIN_PRESETS: dict[str, dict[str, Any]] = {
    "neon_tech": {
        "brightness": 0.05,
        "contrast": 1.25,
        "saturation": 1.3,
        "hue_shift": 0,
        "gamma": 0.95,
        "vignette": 0.3,
        "tint": "#0A0E1A",
        "tint_opacity": 0.08,
    },
    "dreamy_purple": {
        "brightness": 0.02,
        "contrast": 1.1,
        "saturation": 1.15,
        "hue_shift": 10,
        "gamma": 1.05,
        "vignette": 0.25,
        "tint": "#1A0A2E",
        "tint_opacity": 0.1,
    },
    "vintage_sepia": {
        "brightness": 0.0,
        "contrast": 1.15,
        "saturation": 0.7,
        "hue_shift": 25,
        "gamma": 1.1,
        "vignette": 0.4,
        "tint": "#2B1810",
        "tint_opacity": 0.15,
    },
    "deep_space": {
        "brightness": -0.05,
        "contrast": 1.2,
        "saturation": 1.1,
        "hue_shift": -5,
        "gamma": 0.9,
        "vignette": 0.35,
        "tint": "#050520",
        "tint_opacity": 0.12,
    },
    "clean_medical": {
        "brightness": 0.03,
        "contrast": 1.05,
        "saturation": 0.95,
        "hue_shift": 0,
        "gamma": 1.0,
        "vignette": 0.15,
        "tint": "#F0FFF0",
        "tint_opacity": 0.05,
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
            logger.warning("[ColorEngine] 프리셋 '%s' 없음. 기본값 사용.", preset_name)
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
                frame = (
                    frame * (1 - preset.tint_opacity)
                    + tint_layer * preset.tint_opacity
                )

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

    # ── v2: LUT 기반 컬러 그레이딩 ─────────────────────────────────

    def apply_lut(
        self, clip, lut_r: np.ndarray | None = None, lut_g: np.ndarray | None = None, lut_b: np.ndarray | None = None
    ) -> Any:
        """1D LUT (Look-Up Table)를 적용합니다.

        256 길이의 numpy 배열로 각 채널의 입출력 매핑을 정의합니다.
        LUT가 None이면 해당 채널은 변환하지 않습니다.

        Args:
            clip: moviepy 클립.
            lut_r: Red 채널 LUT (0-255 → 0-255).
            lut_g: Green 채널 LUT.
            lut_b: Blue 채널 LUT.

        Returns:
            LUT가 적용된 클립.
        """
        identity = np.arange(256, dtype=np.uint8)
        r_table = lut_r if lut_r is not None else identity
        g_table = lut_g if lut_g is not None else identity
        b_table = lut_b if lut_b is not None else identity

        # 길이 검증
        for name, table in [("R", r_table), ("G", g_table), ("B", b_table)]:
            if len(table) != 256:
                logger.warning("[ColorEngine v2] LUT %s 길이가 256이 아님 (%d), 무시", name, len(table))
                return clip

        def _apply_lut(get_frame, t):
            frame = get_frame(t)
            result = np.empty_like(frame)
            result[:, :, 0] = r_table[frame[:, :, 0]]
            result[:, :, 1] = g_table[frame[:, :, 1]]
            result[:, :, 2] = b_table[frame[:, :, 2]]
            return result

        return clip.transform(_apply_lut)

    # ── v2: 역할별 자동 그레이딩 ─────────────────────────────────

    _ROLE_ADJUSTMENTS: dict[str, dict[str, float]] = {
        "hook": {"contrast": 1.3, "saturation": 1.25, "brightness": 0.03, "gamma": 0.92},
        "body": {"contrast": 1.1, "saturation": 1.05, "brightness": 0.0, "gamma": 1.0},
        "cta": {"contrast": 1.15, "saturation": 1.1, "brightness": 0.05, "gamma": 1.08},
    }

    def apply_role_grading(self, clip, role: str = "body") -> Any:
        """씬 역할에 따라 자동으로 컬러 그레이딩을 적용합니다.

        hook: 높은 대비 + 채도 → 시선 집중
        body: 표준 → 편안한 시청
        cta:  밝은 감마 → 긍정적 인상

        기존 프리셋 위에 역할 보정을 추가 적용합니다.

        Args:
            clip: moviepy 클립.
            role: 씬 역할 ("hook" | "body" | "cta").

        Returns:
            역할 기반 그레이딩이 적용된 클립.
        """
        adjustments = self._ROLE_ADJUSTMENTS.get(role, self._ROLE_ADJUSTMENTS["body"])

        # 기존 프리셋과 역할 보정을 조합
        combined_brightness = self.preset.brightness + adjustments["brightness"]
        combined_contrast = self.preset.contrast * adjustments["contrast"]
        combined_saturation = self.preset.saturation * adjustments["saturation"]
        combined_gamma = self.preset.gamma * adjustments["gamma"]

        def _grade_role(get_frame, t):
            frame = get_frame(t).astype(np.float32)
            if combined_brightness != 0:
                frame = frame + combined_brightness * 255
            if combined_contrast != 1.0:
                frame = (frame - 127.5) * combined_contrast + 127.5
            if combined_gamma != 1.0:
                frame = np.clip(frame, 0, 255)
                frame = 255 * (frame / 255) ** (1.0 / combined_gamma)
            if combined_saturation != 1.0:
                gray = 0.299 * frame[:, :, 0] + 0.587 * frame[:, :, 1] + 0.114 * frame[:, :, 2]
                gray = gray[:, :, np.newaxis]
                frame = gray + combined_saturation * (frame - gray)
            return np.clip(frame, 0, 255).astype(np.uint8)

        logger.debug(
            "[ColorEngine v2] role_grading: role=%s, contrast=%.2f, sat=%.2f, gamma=%.2f",
            role,
            combined_contrast,
            combined_saturation,
            combined_gamma,
        )
        return clip.transform(_grade_role)

    # ── v2: 프리셋 블렌딩 ────────────────────────────────────────

    @classmethod
    def blend_presets(cls, preset_a: str, preset_b: str, ratio: float = 0.5) -> ColorEngine:
        """두 프리셋을 비율에 따라 블렌딩한 새 ColorEngine을 생성합니다.

        Args:
            preset_a: 첫 번째 프리셋 이름.
            preset_b: 두 번째 프리셋 이름.
            ratio: 블렌딩 비율 (0.0 = 100% A, 1.0 = 100% B).

        Returns:
            블렌딩된 프리셋의 ColorEngine.
        """
        ratio = max(0.0, min(1.0, ratio))
        presets = _load_presets()
        a_data = presets.get(preset_a, {})
        b_data = presets.get(preset_b, {})

        if not a_data:
            logger.warning("[ColorEngine v2] preset '%s' not found, using defaults", preset_a)
        if not b_data:
            logger.warning("[ColorEngine v2] preset '%s' not found, using defaults", preset_b)

        blended: dict[str, Any] = {}
        numeric_keys = ["brightness", "contrast", "saturation", "hue_shift", "gamma", "vignette", "tint_opacity"]
        for key in numeric_keys:
            val_a = float(a_data.get(key, 0 if key in ("brightness", "hue_shift", "vignette", "tint_opacity") else 1.0))
            val_b = float(b_data.get(key, 0 if key in ("brightness", "hue_shift", "vignette", "tint_opacity") else 1.0))
            blended[key] = val_a * (1 - ratio) + val_b * ratio

        # tint: A 우세 시 A의 tint, B 우세 시 B의 tint
        blended["tint"] = b_data.get("tint", a_data.get("tint", "")) if ratio > 0.5 else a_data.get("tint", "")

        engine = cls.__new__(cls)
        engine._presets = presets
        engine.preset = ColorPreset(blended)
        engine.preset_name = f"{preset_a}+{preset_b}@{ratio:.2f}"
        logger.debug("[ColorEngine v2] blended: %s", engine.preset_name)
        return engine

    # ── v2: 자동 밝기/대비 보정 ──────────────────────────────────

    @staticmethod
    def auto_correct(clip, *, target_mean: float = 128.0, target_std: float = 50.0) -> Any:
        """프레임 분석 기반 자동 밝기/대비 보정.

        첫 프레임의 휘도를 분석하여 target_mean, target_std에 맞게
        전체 클립의 밝기와 대비를 조정합니다.

        Args:
            clip: moviepy 클립.
            target_mean: 목표 평균 밝기 (0-255).
            target_std: 목표 대비 (표준편차).

        Returns:
            보정된 클립.
        """
        try:
            sample_frame = clip.get_frame(0).astype(np.float32)
        except Exception:
            logger.warning("[ColorEngine v2] auto_correct: 프레임 읽기 실패, 패스스루")
            return clip

        # 휘도 계산 (BT.601)
        luma = 0.299 * sample_frame[:, :, 0] + 0.587 * sample_frame[:, :, 1] + 0.114 * sample_frame[:, :, 2]
        current_mean = float(np.mean(luma))
        current_std = float(np.std(luma))

        if current_std < 1.0:
            current_std = 1.0  # 단색 이미지 방어

        # 보정 파라미터 계산
        contrast_factor = target_std / current_std
        brightness_offset = target_mean - current_mean * contrast_factor

        # 과보정 제한
        contrast_factor = max(0.5, min(2.0, contrast_factor))
        brightness_offset = max(-80, min(80, brightness_offset))

        logger.debug(
            "[ColorEngine v2] auto_correct: mean=%.1f→%.1f, std=%.1f→%.1f, contrast=%.2f, brightness_offset=%.1f",
            current_mean,
            target_mean,
            current_std,
            target_std,
            contrast_factor,
            brightness_offset,
        )

        def _auto_correct_frame(get_frame, t):
            frame = get_frame(t).astype(np.float32)
            frame = frame * contrast_factor + brightness_offset
            return np.clip(frame, 0, 255).astype(np.uint8)

        return clip.transform(_auto_correct_frame)

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    @staticmethod
    def _make_vignette_mask(w: int, h: int, strength: float) -> np.ndarray:
        """비네트 마스크 (3채널, float32) 생성."""
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2, h / 2
        max_r = np.sqrt(cx**2 + cy**2)
        dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_r
        mask = 1.0 - strength * dist**2
        mask = np.clip(mask, 0.3, 1.0)
        return mask[:, :, np.newaxis]

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (128, 128, 128)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
