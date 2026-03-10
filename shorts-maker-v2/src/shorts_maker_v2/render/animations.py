from __future__ import annotations

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


def apply_text_animation(clip: ImageClip, animation_type: str, duration: float = 0.5) -> VideoClip:
    """
    Apply a text animation effect to a static ImageClip (e.g., caption).
    Supported types: 'typing', 'glitch', 'popup', or 'none', 'random'.
    """
    if animation_type == "random":
        animation_type = random.choice(["typing", "glitch", "popup"])
        
    if animation_type == "typing":
        return _apply_typing_effect(clip, duration)
    elif animation_type == "glitch":
        return _apply_glitch_effect(clip, duration)
    elif animation_type == "popup":
        return _apply_popup_effect(clip, duration)
        
    return clip
