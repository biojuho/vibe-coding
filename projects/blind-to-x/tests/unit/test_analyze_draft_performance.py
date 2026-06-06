from __future__ import annotations

import sys
from pathlib import Path

import yaml

_BTX_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BTX_ROOT))

from scripts.analyze_draft_performance import (  # noqa: E402
    _build_topic_weight_map,
    _update_classification_weights,
)


def test_build_topic_weight_map_normalizes_score_spread():
    weights = _build_topic_weight_map(
        [
            {"topic": "salary", "composite": 20.0},
            {"topic": "career", "composite": 60.0},
            {"topic": "culture", "composite": 100.0},
        ]
    )

    assert weights == {
        "salary": 0.5,
        "career": 1.0,
        "culture": 1.5,
    }


def test_build_topic_weight_map_keeps_tied_scores_neutral():
    weights = _build_topic_weight_map(
        [
            {"topic": "salary", "composite": 42.0},
            {"topic": "career", "composite": 42.0},
        ]
    )

    assert weights == {"salary": 1.0, "career": 1.0}


def test_build_topic_weight_map_skips_invalid_rows():
    weights = _build_topic_weight_map(
        [
            {"topic": "salary", "composite": "50.0"},
            {"topic": "", "composite": 90.0},
            {"topic": "career"},
            {"topic": "culture", "composite": "not-a-number"},
        ]
    )

    assert weights == {"salary": 1.0}


def test_update_classification_weights_updates_matching_rules(tmp_path):
    rules_path = tmp_path / "classification.yaml"
    rules_path.write_text(
        "# keep this header\n"
        "topic_rules:\n"
        "  - label: salary\n"
        "    keywords: [pay]\n"
        "  - label: career\n"
        "    keywords: [move]\n"
        "    performance_weight: 0.5\n"
        "  - label: untouched\n"
        "    keywords: [other]\n",
        encoding="utf-8",
    )

    changed = _update_classification_weights(
        [
            {"topic": "salary", "composite": 20.0},
            {"topic": "career", "composite": 60.0},
        ],
        rules_path,
    )

    assert changed is True
    text = rules_path.read_text(encoding="utf-8")
    assert text.startswith("# keep this header\n")
    data = yaml.safe_load(text)
    by_label = {rule["label"]: rule for rule in data["topic_rules"]}
    assert by_label["salary"]["performance_weight"] == 0.5
    assert by_label["career"]["performance_weight"] == 1.5
    assert "performance_weight" not in by_label["untouched"]


def test_update_classification_weights_noops_when_weights_match(tmp_path):
    rules_path = tmp_path / "classification.yaml"
    rules_path.write_text(
        "topic_rules:\n  - label: salary\n    keywords: [pay]\n    performance_weight: 1.0\n",
        encoding="utf-8",
    )

    changed = _update_classification_weights(
        [{"topic": "salary", "composite": 42.0}],
        rules_path,
    )

    assert changed is False
