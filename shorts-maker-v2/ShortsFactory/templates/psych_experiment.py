"""psych_experiment.py — 심리 실험형 템플릿"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene


class PsychExperimentTemplate(BaseTemplate):
    template_name = "psych_experiment"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", "이 실험 결과, 충격적입니다"),
                duration=4.0,
            )
        )
        if data.get("background"):
            scenes.append(Scene(role="body", text=data["background"], duration=5.0))
        if data.get("experiment"):
            scenes.append(
                Scene(
                    role="body",
                    text=data["experiment"],
                    keywords=data.get("keywords", []),
                    duration=6.0,
                )
            )
        if data.get("result"):
            scenes.append(
                Scene(
                    role="body",
                    text=data["result"],
                    keywords=data.get("result_keywords", []),
                    duration=5.0,
                )
            )
        if data.get("implication"):
            scenes.append(Scene(role="body", text=data["implication"], duration=5.0))
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", "더 많은 심리학 이야기가 궁금하다면!"),
                duration=3.0,
            )
        )
        return self.finalize_scenes(scenes)
