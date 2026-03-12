"""history_mystery.py — 역사 미스터리형 템플릿"""
from __future__ import annotations
from typing import Any
from ShortsFactory.templates.base_template import BaseTemplate, Scene


class HistoryMysteryTemplate(BaseTemplate):
    template_name = "history_mystery"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(Scene(
            role="hook",
            text=data.get("hook_text", "아무도 풀지 못한 역사의 수수께끼"),
            duration=3.5, animation="fade_in",
            extra={"font_size": 80, "text_color": "#D4A574"},
        ))
        # 미스터리 배경
        if data.get("background"):
            scenes.append(Scene(
                role="body", text=data["background"],
                duration=6.0, animation="fade_in",
                extra={"style": "mystery_intro"},
            ))
        # 단서들
        for i, clue in enumerate(data.get("clues", [])):
            text = clue if isinstance(clue, str) else clue.get("text", "")
            kw = [] if isinstance(clue, str) else clue.get("keywords", [])
            scenes.append(Scene(
                role="body", text=f"단서 {i+1}: {text}",
                keywords=kw, duration=5.0,
                animation="slide_in_right",
                extra={"clue_index": i + 1, "style": "clue_card"},
            ))
        # 가설들
        for hyp in data.get("hypotheses", []):
            scenes.append(Scene(
                role="body",
                text=hyp if isinstance(hyp, str) else hyp.get("text", ""),
                duration=5.0, animation="fade_in",
                extra={"style": "hypothesis_card"},
            ))
        # 결론/미제
        if data.get("conclusion"):
            scenes.append(Scene(
                role="body", text=data["conclusion"],
                keywords=data.get("conclusion_keywords", []),
                duration=5.0, animation="glow",
            ))
        scenes.append(Scene(
            role="cta", text=data.get("cta_text", "역사의 반전, 더 알고 싶다면!"),
            duration=3.0,
        ))
        return self.finalize_scenes(scenes)
