"""space_countdown.py — 우주 카운트다운형 템플릿"""

from __future__ import annotations

from ShortsFactory.templates.base_template import BaseTemplate
from ShortsFactory.templates.countdown_mixin import CountdownMixin


class SpaceCountdownTemplate(CountdownMixin, BaseTemplate):
    template_name = "space_countdown"

    default_hook_text = "우주에서 가장 거대한 것 TOP 5"
    hook_animation = "zoom_flash"
    hook_font_size = 90
    body_animation = "slide_in_right"
    default_cta_text = "우주의 경이로움, 더 알고 싶다면!"
    include_value = True
