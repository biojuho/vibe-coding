"""
transition_engine.py — 전환 효과 엔진 v2
======================================
씬 간 전환 효과(crossfade, flash, cut, swipe, blur_dissolve, zoom)를 적용합니다.

v2 개선사항:
- swipe (좌→우 / 상→하) 전환
- blur_dissolve (가우시안 블러 디졸브)
- zoom_through (줌-인 전환)
- 구조적 역할 기반 자동 전환 선택 개선
- 전환 속도/방향 커스터마이징

독립 사용:
    from ShortsFactory.engines.transition_engine import TransitionEngine
    engine = TransitionEngine(channel_config)
    clips = engine.apply(clip_list, roles=["hook", "body", "body", "cta"])
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

import numpy as np
from PIL import Image, ImageFilter

if TYPE_CHECKING:
    from moviepy import ColorClip, CompositeVideoClip, VideoClip

logger = logging.getLogger(__name__)


def _import_moviepy():
    """moviepy를 lazy import합니다 (ffmpeg 미설치 환경 대응)."""
    from moviepy import ColorClip, CompositeVideoClip, VideoClip, concatenate_videoclips
    return ColorClip, CompositeVideoClip, VideoClip, concatenate_videoclips


# 역할 쌍 → 전환 스타일 매핑 (v2: 더 다양한 전환)
_STRUCTURAL_TRANSITIONS: dict[tuple[str, str], str] = {
    ("hook", "body"): "flash",
    ("body", "body"): "crossfade",
    ("body", "cta"): "zoom_through",
    ("hook", "cta"): "flash",
    ("intro", "hook"): "swipe_right",
    ("cta", "outro"): "blur_dissolve",
}


class TransitionEngine:
    """씬 간 전환 효과 엔진 v2.

    v2 추가 효과:
    - swipe_left / swipe_right / swipe_up / swipe_down
    - blur_dissolve
    - zoom_through

    Args:
        channel_config: channel_profiles.yaml에서 읽은 채널 설정 dict.
    """

    def __init__(self, channel_config: dict[str, Any] | None = None) -> None:
        self.config = channel_config or {}
        self.palette = self.config.get("palette", {})
        self._default_duration = 0.4
        self._width = 1080
        self._height = 1920

    # ── 공개 메서드 ─────────────────────────────────────────────────────

    def apply(
        self,
        clips: list,
        *,
        roles: list[str] | None = None,
        default_style: str = "crossfade",
    ) -> list:
        """클립 리스트에 전환 효과를 적용합니다.

        Args:
            clips: moviepy 클립 리스트.
            roles: 각 클립의 역할 (hook/body/cta 등).
            default_style: 역할 미지정 시 기본 전환 스타일.

        Returns:
            전환 효과가 적용된 클립 리스트.
        """
        if len(clips) <= 1:
            return clips

        result: list = [clips[0]]
        for i in range(1, len(clips)):
            if roles and i < len(roles) and i - 1 < len(roles):
                prev_role = self._normalize_role(roles[i - 1])
                cur_role = self._normalize_role(roles[i])
                style = _STRUCTURAL_TRANSITIONS.get(
                    (prev_role, cur_role), default_style
                )
            else:
                style = default_style

            transition_clip = self._make_transition(
                clips[i - 1], clips[i], style
            )
            if transition_clip is not None:
                result.append(transition_clip)
            result.append(clips[i])

        return result

    def crossfade(self, clip_a, clip_b, duration: float = 0.4):
        """두 클립 사이에 크로스페이드 전환.

        Returns:
            크로스페이드가 적용된 clip_b.
        """
        d = min(duration, clip_a.duration * 0.3, clip_b.duration * 0.3)
        if d <= 0:
            return clip_b
        from moviepy.video.fx import CrossFadeIn  # [QA 수정] MoviePy v2 Effect 클래스
        return clip_b.with_effects([CrossFadeIn(d)])

    def flash(self, duration: float = 0.15):
        """흰색 플래시 전환 클립 생성."""
        ColorClip, _, _, _ = _import_moviepy()
        from moviepy.video.fx import CrossFadeOut  # [QA 수정] MoviePy v2 Effect 클래스
        return ColorClip(
            size=(self._width, self._height), color=(255, 255, 255)
        ).with_duration(duration).with_effects(
            [CrossFadeOut(duration * 0.6)]
        )

    def cut(self) -> None:
        """컷 전환 (효과 없음)."""
        return None

    # ── v2 신규 전환 효과 ─────────────────────────────────────────────

    def swipe(
        self,
        clip_a,
        clip_b,
        *,
        direction: str = "right",
        duration: float = 0.3,
    ):
        """스와이프 전환: 한 클립이 밀려나면서 다음 클립이 나타남.

        Args:
            clip_a: 나가는 클립.
            clip_b: 들어오는 클립.
            direction: 스와이프 방향 ("left", "right", "up", "down").
            duration: 전환 시간.

        Returns:
            전환 효과가 적용된 CompositeVideoClip.
        """
        w, h = self._width, self._height
        d = min(duration, clip_a.duration * 0.4, clip_b.duration * 0.4)

        def make_frame(t):
            """두 프레임을 스와이프로 합성."""
            progress = min(1.0, t / max(d, 0.01))
            # ease-out 보간
            p = 1.0 - (1.0 - progress) ** 2

            frame_a = clip_a.get_frame(clip_a.duration - d + t)
            frame_b = clip_b.get_frame(t)

            # 프레임 크기 맞춤
            fa = self._resize_frame(frame_a, w, h)
            fb = self._resize_frame(frame_b, w, h)

            result = np.zeros((h, w, 3), dtype=np.uint8)

            if direction == "right":
                offset = int(w * p)
                if offset < w:
                    result[:, offset:] = fa[:, :w - offset]
                result[:, :offset] = fb[:, w - offset:]
            elif direction == "left":
                offset = int(w * p)
                if offset < w:
                    result[:, :w - offset] = fa[:, offset:]
                result[:, w - offset:] = fb[:, :offset]
            elif direction == "down":
                offset = int(h * p)
                if offset < h:
                    result[offset:, :] = fa[:h - offset, :]
                result[:offset, :] = fb[h - offset:, :]
            elif direction == "up":
                offset = int(h * p)
                if offset < h:
                    result[:h - offset, :] = fa[offset:, :]
                result[h - offset:, :] = fb[:offset, :]

            return result

        _, _, VideoClip, _ = _import_moviepy()
        return VideoClip(make_frame, duration=d).with_fps(30)

    def blur_dissolve(
        self,
        clip_a,
        clip_b,
        *,
        duration: float = 0.5,
        max_blur: int = 20,
    ):
        """블러 디졸브 전환: A가 블러되면서 B로 전환.

        Args:
            clip_a: 나가는 클립.
            clip_b: 들어오는 클립.
            duration: 전환 시간.
            max_blur: 최대 블러 반경.

        Returns:
            전환 효과가 적용된 VideoClip.
        """
        w, h = self._width, self._height
        d = min(duration, clip_a.duration * 0.5, clip_b.duration * 0.5)

        def make_frame(t):
            progress = min(1.0, t / max(d, 0.01))
            # ease-in-out
            p = progress * progress * (3 - 2 * progress)

            frame_a = clip_a.get_frame(clip_a.duration - d + t)
            frame_b = clip_b.get_frame(t)

            fa = self._resize_frame(frame_a, w, h)
            fb = self._resize_frame(frame_b, w, h)

            # A에 가우시안 블러 적용 (점점 강해짐)
            blur_radius = int(max_blur * p)
            if blur_radius > 0:
                img_a = Image.fromarray(fa)
                img_a = img_a.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                fa = np.array(img_a)

            # 가중 평균으로 블렌딩
            result = (fa.astype(np.float32) * (1 - p) + fb.astype(np.float32) * p)
            return result.astype(np.uint8)

        _, _, VideoClip, _ = _import_moviepy()
        return VideoClip(make_frame, duration=d).with_fps(30)

    def zoom_through(
        self,
        clip_a,
        clip_b,
        *,
        duration: float = 0.4,
        max_zoom: float = 2.0,
    ):
        """줌-스루 전환: A가 줌-인되면서 B가 나타남.

        중앙으로 줌-인하면서 기존 클립이 사라지고 새 클립이 줌-아웃되며 나타남.

        Args:
            clip_a: 나가는 클립.
            clip_b: 들어오는 클립.
            duration: 전환 시간.
            max_zoom: 최대 확대 배율.

        Returns:
            전환 효과가 적용된 VideoClip.
        """
        w, h = self._width, self._height
        d = min(duration, clip_a.duration * 0.3, clip_b.duration * 0.3)

        def make_frame(t):
            progress = min(1.0, t / max(d, 0.01))
            # ease-in-out
            p = progress * progress * (3 - 2 * progress)

            if p < 0.5:
                # 전반부: A가 줌-인
                frame = clip_a.get_frame(clip_a.duration - d + t)
                frame = self._resize_frame(frame, w, h)
                zoom = 1.0 + (max_zoom - 1.0) * (p / 0.5)
                alpha = 1.0 - p / 0.5
            else:
                # 후반부: B가 줌-아웃
                frame = clip_b.get_frame(t)
                frame = self._resize_frame(frame, w, h)
                zoom = max_zoom - (max_zoom - 1.0) * ((p - 0.5) / 0.5)
                alpha = (p - 0.5) / 0.5

            # 중앙 크롭을 이용한 줌 효과
            result = self._apply_zoom(frame, zoom, w, h)

            # 투명도 조절 (검정으로 페이드)
            result = (result.astype(np.float32) * alpha).astype(np.uint8)

            return result

        _, _, VideoClip, _ = _import_moviepy()
        return VideoClip(make_frame, duration=d).with_fps(30)

    def color_wipe(
        self,
        duration: float = 0.2,
        color: str | None = None,
    ):
        """컬러 와이프 전환: 채널 accent 색상으로 화면을 한 번 스윕.

        Args:
            duration: 전환 시간.
            color: 와이프 색상 (None이면 palette accent).

        Returns:
            전환 클립.
        """
        w, h = self._width, self._height
        hex_color = color or self.palette.get("accent", "#00FF88")
        rgb = self._hex_to_rgb(hex_color)

        def make_frame(t):
            progress = min(1.0, t / max(duration, 0.01))
            frame = np.zeros((h, w, 3), dtype=np.uint8)

            # 사각형 와이프 (좌→우)
            wipe_x = int(w * progress * 2)  # 2배속으로 지나감
            if wipe_x <= w:
                # 와이프 바 (너비 80px)
                bar_start = max(0, wipe_x - 80)
                bar_end = min(w, wipe_x)
                for x in range(bar_start, bar_end):
                    # 페이드 아웃
                    alpha = (x - bar_start) / max(bar_end - bar_start, 1)
                    for c in range(3):
                        frame[:, x, c] = int(rgb[c] * alpha)

            return frame

        _, _, VideoClip, _ = _import_moviepy()
        return VideoClip(make_frame, duration=duration).with_fps(30)

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    def _make_transition(self, clip_a, clip_b, style: str):
        """전환 스타일에 따라 전환 클립/효과를 생성합니다."""
        if style == "flash":
            return self.flash()
        elif style == "crossfade":
            return None  # crossfade는 concatenate 시 적용
        elif style == "cut":
            return None
        elif style.startswith("swipe"):
            parts = style.split("_")
            direction = parts[1] if len(parts) > 1 else "right"
            return self.swipe(clip_a, clip_b, direction=direction)
        elif style == "blur_dissolve":
            return self.blur_dissolve(clip_a, clip_b)
        elif style == "zoom_through":
            return self.zoom_through(clip_a, clip_b)
        elif style == "color_wipe":
            return self.color_wipe()
        else:
            logger.debug("[TransitionEngine] 알 수 없는 스타일 '%s', 건너뜀", style)
            return None

    @staticmethod
    def _normalize_role(role: str) -> str:
        """역할 이름을 hook/body/cta/intro/outro 중 하나로 정규화."""
        role_lower = role.lower()
        if role_lower in ("hook",):
            return "hook"
        elif role_lower in ("cta",):
            return "cta"
        elif role_lower in ("intro",):
            return "intro"
        elif role_lower in ("outro",):
            return "outro"
        else:
            return "body"

    @staticmethod
    def _resize_frame(frame: np.ndarray, w: int, h: int) -> np.ndarray:
        """프레임을 지정 크기로 리사이즈."""
        fh, fw = frame.shape[:2]
        if fh == h and fw == w:
            return frame
        img = Image.fromarray(frame)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    @staticmethod
    def _apply_zoom(frame: np.ndarray, zoom: float, w: int, h: int) -> np.ndarray:
        """프레임에 줌 효과를 적용 (중앙 크롭 + 리사이즈)."""
        if zoom <= 1.0:
            return frame
        fh_orig = frame.shape[0]  # [QA 수정] 미사용 변수 제거
        fw_orig = frame.shape[1]

        crop_w = int(fw_orig / zoom)
        crop_h = int(fh_orig / zoom)
        cx = fw_orig // 2
        cy = fh_orig // 2

        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(fw_orig, x1 + crop_w)
        y2 = min(fh_orig, y1 + crop_h)

        cropped = frame[y1:y2, x1:x2]
        img = Image.fromarray(cropped)
        img = img.resize((w, h), Image.LANCZOS)
        return np.array(img)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (255, 255, 255)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
