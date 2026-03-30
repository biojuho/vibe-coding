"""health_medical_study.py — 의학 연구 인포그래픽 템플릿"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene


class HealthMedicalStudyTemplate(BaseTemplate):
    template_name = "health_medical_study"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes = []
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", "최신 연구가 밝혀낸 충격적 사실"),
                duration=3.0,
                animation="clean_popup",
                extra={"font_size": 80},
            )
        )
        # 연구 소개
        if data.get("study_source"):
            scenes.append(
                Scene(
                    role="body",
                    text=f"연구: {data['study_source']}",
                    duration=4.0,
                    animation="fade_in",
                    extra={"style": "study_source", "text_color": "#3B82F6"},
                )
            )
        if data.get("study_topic"):
            scenes.append(
                Scene(
                    role="body",
                    text=data["study_topic"],
                    keywords=data.get("topic_keywords", []),
                    duration=5.0,
                )
            )
        # 핵심 발견
        for i, finding in enumerate(data.get("findings", [])):
            if isinstance(finding, dict):
                text = finding.get("text", "")
                kw = finding.get("keywords", [])
                value = finding.get("value", "")
            else:
                text, kw, value = str(finding), [], ""
            badge = f"핵심 발견 {i + 1:02d}"
            full = f"{text}\n{value}" if value else text
            scenes.append(
                Scene(
                    role="body",
                    text=full,
                    keywords=kw,
                    duration=5.0,
                    animation="slide_up",
                    extra={"badge": badge, "style": "finding_card"},
                )
            )
        # 결론
        if data.get("conclusion"):
            scenes.append(
                Scene(
                    role="body",
                    text=data["conclusion"],
                    duration=4.0,
                    animation="fade_in",
                    extra={"style": "conclusion"},
                )
            )
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", "건강 정보, 더 알고 싶다면!"),
                duration=3.0,
            )
        )
        return self.finalize_scenes(scenes)
