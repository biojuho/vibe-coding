"""history_countdown.py — 역사 카운트다운형 템플릿"""

from __future__ import annotations

from ShortsFactory.templates.base_template import BaseTemplate
from ShortsFactory.templates.countdown_mixin import CountdownMixin


class HistoryCountdownTemplate(CountdownMixin, BaseTemplate):
    template_name = "history_countdown"

    default_hook_text = "역사를 바꾼 순간 TOP 5"
    hook_animation = "fade_in"
    hook_font_size = 80
    body_animation = "slide_in_right"
    default_cta_text = "역사의 반전, 더 알고 싶다면!"
