from __future__ import annotations

import math
import random

import numpy as np
from moviepy import ImageClip, VideoClip


def _apply_typing_effect(clip: ImageClip, duration: float) -> VideoClip:
    """Reveals the image from left to right."""
    w = clip.w

    def filter_frame(get_frame, t):
        frame = np.copy(get_frame(t))
        if t >= duration:
            return frame
        progress = max(0.0, t / duration)
        reveal_w = int(w * progress)
        if reveal_w < w:
            frame[:, reveal_w:] = 0
        return frame

    def filter_mask(get_frame, t):
        mask = np.copy(get_frame(t))
        if t >= duration:
            return mask
        progress = max(0.0, t / duration)
        reveal_w = int(w * progress)
        if reveal_w < w:
            mask[:, reveal_w:] = 0
        return mask

    new_clip = clip.transform(filter_frame)
    if clip.mask:
        new_clip.mask = clip.mask.transform(filter_mask)
    return new_clip


def _apply_popup_effect(clip: ImageClip, duration: float) -> VideoClip:
    """Scales up from 0.5 to 1.0 with a slight bounce."""

    def resize_func(t):
        if t >= duration:
            return 1.0
        p = max(0.0, t / duration)
        if p < 0.7:
            # 0.5 to 1.1 bounds
            return 0.5 + (0.6 / 0.7) * p
        else:
            # 1.1 back to 1.0
            return 1.1 - (0.1 / 0.3) * (p - 0.7)

    return clip.resized(resize_func)


def _apply_glitch_effect(clip: ImageClip, duration: float) -> VideoClip:
    """Applies random RGB shifts and horizontal displacements."""

    def filter_frame(get_frame, t):
        frame = get_frame(t)
        if t >= duration:
            return frame
        # Only glitch intermittently
        if int(t * 20) % 2 == 0:
            return frame

        shift = random.randint(-15, 15)
        if shift == 0:
            return frame

        glitched = np.zeros_like(frame)
        if shift > 0:
            glitched[:, shift:] = frame[:, :-shift]
        else:
            glitched[:, :shift] = frame[:, -shift:]

        # Simple color channel swap (R and B)
        glitched_rgb = np.copy(glitched)
        glitched_rgb[:, :, 0] = glitched[:, :, 2]
        glitched_rgb[:, :, 2] = glitched[:, :, 0]
        return glitched_rgb

    def filter_mask(get_frame, t):
        mask = get_frame(t)
        if t >= duration:
            return mask
        if int(t * 20) % 2 == 0:
            return mask

        shift = random.randint(-15, 15)
        if shift == 0:
            return mask

        glitched = np.zeros_like(mask)
        if shift > 0:
            glitched[:, shift:] = mask[:, :-shift]
        else:
            glitched[:, :shift] = mask[:, -shift:]
        return glitched

    new_clip = clip.transform(filter_frame)
    if clip.mask:
        new_clip.mask = clip.mask.transform(filter_mask)
    return new_clip


def _apply_bounce_effect(clip: ImageClip, duration: float) -> VideoClip:
    """탄성 바운스 등장 효과 (위에서 아래로 떨어지며 바운스)."""

    def resize_func(t):
        if t >= duration:
            return 1.0
        p = max(0.0, t / duration)
        # 감쇠 사인파: 위에서 떨어져 바운스
        decay = math.exp(-4.0 * p)
        bounce = abs(math.sin(p * math.pi * 3.0)) * decay
        return 0.3 + 0.7 * (1.0 - bounce) * min(1.0, p * 2.0)

    return clip.resized(resize_func)


def _apply_countdown_effect(clip: ImageClip, duration: float) -> VideoClip:
    """카운트다운 오버레이 효과 (3,2,1 → 콘텐츠 등장).

    처음 0.9초간 3→2→1 페이드 후 메인 콘텐츠 표시.
    """
    countdown_dur = min(0.9, duration * 0.3)  # 최대 0.9초 또는 전체의 30%

    def filter_frame(get_frame, t):
        frame = get_frame(t)
        if t >= countdown_dur:
            return frame
        # 카운트다운 중에는 프레임을 점점 밝게 (fade-in)
        progress = t / countdown_dur
        fade = min(1.0, progress * 1.5)
        return (frame.astype(np.float32) * fade).astype(np.uint8)

    return clip.transform(filter_frame)


def _apply_particle_effect(clip: ImageClip, duration: float) -> VideoClip:
    """간단한 파티클(별/반짝임) 오버레이 효과.

    프레임 위에 랜덤 위치의 밝은 점을 오버레이.
    """
    h, w = clip.h, clip.w
    n_particles = 15
    rng = np.random.RandomState(42)
    particles = [
        (
            rng.randint(0, max(1, w - 1)),
            rng.randint(0, max(1, h - 1)),
            rng.uniform(0.3, 1.0),
            rng.uniform(0.5, 2.0),
        )  # x, y, max_alpha, speed
        for _ in range(n_particles)
    ]

    def filter_frame(get_frame, t):
        frame = np.copy(get_frame(t))
        if t >= duration:
            return frame

        for px, py, max_a, speed in particles:
            # 사인파로 반짝이는 알파
            alpha = max(0.0, max_a * abs(math.sin(t * speed * math.pi)))
            if alpha < 0.1:
                continue
            # 작은 원형 파티클 (3x3)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        blend = alpha * (0.6 if abs(dx) + abs(dy) > 1 else 1.0)
                        frame[ny, nx] = np.clip(
                            frame[ny, nx].astype(np.float32) + 255 * blend,
                            0,
                            255,
                        ).astype(np.uint8)
        return frame

    return clip.transform(filter_frame)


def apply_text_animation(clip: ImageClip, animation_type: str, duration: float = 0.5) -> VideoClip:
    """
    Apply a text animation effect to a static ImageClip (e.g., caption).
    Supported types: 'typing', 'glitch', 'popup', 'bounce', 'countdown',
                     'particle', 'none', 'random'.
    """
    if animation_type == "random":
        animation_type = random.choice(["typing", "glitch", "popup", "bounce"])

    effects = {
        "typing": _apply_typing_effect,
        "glitch": _apply_glitch_effect,
        "popup": _apply_popup_effect,
        "bounce": _apply_bounce_effect,
        "countdown": _apply_countdown_effect,
        "particle": _apply_particle_effect,
    }
    fn = effects.get(animation_type)
    if fn is not None:
        return fn(clip, duration)

    return clip
