from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_experiment_dry_run import (  # noqa: E402
    DEFAULT_FIXTURE,
    OBJECTIVE_METRICS,
    _format_batch_console_summary,
    _format_single_console_summary,
    _operator_actions,
    build_review_experiment,
    build_review_experiment_batch,
    main,
    review_records_to_fixtures,
)


def _ready_review_fixture(
    *,
    title: str = "Ready draft",
    url: str = "https://example.com/ready",
    latency_ms: int = 950,
) -> dict[str, object]:
    return {
        "post_data": {
            "title": title,
            "url": url,
            "x_publish_status": "Ready to Post",
            "provider_used": "openai",
            "model_used": "gpt-4.1-mini",
            "latency_ms": latency_ms,
            "token_cost_estimate": 0.012,
            "risk_flags": [],
        },
        "drafts": {
            "twitter": "Publishable draft",
            "_quality_gate_score": 9.2,
            "_max_semantic_similarity": 0.12,
        },
        "analysis": {
            "final_rank_score": 91,
        },
    }


def _ready_batch_payload() -> dict[str, list[dict[str, object]]]:
    return {"fixtures": [_ready_review_fixture()]}


def test_build_review_experiment_recommends_recovery_card_for_provider_failure():
    report = build_review_experiment(DEFAULT_FIXTURE)

    assert report["dry_run"] is True
    assert report["safety"] == {
        "read_only": True,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }
    assert report["objective_metrics"] == list(OBJECTIVE_METRICS)
    assert report["comparison"]["recommendation"] == "adopt_candidate"

    current = report["variants"]["current"]
    candidate = report["variants"]["candidate"]
    assert candidate["review_efficiency_score"] > current["review_efficiency_score"]
    assert candidate["operator_action_count"] > current["operator_action_count"]
    assert len(candidate["missing_required_signals"]) < len(current["missing_required_signals"])

    signals = candidate["signals"]
    assert signals["provider"] == "gemini"
    assert signals["model"] == "gemini-2.5-flash"
    assert signals["latency_ms"] == 830.0
    assert signals["token_cost_estimate"] == 0.038
    assert signals["operator_action_required"] is True
    assert signals["provider_failure_summary"]["categories"] == {"auth": 1, "rate_limit": 1}
    assert signals["provider_failure_summary"]["primary_failure"] == {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "category": "auth",
        "retryable": False,
        "circuit_breaker_candidate": True,
        "error_preview": "",
        "operator_action": "Check provider API key",
    }
    assert [action["action"] for action in signals["operator_actions"]][:2] == [
        "repair_provider_access",
        "repair_provider_access",
    ]


def test_provider_failure_summary_falls_back_to_failure_records_when_summary_is_missing():
    fixture = json.loads(json.dumps(DEFAULT_FIXTURE))
    fixture["post_data"].pop("draft_provider_failure_summary")

    report = build_review_experiment_batch([fixture], min_item_count=1)
    signals = report["items"][0]["candidate"]["signals"]

    assert signals["provider_failure_summary"] == {
        "providers_attempted": ["gemini", "openai"],
        "categories": {"auth": 1, "rate_limit": 1},
        "operator_action_required": True,
        "primary_operator_action": "Check provider API key",
        "primary_failure": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "error_preview": "",
            "operator_action": "Check provider API key",
        },
    }
    assert report["summary"]["candidate_provider_failure_category_counts"] == {"auth": 1, "rate_limit": 1}
    assert report["summary"]["candidate_provider_failure_provider_counts"] == {"gemini": 1, "openai": 1}
    assert report["summary"]["candidate_primary_provider_failure_category_counts"] == {"auth": 1}
    assert report["summary"]["candidate_primary_provider_failure_provider_counts"] == {"openai": 1}
    assert report["summary"]["candidate_primary_provider_failure_actions"] == [
        {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "operator_action": "Check provider API key",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "count": 1,
        }
    ]


def test_provider_failure_summary_sanitizes_partial_dirty_summary():
    fixture = json.loads(json.dumps(DEFAULT_FIXTURE))
    fixture["post_data"]["draft_provider_failure_summary"] = {
        "providers_attempted": "gemini, ,gemini, openai",
        "categories": {"rate_limit": "2", "auth": "not-a-number", "": 3, "quota": 0},
        "operator_action_required": "false",
        "primary_operator_action": "  ",
    }
    fixture["post_data"]["draft_provider_failures"] = [
        {
            "provider": "gemini",
            "category": "auth",
            "operator_action_required": "true",
            "operator_action": "Check Gemini credentials",
        },
        {
            "provider_name": "moonshot",
            "failure_category": "timeout",
            "operator_action_required": "false",
        },
    ]

    report = build_review_experiment_batch([fixture], min_item_count=1)
    signals = report["items"][0]["candidate"]["signals"]

    assert signals["provider_failure_summary"] == {
        "providers_attempted": ["gemini", "openai", "moonshot"],
        "categories": {"rate_limit": 2, "auth": 1, "timeout": 1},
        "operator_action_required": True,
        "primary_operator_action": "Check Gemini credentials",
        "primary_failure": {
            "provider": "gemini",
            "model": "",
            "category": "auth",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "error_preview": "",
            "operator_action": "Check Gemini credentials",
        },
    }
    assert report["summary"]["candidate_provider_failure_category_counts"] == {
        "rate_limit": 2,
        "auth": 1,
        "timeout": 1,
    }
    assert report["summary"]["candidate_provider_failure_provider_counts"] == {
        "gemini": 1,
        "moonshot": 1,
        "openai": 1,
    }


def test_provider_failure_false_string_does_not_require_candidate_action():
    fixture = _ready_review_fixture(title="Ready draft with provider note")
    fixture["post_data"]["draft_provider_failures"] = [
        {
            "provider": "gemini",
            "category": "timeout",
            "operator_action_required": "false",
        }
    ]

    report = build_review_experiment(fixture)
    signals = report["variants"]["candidate"]["signals"]

    assert signals["success"] is True
    assert signals["provider_failure_summary"]["operator_action_required"] is False
    assert signals["operator_action_required"] is False
    assert signals["operator_actions"] == []


def test_generation_failed_false_string_keeps_ready_draft_successful():
    fixture = _ready_review_fixture(title="Ready draft with false generation flag")
    fixture["post_data"]["draft_generation_failed"] = "false"

    report = build_review_experiment(fixture)
    signals = report["variants"]["candidate"]["signals"]

    assert signals["success"] is True
    assert signals["operator_action_required"] is False
    assert signals["operator_actions"] == []


def test_duplicate_string_flags_override_similarity_fallback():
    true_fixture = _ready_review_fixture(title="Ready draft with duplicate true flag")
    true_fixture["post_data"]["duplicate_or_near_duplicate"] = "true"
    false_fixture = _ready_review_fixture(title="Ready draft with duplicate false flag")
    false_fixture["post_data"]["duplicate_or_near_duplicate"] = "false"
    false_fixture["post_data"]["max_semantic_similarity"] = 0.92

    true_signals = build_review_experiment(true_fixture)["variants"]["candidate"]["signals"]
    false_signals = build_review_experiment(false_fixture)["variants"]["candidate"]["signals"]

    assert true_signals["duplicate_or_near_duplicate"] is True
    assert [action["action"] for action in true_signals["operator_actions"]] == ["rewrite_duplicate_draft"]
    assert false_signals["duplicate_or_near_duplicate"] is False
    assert false_signals["operator_actions"] == []


def test_zero_quality_gate_score_is_not_replaced_by_average_fallback():
    fixture = _ready_review_fixture(title="Ready draft with zero quality score")
    fixture["drafts"]["_quality_gate_score"] = 0
    fixture["post_data"]["quality_gate_scores"] = [9, 10]

    report = build_review_experiment(fixture)
    signals = report["variants"]["candidate"]["signals"]

    assert signals["draft_quality_score"] == 0.0
    assert signals["success"] is True


def test_blank_review_queue_operator_action_does_not_require_action():
    fixture = _ready_review_fixture(title="Ready draft with blank review action")
    fixture["post_data"]["review_queue_operator_action"] = "   "

    report = build_review_experiment(fixture)
    signals = report["variants"]["candidate"]["signals"]

    assert signals["success"] is True
    assert signals["operator_action_required"] is False
    assert signals["operator_actions"] == []


def test_review_queue_priority_zero_is_preserved():
    fixture = _ready_review_fixture(title="Ready draft with priority zero action")
    fixture["post_data"]["review_queue_operator_action"] = "manual_check"
    fixture["post_data"]["review_queue_operator_reason"] = "Needs manual check"
    fixture["post_data"]["review_queue_priority"] = 0

    report = build_review_experiment(fixture)
    actions = report["variants"]["candidate"]["signals"]["operator_actions"]

    assert actions == [
        {
            "action": "review_queue_action",
            "reason": "manual_check: Needs manual check",
            "priority": 0,
        }
    ]


def test_operator_actions_sort_priority_zero_first():
    metrics = {
        "success": True,
        "operator_action_required": True,
        "provider_failure_summary": {},
        "safety_risk_flags": [],
        "duplicate_or_near_duplicate": False,
        "x_publish_status": "failed",
    }
    fixture = {
        "post_data": {
            "review_queue_operator_action": "manual_check",
            "review_queue_operator_reason": "Needs manual check",
            "review_queue_priority": 0,
        }
    }

    actions = _operator_actions(metrics, fixture)

    assert [(action["action"], action["priority"]) for action in actions] == [
        ("review_queue_action", 0),
        ("resolve_x_publish_status", 40),
    ]


def test_x_publish_status_action_matching_is_case_insensitive():
    fixture = _ready_review_fixture(title="Ready draft with lowercase failed status")
    fixture["post_data"]["x_publish_status"] = " failed "

    report = build_review_experiment(fixture)
    signals = report["variants"]["candidate"]["signals"]

    assert signals["success"] is True
    assert signals["operator_action_required"] is True
    assert signals["operator_actions"] == [
        {
            "action": "resolve_x_publish_status",
            "reason": "failed",
            "priority": 40,
        }
    ]


def test_custom_fixture_surfaces_x_status_and_duplicate_review_actions():
    report = build_review_experiment(
        {
            "post_data": {
                "title": "Ready draft needs duplicate review",
                "url": "https://example.com/custom",
                "x_publish_status": "Ready to Post",
                "provider_used": "openai",
                "model_used": "gpt-4.1-mini",
                "latency_ms": 1200,
                "token_cost_estimate": "0.024",
                "risk_flags": "legal, privacy",
            },
            "drafts": {
                "twitter": "Publishable draft",
                "_quality_gate_score": 8.8,
                "_max_semantic_similarity": 0.91,
            },
            "analysis": {
                "final_rank_score": "88",
            },
        },
        input_source="unit_fixture",
    )

    candidate_signals = report["variants"]["candidate"]["signals"]
    action_names = [action["action"] for action in candidate_signals["operator_actions"]]
    assert candidate_signals["success"] is True
    assert candidate_signals["duplicate_or_near_duplicate"] is True
    assert candidate_signals["safety_risk_flags"] == ["legal", "privacy"]
    assert "rewrite_duplicate_draft" in action_names
    assert "review_risk_flags" in action_names
    assert "resolve_x_publish_status" not in action_names


def test_build_review_experiment_batch_aggregates_multi_item_deltas():
    clean_fixture = _ready_review_fixture(title="Clean ready draft")

    report = build_review_experiment_batch([DEFAULT_FIXTURE, clean_fixture], input_source="unit_batch")

    assert report["batch"] is True
    assert report["dry_run"] is True
    assert report["summary"]["item_count"] == 2
    assert report["summary"]["recommendation_counts"]["adopt_candidate"] == 2
    assert report["summary"]["candidate_adoption_rate"] == 1.0
    assert report["summary"]["average_score_delta"] > 0
    assert report["summary"]["candidate_operator_action_total"] == 6
    assert report["summary"]["average_operator_actions_per_item"] == 3.0
    assert report["summary"]["max_operator_actions_per_item"] == 6
    assert report["summary"]["operator_action_noise_threshold"] == 3
    assert report["summary"]["candidate_safety_risk_item_count"] == 1
    assert report["summary"]["candidate_safety_risk_flag_counts"] == {"draft_generation_failed": 1}
    assert report["summary"]["candidate_provider_failure_category_counts"] == {"auth": 1, "rate_limit": 1}
    assert report["summary"]["candidate_provider_failure_provider_counts"] == {"gemini": 1, "openai": 1}
    assert report["summary"]["candidate_primary_provider_failure_category_counts"] == {"auth": 1}
    assert report["summary"]["candidate_primary_provider_failure_provider_counts"] == {"openai": 1}
    assert report["summary"]["candidate_primary_provider_failure_actions"] == [
        {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "operator_action": "Check provider API key and quota before retrying",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "count": 1,
        }
    ]
    assert report["summary"]["candidate_top_operator_actions"][0] == {
        "action": "repair_provider_access",
        "count": 3,
        "priority": 10,
        "reason": "Check provider API key",
    }
    assert report["summary"]["high_noise_item_count"] == 1
    assert report["summary"]["high_noise_items"] == [
        {
            "index": 1,
            "title": "Review-only draft with provider fallback",
            "url": "https://example.com/posts/1",
            "operator_action_count": 6,
            "missing_required_signal_count": 0,
            "score_delta": 28.0,
        }
    ]
    assert report["summary"]["candidate_missing_metric_count"] == 0
    assert report["summary"]["candidate_total_metric_slots"] == 20
    assert report["summary"]["candidate_missing_metric_rate"] == 0.0
    assert report["summary"]["candidate_missing_metric_counts"]["safety_risk_flags"] == 0
    assert report["summary"]["candidate_missing_metric_counts"]["provider"] == 0
    assert report["summary"]["candidate_missing_metric_rates"]["safety_risk_flags"] == 0.0
    assert report["summary"]["candidate_missing_metric_owner_counts"] == {}
    assert report["summary"]["candidate_top_missing_metric_owners"] == []
    assert report["summary"]["candidate_top_missing_metrics"] == []
    safety_hint = report["summary"]["candidate_missing_metric_hints"]["safety_risk_flags"]
    assert safety_hint == {
        "metric": "safety_risk_flags",
        "count": 0,
        "rate": 0.0,
        "reason": "The safety review result was not exported.",
        "operator_action": "Export safety_risk_flags or an explicit reviewed-no-risk marker.",
        "owner": "safety_review",
    }
    assert report["summary"]["candidate_top_missing_metric_hints"] == []
    confidence = report["summary"]["candidate_experiment_confidence"]
    assert confidence["level"] == "needs_more_evidence"
    assert confidence["operator_action_required"] is True
    assert confidence["observed_item_count"] == 2
    assert confidence["observed_adoption_rate"] == 1.0
    assert confidence["observed_missing_metric_rate"] == 0.0
    assert confidence["observed_average_operator_actions_per_item"] == 3.0
    assert [issue["code"] for issue in confidence["issues"]] == [
        "sample_size_too_small",
        "operator_action_noise_high",
    ]
    assert report["summary"]["candidate_ready_for_rollout"] is False
    assert report["summary"]["candidate_rollout_blockers"] == [
        "sample_size_too_small",
        "operator_action_noise_high",
    ]
    assert report["summary"]["candidate_rollout_blocker_actions"] == [
        {
            "code": "sample_size_too_small",
            "source": "confidence",
            "operator_action": "Run the dry-run with at least 3 review items.",
            "reason": "The batch has too few items to trust the candidate adoption rate.",
        },
        {
            "code": "operator_action_noise_high",
            "source": "confidence",
            "operator_action": "Reduce or group candidate operator actions before rollout.",
            "reason": "The candidate card is producing a noisy operator action queue.",
        },
    ]
    assert (
        report["summary"]["candidate_rollout_reason"]
        == "blocked: run the dry-run with at least 3 review items; additional blockers: 1"
    )
    assert [item["title"] for item in report["items"]] == [
        "Review-only draft with provider fallback",
        "Clean ready draft",
    ]
    assert report["items"][0]["comparison"]["score_delta"] > report["items"][1]["comparison"]["score_delta"]

    relaxed_report = build_review_experiment_batch(
        [DEFAULT_FIXTURE, clean_fixture],
        input_source="unit_batch_relaxed_actions",
        min_item_count=2,
        max_operator_actions_per_item=6,
    )
    relaxed_confidence = relaxed_report["summary"]["candidate_experiment_confidence"]
    assert relaxed_confidence["level"] == "actionable"
    assert relaxed_confidence["max_average_operator_actions_per_item"] == 6
    assert relaxed_report["summary"]["operator_action_noise_threshold"] == 6
    assert relaxed_report["summary"]["high_noise_item_count"] == 0
    assert relaxed_report["summary"]["candidate_ready_for_rollout"] is True


def test_batch_confidence_is_actionable_for_sufficient_complete_sample():
    fixtures = []
    for index in range(3):
        fixtures.append(
            _ready_review_fixture(
                title=f"Complete ready draft {index}",
                url=f"https://example.com/complete/{index}",
                latency_ms=900 + index,
            )
        )

    report = build_review_experiment_batch(fixtures, input_source="complete_batch")

    confidence = report["summary"]["candidate_experiment_confidence"]
    assert confidence == {
        "level": "actionable",
        "operator_action_required": False,
        "min_item_count": 3,
        "max_missing_metric_rate": 0.25,
        "max_average_operator_actions_per_item": 3,
        "observed_item_count": 3,
        "observed_adoption_rate": 1.0,
        "observed_missing_metric_rate": 0.0,
        "observed_average_operator_actions_per_item": 0.0,
        "issues": [],
    }
    assert report["summary"]["candidate_ready_for_rollout"] is True
    assert report["summary"]["candidate_rollout_blockers"] == []
    assert report["summary"]["candidate_rollout_reason"] == "ready: confidence and safety gates passed"

    strict_report = build_review_experiment_batch(
        fixtures,
        input_source="complete_batch_strict",
        min_item_count=4,
        max_missing_metric_rate=0.0,
    )
    strict_confidence = strict_report["summary"]["candidate_experiment_confidence"]
    assert strict_confidence["level"] == "needs_more_evidence"
    assert strict_confidence["min_item_count"] == 4
    assert strict_confidence["max_missing_metric_rate"] == 0.0
    assert strict_report["summary"]["candidate_ready_for_rollout"] is False
    assert strict_report["summary"]["candidate_rollout_blockers"] == ["sample_size_too_small"]
    assert strict_report["summary"]["candidate_rollout_reason"] == (
        "blocked: run the dry-run with at least 4 review items"
    )


def test_main_writes_ascii_json_report(tmp_path, capsys):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "post_data": {
                    "title": "한글 제목",
                    "url": "https://example.com/korean",
                    "draft_generation_failed": True,
                    "x_publish_status": "Needs Edit",
                },
                "drafts": {"_generation_failed": True},
                "analysis": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "report.json"

    assert main(["--input", str(fixture_path), "--output", str(output_path), "--json"]) == 0

    payload_text = output_path.read_text(encoding="utf-8")
    assert payload_text
    assert all(ord(char) < 128 for char in payload_text)

    payload = json.loads(payload_text)
    assert payload["input_source"] == str(fixture_path)
    assert payload["variants"]["candidate"]["signals"]["operator_action_required"] is True
    assert payload["output"] == {
        "path": str(output_path),
        "written": True,
        "write_suppressed": False,
        "suppression_flags": [],
    }

    stdout = capsys.readouterr().out
    assert '"dry_run": true' in stdout


def test_main_single_mode_prints_rollout_gate_without_json(tmp_path, capsys):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(DEFAULT_FIXTURE), encoding="utf-8")
    output_path = tmp_path / "report.json"

    assert main(["--input", str(fixture_path), "--output", str(output_path)]) == 0

    stdout = capsys.readouterr().out
    assert "review_experiment_dry_run=" in stdout
    assert "recommendation=adopt_candidate" in stdout
    assert "ready_for_rollout=False" in stdout
    assert "rollout_reason=blocked: run batch dry-run for rollout confidence" in stdout


def test_console_summary_helpers_preserve_operator_output_contract():
    single_report = build_review_experiment(DEFAULT_FIXTURE)
    assert _format_single_console_summary(single_report, "(not written)") == (
        "review_experiment_dry_run=(not written) "
        "recommendation=adopt_candidate score_delta=28.0 "
        "operator_action_count=6 "
        "top_operator_action=repair_provider_access "
        "top_operator_action_count=3 "
        "top_operator_action_reason=Check provider API key "
        "ready_for_rollout=False "
        "rollout_reason=blocked: run batch dry-run for rollout confidence"
    )

    batch_report = build_review_experiment_batch([DEFAULT_FIXTURE], min_item_count=1)
    assert _format_batch_console_summary(batch_report, "report.json").startswith(
        "review_experiment_dry_run=report.json batch_items=1 adoption_rate=1.0 "
        "avg_score_delta=28.0 missing_metric_rate=0.0 top_missing_metric=- top_missing_metric_count=0 "
        "top_missing_owner=- top_missing_owner_count=0 top_missing_owner_metric=- top_missing_owner_action=- "
        "operator_actions_total=6 avg_operator_actions=6.0 high_noise_items=1 "
        "safety_risk_items=1 safety_risk_flags=draft_generation_failed=1 "
        "provider_failure_categories=auth=1,rate_limit=1 provider_failure_providers=gemini=1,openai=1 "
        "primary_provider_failure_categories=auth=1 primary_provider_failure_providers=openai=1 "
        "top_operator_action=repair_provider_access top_operator_action_count=3 "
        "top_operator_action_reason=Check provider API key "
        "rollout_blocker_count=1 rollout_blocker_codes=operator_action_noise_high "
        "top_rollout_blocker_code=operator_action_noise_high "
        "top_rollout_blocker_source=confidence top_rollout_blocker_owner=- top_rollout_blocker_metric=- "
        "top_rollout_blocker_action=Reduce or group candidate operator actions before rollout. "
        "ready_for_rollout=False rollout_reason=blocked:"
    )


def test_main_batch_mode_accepts_fixture_wrapper_and_writes_summary(tmp_path, capsys):
    fixture_path = tmp_path / "batch.json"
    fixture_path.write_text(
        json.dumps(
            {
                "fixtures": [
                    DEFAULT_FIXTURE,
                    {
                        "post_data": {
                            "title": "Needs status",
                            "url": "https://example.com/status",
                            "x_publish_status": "",
                        },
                        "drafts": {
                            "twitter": "Draft body",
                            "_provider_used": "deepseek",
                            "_model_used": "deepseek-chat",
                            "_quality_gate_score": 7.5,
                        },
                        "analysis": {
                            "final_rank_score": 82,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "batch-report.json"

    assert (
        main(
            [
                "--batch",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--min-items",
                "5",
                "--max-missing-rate",
                "0.1",
                "--max-operator-actions",
                "8",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["batch"] is True
    assert payload["summary"]["item_count"] == 2
    assert payload["summary"]["candidate_adoption_rate"] == 1.0
    assert payload["summary"]["candidate_experiment_confidence"]["min_item_count"] == 5
    assert payload["summary"]["candidate_experiment_confidence"]["max_missing_metric_rate"] == 0.1
    assert payload["summary"]["candidate_experiment_confidence"]["max_average_operator_actions_per_item"] == 8
    assert payload["summary"]["operator_action_noise_threshold"] == 8
    assert payload["summary"]["candidate_rollout_reason"].startswith(
        "blocked: run the dry-run with at least 5 review items"
    )
    assert payload["items"][1]["candidate"]["signals"]["provider"] == "deepseek"

    stdout = capsys.readouterr().out
    assert '"batch": true' in stdout


def test_main_batch_mode_prints_rollout_gate_without_json(tmp_path, capsys):
    fixture_path = tmp_path / "batch.json"
    fixture_path.write_text(json.dumps(_ready_batch_payload()), encoding="utf-8")
    output_path = tmp_path / "batch-report.json"

    assert (
        main(
            [
                "--batch",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--min-items",
                "1",
            ]
        )
        == 0
    )

    stdout = capsys.readouterr().out
    assert "review_experiment_dry_run=" in stdout
    assert "ready_for_rollout=True" in stdout
    assert "rollout_reason=ready: confidence and safety gates passed" in stdout


def test_main_summary_only_prints_rollout_gate_without_writing_report(tmp_path, capsys):
    fixture_path = tmp_path / "batch.json"
    fixture_path.write_text(json.dumps(_ready_batch_payload()), encoding="utf-8")
    output_path = tmp_path / "summary-only-report.json"

    assert (
        main(
            [
                "--batch",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--min-items",
                "1",
                "--summary-only",
            ]
        )
        == 0
    )

    stdout = capsys.readouterr().out
    assert not output_path.exists()
    assert "review_experiment_dry_run=(not written)" in stdout
    assert "missing_metric_rate=0.0" in stdout
    assert "top_missing_metric=-" in stdout
    assert "top_missing_metric_count=0" in stdout
    assert "operator_actions_total=0" in stdout
    assert "safety_risk_items=0" in stdout
    assert "safety_risk_flags=-" in stdout
    assert "provider_failure_categories=-" in stdout
    assert "provider_failure_providers=-" in stdout
    assert "primary_provider_failure_categories=-" in stdout
    assert "primary_provider_failure_providers=-" in stdout
    assert "top_operator_action=-" in stdout
    assert "rollout_blocker_count=0" in stdout
    assert "rollout_blocker_codes=-" in stdout
    assert "top_rollout_blocker_code=-" in stdout
    assert "top_rollout_blocker_action=-" in stdout
    assert "ready_for_rollout=True" in stdout
    assert "rollout_reason=ready: confidence and safety gates passed" in stdout


def test_main_summary_only_json_prints_report_without_writing_report(tmp_path, capsys):
    fixture_path = tmp_path / "batch.json"
    fixture_path.write_text(json.dumps(_ready_batch_payload()), encoding="utf-8")
    output_path = tmp_path / "summary-only-json-report.json"

    assert (
        main(
            [
                "--batch",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--min-items",
                "1",
                "--summary-only",
                "--json",
            ]
        )
        == 0
    )

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert not output_path.exists()
    assert payload["output"] == {
        "path": str(output_path),
        "written": False,
        "write_suppressed": True,
        "suppression_flags": ["summary_only"],
    }
    assert payload["batch"] is True
    assert payload["summary"]["candidate_ready_for_rollout"] is True
    assert payload["summary"]["candidate_safety_risk_item_count"] == 0
    assert payload["summary"]["candidate_safety_risk_flag_counts"] == {}
    assert payload["summary"]["candidate_provider_failure_category_counts"] == {}
    assert payload["summary"]["candidate_provider_failure_provider_counts"] == {}
    assert payload["summary"]["candidate_primary_provider_failure_category_counts"] == {}
    assert payload["summary"]["candidate_primary_provider_failure_provider_counts"] == {}
    assert payload["summary"]["candidate_primary_provider_failure_actions"] == []
    assert payload["summary"]["candidate_rollout_reason"] == "ready: confidence and safety gates passed"
    assert "review_experiment_dry_run=(not written)" not in stdout


def test_main_review_records_summary_only_prints_missing_metric_topline(tmp_path, capsys):
    fixture_path = tmp_path / "review-queue-report.json"
    fixture_path.write_text(
        json.dumps(
            {
                "operator_actions": [
                    {
                        "page_id": "page-blocked",
                        "title": "Blocked item",
                        "x_publish_status": "Blocked",
                        "x_publish_error": "Missing tweet draft text",
                        "action": "fix_blocked_publish",
                        "reason": "Missing tweet draft text",
                        "priority": 10,
                    }
                ],
                "ready_attention_items": [
                    {
                        "page_id": "page-ready",
                        "title": "Ready item",
                        "x_publish_status": "Ready to Post",
                        "tweet_body": "Ready draft",
                        "action": "publish_or_reschedule",
                        "reason": "stale ready item",
                        "priority": 30,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "summary-only-review-records.json"

    assert (
        main(
            [
                "--input-mode",
                "review-records",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--summary-only",
            ]
        )
        == 0
    )

    stdout = capsys.readouterr().out
    assert not output_path.exists()
    assert "review_experiment_dry_run=(not written)" in stdout
    assert "missing_metric_rate=0.7" in stdout
    assert "top_missing_metric=latency_ms" in stdout
    assert "top_missing_metric_count=2" in stdout
    assert "top_missing_owner=provider_telemetry" in stdout
    assert "top_missing_owner_count=6" in stdout
    assert "top_missing_owner_metric=latency_ms" in stdout
    assert "rollout_blocker_count=2" in stdout
    assert "rollout_blocker_codes=sample_size_too_small,missing_metric_rate_high" in stdout
    assert "top_rollout_blocker_code=sample_size_too_small" in stdout
    assert "top_rollout_blocker_source=confidence" in stdout
    assert "top_rollout_blocker_action=Run the dry-run with at least 3 review items." in stdout
    assert "rollout_reason=blocked: run the dry-run with at least 3 review items; additional blockers: 1" in stdout


def test_main_no_write_json_marks_write_suppressed(tmp_path, capsys):
    fixture_path = tmp_path / "batch.json"
    fixture_path.write_text(json.dumps(_ready_batch_payload()), encoding="utf-8")
    output_path = tmp_path / "no-write-json-report.json"

    assert (
        main(
            [
                "--batch",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--min-items",
                "1",
                "--no-write",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert not output_path.exists()
    assert payload["output"] == {
        "path": str(output_path),
        "written": False,
        "write_suppressed": True,
        "suppression_flags": ["no_write"],
    }
    assert payload["batch"] is True
    assert payload["summary"]["candidate_ready_for_rollout"] is True


def test_main_review_records_mode_honors_max_missing_rate_override(tmp_path):
    fixture_path = tmp_path / "review-records.json"
    fixture_path.write_text(
        json.dumps(
            {
                "ready_attention_items": [
                    {
                        "title": "Sparse but accepted item",
                        "page_url": "https://notion.so/page-sparse",
                        "x_publish_status": "Ready to Post",
                        "tweet_body": "Ready draft",
                        "risk_flags": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "review-records-report.json"

    assert (
        main(
            [
                "--input-mode",
                "review-records",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--min-items",
                "1",
                "--max-missing-rate",
                "0.7",
                "--max-operator-actions",
                "0",
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    confidence = payload["summary"]["candidate_experiment_confidence"]
    assert confidence["max_missing_metric_rate"] == 0.7
    assert confidence["max_average_operator_actions_per_item"] == 0
    assert confidence["observed_missing_metric_rate"] == 0.6
    assert payload["summary"]["candidate_ready_for_rollout"] is True
    assert payload["summary"]["candidate_rollout_blockers"] == []


@pytest.mark.parametrize(
    ("flag", "value", "message"),
    [
        ("--min-items", "0", "must be at least 1"),
        ("--max-missing-rate", "-0.1", "must be between 0 and 1"),
        ("--max-missing-rate", "1.1", "must be between 0 and 1"),
        ("--max-operator-actions", "-1", "must be at least 0"),
    ],
)
def test_main_rejects_invalid_threshold_arguments(flag, value, message, tmp_path, capsys):
    output_path = tmp_path / "should-not-write.json"

    with pytest.raises(SystemExit) as exc_info:
        main(["--batch", flag, value, "--output", str(output_path), "--json"])

    assert exc_info.value.code == 2
    assert not output_path.exists()
    stderr = capsys.readouterr().err
    assert flag in stderr
    assert message in stderr


def test_review_records_to_fixtures_maps_review_queue_fields():
    fixtures = review_records_to_fixtures(
        [
            {
                "page_id": "page-blocked",
                "page_url": "https://notion.so/page-blocked",
                "title": "Blocked item",
                "x_publish_status": "Blocked",
                "x_publish_error": "Twitter post failed",
                "action": "fix_blocked_publish",
                "reason": "Twitter post failed",
                "error_bucket": "x_post_failed",
                "triage_bucket": "x_post_failed",
                "priority": 10,
                "risk_flags": ["media_issue"],
                "tweet_body": "",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "latency_ms": 1500,
                "token_cost_estimate": 0.045,
                "final_rank_score": 83,
                "draft_quality_score": 6.5,
                "provider_failure_summary": {
                    "providers_attempted": ["openai", "gemini"],
                    "categories": {"auth": 1, "rate_limit": 1},
                    "operator_action_required": True,
                    "primary_operator_action": "Check provider API key before rerunning.",
                    "primary_failure": {
                        "provider": "openai",
                        "model": "gpt-4.1-mini",
                        "category": "auth",
                        "retryable": False,
                        "circuit_breaker_candidate": True,
                        "operator_action": "Check provider API key before rerunning.",
                    },
                },
            }
        ]
    )

    assert len(fixtures) == 1
    fixture = fixtures[0]
    assert fixture["post_data"]["page_id"] == "page-blocked"
    assert fixture["post_data"]["url"] == "https://notion.so/page-blocked"
    assert fixture["post_data"]["x_publish_status"] == "Blocked"
    assert fixture["post_data"]["review_queue_operator_action"] == "fix_blocked_publish"
    assert fixture["post_data"]["review_queue_priority"] == 10
    assert fixture["post_data"]["review_queue_error_bucket"] == "x_post_failed"
    assert fixture["post_data"]["review_queue_triage_bucket"] == "x_post_failed"
    assert fixture["post_data"]["draft_provider_failure_summary"]["primary_failure"]["provider"] == "openai"
    assert fixture["drafts"]["_provider_used"] == "openai"
    assert fixture["drafts"]["_quality_gate_score"] == 6.5

    report = build_review_experiment_batch(fixtures, input_source="review_queue")
    candidate_signals = report["items"][0]["candidate"]["signals"]
    assert candidate_signals["operator_action_required"] is True
    assert candidate_signals["latency_ms"] == 1500.0
    assert candidate_signals["token_cost_estimate"] == 0.045
    assert candidate_signals["operator_actions"][0]["action"] == "review_queue_action"
    assert candidate_signals["operator_actions"][0]["reason"] == "fix_blocked_publish: Twitter post failed"
    assert candidate_signals["operator_actions"][0]["error_bucket"] == "x_post_failed"
    assert candidate_signals["operator_actions"][0]["triage_bucket"] == "x_post_failed"
    assert candidate_signals["operator_actions"][1] == {
        "action": "repair_provider_access",
        "reason": "Check provider API key before rerunning.",
        "priority": 10,
    }
    assert candidate_signals["provider_failure_summary"]["primary_failure"]["category"] == "auth"
    assert report["summary"]["candidate_operator_error_bucket_counts"] == {"x_post_failed": 1}
    assert report["summary"]["candidate_operator_triage_bucket_counts"] == {"x_post_failed": 1}
    assert report["summary"]["candidate_provider_failure_category_counts"] == {"auth": 1, "rate_limit": 1}
    assert report["summary"]["candidate_provider_failure_provider_counts"] == {"gemini": 1, "openai": 1}
    assert report["summary"]["candidate_primary_provider_failure_category_counts"] == {"auth": 1}
    assert report["summary"]["candidate_primary_provider_failure_provider_counts"] == {"openai": 1}
    assert report["summary"]["candidate_primary_provider_failure_actions"] == [
        {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "category": "auth",
            "operator_action": "Check provider API key before rerunning.",
            "retryable": False,
            "circuit_breaker_candidate": True,
            "count": 1,
        }
    ]


def test_review_records_to_fixtures_preserves_empty_reviewed_safety_flags():
    fixtures = review_records_to_fixtures(
        [
            {
                "title": "Reviewed clean item",
                "page_url": "https://notion.so/page-clean",
                "x_publish_status": "Ready to Post",
                "tweet_body": "Ready draft",
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "latency_ms": 900,
                "token_cost_estimate": 0.012,
                "final_rank_score": 91,
                "draft_quality_score": 9.1,
                "risk_flags": [],
            }
        ]
    )

    assert fixtures[0]["post_data"]["risk_flags"] == []

    report = build_review_experiment_batch(fixtures * 3, input_source="reviewed_clean_queue")
    assert report["summary"]["candidate_missing_metric_counts"]["safety_risk_flags"] == 0
    assert report["summary"]["candidate_missing_metric_rate"] == 0.0
    assert report["summary"]["candidate_experiment_confidence"]["level"] == "actionable"
    assert report["summary"]["candidate_ready_for_rollout"] is True
    assert report["summary"]["candidate_rollout_blockers"] == []
    assert report["summary"]["candidate_rollout_reason"] == "ready: confidence and safety gates passed"
    assert report["items"][0]["candidate"]["signals"]["safety_risk_flags"] == []


def test_main_review_records_mode_accepts_review_queue_report_export(tmp_path, capsys):
    fixture_path = tmp_path / "review-queue-report.json"
    fixture_path.write_bytes(
        b"\xef\xbb\xbf"
        + json.dumps(
            {
                "dry_run": True,
                "operator_actions": [
                    {
                        "page_id": "page-blocked",
                        "page_url": "https://notion.so/page-blocked",
                        "title": "Blocked item",
                        "x_publish_status": "Blocked",
                        "x_publish_error": "Missing tweet draft text",
                        "action": "fix_blocked_publish",
                        "reason": "Missing tweet draft text",
                        "priority": 10,
                    }
                ],
                "ready_attention_items": [
                    {
                        "page_id": "page-ready",
                        "page_url": "https://notion.so/page-ready",
                        "title": "Ready item",
                        "x_publish_status": "Ready to Post",
                        "tweet_body": "Ready draft",
                        "action": "publish_or_reschedule",
                        "reason": "stale ready item",
                        "priority": 30,
                    }
                ],
            }
        ).encode("utf-8")
    )
    output_path = tmp_path / "review-records-report.json"

    assert (
        main(
            [
                "--input-mode",
                "review-records",
                "--input",
                str(fixture_path),
                "--output",
                str(output_path),
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["batch"] is True
    assert payload["summary"]["item_count"] == 2
    assert payload["safety"]["notion_writes"] is False
    assert payload["safety"]["x_posts"] is False
    assert payload["summary"]["average_operator_actions_per_item"] == 2.0
    assert payload["summary"]["high_noise_item_count"] == 0
    assert payload["summary"]["candidate_missing_metric_count"] == 14
    assert payload["summary"]["candidate_total_metric_slots"] == 20
    assert payload["summary"]["candidate_missing_metric_rate"] == 0.7
    assert payload["summary"]["candidate_missing_metric_counts"] == {
        "success": 0,
        "latency_ms": 2,
        "provider": 2,
        "model": 2,
        "token_cost_estimate": 2,
        "final_rank_score": 2,
        "draft_quality_score": 2,
        "safety_risk_flags": 2,
        "duplicate_or_near_duplicate": 0,
        "operator_action_required": 0,
    }
    assert payload["summary"]["candidate_missing_metric_owner_counts"] == {
        "provider_telemetry": 6,
        "cost_tracking": 2,
        "quality_gate": 2,
        "safety_review": 2,
        "source_ranking": 2,
    }
    assert payload["summary"]["candidate_missing_metric_rates"]["latency_ms"] == 1.0
    assert payload["summary"]["candidate_top_missing_metrics"] == [
        {"metric": "latency_ms", "count": 2, "rate": 1.0},
        {"metric": "provider", "count": 2, "rate": 1.0},
        {"metric": "model", "count": 2, "rate": 1.0},
        {"metric": "token_cost_estimate", "count": 2, "rate": 1.0},
        {"metric": "final_rank_score", "count": 2, "rate": 1.0},
    ]
    latency_hint = payload["summary"]["candidate_missing_metric_hints"]["latency_ms"]
    assert latency_hint["count"] == 2
    assert latency_hint["rate"] == 1.0
    assert latency_hint["owner"] == "provider_telemetry"
    assert "latency_ms" in latency_hint["operator_action"]
    assert payload["summary"]["candidate_top_missing_metric_hints"][0] == latency_hint
    assert payload["summary"]["candidate_top_missing_metric_hints"][4]["metric"] == "final_rank_score"
    assert payload["summary"]["candidate_top_missing_metric_owners"][0] == {
        "owner": "provider_telemetry",
        "count": 6,
        "share": 0.429,
        "top_metric": "latency_ms",
        "top_metric_count": 2,
        "operator_action": "Include latency_ms from generation telemetry in review records.",
    }
    confidence = payload["summary"]["candidate_experiment_confidence"]
    assert confidence["level"] == "needs_more_evidence"
    assert confidence["observed_missing_metric_rate"] == 0.7
    assert [issue["code"] for issue in confidence["issues"]] == [
        "sample_size_too_small",
        "missing_metric_rate_high",
    ]
    missing_metric_issue = confidence["issues"][1]
    assert missing_metric_issue == {
        "code": "missing_metric_rate_high",
        "reason": "Too many objective metric slots are missing from the candidate evidence.",
        "operator_action": "provider_telemetry: Include latency_ms from generation telemetry in review records.",
        "owner": "provider_telemetry",
        "owner_count": 6,
        "top_metric": "latency_ms",
        "top_metric_count": 2,
        "owner_operator_action": "Include latency_ms from generation telemetry in review records.",
    }
    assert payload["summary"]["candidate_ready_for_rollout"] is False
    assert payload["summary"]["candidate_rollout_blockers"] == [
        "sample_size_too_small",
        "missing_metric_rate_high",
    ]
    assert payload["summary"]["candidate_rollout_blocker_actions"] == [
        {
            "code": "sample_size_too_small",
            "source": "confidence",
            "operator_action": "Run the dry-run with at least 3 review items.",
            "reason": "The batch has too few items to trust the candidate adoption rate.",
        },
        {
            "code": "missing_metric_rate_high",
            "source": "confidence",
            "operator_action": "provider_telemetry: Include latency_ms from generation telemetry in review records.",
            "reason": "Too many objective metric slots are missing from the candidate evidence.",
            "owner": "provider_telemetry",
            "owner_count": 6,
            "top_metric": "latency_ms",
            "top_metric_count": 2,
            "owner_operator_action": "Include latency_ms from generation telemetry in review records.",
        },
    ]
    assert (
        payload["summary"]["candidate_rollout_reason"]
        == "blocked: run the dry-run with at least 3 review items; additional blockers: 1"
    )
    assert [item["title"] for item in payload["items"]] == ["Blocked item", "Ready item"]
    assert payload["items"][0]["candidate"]["signals"]["operator_actions"][0]["action"] == "review_queue_action"
    assert payload["items"][1]["candidate"]["signals"]["success"] is True

    stdout = capsys.readouterr().out
    assert '"batch": true' in stdout
