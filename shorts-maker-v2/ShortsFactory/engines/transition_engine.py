"""
transition_engine.py — 전환 효과 엔진
======================================
씬 간 전환 효과(crossfade, flash, cut, swipe)를 적용합니다.

독립 사용:
    from ShortsFactory.engines.transition_engine import TransitionEngine
    engine = TransitionEngine(channel_config)
    clips = engine.apply(clip_list, roles=["hook", "body", "body", "cta"])
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from moviepy import (
    ColorClip,
    CompositeVideoClip,
    VideoClip,
    concatenate_videoclips,
)

logger = logging.getLogger(__name__)

# 역할 쌍 → 전환 스타일 매핑
_STRUCTURAL_TRANSITIONS: dict[tuple[str, str], str] = {
    ("hook", "body"): "flash",
    ("body", "body"): "crossfade",
    ("body", "cta"): "flash",
    ("hook", "cta"): "flash",
}


class TransitionEngine:
    """씬 간 전환 효과 엔진.

    Args:
        channel_config: channels.yaml에서 읽은 채널 설정 dict.
    """

    def __init__(self, channel_config: dict[str, Any] | None = None) -> None:
        self.config = channel_config or {}
        self.palette = self.config.get("palette", {})
        self._default_duration = 0.4

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
        return clip_b.with_effects([lambda c: c.crossfadein(d)])

    def flash(self, duration: float = 0.15) -> ColorClip:
        """흰색 플래시 전환 클립 생성."""
        return ColorClip(
            size=(1080, 1920), color=(255, 255, 255)
        ).with_duration(duration).with_effects(
            [lambda c: c.crossfadeout(duration * 0.6)]
        )

    def cut(self) -> None:
        """컷 전환 (효과 없음)."""
        return None

    # ── 내부 메서드 ─────────────────────────────────────────────────────

    def _make_transition(self, clip_a, clip_b, style: str):
        """전환 스타일에 따라 전환 클립/효과를 생성합니다."""
        if style == "flash":
            return self.flash()
        elif style == "crossfade":
            # crossfade는 clip_b 자체에 효과를 적용하므로 None 반환
            # (실제 적용은 concatenate 시점)
            return None
        elif style == "cut":
            return None
        else:
            return None

    @staticmethod
    def _normalize_role(role: str) -> str:
        """역할 이름을 hook/body/cta 중 하나로 정규화."""
        role_lower = role.lower()
        if role_lower in ("hook",):
            return "hook"
        elif role_lower in ("cta",):
            return "cta"
        else:
            return "body"
