"""Shared loader for split YAML rule files under rules/."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = PROJECT_ROOT / "rules"

RULE_FILE_ORDER = (
    "classification.yaml",
    "examples.yaml",
    "prompts.yaml",
    "platforms.yaml",
    "editorial.yaml",
)

RULE_SECTION_FILES = {
    "topic_rules": "classification.yaml",
    "emotion_rules": "classification.yaml",
    "audience_rules": "classification.yaml",
    "hook_rules": "classification.yaml",
    "season_weights": "classification.yaml",
    "source_hints": "classification.yaml",
    "golden_examples": "examples.yaml",
    "golden_examples_threads": "examples.yaml",
    "golden_examples_naver_blog": "examples.yaml",
    "anti_examples": "examples.yaml",
    "tone_mapping": "prompts.yaml",
    "tone_mapping_threads": "prompts.yaml",
    "tone_mapping_naver_blog": "prompts.yaml",
    "draft_formats": "prompts.yaml",
    "prompt_templates": "prompts.yaml",
    "prompt_variants": "prompts.yaml",
    "threads_cta_mapping": "prompts.yaml",
    "naver_blog_seo_tags": "prompts.yaml",
    "topic_prompt_strategies": "prompts.yaml",
    "platform_regulations": "platforms.yaml",
    "cross_source_insight": "platforms.yaml",
    "trends": "platforms.yaml",
    "brand_voice": "editorial.yaml",
    "cliche_watchlist": "editorial.yaml",
    "editorial_thresholds": "editorial.yaml",
    "x_editorial_rules": "editorial.yaml",
}

_merged_rules_cache: dict[str, Any] | None = None


def _read_yaml_file(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except Exception as exc:
        logger.warning("Failed to load rules file %s: %s", path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def reset_rules_cache() -> None:
    global _merged_rules_cache
    _merged_rules_cache = None


def load_rules(force_reload: bool = False) -> dict[str, Any]:
    global _merged_rules_cache
    if force_reload:
        reset_rules_cache()
    if _merged_rules_cache is not None:
        return copy.deepcopy(_merged_rules_cache)

    merged: dict[str, Any] = {}
    for file_name in RULE_FILE_ORDER:
        merged.update(_read_yaml_file(RULES_DIR / file_name))
    _merged_rules_cache = merged
    logger.debug("Loaded rules from %s", RULES_DIR)
    return copy.deepcopy(_merged_rules_cache)


def get_rule_section(key: str, default: Any = None, *, force_reload: bool = False) -> Any:
    rules = load_rules(force_reload=force_reload)
    if key not in rules:
        return copy.deepcopy(default)
    return copy.deepcopy(rules[key])


def get_rule_file_path(section: str) -> Path:
    file_name = RULE_SECTION_FILES.get(section)
    if file_name:
        return RULES_DIR / file_name
    return RULES_DIR / RULE_FILE_ORDER[0]
