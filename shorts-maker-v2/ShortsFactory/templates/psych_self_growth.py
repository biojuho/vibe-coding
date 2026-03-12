"""psych_self_growth.py — 심리 자기성장형 템플릿"""
from __future__ import annotations
from typing import Any
from ShortsFactory.templates.base_template import BaseTemplate, Scene


class PsychSelfGrowthTemplate(BaseTemplate):
    template_name = "psychology_self_growth"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(Scene(
            role="hook",
            text=data.get("hook_text", "오늘부터 달라지는 나"),
            duration=3.5, animation="fade_in",
            extra={"font_size": 70, "text_color": "#E879F9"},
        ))
        # 인용구/메시지
        if data.get("quote"):
            scenes.append(Scene(
                role="body", text=f'"{data["quote"]}"',
                keywords=data.get("quote_keywords", []),
                duration=6.0, animation="fade_in",
                extra={"style": "quote_card", "font_size": 55},
            ))
        # 성장 단계들
        for i, step in enumerate(data.get("steps", [])):
            text = step if isinstance(step, str) else step.get("text", "")
            kw = [] if isinstance(step, str) else step.get("keywords", [])
            scenes.append(Scene(
                role="body", text=f"{i+1}. {text}",
                keywords=kw, duration=5.0,
                animation="slide_up",
                extra={"step_index": i + 1},
            ))
        # 마무리 감성 메시지
        if data.get("closing"):
            scenes.append(Scene(
                role="body", text=data["closing"],
                duration=5.0, animation="fade_in",
                extra={"style": "emotional_closing"},
            ))
        scenes.append(Scene(
            role="cta", text=data.get("cta_text", "나를 이해하는 시간, 더 함께해요"),
            duration=3.0,
        ))
        return self.finalize_scenes(scenes)
