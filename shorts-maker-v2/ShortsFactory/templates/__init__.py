"""ShortsFactory Templates — 콘텐츠 유형별 템플릿."""
from ShortsFactory.templates.base_template import BaseTemplate
from ShortsFactory.templates.ai_news import AiNewsTemplate
from ShortsFactory.templates.psych_experiment import PsychExperimentTemplate
from ShortsFactory.templates.history_timeline import HistoryTimelineTemplate
from ShortsFactory.templates.space_scale import SpaceScaleTemplate
from ShortsFactory.templates.health_dodont import HealthDoDontTemplate
from ShortsFactory.templates.future_countdown import FutureCountdownTemplate
from ShortsFactory.templates.tech_vs import TechVsTemplate

TEMPLATE_REGISTRY: dict[str, type[BaseTemplate]] = {
    "ai_news": AiNewsTemplate,
    "psych_experiment": PsychExperimentTemplate,
    "history_timeline": HistoryTimelineTemplate,
    "space_scale": SpaceScaleTemplate,
    "health_dodont": HealthDoDontTemplate,
    "future_countdown": FutureCountdownTemplate,
    "tech_vs": TechVsTemplate,
}

__all__ = ["BaseTemplate", "TEMPLATE_REGISTRY"]
