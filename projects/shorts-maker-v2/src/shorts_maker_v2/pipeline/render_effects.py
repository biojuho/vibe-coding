from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any

import numpy as np
from moviepy import (
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    vfx,
)

if TYPE_CHECKING:
    from shorts_maker_v2.config import AppConfig

logger = logging.getLogger(__name__)

# Role-pair → candidate transition styles (module-level constant)
_STRUCTURAL_MAPPING: dict[tuple[str, str], list[str]] = {
    ("hook", "body"): ["flash", "glitch", "zoom", "rgb_split", "iris"],  # 강한 전환
    ("hook", "cta"): ["flash", "zoom", "iris"],  # 직접 CTA
    ("body", "body"): ["crossfade", "slide", "wipe", "morph_cut"],  # 부드러운 흐름
    ("body", "cta"): ["crossfade", "slide", "zoom", "wipe"],  # 자연스러운 마무리
    ("cta", "body"): ["flash", "glitch", "rgb_split"],  # 재시작 강조
    ("body", "closing"): ["crossfade"],  # 조용한 마무리
    ("cta", "closing"): ["crossfade"],  # CTA 후 여운
    ("hook", "closing"): ["crossfade"],  # 직접 클로징
}


class RenderEffectsMixin:
    """Camera-motion effects and scene transitions.

    Mixed into ``RenderStep`` – all ``self.*`` access refers to RenderStep
    attributes (``config``, ``_channel_key``, ``_pick_transition_style``, etc.).
    """

    # 랜덤 풀에서 제외할 효과 (명시적 지정에서만 사용)
    _RANDOM_EXCLUDE: set[str] = {"shake", "dramatic_ken_burns"}

    # ── Effect map ────────────────────────────────────────────────────────────

    def _build_effect_map(self, target_width: int, target_height: int) -> dict[str, Any]:
        """모든 카메라 모션 효과의 단일 매핑."""
        config: AppConfig = self.config  # type: ignore[attr-defined]
        return {
            "ken_burns": lambda c: self._ken_burns(c, target_width, target_height),
            "dramatic_ken_burns": lambda c: self._dramatic_ken_burns(c, target_width, target_height),
            "zoom_out": lambda c: self._zoom_out(c, target_width, target_height),
            "pan_left": lambda c: self._pan_horizontal(c, target_width, target_height, +1),
            "pan_right": lambda c: self._pan_horizontal(c, target_width, target_height, -1),
            "drift": lambda c: self._drift(c, target_width, target_height),
            "push_in": lambda c: self._push_in(c, target_width, target_height),
            "shake": lambda c: self._shake(c, target_width, target_height, fps=config.video.fps),
            "ease_ken_burns": lambda c: self._ease_ken_burns(c, target_width, target_height),
        }

    # ── Named / channel / random dispatch ─────────────────────────────────────

    def _apply_named_effect(
        self, effect_name: str, clip: Any, target_width: int, target_height: int
    ) -> tuple[Any, str]:
        effect_map = self._build_effect_map(target_width, target_height)
        fn = effect_map.get(effect_name)
        if fn is None:
            return self._apply_random_effect(clip, target_width, target_height)
        return fn(clip), effect_name

    def _apply_channel_image_motion(
        self,
        clip: Any,
        *,
        role: str,
        target_width: int,
        target_height: int,
        exclude: str = "",
    ) -> tuple[Any, str]:
        channel_motion = self._CHANNEL_MOTION_CHOICES.get(self._channel_key, {})  # type: ignore[attr-defined]
        motion = channel_motion.get(role)
        if isinstance(motion, str):
            return self._apply_named_effect(motion, clip, target_width, target_height)
        if isinstance(motion, list) and motion:
            candidates = [name for name in motion if name != exclude] or motion
            chosen = random.choice(candidates)
            return self._apply_named_effect(chosen, clip, target_width, target_height)
        if role == "hook":
            return self._apply_named_effect("dramatic_ken_burns", clip, target_width, target_height)
        return self._apply_random_effect(clip, target_width, target_height, exclude=exclude)

    def _apply_random_effect(
        self,
        clip: Any,
        target_width: int,
        target_height: int,
        *,
        exclude: str = "",
    ) -> tuple[Any, str]:
        """zoom-in / zoom-out / pan / drift / push_in / ease_ken_burns 중 랜덤 선택."""
        all_effects = self._build_effect_map(target_width, target_height)
        excluded = self._RANDOM_EXCLUDE | {exclude}
        candidates = {k: v for k, v in all_effects.items() if k not in excluded}
        if not candidates:
            candidates = all_effects
        chosen_name = random.choice(list(candidates.keys()))
        return candidates[chosen_name](clip), chosen_name

    # ── Static camera-motion effects ──────────────────────────────────────────

    @staticmethod
    def _ken_burns(clip: Any, target_width: int, target_height: int, zoom: float = 0.06) -> Any:
        """이미지 클립에 서서히 줌인하는 켄번스 효과 적용."""

        def resize_func(t: float) -> float:
            return 1.0 + zoom * (t / max(clip.duration, 0.001))

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _dramatic_ken_burns(clip: Any, target_width: int, target_height: int, zoom: float = 0.12) -> Any:
        """Hook 씬용 빠르고 강렬한 줌인 효과 (기본 zoom 2배)."""

        def resize_func(t: float) -> float:
            return 1.0 + zoom * (t / max(clip.duration, 0.001))

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _zoom_out(clip: Any, target_width: int, target_height: int, zoom: float = 0.06) -> Any:
        """이미지 클립에 서서히 줌아웃하는 효과 적용."""

        def resize_func(t: float) -> float:
            return 1.0 + zoom * (1.0 - t / max(clip.duration, 0.001))

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _pan_horizontal(clip: Any, target_width: int, target_height: int, direction: int = 1) -> Any:
        """이미지 클립에 수평 패닝 효과 적용 (direction: +1=좌->우, -1=우->좌)."""
        overscan = 0.12
        zoomed = clip.resized(1.0 + overscan)
        max_shift = zoomed.w * overscan / 2
        dur = max(clip.duration, 0.001)
        zw, zh = zoomed.w, zoomed.h
        y_center = zh / 2

        def make_frame(get_frame: Any, t: float) -> Any:
            frame = get_frame(t)
            progress = t / dur - 0.5
            cx = zw / 2 + direction * max_shift * progress
            x1 = int(max(0, cx - target_width / 2))
            y1 = int(max(0, y_center - target_height / 2))
            return frame[y1 : y1 + target_height, x1 : x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    @staticmethod
    def _drift(clip: Any, target_width: int, target_height: int, speed: float = 0.04) -> Any:
        """Body 씬용 느린 수평 드리프트 (미세한 움직임감)."""
        overscan = 0.06
        zoomed = clip.resized(1.0 + overscan)
        max_shift = zoomed.w * overscan / 2
        dur = max(clip.duration, 0.001)
        zw, zh = zoomed.w, zoomed.h

        def make_frame(get_frame: Any, t: float) -> Any:
            frame = get_frame(t)
            progress = (t / dur) * 2 - 1  # -1 to +1
            cx = zw / 2 + max_shift * progress * speed / 0.04
            x1 = int(max(0, min(cx - target_width / 2, zw - target_width)))
            y1 = int(max(0, (zh - target_height) / 2))
            return frame[y1 : y1 + target_height, x1 : x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    @staticmethod
    def _push_in(clip: Any, target_width: int, target_height: int, zoom: float = 0.08) -> Any:
        """CTA 씬용 점진적 줌인 (긴박감 연출). ease-out 커브 적용."""

        def resize_func(t: float) -> float:
            progress = t / max(clip.duration, 0.001)
            eased = 1.0 - (1.0 - progress) ** 2
            return 1.0 + zoom * eased

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    @staticmethod
    def _shake(clip: Any, target_width: int, target_height: int, amplitude: int = 3, fps: int = 30) -> Any:
        """Hook 씬용 미세 진동 효과 (충격/긴장감)."""
        overscan = 0.04
        zoomed = clip.resized(1.0 + overscan)
        dur = max(clip.duration, 0.001)
        zw, zh = zoomed.w, zoomed.h
        cx, cy = zw / 2, zh / 2
        n_frames = max(1, int(dur * fps))
        rng = np.random.RandomState(42)
        offsets_x = rng.randint(-amplitude, amplitude + 1, size=n_frames)
        offsets_y = rng.randint(-amplitude, amplitude + 1, size=n_frames)

        def make_frame(get_frame: Any, t: float) -> Any:
            frame = get_frame(t)
            decay = max(0.0, 1.0 - t / dur * 0.7)
            idx = min(int(t * fps), n_frames - 1)
            ox = int(offsets_x[idx] * decay)
            oy = int(offsets_y[idx] * decay)
            x1 = int(max(0, min(cx - target_width / 2 + ox, zw - target_width)))
            y1 = int(max(0, min(cy - target_height / 2 + oy, zh - target_height)))
            return frame[y1 : y1 + target_height, x1 : x1 + target_width]

        return zoomed.transform(make_frame).with_duration(clip.duration)

    @staticmethod
    def _ease_ken_burns(clip: Any, target_width: int, target_height: int, zoom: float = 0.08) -> Any:
        """ease-in-out Ken Burns (부드러운 시작/끝). Body 씬에 적합."""

        def resize_func(t: float) -> float:
            progress = t / max(clip.duration, 0.001)
            eased = 4 * progress**3 if progress < 0.5 else 1 - (-2 * progress + 2) ** 3 / 2
            return 1.0 + zoom * eased

        zoomed = clip.resized(resize_func)
        return zoomed.cropped(
            x_center=zoomed.w / 2,
            y_center=zoomed.h / 2,
            width=target_width,
            height=target_height,
        )

    # ── Fit / resize helper ───────────────────────────────────────────────────

    @staticmethod
    def _fit_vertical(clip: Any, target_width: int, target_height: int) -> Any:
        scale = max(target_width / clip.w, target_height / clip.h)
        resized = clip.resized(scale)
        x1 = max(0, (resized.w - target_width) / 2)
        y1 = max(0, (resized.h - target_height) / 2)
        return resized.cropped(x1=x1, y1=y1, x2=x1 + target_width, y2=y1 + target_height)

    # ── Transition staticmethods ──────────────────────────────────────────────
    # Each handler signature: (clip, *, i, is_last, fade_sec, tw, th, prev_clip, **_)
    # Returns: (clips_to_add: list[Any], replace_last: Any | None)
    #   - clips_to_add  : appended to result
    #   - replace_last  : if not None, replaces result[-1] (used by wipe)

    @staticmethod
    def _white_frame(tw: int, th: int, duration: float = 0.12) -> ImageClip:
        arr = np.ones((th, tw, 3), dtype="uint8") * 255
        return ImageClip(arr, is_mask=False).with_duration(duration)

    @staticmethod
    def _transition_crossfade(clip: Any, *, i: int, is_last: bool, fade_sec: float, **_: Any) -> tuple[list[Any], Any]:
        effects = []
        if fade_sec > 0:
            if i > 0:
                effects.append(vfx.FadeIn(fade_sec))
            if not is_last:
                effects.append(vfx.FadeOut(fade_sec))
        if effects:
            clip = clip.with_effects(effects)
        return [clip], None

    @staticmethod
    def _transition_flash(clip: Any, *, is_last: bool, tw: int, th: int, **_: Any) -> tuple[list[Any], Any]:
        clips = [clip]
        if not is_last:
            clips.append(RenderEffectsMixin._white_frame(tw, th))
        return clips, None

    @staticmethod
    def _transition_glitch(clip: Any, *, is_last: bool, tw: int, th: int, **_: Any) -> tuple[list[Any], Any]:
        """Glitch: RGB 채널 분리 + 흰색 플래시 (0.2초)."""
        glitch_dur = 0.2

        def _glitch_factory(_clip: Any, _dur: float, _tw: int, _th: int) -> Any:
            def _filter(get_frame: Any, t: float) -> Any:
                frame = get_frame(t)
                remaining = _clip.duration - t
                if remaining > _dur:
                    return frame
                progress = 1.0 - (remaining / max(0.01, _dur))
                shift = int(18 * (1.0 - progress))
                if shift == 0:
                    return frame
                out = np.copy(frame)
                if shift < _tw:
                    out[:, shift:, 0] = frame[:, :-shift, 0]
                    out[:, :-shift, 2] = frame[:, shift:, 2]
                out[::2, :, :] = np.clip(out[::2, :, :].astype(np.int16) + int(30 * (1.0 - progress)), 0, 255).astype(
                    np.uint8
                )
                return out

            return _filter

        clip = clip.transform(_glitch_factory(clip, glitch_dur, tw, th))
        clips = [clip]
        if not is_last:
            clips.append(RenderEffectsMixin._white_frame(tw, th, 0.06))
        return clips, None

    @staticmethod
    def _transition_zoom(clip: Any, *, is_last: bool, fade_sec: float, **_: Any) -> tuple[list[Any], Any]:
        """Zoom: 현재 클립 끝을 줌-아웃하며 전환."""
        if fade_sec > 0 and not is_last:
            clip = clip.with_effects([vfx.FadeOut(fade_sec * 0.5)])
        return [clip], None

    @staticmethod
    def _transition_slide(clip: Any, *, i: int, is_last: bool, fade_sec: float, **_: Any) -> tuple[list[Any], Any]:
        """Slide: 페이드인/아웃으로 자연스러운 슬라이드 느낌."""
        effects = []
        if i > 0:
            effects.append(vfx.FadeIn(fade_sec * 1.5))
        if not is_last:
            effects.append(vfx.FadeOut(fade_sec * 0.5))
        if effects:
            clip = clip.with_effects(effects)
        return [clip], None

    @staticmethod
    def _transition_wipe(
        clip: Any, *, i: int, fade_sec: float, tw: int, th: int, prev_clip: Any, **_: Any
    ) -> tuple[list[Any], Any]:
        """Wipe: 왼->오 와이프 전환 (이전 클립 위에 다음 클립이 덮어감)."""
        if i == 0 or prev_clip is None:
            return [clip], None

        wipe_dur = min(fade_sec * 2, 0.5)

        def _wipe_mask_factory(_dur: float, _tw: int, _th: int) -> Any:
            def _make_mask(t: float) -> Any:
                buf = np.zeros((_th, _tw), dtype="float32")
                progress = min(1.0, t / max(0.01, _dur))
                reveal_w = int(_tw * progress)
                if reveal_w > 0:
                    buf[:, :reveal_w] = 1.0
                return buf

            return _make_mask

        wipe_mask = VideoClip(_wipe_mask_factory(wipe_dur, tw, th), duration=wipe_dur, is_mask=True)
        wipe_clip = clip.subclipped(0, wipe_dur)
        wipe_clip = wipe_clip.with_start(prev_clip.duration - wipe_dur)
        wipe_clip = wipe_clip.with_mask(wipe_mask)
        combined = CompositeVideoClip([prev_clip, wipe_clip], size=(tw, th)).with_duration(prev_clip.duration)
        # replace_last=combined: wipe는 clips_to_add 없이 result[-1]만 교체
        return [], combined

    @staticmethod
    def _transition_iris(clip: Any, *, fade_sec: float, tw: int, th: int, **_: Any) -> tuple[list[Any], Any]:
        """Iris: 원형으로 확장되며 등장 (아이리스 전환)."""
        iris_dur = min(fade_sec * 2, 0.4)
        cx, cy = tw / 2, th / 2
        max_r = (tw**2 + th**2) ** 0.5 / 2
        y_grid, x_grid = np.ogrid[:th, :tw]
        dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)

        def _iris_factory(_dur: float, _dist: Any, _max_r: float) -> Any:
            def _filter(get_frame: Any, t: float) -> Any:
                frame = get_frame(t)
                if t >= _dur:
                    return frame
                radius = _max_r * (t / max(0.01, _dur))
                mask_3d = (_dist <= radius).astype(np.float32)[:, :, np.newaxis]
                return (frame.astype(np.float32) * mask_3d).astype(np.uint8)

            return _filter

        clip = clip.transform(_iris_factory(iris_dur, dist, max_r))
        return [clip], None

    @staticmethod
    def _transition_rgb_split(clip: Any, *, fade_sec: float, **_: Any) -> tuple[list[Any], Any]:
        """RGB Split: RGB 채널 분리 글리치 전환."""
        split_dur = min(fade_sec, 0.25)

        def _rgb_factory(_dur: float) -> Any:
            def _filter(get_frame: Any, t: float) -> Any:
                frame = get_frame(t)
                if t >= _dur:
                    return frame
                shift = int(12 * (1.0 - t / max(0.01, _dur)))
                if shift == 0:
                    return frame
                out = np.copy(frame)
                out[:, shift:, 0] = frame[:, :-shift, 0]
                out[:, :-shift, 2] = frame[:, shift:, 2]
                return out

            return _filter

        clip = clip.transform(_rgb_factory(split_dur))
        return [clip], None

    @staticmethod
    def _transition_morph_cut(clip: Any, *, i: int, is_last: bool, fade_sec: float, **_: Any) -> tuple[list[Any], Any]:
        """Morph Cut: 급속 줌인 + 페이드 (점프컷 부드러움)."""
        if fade_sec > 0:
            morph_dur = min(fade_sec, 0.3)
            if not is_last:
                clip = clip.with_effects([vfx.FadeOut(morph_dur)])
            if i > 0:
                clip = clip.with_effects([vfx.FadeIn(morph_dur)])

                def _morph_resize(_dur: float) -> Any:
                    def _resize(t: float) -> float:
                        if t >= _dur:
                            return 1.0
                        return 1.05 - 0.05 * (t / max(0.01, _dur))

                    return _resize

                clip = clip.resized(_morph_resize(morph_dur))
        return [clip], None

    # ── Transition picker / applier ───────────────────────────────────────────

    def _pick_transition_style(self) -> str:
        """'random'이면 실제 스타일 중 하나를 무작위 선택."""
        config: AppConfig = self.config  # type: ignore[attr-defined]
        style = config.video.transition_style
        if style == "random":
            return random.choice(["crossfade", "flash", "glitch", "zoom", "slide", "wipe", "iris"])
        return style

    @staticmethod
    def _resolve_structural_style(prev_role: str, cur_role: str, channel_mapping: dict) -> str:
        """역할 쌍에 따른 전환 스타일 결정 (Phase 4-C)."""
        pair = (prev_role, cur_role)
        if pair in channel_mapping:
            return random.choice(channel_mapping[pair])
        choices = _STRUCTURAL_MAPPING.get(pair, ["crossfade", "slide"])
        return random.choice(choices)

    def _apply_transitions(
        self,
        clips: list[Any],
        target_width: int,
        target_height: int,
        roles: list[str] | None = None,
    ) -> list[Any]:
        """
        씬 클립 목록에 전환 효과 적용.
        roles가 주어지면 구조적 패턴 사용:
          Hook->Body : flash (강한 전환)
          Body->Body : crossfade (부드러운 흐름)
          Body->CTA  : crossfade (자연스러운 마무리)
        roles가 없거나 config가 "random"이 아니면 기존 동작 유지.
        """
        config: AppConfig = self.config  # type: ignore[attr-defined]
        fade_sec = config.audio.fade_duration
        global_style = config.video.transition_style

        if global_style == "cut":
            return clips

        channel_mapping = self._CHANNEL_TRANSITIONS.get(self._channel_key, {})  # type: ignore[attr-defined]
        result: list[Any] = []

        for i, clip in enumerate(clips):
            is_last = i == len(clips) - 1

            if roles and i > 0 and global_style == "random" and i < len(roles):
                style = self._resolve_structural_style(roles[min(i - 1, len(roles) - 1)], roles[i], channel_mapping)
            elif global_style == "random":
                style = self._pick_transition_style()
            else:
                style = global_style

            handler = _TRANSITION_DISPATCH.get(style)
            if handler is None:  # unknown style → cut
                result.append(clip)
                continue

            clips_to_add, replace_last = handler(
                clip,
                i=i,
                is_last=is_last,
                fade_sec=fade_sec,
                tw=target_width,
                th=target_height,
                prev_clip=result[-1] if result else None,
            )

            if replace_last is not None:
                result[-1] = replace_last
            result.extend(clips_to_add)

        return result


# Dispatch table populated after class body (references staticmethods by name)
_TRANSITION_DISPATCH: dict[str, Any] = {
    "crossfade": RenderEffectsMixin._transition_crossfade,
    "flash": RenderEffectsMixin._transition_flash,
    "glitch": RenderEffectsMixin._transition_glitch,
    "zoom": RenderEffectsMixin._transition_zoom,
    "slide": RenderEffectsMixin._transition_slide,
    "wipe": RenderEffectsMixin._transition_wipe,
    "iris": RenderEffectsMixin._transition_iris,
    "rgb_split": RenderEffectsMixin._transition_rgb_split,
    "morph_cut": RenderEffectsMixin._transition_morph_cut,
}
