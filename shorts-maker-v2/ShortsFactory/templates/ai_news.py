"""ai_news.py — AI 속보형 템플릿 (v2 — 사양서 반영)

시간 기반 레이아웃:
  0.0~1.5초 : 훅 (🚨 AI 속보, 글리치+플래시)
  1.5~3.0초 : 헤드라인 (네온 글로우, 슬라이드업)
  3.0~N초   : 본문 카드 ×3~5 (슬라이드인→유지→슬라이드아웃)
  N~N+5초   : CTA (페이드인, 그라데이션 배경)
"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene

# ── 타이밍 상수 ───────────────────────────────────────────────────
_HOOK_START = 0.0
_HOOK_DURATION = 1.5
_HEADLINE_START = 1.5
_HEADLINE_DUR = 1.5
_CARD_START = 3.0
_CARD_SHOW_DUR = 4.0  # 카드 당 표시 시간
_CARD_TRANS_DUR = 0.4  # 카드 전환 시간 (슬라이드 인/아웃 포함)
_CTA_DURATION = 5.0


class AiNewsTemplate(BaseTemplate):
    """AI/기술 뉴스 속보 템플릿.

    사양서의 시간 기반 레이아웃, 글리치+플래시 훅,
    네온 글로우 헤드라인, 슬라이드 카드, CTA를 반영합니다.
    """

    template_name = "ai_news"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes: list[Scene] = []

        # ── 1) 훅 (0~1.5초) ──────────────────────────────────────
        hook_text = data.get("hook_text", "🚨 AI 속보")
        scenes.append(
            Scene(
                role="hook",
                text=hook_text,
                duration=_HOOK_DURATION,
                start_time=_HOOK_START,
                animation="glitch_flash",  # HookEngine.create_hook_with_flash()
                extra={
                    "font_size": 120,
                    "text_color": "#FF4444",
                    "glitch_duration": 0.1,
                    "flash_duration": 0.15,
                    "flash_peak": 1.5,
                },
            )
        )

        # ── 2) 헤드라인 (1.5~3초) ───────────────────────────────
        title = data.get("news_title", data.get("title", ""))
        if title:
            scenes.append(
                Scene(
                    role="headline",
                    text=title,
                    duration=_HEADLINE_DUR,
                    start_time=_HEADLINE_START,
                    animation="slide_up",  # 하단에서 슬라이드업 0.3초 + 페이드인
                    extra={
                        "font_size": 80,
                        "text_color": "#00D4FF",
                        "glow": True,
                        "glow_color": "#00D4FF",
                        "glow_radius": 20,
                        "slide_duration": 0.3,
                    },
                )
            )

        # ── 3) 본문 카드 (3~N초) ────────────────────────────────
        points = data.get("points", [])
        card_time = _CARD_START
        for i, pt in enumerate(points):
            if isinstance(pt, dict):
                card_text = pt.get("text", "")
                card_keywords = pt.get("keywords", [])
            else:
                card_text = str(pt)
                card_keywords = []

            scenes.append(
                Scene(
                    role="body",
                    text=card_text,
                    keywords=card_keywords,
                    duration=_CARD_SHOW_DUR,
                    start_time=card_time,
                    animation="slide_in_right",  # 우측 슬라이드인 → 좌측 슬라이드아웃
                    extra={
                        "card_index": i + 1,
                        "card_total": len(points),
                        "badge_number": i + 1,
                        "badge_color": "#7C3AED",
                        "card_bg": "#111827",
                        "card_bg_opacity": 0.85,
                        "card_radius": 16,
                        "font_size": 42,
                        "slide_in_duration": 0.3,
                        "slide_out_duration": 0.3,
                        "crossfade_duration": 0.1,
                    },
                )
            )
            card_time += _CARD_SHOW_DUR + _CARD_TRANS_DUR

            # SFX 마커: whoosh 사운드 위치
            scenes[-1].extra["sfx_marker"] = {
                "type": "whoosh",
                "time": card_time - _CARD_TRANS_DUR,
            }

        # ── 4) CTA (N~N+5초) ────────────────────────────────────
        cta_text = data.get(
            "cta_text",
            "다음 AI 소식도 놓치지 마세요",  # 프로젝트 철학 준수 기본값
        )
        scenes.append(
            Scene(
                role="cta",
                text=cta_text,
                duration=_CTA_DURATION,
                start_time=card_time,
                animation="fade_in",
                extra={
                    "font_size": 60,
                    "gradient_shift": True,
                    "gradient_start": "#0A0E1A",
                    "gradient_end": "#1a0a2e",
                    "gradient_duration": 3.0,
                },
            )
        )

        return self.finalize_scenes(scenes)

    def get_total_duration(self, scenes: list[Scene]) -> float:
        """전체 영상 길이(초)를 반환합니다."""
        if not scenes:
            return 0.0
        last = scenes[-1]
        return (last.start_time or 0.0) + last.duration

    def get_sfx_markers(self, scenes: list[Scene]) -> list[dict[str, Any]]:
        """모든 SFX 마커(whoosh 등)를 추출합니다.

        Returns:
            [{"type": "whoosh", "time": 3.4}, ...] 형태의 리스트.
        """
        markers = []
        for scene in scenes:
            marker = scene.extra.get("sfx_marker")
            if marker:
                markers.append(marker)
        return markers
