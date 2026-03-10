"""tech_vs.py — 기술 비교(VS) 템플릿

시간 기반 레이아웃:
  0~2초         : 인트로 (좌우 슬라이드인 + VS 충돌)
  2~N초         : 비교 항목별 바 차트 (각 4초, 0→목표값 채움 애니메이션)
  N~N+3초       : 결론 (승자 색상 글로우 + "승자: ○○")

입력:
  item_a: {name, image, scores: {항목: 값}}
  item_b: {name, image, scores: {항목: 값}}
  categories: [str]
"""
from __future__ import annotations
from typing import Any
from ShortsFactory.templates.base_template import BaseTemplate, Scene

# ── 타이밍 상수 ───────────────────────────────────────────────────
_INTRO_DURATION     = 2.0
_CATEGORY_DURATION  = 4.0
_CONCLUSION_DURATION = 3.0

# ── 색상 상수 ────────────────────────────────────────────────────
_COLOR_A = "#00D4FF"   # 시안
_COLOR_B = "#7C3AED"   # 퍼플
_VS_COLOR = "#FF4444"  # 빨강


class TechVsTemplate(BaseTemplate):
    """기술 비교(VS) 쇼츠 템플릿.

    좌우 분할 비교 → 항목별 스코어 바 → 승자 발표.
    """
    template_name = "tech_vs"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes: list[Scene] = []

        item_a = data.get("item_a", {})
        item_b = data.get("item_b", {})
        categories = data.get("categories", [])
        name_a = item_a.get("name", "A")
        name_b = item_b.get("name", "B")
        scores_a = item_a.get("scores", {})
        scores_b = item_b.get("scores", {})

        current_time = 0.0

        # ── 1) 인트로 (0~2초) — VS 충돌 ─────────────────────────
        scenes.append(Scene(
            role="hook",
            text=f"{name_a} vs {name_b}",
            duration=_INTRO_DURATION,
            start_time=current_time,
            animation="vs_clash",
            extra={
                "name_a": name_a,
                "name_b": name_b,
                "image_a": item_a.get("image"),
                "image_b": item_b.get("image"),
                "color_a": _COLOR_A,
                "color_b": _COLOR_B,
                "vs_color": _VS_COLOR,
                "vs_badge_pulse": True,
                "slide_in_duration": 0.4,
            },
        ))
        current_time += _INTRO_DURATION

        # ── 2) 비교 항목별 바 차트 (각 4초) ─────────────────────
        for cat in categories:
            score_a = scores_a.get(cat, 0)
            score_b = scores_b.get(cat, 0)

            scenes.append(Scene(
                role="body",
                text=cat,
                duration=_CATEGORY_DURATION,
                start_time=current_time,
                animation="bar_fill",
                extra={
                    "category": cat,
                    "score_a": score_a,
                    "score_b": score_b,
                    "max_score": max(score_a, score_b, 1) * 1.2,
                    "color_a": _COLOR_A,
                    "color_b": _COLOR_B,
                    "name_a": name_a,
                    "name_b": name_b,
                    "fill_duration": 0.5,
                    "font_size": 44,
                    # VS 타이틀 바 유지 (상단 15%)
                    "vs_title_bar": True,
                    # 좌우 분할 카드 (중앙 55%)
                    "split_cards": True,
                    # 스코어 바 (하단 30%)
                    "score_bar": True,
                },
            ))

            # SFX: 바 채움 사운드
            scenes[-1].extra["sfx_marker"] = {
                "type": "bar_fill",
                "time": current_time + 0.3,
            }

            current_time += _CATEGORY_DURATION

        # ── 3) 결론 (N~N+3초) — 승자 발표 ──────────────────────
        total_a = sum(scores_a.get(c, 0) for c in categories)
        total_b = sum(scores_b.get(c, 0) for c in categories)

        if total_a > total_b:
            winner = name_a
            winner_color = _COLOR_A
        elif total_b > total_a:
            winner = name_b
            winner_color = _COLOR_B
        else:
            winner = "무승부"
            winner_color = "#FFFFFF"

        conclusion_text = data.get(
            "conclusion_text",
            f"승자: {winner}" if winner != "무승부" else "결과: 무승부!",
        )

        scenes.append(Scene(
            role="cta",
            text=conclusion_text,
            duration=_CONCLUSION_DURATION,
            start_time=current_time,
            animation="winner_glow",
            extra={
                "winner": winner,
                "winner_color": winner_color,
                "total_a": total_a,
                "total_b": total_b,
                "name_a": name_a,
                "name_b": name_b,
                "color_a": _COLOR_A,
                "color_b": _COLOR_B,
                "font_size": 72,
                "glow": True,
                "glow_color": winner_color,
                "glow_radius": 25,
                "full_screen_glow": True,
            },
        ))

        # SFX: 승자 발표 팡파르
        scenes[-1].extra["sfx_marker"] = {
            "type": "fanfare" if winner != "무승부" else "draw",
            "time": current_time,
        }

        return self.finalize_scenes(scenes)

    def get_total_duration(self, scenes: list[Scene]) -> float:
        if not scenes:
            return 0.0
        last = scenes[-1]
        return (last.start_time or 0.0) + last.duration

    def get_sfx_markers(self, scenes: list[Scene]) -> list[dict[str, Any]]:
        markers = []
        for scene in scenes:
            marker = scene.extra.get("sfx_marker")
            if marker:
                markers.append(marker)
        return markers

    def get_winner(self, scenes: list[Scene]) -> dict[str, Any]:
        """승자 정보를 반환합니다."""
        for scene in scenes:
            if scene.role == "cta" and "winner" in scene.extra:
                return {
                    "winner": scene.extra["winner"],
                    "winner_color": scene.extra["winner_color"],
                    "total_a": scene.extra["total_a"],
                    "total_b": scene.extra["total_b"],
                }
        return {"winner": "unknown", "winner_color": "#FFFFFF", "total_a": 0, "total_b": 0}
