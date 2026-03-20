"""health_countdown.py — 건강 카운트다운형 템플릿"""

from __future__ import annotations

from ShortsFactory.templates.base_template import BaseTemplate
from ShortsFactory.templates.countdown_mixin import CountdownMixin


class HealthCountdownTemplate(CountdownMixin, BaseTemplate):
    template_name = "health_countdown"

    default_hook_text = "건강을 지키는 습관 TOP 5"
    hook_animation = "clean_popup"
    hook_font_size = 80
    body_animation = "slide_up"
    default_cta_text = "건강 정보, 더 알고 싶다면!"
