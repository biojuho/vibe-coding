"""space_scale.py — 우주 스케일형 템플릿"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene


class SpaceScaleTemplate(BaseTemplate):
    template_name = "space_scale"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", "이 스케일, 상상이 되시나요?"),
                duration=4.0,
            )
        )
        for comp in data.get("comparisons", []):
            text = f"{comp.get('small', '')} vs {comp.get('large', '')}"
            if comp.get("desc"):
                text += f"\n{comp['desc']}"
            scenes.append(
                Scene(
                    role="body",
                    text=text,
                    keywords=comp.get("keywords", []),
                    duration=5.0,
                )
            )
        for fact in data.get("facts", []):
            if isinstance(fact, dict):
                scenes.append(
                    Scene(
                        role="body",
                        text=fact.get("text", ""),
                        keywords=fact.get("keywords", []),
                        duration=5.0,
                    )
                )
            else:
                scenes.append(Scene(role="body", text=str(fact), duration=5.0))
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", "우주의 경이로움, 더 알고 싶다면!"),
                duration=3.0,
            )
        )
        return self.finalize_scenes(scenes)
