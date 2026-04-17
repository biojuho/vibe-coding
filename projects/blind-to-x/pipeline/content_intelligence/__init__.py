"""
content_intelligence package - Refactored from monolithic content_intelligence.py
"""

from pipeline.content_intelligence.models import ContentProfile
from pipeline.content_intelligence.rules import (
    _load_rules,
    _yaml_rules_to_tuples,
    get_topic_rules,
    get_emotion_rules,
    get_audience_rules,
    TOPIC_RULES,
    EMOTION_RULES,
    AUDIENCE_RULES,
    get_time_context,
    get_topic_hook,
    get_source_hint,
    get_season_boost,
)
from pipeline.content_intelligence.utils import (
    _round_score,
    _extract_empathy_anchor,
)
from pipeline.content_intelligence.classifiers import (
    classify_topic_cluster,
    classify_emotion_axis,
    classify_audience_fit,
    classify_hook_type,
    recommend_draft_type,
)
from pipeline.content_intelligence.scoring_editorial import (
    evaluate_candidate_editorial_fit,
    calculate_publishability_score,
)
from pipeline.content_intelligence.scoring_performance import calculate_performance_score
from pipeline.content_intelligence.scoring_6d import calculate_6d_score, calibrate_weights
from pipeline.content_intelligence.boosting import estimate_viral_boost_llm
from pipeline.content_intelligence.builder import build_content_profile

__all__ = [
    "ContentProfile",
    "get_topic_rules",
    "get_emotion_rules",
    "get_audience_rules",
    "TOPIC_RULES",
    "EMOTION_RULES",
    "AUDIENCE_RULES",
    "get_time_context",
    "get_topic_hook",
    "get_source_hint",
    "get_season_boost",
    "classify_topic_cluster",
    "classify_emotion_axis",
    "classify_audience_fit",
    "classify_hook_type",
    "recommend_draft_type",
    "evaluate_candidate_editorial_fit",
    "calculate_publishability_score",
    "calculate_performance_score",
    "calculate_6d_score",
    "calibrate_weights",
    "estimate_viral_boost_llm",
    "build_content_profile",
    "_load_rules",
    "_yaml_rules_to_tuples",
    "_round_score",
    "_extract_empathy_anchor",
]
