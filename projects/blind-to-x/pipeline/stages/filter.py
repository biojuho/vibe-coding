"""Compatibility exports for the filter/profile stage."""

from pipeline.process_stages.filter_profile_stage import run_filter_profile_stage as run_filter_stage
from pipeline.process_stages.runtime import (
    INAPPROPRIATE_TITLE_KEYWORDS,
    REJECT_EMOTION_AXES,
    SPAM_KEYWORDS,
    SPAM_TITLE_KEYWORDS,
)

__all__ = [
    "INAPPROPRIATE_TITLE_KEYWORDS",
    "REJECT_EMOTION_AXES",
    "SPAM_KEYWORDS",
    "SPAM_TITLE_KEYWORDS",
    "run_filter_stage",
]
