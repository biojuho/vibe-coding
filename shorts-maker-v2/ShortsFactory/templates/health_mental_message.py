"""health_mental_message.py — 정신건강 감성 메시지 템플릿"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene


class HealthMentalMessageTemplate(BaseTemplate):
    template_name = "health_mental_message"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        # 부드러운 인트로
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", ""),
                duration=3.0,
                animation="fade_in",
                extra={"breathing": True, "style": "gentle_intro"},
            )
        )
        # 메시지 (줄 단위 페이드인)
        lines = data.get("lines", [])
        for i, line in enumerate(lines):
            text = line if isinstance(line, str) else line.get("text", "")
            kw = [] if isinstance(line, str) else line.get("keywords", [])
            scenes.append(
                Scene(
                    role="body",
                    text=text,
                    keywords=kw,
                    duration=4.0,
                    animation="fade_in",
                    extra={
                        "line_index": i,
                        "delay": i * 0.7,
                        "style": "message_line",
                        "font": "NanumMyeongjo",
                        "font_size": 55,
                    },
                )
            )
        # 마무리 위로 메시지
        closing = data.get("closing", "오늘 하루도 잘 버텼어요")
        scenes.append(
            Scene(
                role="body",
                text=closing,
                duration=5.0,
                animation="fade_in",
                extra={"style": "warm_closing"},
            )
        )
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", ""),
                duration=3.0,
            )
        )
        return self.finalize_scenes(scenes)
