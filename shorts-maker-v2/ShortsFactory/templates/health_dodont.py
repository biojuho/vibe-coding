"""health_dodont.py — 건강 DO/DON'T형 템플릿"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene


class HealthDoDontTemplate(BaseTemplate):
    template_name = "health_dodont"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", "이것만은 꼭 지키세요!"),
                duration=4.0,
            )
        )
        # DO 리스트
        for item in data.get("do_items", []):
            if isinstance(item, dict):
                scenes.append(
                    Scene(
                        role="body",
                        text=f"✅ {item.get('text', '')}",
                        keywords=item.get("keywords", []),
                        duration=5.0,
                        extra={"type": "do"},
                    )
                )
            else:
                scenes.append(
                    Scene(
                        role="body",
                        text=f"✅ {item}",
                        duration=5.0,
                        extra={"type": "do"},
                    )
                )
        # DON'T 리스트
        for item in data.get("dont_items", []):
            if isinstance(item, dict):
                scenes.append(
                    Scene(
                        role="body",
                        text=f"❌ {item.get('text', '')}",
                        keywords=item.get("keywords", []),
                        duration=5.0,
                        extra={"type": "dont"},
                    )
                )
            else:
                scenes.append(
                    Scene(
                        role="body",
                        text=f"❌ {item}",
                        duration=5.0,
                        extra={"type": "dont"},
                    )
                )
        # 요약
        if data.get("summary"):
            scenes.append(Scene(role="body", text=data["summary"], duration=4.0))
        # CTA
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", "건강 정보, 더 알고 싶다면!"),
                duration=3.0,
            )
        )
        # 면책조항은 finalize_scenes에서 자동 삽입 (disclaimer=true)
        return self.finalize_scenes(scenes)
