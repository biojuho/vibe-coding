from __future__ import annotations

from pipeline.rules_loader import (
    RULES_DIR,
    get_rule_file_path,
    get_rule_section,
    has_split_rule_files,
    load_rules,
)


def test_split_rule_files_exist() -> None:
    assert has_split_rule_files() is True
    assert (RULES_DIR / "classification.yaml").exists()
    assert (RULES_DIR / "examples.yaml").exists()
    assert (RULES_DIR / "prompts.yaml").exists()
    assert (RULES_DIR / "platforms.yaml").exists()
    assert (RULES_DIR / "editorial.yaml").exists()


def test_load_rules_merges_split_sections() -> None:
    rules = load_rules(force_reload=True)

    assert "topic_rules" in rules
    assert "prompt_templates" in rules
    assert "platform_regulations" in rules
    assert "brand_voice" in rules


def test_rule_section_source_paths_follow_split_layout() -> None:
    assert get_rule_file_path("topic_rules") == RULES_DIR / "classification.yaml"
    assert get_rule_file_path("brand_voice") == RULES_DIR / "editorial.yaml"
    assert isinstance(get_rule_section("cliche_watchlist", []), list)
    assert isinstance(get_rule_section("brand_voice", {}), dict)
