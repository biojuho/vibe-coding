"""psych_quiz.py — 심리 퀴즈형 템플릿"""
from __future__ import annotations
from typing import Any
from ShortsFactory.templates.base_template import BaseTemplate, Scene


class PsychQuizTemplate(BaseTemplate):
    template_name = "psychology_quiz"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(Scene(
            role="hook", text=data.get("hook_text", "당신은 어떤 유형일까요?"),
            duration=3.0, animation="typewriter",
        ))
        # 질문
        if data.get("question"):
            scenes.append(Scene(
                role="body", text=data["question"],
                duration=5.0, animation="fade_in",
                extra={"font_size": 60, "style": "question_card"},
            ))
        # 선택지
        for i, opt in enumerate(data.get("options", [])):
            label = chr(65 + i)  # A, B, C, D
            text = f"{label}. {opt}" if isinstance(opt, str) else f"{label}. {opt.get('text', '')}"
            scenes.append(Scene(
                role="body", text=text, duration=4.0,
                animation="slide_in_right",
                extra={"option_index": i, "style": "option_card"},
            ))
        # 결과 공개
        if data.get("answer"):
            scenes.append(Scene(
                role="body", text=f"정답: {data['answer']}",
                keywords=data.get("answer_keywords", []),
                duration=5.0, animation="glow",
                extra={"style": "answer_reveal"},
            ))
        if data.get("explanation"):
            scenes.append(Scene(
                role="body", text=data["explanation"], duration=5.0,
            ))
        scenes.append(Scene(
            role="cta", text=data.get("cta_text", "더 많은 심리 퀴즈가 궁금하다면!"),
            duration=3.0,
        ))
        return self.finalize_scenes(scenes)
