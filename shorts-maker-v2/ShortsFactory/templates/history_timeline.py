"""history_timeline.py — 역사 타임라인형 템플릿"""
from __future__ import annotations
from typing import Any
from ShortsFactory.templates.base_template import BaseTemplate, Scene

class HistoryTimelineTemplate(BaseTemplate):
    template_name = "history_timeline"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(Scene(
            role="hook", text=data.get("hook_text", "역사 교과서엔 없는 충격적 사실"),
            duration=4.0,
        ))
        for ev in data.get("events", []):
            text = f"{ev.get('date','')} — {ev.get('title','')}"
            if ev.get("desc"):
                text += f"\n{ev['desc']}"
            scenes.append(Scene(
                role="body", text=text,
                keywords=ev.get("keywords", []), duration=5.0,
                extra={"date": ev.get("date",""), "title": ev.get("title","")},
            ))
        if data.get("conclusion"):
            scenes.append(Scene(role="body", text=data["conclusion"], duration=4.0))
        scenes.append(Scene(
            role="cta", text=data.get("cta_text", "역사의 반전, 더 알고 싶다면!"),
            duration=3.0,
        ))
        return self.finalize_scenes(scenes)
