"""space_fact_bomb.py — 우주 팩트 폭탄형 템플릿"""
from __future__ import annotations
from typing import Any
from ShortsFactory.templates.base_template import BaseTemplate, Scene


class SpaceFactBombTemplate(BaseTemplate):
    template_name = "space_fact_bomb"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(Scene(
            role="hook",
            text=data.get("hook_text", "우주에서 가장 미친 사실"),
            duration=2.5, animation="zoom_flash",
            extra={"font_size": 100, "text_color": "#06B6D4"},
        ))
        for i, fact in enumerate(data.get("facts", [])):
            if isinstance(fact, dict):
                text = fact.get("text", "")
                kw = fact.get("keywords", [])
                sub = fact.get("sub", "")
            else:
                text, kw, sub = str(fact), [], ""
            badge = f"FACT {i+1:02d}"
            scenes.append(Scene(
                role="body", text=text, keywords=kw,
                duration=5.0, animation="slide_in_right",
                extra={
                    "badge": badge, "badge_color": "#06B6D4",
                    "sub_text": sub, "style": "fact_card",
                },
            ))
        if data.get("closing"):
            scenes.append(Scene(
                role="body", text=data["closing"],
                duration=4.0, animation="fade_in",
                extra={"style": "emotional_closing"},
            ))
        scenes.append(Scene(
            role="cta", text=data.get("cta_text", "우주의 경이로움, 더 알고 싶다면!"),
            duration=3.0,
        ))
        return self.finalize_scenes(scenes)
