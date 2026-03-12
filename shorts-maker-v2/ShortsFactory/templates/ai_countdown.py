"""ai_countdown.py — AI 카운트다운형 템플릿"""
from __future__ import annotations
from ShortsFactory.templates.base_template import BaseTemplate
from ShortsFactory.templates.countdown_mixin import CountdownMixin


class AiCountdownTemplate(CountdownMixin, BaseTemplate):
    template_name = "ai_countdown"

    default_hook_text = "AI가 바꿀 미래 TOP 5"
    hook_animation = "glitch_flash"
    hook_font_size = 100
    hook_duration = 2.5
    body_animation = "slide_in_right"
    default_cta_text = "다음 AI 소식도 놓치지 마세요"
