"""history_fact_reversal.py — 역사 반전 팩트형 템플릿"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene


class HistoryFactReversalTemplate(BaseTemplate):
    template_name = "history_fact_reversal"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", "교과서가 틀렸다?!"),
                duration=3.0,
                animation="fade_in",
                extra={"font_size": 90, "text_color": "#C41E3A"},
            )
        )
        # 통념 (사람들이 알고 있는 것)
        if data.get("myth"):
            scenes.append(
                Scene(
                    role="body",
                    text=f"우리가 아는 것:\n{data['myth']}",
                    duration=5.0,
                    animation="slide_up",
                    extra={"style": "myth_card", "text_color": "#888"},
                )
            )
        # 반전 사실
        if data.get("truth"):
            scenes.append(
                Scene(
                    role="body",
                    text=f"사실은:\n{data['truth']}",
                    keywords=data.get("truth_keywords", []),
                    duration=6.0,
                    animation="glow",
                    extra={"style": "truth_reveal", "text_color": "#D4A574"},
                )
            )
        # 근거/증거
        for ev in data.get("evidence", []):
            text = ev if isinstance(ev, str) else ev.get("text", "")
            scenes.append(
                Scene(
                    role="body",
                    text=text,
                    duration=5.0,
                    animation="fade_in",
                    extra={"style": "evidence_card"},
                )
            )
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", "역사의 반전, 더 알고 싶다면!"),
                duration=3.0,
            )
        )
        return self.finalize_scenes(scenes)
