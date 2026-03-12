"""
hook_engine.py — 훅 장면 엔진 v2
===============================
채널별 hook_style에 따라 자동으로 훅 애니메이션을 적용합니다.

v2 개선사항:
- glitch: RGB 채널 분리 시프트 + 노이즈 합성 (사양서 rgbashift 반영)
- brightness flash: 밝기 1.0→1.5→1.0 (0.15초)
- shake: 화면 흔들림 효과 (랜덤 x/y 오프셋)
- reveal: 원형 마스크 확장 애니메이션
- combo: 여러 효과의 순차/병렬 조합 시스템
"""
from __future__ import annotations
import logging, random, math
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)

# hook_style → animation 매핑 (v2: 확장)
_HOOK_ANIMATIONS = {
    "glitch": "glitch",
    "typewriter": "typing",
    "zoom_flash": "popup",
    "clean_popup": "popup",
    "shake": "shake",               # v2: 화면 흔들림
    "reveal": "reveal",             # v2: 원형 마스크 공개
    "glitch_shake": "combo_gs",     # v2: 글리치 + 쉐이크
    "reveal_flash": "combo_rf",     # v2: 리벌 + 플래시
}


def _apply_typing(clip, duration: float):
    w = clip.w
    def filt(get_frame, t):
        frame = np.copy(get_frame(t))
        if t >= duration: return frame
        p = max(0.0, t / duration)
        rw = int(w * p)
        if rw < w: frame[:, rw:] = 0
        return frame
    def filt_mask(get_frame, t):
        m = np.copy(get_frame(t))
        if t >= duration: return m
        p = max(0.0, t / duration)
        rw = int(w * p)
        if rw < w: m[:, rw:] = 0
        return m
    nc = clip.transform(filt)
    if clip.mask: nc.mask = clip.mask.transform(filt_mask)
    return nc

def _apply_popup(clip, duration: float):
    def rs(t):
        if t >= duration: return 1.0
        p = max(0.0, t / duration)
        return (0.5 + (0.6/0.7)*p) if p < 0.7 else (1.1 - (0.1/0.3)*(p-0.7))
    return clip.resized(rs)

def _apply_glitch(clip, duration: float):
    """개선된 글리치: RGB 채널 분리 시프트 + 노이즈 합성.

    사양서 요구사항:
    - 0.1초간 rgbashift + 노이즈
    - RGB 각 채널을 서로 다른 방향으로 시프트
    - 랜덤 노이즈 오버레이
    """
    def filt(get_frame, t):
        frame = get_frame(t)
        if duration <= 0 or t >= duration:  # [QA 수정] duration=0 방어
            return frame

        # 글리치 강도: 시작 시 강하고 점점 약해짐
        intensity = 1.0 - (t / duration)
        frame = np.copy(frame)

        # 프레임의 60%에서 글리치 적용 (간헐적 깜빡임)
        if random.random() < 0.6 * intensity:
            h, w, c = frame.shape

            # 1) RGB 채널 분리 시프트 (각 채널 다른 방향)
            shift_r = random.randint(-int(20 * intensity), int(20 * intensity))
            shift_b = random.randint(-int(15 * intensity), int(15 * intensity))

            result = np.zeros_like(frame)
            # Red 채널 수평 시프트
            if shift_r > 0:
                result[:, shift_r:, 0] = frame[:, :-shift_r, 0]
            elif shift_r < 0:
                result[:, :shift_r, 0] = frame[:, -shift_r:, 0]
            else:
                result[:, :, 0] = frame[:, :, 0]

            # Green 채널 — 원본 유지
            result[:, :, 1] = frame[:, :, 1]

            # Blue 채널 수평 시프트
            if shift_b > 0:
                result[:, shift_b:, 2] = frame[:, :-shift_b, 2]
            elif shift_b < 0:
                result[:, :shift_b, 2] = frame[:, -shift_b:, 2]
            else:
                result[:, :, 2] = frame[:, :, 2]

            frame = result

            # 2) 수평 라인 글리치 (랜덤 행 위치 이동)
            num_lines = random.randint(2, max(3, int(8 * intensity)))
            for _ in range(num_lines):
                y = random.randint(0, h - 1)
                band_h = random.randint(1, max(2, int(10 * intensity)))
                y_end = min(h, y + band_h)
                x_shift = random.randint(-int(40 * intensity), int(40 * intensity))
                if x_shift > 0:
                    frame[y:y_end, x_shift:] = frame[y:y_end, :-x_shift]
                elif x_shift < 0:
                    frame[y:y_end, :x_shift] = frame[y:y_end, -x_shift:]

            # 3) 노이즈 오버레이
            noise_strength = int(30 * intensity)
            if noise_strength > 0:
                noise = np.random.randint(
                    -noise_strength, noise_strength,
                    frame.shape, dtype=np.int16,
                )
                frame = np.clip(
                    frame.astype(np.int16) + noise, 0, 255,
                ).astype(np.uint8)

        return frame

    return clip.transform(filt)


def _apply_brightness_flash(clip, flash_duration: float = 0.15, peak: float = 1.5):
    """밝기 플래시: 1.0→peak→1.0 (사양서: 0.15초).

    Args:
        clip: 대상 클립.
        flash_duration: 플래시 지속 시간.
        peak: 최대 밝기 배율.
    """
    def filt(get_frame, t):
        frame = get_frame(t)
        if t >= flash_duration:
            return frame
        # 삼각파: 0→peak→1.0
        p = t / flash_duration
        if p < 0.5:
            brightness = 1.0 + (peak - 1.0) * (p / 0.5)
        else:
            brightness = peak - (peak - 1.0) * ((p - 0.5) / 0.5)
        return np.clip(
            frame.astype(np.float32) * brightness, 0, 255,
        ).astype(np.uint8)
    return clip.transform(filt)


# ── v2 신규 효과 ──────────────────────────────────────────────────

def _apply_shake(clip, duration: float, max_offset: int = 15):
    """화면 흔들림 효과: 랜덤 x/y 오프셋 적용.

    긴장감/임팩트를 위한 카메라 쉐이크 효과.
    강도는 시간에 따라 감쇠합니다.

    Args:
        clip: 대상 클립.
        duration: 쉐이크 지속 시간.
        max_offset: 최대 픽셀 오프셋.
    """
    def filt(get_frame, t):
        frame = get_frame(t)
        if duration <= 0 or t >= duration:  # [QA 수정] duration=0 방어
            return frame

        intensity = 1.0 - (t / duration)
        frame = np.copy(frame)
        h, w = frame.shape[:2]

        # 랜덤 오프셋 (감쇠 적용)
        ox = random.randint(-int(max_offset * intensity), int(max_offset * intensity))
        oy = random.randint(-int(max_offset * intensity), int(max_offset * intensity))

        result = np.zeros_like(frame)

        # x 오프셋
        if ox > 0:
            result[:, ox:] = frame[:, :w - ox]
        elif ox < 0:
            result[:, :ox] = frame[:, -ox:]
        else:
            result = frame.copy()

        # y 오프셋
        if oy > 0:
            shifted = result.copy()
            result = np.zeros_like(frame)
            result[oy:] = shifted[:h - oy]
        elif oy < 0:
            shifted = result.copy()
            result = np.zeros_like(frame)
            result[:oy] = shifted[-oy:]

        return result

    return clip.transform(filt)


def _apply_reveal(clip, duration: float):
    """원형 마스크 확장 애니메이션: 중앙에서 원이 커지며 클립을 공개.

    Args:
        clip: 대상 클립.
        duration: 리벌 지속 시간.
    """
    def filt(get_frame, t):
        frame = get_frame(t)
        if duration <= 0 or t >= duration:  # [QA 수정] duration=0 방어
            return frame

        frame = np.copy(frame)
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        # ease-out 보간
        p = t / duration
        p = 1.0 - (1.0 - p) ** 3  # cubic ease-out

        # 최대 반경: 대각선 절반
        max_radius = math.sqrt(cx ** 2 + cy ** 2)
        radius = max_radius * p

        # 원형 마스크 생성
        y_grid, x_grid = np.ogrid[:h, :w]
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
        mask = (dist <= radius).astype(np.float32)

        # 부드러운 엣지 (안티앨리어싱)
        edge_width = max(1, int(max_radius * 0.02))
        fade_zone = np.clip((radius - dist) / edge_width, 0, 1)
        mask = fade_zone

        # 마스크 적용
        for c in range(frame.shape[2]):
            frame[:, :, c] = (frame[:, :, c].astype(np.float32) * mask).astype(np.uint8)

        return frame

    return clip.transform(filt)


class HookEngine:
    """훅 장면 엔진 v2. 채널별 hook_style 자동 적용.

    v2 추가 효과:
    - shake: 화면 흔들림 (긴장감)
    - reveal: 원형 마스크 공개
    - combo_gs: 글리치 + 쉐이크 조합
    - combo_rf: 리벌 + 플래시 조합

    Args:
        channel_config: channels.yaml에서 읽은 채널 설정 dict.
    """
    def __init__(self, channel_config: dict[str, Any]) -> None:
        self.config = channel_config
        self.hook_style = channel_config.get("hook_style", "popup")
        self.palette = channel_config.get("palette", {})

    def create_hook(self, clip, *, duration: float = 0.5):
        """채널 hook_style에 맞는 애니메이션을 클립에 적용합니다."""
        anim = _HOOK_ANIMATIONS.get(self.hook_style, "popup")
        logger.debug("[HookEngine] style=%s → anim=%s", self.hook_style, anim)

        if anim == "typing":
            return _apply_typing(clip, duration)
        elif anim == "glitch":
            return _apply_glitch(clip, duration)
        elif anim == "popup":
            return _apply_popup(clip, duration)
        elif anim == "shake":
            return _apply_shake(clip, duration)
        elif anim == "reveal":
            return _apply_reveal(clip, duration)
        elif anim == "combo_gs":
            return self._apply_combo(clip, ["glitch", "shake"], duration)
        elif anim == "combo_rf":
            return self._apply_combo(clip, ["reveal", "flash"], duration)
        return clip

    def create_hook_with_flash(self, clip, *, glitch_duration: float = 0.1,
                                flash_duration: float = 0.15, flash_peak: float = 1.5):
        """글리치 + 밝기 플래시를 순차 적용합니다.

        사양서 요구사항:
        - 글리치 효과: 0.1초간 rgbashift + 노이즈
        - 배경 순간 플래시: 밝기 1.0→1.5→1.0, 0.15초

        Args:
            clip: 대상 클립.
            glitch_duration: 글리치 지속 시간.
            flash_duration: 플래시 지속 시간.
            flash_peak: 최대 밝기 배율.
        """
        clip = _apply_glitch(clip, glitch_duration)
        clip = _apply_brightness_flash(clip, flash_duration, flash_peak)
        return clip

    def create_hook_with_shake(self, clip, *, shake_duration: float = 0.3,
                                flash_duration: float = 0.15, flash_peak: float = 1.3):
        """쉐이크 + 밝기 플래시를 순차 적용합니다.

        Args:
            clip: 대상 클립.
            shake_duration: 쉐이크 지속 시간.
            flash_duration: 플래시 지속 시간.
            flash_peak: 최대 밝기 배율.
        """
        clip = _apply_shake(clip, shake_duration)
        clip = _apply_brightness_flash(clip, flash_duration, flash_peak)
        return clip

    def create_hook_with_reveal(self, clip, *, reveal_duration: float = 0.5,
                                 flash_duration: float = 0.1, flash_peak: float = 1.2):
        """리벌 + 밝기 플래시를 순차 적용합니다.

        Args:
            clip: 대상 클립.
            reveal_duration: 리벌 지속 시간.
            flash_duration: 플래시 지속 시간.
            flash_peak: 최대 밝기 배율.
        """
        clip = _apply_reveal(clip, reveal_duration)
        clip = _apply_brightness_flash(clip, flash_duration, flash_peak)
        return clip

    def get_animation_type(self) -> str:
        """현재 채널의 훅 애니메이션 타입 반환."""
        return _HOOK_ANIMATIONS.get(self.hook_style, "popup")

    def list_available_effects(self) -> list[str]:
        """사용 가능한 모든 효과 이름을 반환합니다."""
        return ["typing", "glitch", "popup", "shake", "reveal",
                "combo_gs", "combo_rf", "flash"]

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    def _apply_combo(self, clip, effects: list[str], duration: float):
        """여러 효과를 순차적으로 조합 적용.

        Args:
            clip: 대상 클립.
            effects: 효과 이름 리스트 (순서대로 적용).
            duration: 각 효과의 지속 시간 (전체 시간을 균등 분배).
        """
        each_dur = duration / max(len(effects), 1)

        _EFFECT_MAP = {
            "glitch": _apply_glitch,
            "shake": _apply_shake,
            "reveal": _apply_reveal,
            "typing": _apply_typing,
            "popup": _apply_popup,
            "flash": lambda c, d: _apply_brightness_flash(c, d),
        }

        for effect_name in effects:
            fn = _EFFECT_MAP.get(effect_name)
            if fn:
                clip = fn(clip, each_dur)
            else:
                logger.warning("[HookEngine] 알 수 없는 효과: %s", effect_name)

        return clip
