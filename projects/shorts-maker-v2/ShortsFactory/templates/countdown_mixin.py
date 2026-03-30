"""countdown_mixin.py — 카운트다운형 템플릿의 공통 로직을 추출한 Mixin.

4개 채널(history, space, health, ai)의 카운트다운 템플릿이
동일한 구조(Hook → Items 루프 → CTA)를 공유하므로,
공통 로직을 Mixin으로 추출하여 코드 중복을 제거합니다.

서브클래스에서 클래스 변수로 채널별 기본값만 지정하면
build_scenes가 자동으로 작동합니다.
"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import Scene


class CountdownMixin:
    """카운트다운형 템플릿의 공통 build_scenes 로직.

    서브클래스에서 다음 클래스 변수를 오버라이드합니다:
        - default_hook_text: 기본 훅 텍스트
        - hook_animation: 훅 애니메이션 (default: "clean_popup")
        - hook_font_size: 훅 폰트 크기 (default: 80)
        - hook_duration: 훅 지속 시간 (default: 3.0)
        - body_animation: 본문 애니메이션 (default: "slide_in_right")
        - body_duration: 본문 카드 지속 시간 (default: 5.0)
        - default_cta_text: 기본 CTA 텍스트
        - cta_duration: CTA 지속 시간 (default: 3.0)
        - card_style: 카드 스타일 키 (default: "countdown_card")
        - include_value: True이면 item의 'value' 필드도 텍스트에 포함 (default: False)
    """

    # --- 서브클래스 오버라이드 포인트 ---
    default_hook_text: str = "TOP 5"
    hook_animation: str = "clean_popup"
    hook_font_size: int = 80
    hook_duration: float = 3.0

    body_animation: str = "slide_in_right"
    body_duration: float = 5.0
    card_style: str = "countdown_card"
    include_value: bool = False

    default_cta_text: str = "더 알고 싶다면!"
    cta_duration: float = 3.0

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        """공통 카운트다운 씬 빌드 로직.

        data 구조:
            hook_text: str (선택)
            items: list[dict] — 각 item에 rank, title/text, description, value, keywords
            cta_text: str (선택)
        """
        scenes: list[Scene] = []

        # Hook
        scenes.append(
            Scene(
                role="hook",
                text=data.get("hook_text", self.default_hook_text),
                duration=self.hook_duration,
                animation=self.hook_animation,
                extra={"font_size": self.hook_font_size},
            )
        )

        # Items (countdown cards)
        for item in data.get("items", []):
            rank = item.get("rank", "")
            text = item.get("title", item.get("text", ""))
            desc = item.get("description", "")
            value = item.get("value", "")

            full = f"#{rank} {text}" if rank else text
            if self.include_value and value:
                full += f"\n{value}"
            if desc:
                full += f"\n{desc}"

            extra: dict[str, Any] = {"rank": rank, "style": self.card_style}
            if self.include_value and value:
                extra["value"] = value

            scenes.append(
                Scene(
                    role="body",
                    text=full,
                    keywords=item.get("keywords", []),
                    duration=self.body_duration,
                    animation=self.body_animation,
                    extra=extra,
                )
            )

        # CTA
        scenes.append(
            Scene(
                role="cta",
                text=data.get("cta_text", self.default_cta_text),
                duration=self.cta_duration,
            )
        )

        return self.finalize_scenes(scenes)
