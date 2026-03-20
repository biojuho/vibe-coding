"""ShortsFactory Templates — 17종 콘텐츠 유형별 템플릿 + 1 alias = 18 엔트리 (Single Registry)."""

from ShortsFactory.templates.ai_countdown import AiCountdownTemplate

# AI/Tech (3)
from ShortsFactory.templates.ai_news import AiNewsTemplate
from ShortsFactory.templates.base_template import BaseTemplate, Scene
from ShortsFactory.templates.future_countdown import FutureCountdownTemplate
from ShortsFactory.templates.health_countdown import HealthCountdownTemplate

# Health (4)
from ShortsFactory.templates.health_dodont import HealthDoDontTemplate
from ShortsFactory.templates.health_medical_study import HealthMedicalStudyTemplate
from ShortsFactory.templates.health_mental_message import HealthMentalMessageTemplate
from ShortsFactory.templates.history_countdown import HistoryCountdownTemplate
from ShortsFactory.templates.history_fact_reversal import HistoryFactReversalTemplate
from ShortsFactory.templates.history_mystery import HistoryMysteryTemplate

# History (4)
from ShortsFactory.templates.history_timeline import HistoryTimelineTemplate

# Psychology (3)
from ShortsFactory.templates.psych_experiment import PsychExperimentTemplate
from ShortsFactory.templates.psych_quiz import PsychQuizTemplate
from ShortsFactory.templates.psych_self_growth import PsychSelfGrowthTemplate
from ShortsFactory.templates.space_countdown import SpaceCountdownTemplate
from ShortsFactory.templates.space_fact_bomb import SpaceFactBombTemplate

# Space (3)
from ShortsFactory.templates.space_scale import SpaceScaleTemplate
from ShortsFactory.templates.tech_vs import TechVsTemplate

TEMPLATE_REGISTRY: dict[str, type[BaseTemplate]] = {
    # AI/Tech
    "ai_news": AiNewsTemplate,
    "ai_news_breaking": AiNewsTemplate,  # alias
    "tech_vs": TechVsTemplate,
    "future_countdown": FutureCountdownTemplate,
    "ai_countdown": AiCountdownTemplate,
    # Psychology
    "psychology_experiment": PsychExperimentTemplate,
    "psychology_quiz": PsychQuizTemplate,
    "psychology_self_growth": PsychSelfGrowthTemplate,
    # History
    "history_timeline": HistoryTimelineTemplate,
    "history_mystery": HistoryMysteryTemplate,
    "history_fact_reversal": HistoryFactReversalTemplate,
    "history_countdown": HistoryCountdownTemplate,
    # Space
    "space_scale": SpaceScaleTemplate,
    "space_fact_bomb": SpaceFactBombTemplate,
    "space_countdown": SpaceCountdownTemplate,
    # Health
    "health_do_vs_dont": HealthDoDontTemplate,
    "health_medical_study": HealthMedicalStudyTemplate,
    "health_mental_message": HealthMentalMessageTemplate,
    "health_countdown": HealthCountdownTemplate,
}

__all__ = ["BaseTemplate", "Scene", "TEMPLATE_REGISTRY"]
