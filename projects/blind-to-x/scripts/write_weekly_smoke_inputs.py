from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BTX_ROOT = Path(__file__).resolve().parent.parent
if str(BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(BTX_ROOT))

from scripts.verify_weekly_smoke import (  # noqa: E402
    DEFAULT_RECOMPUTE_CONTRACT_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_REVIEW_EXPERIMENT_PATH,
    DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
    DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
    EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
    EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS,
    validate_manifest_contract,
    validate_manifest_repair_queue_contract,
    validate_manifest_strategy_summary_contract,
)

DEFAULT_OUTPUT_DIR = Path(".tmp")
DEFAULT_WEEKLY_REPORT_PAYLOAD_NAME = "weekly_report_payload_smoke.json"
DEFAULT_REVIEW_RECORD_SAMPLE_NAME = "review_queue_report_sample.json"
DEFAULT_MANIFEST_NAME = "weekly_smoke_manifest.json"
MANIFEST_SCHEMA_VERSION = 1
SMOKE_PROFILE = "weekly_report_ab_source_preflight"
SAFE_POWERSHELL_ARG_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:\\=-")
EXPECTED_REPORT_FRAGMENTS = [
    "Review top operator actions:",
    "Missing metric owners:",
    "Safety risk flags:",
    "Provider failures:",
    "Provider failure repair:",
    "Rollout blocker actions:",
    "Source trend operator actions:",
    "Evidence fields:",
    "Top source evidence:",
    "Operator action mismatches:",
    "Strategy operator action mismatches:",
    "Source operator actions:",
    "Repair queue:",
    "Primary repair target:",
    "count_total=6",
    "consistency=ok",
    "Recompute Scores Runtime Contract (dry-run)",
    "metric_missing=current:2/10,candidate:2/10",
]
EXPECTED_REVIEW_STDOUT_FRAGMENTS = list(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS)
EXPECTED_STRATEGY_STDOUT_FRAGMENTS = list(EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS)
SAFETY_CONTRACT = {
    "read_only": True,
    "browser_launches": False,
    "notion_writes": False,
    "x_posts": False,
    "provider_calls": False,
    "db_writes": False,
    "writes_local_json_only": True,
}
SOURCE_PREFLIGHT_REPAIR_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "source": "blind",
        "status": "blocked",
        "action": "Use a ready fallback source for this run.",
        "reason": "Access blocked during smoke preflight.",
        "signals": ["blocked"],
        "diagnostic_evidence": {},
    },
    {
        "source": "ppomppu",
        "status": "timeout",
        "action": (
            "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid."
        ),
        "reason": "Navigation timed out during smoke preflight.",
        "signals": ["timeout"],
        "diagnostic_evidence": {"error": "navigation timed out during smoke preflight fixture"},
    },
    {
        "source": "dcinside",
        "status": "blocked",
        "action": "Use a ready fallback source for this run.",
        "reason": "Access blocked during smoke preflight.",
        "signals": ["blocked"],
        "diagnostic_evidence": {},
    },
)


def _source_preflight_input_path(output_dir: Path, source: str) -> Path:
    return output_dir / f"source_browser_preflight-{source}.json"


def _command_path(path: Path) -> str:
    return path.as_posix()


def _format_command(parts: list[str | Path]) -> str:
    return " ".join(_quote_powershell_arg(_command_path(part) if isinstance(part, Path) else part) for part in parts)


def _quote_powershell_arg(value: str) -> str:
    if not value:
        return "''"
    if any(char not in SAFE_POWERSHELL_ARG_CHARS for char in value):
        return "'" + value.replace("'", "''") + "'"
    return value


def source_preflight_repair_input_paths(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    return {
        "aggregate": output_dir / "source_browser_preflight.json",
        **{
            str(fixture["source"]): _source_preflight_input_path(output_dir, str(fixture["source"]))
            for fixture in SOURCE_PREFLIGHT_REPAIR_FIXTURES
        },
    }


def expected_repair_queue(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    primary_command = _format_command(
        [
            "py",
            "-3",
            "scripts/source_preflight_evidence_doctor.py",
            "--input",
            _source_preflight_input_path(output_dir, "blind"),
            "--fail-on-warning",
        ]
    )
    return {
        "present": True,
        "total": 6,
        "listed": 6,
        "count_total": 6,
        "consistency": "ok",
        "full_queue_available": True,
        "queue_item_count": 6,
        "primary_repair_command_present": True,
        "primary_repair_target": {
            "present": True,
            "command": primary_command,
            "type": "evidence_doctor",
            "count": 1,
            "buckets": {"blind|blocked": 1},
            "sources": {"blind": 1},
        },
        "source": "manual_ready_gate.repair_commands",
    }


EXPECTED_REPAIR_QUEUE = expected_repair_queue(DEFAULT_OUTPUT_DIR)


def weekly_report_payload() -> dict[str, Any]:
    return {
        "totals": {
            "total": 12,
            "review_queue": 3,
            "approved": 7,
            "published": 5,
        },
        "top_topics": [["career", 6], ["money", 4]],
        "top_hooks": [["question", 5], ["statistic", 3]],
        "top_emotions": [["empathy", 6], ["anger", 2]],
        "top_performers": [
            {
                "title": "Title A",
                "views": 1000,
                "likes": 50,
                "retweets": 10,
                "topic_cluster": "career",
                "hook_type": "question",
                "emotion_axis": "empathy",
            }
        ],
    }


def review_experiment_payload() -> dict[str, Any]:
    return {
        "input_source": ".tmp/review_queue_report_sample.json",
        "dry_run": True,
        "batch": True,
        "safety": {
            "read_only": True,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "item_count": 3,
            "candidate_adoption_rate": 0.667,
            "average_current_review_efficiency_score": 18.0,
            "average_candidate_review_efficiency_score": 24.5,
            "average_score_delta": 6.5,
            "candidate_operator_action_total": 5,
            "average_operator_actions_per_item": 1.667,
            "max_operator_actions_per_item": 2,
            "average_operator_action_delta": 1.667,
            "candidate_top_operator_actions": [
                {
                    "action": "repair_provider_access",
                    "count": 3,
                    "priority": 10,
                    "reason": "Check provider API key",
                },
                {
                    "action": "resolve_x_publish_status",
                    "count": 1,
                    "priority": 40,
                    "reason": "Needs Edit",
                },
            ],
            "candidate_missing_metric_rate": 0.1,
            "candidate_missing_metric_counts": {
                "provider": 0,
                "model": 0,
                "latency_ms": 1,
                "token_cost_estimate": 2,
            },
            "candidate_missing_metric_owner_counts": {
                "cost_tracking": 2,
                "provider_telemetry": 1,
            },
            "candidate_top_missing_metric_owners": [
                {
                    "owner": "cost_tracking",
                    "count": 2,
                    "share": 0.667,
                    "top_metric": "token_cost_estimate",
                    "top_metric_count": 2,
                    "operator_action": "Include token_cost_estimate from the generation cost tracker.",
                },
                {
                    "owner": "provider_telemetry",
                    "count": 1,
                    "share": 0.333,
                    "top_metric": "latency_ms",
                    "top_metric_count": 1,
                    "operator_action": "Include latency_ms from generation telemetry in review records.",
                },
            ],
            "candidate_safety_risk_item_count": 2,
            "candidate_safety_risk_flag_counts": {"privacy": 2, "legal": 1},
            "candidate_provider_failure_category_counts": {"auth": 1, "rate_limit": 1},
            "candidate_provider_failure_provider_counts": {"gemini": 1, "openai": 1},
            "candidate_primary_provider_failure_category_counts": {"auth": 1},
            "candidate_primary_provider_failure_provider_counts": {"openai": 1},
            "candidate_primary_provider_failure_actions": [
                {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "category": "auth",
                    "operator_action": "Check provider API key",
                    "retryable": False,
                    "circuit_breaker_candidate": True,
                    "count": 1,
                }
            ],
            "candidate_operator_error_bucket_counts": {"x_post_failed": 2},
            "candidate_operator_reason_bucket_counts": {"missing_draft": 1},
            "candidate_operator_triage_bucket_counts": {"blocked_publish": 1},
            "candidate_ready_for_rollout": False,
            "candidate_rollout_blocker_actions": [
                {
                    "code": "missing_metric_rate_high",
                    "source": "confidence",
                    "operator_action": ("cost_tracking: Include token_cost_estimate from the generation cost tracker."),
                    "owner": "cost_tracking",
                    "owner_count": 2,
                    "top_metric": "token_cost_estimate",
                    "top_metric_count": 2,
                    "owner_operator_action": "Include token_cost_estimate from the generation cost tracker.",
                }
            ],
            "candidate_rollout_reason": "blocked: fill missing objective metrics before rollout",
            "candidate_experiment_confidence": {
                "issues": [
                    {
                        "code": "missing_metric_rate_high",
                        "operator_action": (
                            "cost_tracking: Include token_cost_estimate from the generation cost tracker."
                        ),
                        "owner": "cost_tracking",
                        "owner_count": 2,
                        "top_metric": "token_cost_estimate",
                        "top_metric_count": 2,
                        "owner_operator_action": "Include token_cost_estimate from the generation cost tracker.",
                    }
                ]
            },
        },
        "items": [
            {
                "current": {"signals": {}, "operator_action_count": 0},
                "candidate": {
                    "signals": {
                        "provider": "gemini",
                        "model": "gemini-2.5-flash",
                        "latency_ms": 400,
                        "token_cost_estimate": 0.01,
                    },
                    "operator_action_count": 2,
                },
            },
            {
                "current": {"signals": {}, "operator_action_count": 0},
                "candidate": {
                    "signals": {
                        "provider": "openai",
                        "model": "gpt-5-mini",
                        "latency_ms": 500,
                        "token_cost_estimate": 0.02,
                    },
                    "operator_action_count": 1,
                },
            },
            {
                "current": {"signals": {}, "operator_action_count": 0},
                "candidate": {
                    "signals": {
                        "provider": "gemini",
                        "model": "gemini-2.5-flash",
                        "latency_ms": 600,
                        "token_cost_estimate": 0.03,
                    },
                    "operator_action_count": 2,
                },
            },
        ],
    }


def review_record_sample_payload() -> dict[str, Any]:
    return {
        "operator_actions": [
            {
                "page_id": "page-blocked",
                "title": "Blocked item",
                "x_publish_status": "Blocked",
                "x_publish_error": "Missing tweet draft text",
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


def source_preflight_trend_payload() -> dict[str, Any]:
    return {
        "status": "WARN",
        "ok": True,
        "safety": {
            "read_only": True,
            "browser_launches": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "report_count": 3,
            "problem_action_count": 4,
            "failure_report_count": 3,
            "operator_action_required_count": 4,
            "strategy_change_ready_count": 2,
            "error_count": 0,
            "warning_count": 1,
            "status_counts": {"timeout": 2, "blocked": 1, "browser_unavailable": 1},
            "source_counts": {"ppomppu": 2, "blind": 1, "fmkorea": 1},
            "failure_report_status_counts": {"valid": 3, "missing": 1},
            "evidence_field_counts": {
                "failure_report_path": 3,
                "screenshot_path": 3,
                "html_snapshot_path": 3,
                "trace_path": 1,
                "error": 1,
            },
            "evidence_gate_status_counts": {
                "strategy_review_ready": 2,
                "fallback_only": 1,
                "fix_evidence_first": 1,
            },
            "top_issue_codes": {"missing_failure_report_path": 1},
            "operator_action_mismatch_count": 1,
            "operator_action_mismatch_source_counts": {"ppomppu": 1},
            "repair_command_count": 3,
            "repair_command_type_counts": {
                "evidence_doctor": 2,
                "source_preflight_capture": 1,
            },
            "top_repair_commands": [
                {
                    "command": "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight.json",
                    "type": "evidence_doctor",
                    "count": 2,
                    "sources": {"ppomppu": 2},
                },
                {
                    "command": (
                        "py -3 main.py --config config.yaml --source ppomppu --source-preflight "
                        "--source-preflight-click-through"
                    ),
                    "type": "source_preflight_capture",
                    "count": 1,
                    "sources": {"ppomppu": 1},
                },
            ],
            "top_operator_actions": [
                {
                    "operator_action": "Inspect captured evidence, then retry.",
                    "count": 3,
                    "sources": {"ppomppu": 2, "blind": 1},
                },
                {
                    "operator_action": "Use a ready fallback source for this run.",
                    "count": 1,
                    "sources": {"fmkorea": 1},
                },
            ],
            "top_source_action": {
                "source": "ppomppu",
                "status": "timeout",
                "count": 2,
                "operator_action": (
                    "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid."
                ),
            },
            "top_source_remediation": {
                "checklist": [
                    (
                        "Open ppomppu evidence fields first: "
                        "failure_report_path, screenshot_path, html_snapshot_path, trace_path, error."
                    ),
                    (
                        "Use a ready fallback source for this run if available; do not increase ppomppu timeout "
                        "until evidence shows a reachable slow page."
                    ),
                    "Rerun ppomppu preflight with --failure-dir after any timeout or selector change.",
                ],
            },
            "top_source_evidence": {
                "source": "ppomppu",
                "status": "timeout",
                "count": 2,
                "input_path": ".tmp/source_browser_preflight-ppomppu.json",
                "operator_action": (
                    "Inspect ppomppu timeout evidence, then adjust timeout or source fallback only after evidence is valid."
                ),
                "evidence_gate_status": "strategy_review_ready",
                "open_first_field": "failure_report_path",
                "open_first": ".tmp/failures/source_preflight/ppomppu-timeout.json",
                "evidence": {
                    "failure_report_path": ".tmp/failures/source_preflight/ppomppu-timeout.json",
                    "trace_path": ".tmp/traces/source_preflight/ppomppu-timeout.zip",
                    "screenshot_path": "screenshots/source_preflight/ppomppu.png",
                    "html_snapshot_path": ".tmp/failures/source_preflight/ppomppu.html",
                },
            },
            "operator_recommendation": {
                "action": "repair_evidence",
                "priority": "medium",
                "source": "ppomppu",
                "status": "timeout",
                "operator_action": (
                    "Run the evidence doctor for affected reports, restore missing artifacts, then rerun trend "
                    "reporting before changing selectors, timeouts, or source strategy."
                ),
            },
        },
        "next_step": "Review warning codes; rerun individual evidence doctor for any unclear report.",
    }


def source_preflight_strategy_payload(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    repair_command_queue = [
        {
            "command": _format_command(
                [
                    "py",
                    "-3",
                    "scripts/source_preflight_evidence_doctor.py",
                    "--input",
                    _source_preflight_input_path(output_dir, "blind"),
                    "--fail-on-warning",
                ]
            ),
            "type": "evidence_doctor",
            "count": 1,
            "sources": {"blind": 1},
            "buckets": {"blind|blocked": 1},
        },
        {
            "command": _format_command(
                [
                    "py",
                    "-3",
                    "scripts/source_preflight_evidence_doctor.py",
                    "--input",
                    _source_preflight_input_path(output_dir, "ppomppu"),
                    "--fail-on-warning",
                ]
            ),
            "type": "evidence_doctor",
            "count": 1,
            "sources": {"ppomppu": 1},
            "buckets": {"ppomppu|timeout": 1},
        },
        {
            "command": _format_command(
                [
                    "py",
                    "-3",
                    "scripts/source_preflight_evidence_doctor.py",
                    "--input",
                    _source_preflight_input_path(output_dir, "dcinside"),
                    "--fail-on-warning",
                ]
            ),
            "type": "evidence_doctor",
            "count": 1,
            "sources": {"dcinside": 1},
            "buckets": {"dcinside|blocked": 1},
        },
        {
            "command": "py -3 main.py --config config.yaml --source blind --source-preflight",
            "type": "source_preflight_capture",
            "count": 1,
            "sources": {"blind": 1},
            "buckets": {"blind|blocked": 1},
        },
        {
            "command": "py -3 main.py --config config.yaml --source ppomppu --source-preflight",
            "type": "source_preflight_capture",
            "count": 1,
            "sources": {"ppomppu": 1},
            "buckets": {"ppomppu|timeout": 1},
        },
        {
            "command": "py -3 main.py --config config.yaml --source dcinside --source-preflight",
            "type": "source_preflight_capture",
            "count": 1,
            "sources": {"dcinside": 1},
            "buckets": {"dcinside|blocked": 1},
        },
    ]
    repair_command_count = sum(int(item["count"]) for item in repair_command_queue)
    return {
        "dry_run": True,
        "trend_status": "WARN",
        "objective_metrics": [
            "success",
            "latency_ms",
            "provider",
            "model",
            "token_cost_estimate",
            "final_rank_score",
            "draft_quality_score",
            "safety_risk_flags",
            "duplicate_or_near_duplicate",
            "operator_action_required",
        ],
        "safety": {
            "read_only": True,
            "browser_launches": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "report_count": 2,
            "problem_action_count": 2,
            "evidence_gate_status_counts": {
                "fix_evidence_first": 3,
            },
            "repair_command_count": 6,
            "repair_command_type_counts": {
                "evidence_doctor": 3,
                "source_preflight_capture": 3,
            },
            "repair_command_queue": repair_command_queue,
            "repair_command_queue_consistency": {
                "status": "ok",
                "repair_command_count": repair_command_count,
                "queue_count_total": repair_command_count,
                "queue_item_count": len(repair_command_queue),
                "top_item_count": 4,
            },
            "top_repair_commands": repair_command_queue[:4],
            "operator_action_mismatch_count": 1,
            "operator_action_mismatch_source_counts": {"ppomppu": 1},
            "top_operator_actions": [
                {
                    "operator_action": "Inspect captured evidence, then retry.",
                    "count": 2,
                    "sources": {"ppomppu": 1, "blind": 1},
                }
            ],
            "missing_metric_counts": {"current": 2, "candidate": 2},
            "measurement_scope": {
                "mode": "local_preflight_evidence",
                "external_llm_calls": False,
                "costed_generation": False,
                "not_measured_metrics": ["latency_ms", "draft_quality_score"],
            },
        },
        "variants": {
            "current": {
                "name": "current_top_source_action",
                "signals": {
                    "provider": "source_preflight",
                    "model": "current_top_source_action",
                    "token_cost_estimate": 0.0,
                    "latency_ms": None,
                    "draft_quality_score": None,
                    "duplicate_or_near_duplicate": False,
                    "final_rank_score": 44.0,
                    "strategy_review_count": 2,
                    "unsafe_strategy_change_count": 1,
                    "success": False,
                    "operator_action_required": True,
                    "safety_risk_flags": ["ungated_strategy_change"],
                },
            },
            "candidate": {
                "name": "candidate_gate_directed_operator_recommendation",
                "signals": {
                    "provider": "source_preflight",
                    "model": "gate_directed_operator_recommendation",
                    "token_cost_estimate": 0.0,
                    "latency_ms": None,
                    "draft_quality_score": None,
                    "duplicate_or_near_duplicate": False,
                    "final_rank_score": 68.0,
                    "strategy_review_count": 1,
                    "unsafe_strategy_change_count": 0,
                    "recommendation_action": "repair_evidence",
                    "success": False,
                    "operator_action_required": True,
                    "safety_risk_flags": ["evidence_repair_required", "repair_command_debt"],
                },
            },
        },
        "comparison": {
            "recommendation": "repair_evidence_first",
            "score_delta": 24.0,
            "unsafe_strategy_change_delta": -1,
            "operator_action_required_delta": 0,
        },
        "rollout_gate": {
            "status": "blocked_repair_evidence",
            "ready_for_manual_strategy_review": False,
            "auto_apply_allowed": False,
            "manual_review_required": True,
            "blocked_by": ["repair_evidence_first", "repair_command_debt"],
            "operator_action": (
                "Run the recommended repair commands and fix invalid failure evidence before reviewing selector, timeout, or source strategy changes."
            ),
        },
        "manual_ready_gate": {
            "required": True,
            "passed": False,
            "status": "blocked",
            "exit_code": 2,
            "reason": (
                "Run the recommended repair commands and fix invalid failure evidence before reviewing selector, timeout, or source strategy changes."
            ),
            "primary_repair_command": repair_command_queue[0]["command"],
            "repair_command_count": repair_command_count,
            "repair_command_remaining_count": repair_command_count - 1,
            "repair_commands": [item["command"] for item in repair_command_queue],
        },
    }


def recompute_runtime_contract_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "ok": True,
        "input_source": ".tmp/recompute_scores_fixture.json",
        "validation_status": "ok",
        "validation_ok": True,
        "record_count": 2,
        "candidate_ranking_weights_present": True,
        "gate_errors": [],
        "errors": [],
        "warnings": [],
        "safety": {
            "notion_reads": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "runtime_contract": {
            "validation": {
                "loads_runtime_dependencies": False,
                "scoring_runs": False,
                "notion_reads": False,
                "notion_writes": False,
                "x_posts": False,
            },
            "scoring_dry_run": {
                "input_fixture": True,
                "scoring_dependencies_may_initialize": True,
                "dependency_scope": "content_intelligence_scoring_and_optional_ml_model_cache",
                "notion_reads": False,
                "notion_writes": False,
                "zero_dependency_validation_command": "scripts/recompute_scores.py --validate-input --input <path> --json",
                "runtime_contract_gate_command": (
                    "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json"
                ),
                "offline_hint": "Prepare ML model caches first before using HF_HUB_OFFLINE=1 for scoring dry-runs.",
            },
        },
        "operator_action": "Runtime contract gate passed; scoring dry-run may proceed for manual review.",
    }


def default_output_paths(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    return {
        "weekly_report_payload": output_dir / DEFAULT_WEEKLY_REPORT_PAYLOAD_NAME,
        "review_records": output_dir / DEFAULT_REVIEW_RECORD_SAMPLE_NAME,
        "review_experiment": output_dir / DEFAULT_REVIEW_EXPERIMENT_PATH.name,
        "source_preflight_trend": output_dir / DEFAULT_SOURCE_PREFLIGHT_TREND_PATH.name,
        "source_preflight_strategy": output_dir / DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH.name,
        "recompute_contract": output_dir / DEFAULT_RECOMPUTE_CONTRACT_PATH.name,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_preflight_failure_report_payload(
    *,
    source: str,
    status: str,
    action: str,
    reason: str,
    signals: list[str],
    failure_report_path: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "classification": {"status": status, "reason": reason, "signals": signals},
        "failure_report": {
            "schema_version": 1,
            "tool": "source_browser_probe",
            "captured_at": "2026-06-10T00:00:00+00:00",
        },
        "operator": {
            "action_required": True,
            "action": action,
            "evidence": {"failure_report_path": failure_report_path},
        },
    }


def _source_preflight_report_payload(problem_actions: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for action in problem_actions:
        status = str(action.get("status") or "unknown")
        source = str(action.get("source") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
    return {
        "status": "WARN",
        "ok": True,
        "summary": {
            "problem_count": len(problem_actions),
            "problem_actions": problem_actions,
            "status_counts": status_counts,
            "source_counts": source_counts,
        },
    }


def _write_source_preflight_repair_inputs(output_dir: Path) -> None:
    aggregate_actions: list[dict[str, Any]] = []
    failure_dir = output_dir / "failures" / "source_preflight"
    for fixture in SOURCE_PREFLIGHT_REPAIR_FIXTURES:
        source = str(fixture["source"])
        status = str(fixture["status"])
        action = str(fixture["action"])
        reason = str(fixture["reason"])
        signals = [str(signal) for signal in fixture["signals"]]
        failure_report_path = failure_dir / f"{source}-{status}.json"
        failure_report_path_text = failure_report_path.as_posix()
        evidence = {"failure_report_path": failure_report_path_text}
        diagnostic_evidence = fixture.get("diagnostic_evidence")
        if isinstance(diagnostic_evidence, dict):
            evidence.update(diagnostic_evidence)
        problem_action = {
            "source": source,
            "status": status,
            "action": action,
            "operator_action_required": True,
            "operator_action": action,
            "evidence": evidence,
        }
        _write_json(
            failure_report_path,
            _source_preflight_failure_report_payload(
                source=source,
                status=status,
                action=action,
                reason=reason,
                signals=signals,
                failure_report_path=failure_report_path_text,
            ),
        )
        _write_json(
            _source_preflight_input_path(output_dir, source), _source_preflight_report_payload([problem_action])
        )
        aggregate_actions.append(problem_action)
    _write_json(output_dir / "source_browser_preflight.json", _source_preflight_report_payload(aggregate_actions))


def write_weekly_smoke_inputs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    paths = default_output_paths(output_dir)
    _write_json(paths["weekly_report_payload"], weekly_report_payload())
    _write_json(paths["review_records"], review_record_sample_payload())
    _write_json(paths["review_experiment"], review_experiment_payload())
    _write_json(paths["source_preflight_trend"], source_preflight_trend_payload())
    _write_json(paths["source_preflight_strategy"], source_preflight_strategy_payload(output_dir))
    _write_json(paths["recompute_contract"], recompute_runtime_contract_payload())
    _write_source_preflight_repair_inputs(output_dir)
    return paths


def build_followup_commands(
    paths: dict[str, Path],
    *,
    manifest_output: Path | None = None,
    self_check: bool = False,
) -> dict[str, str]:
    output_dir = paths["weekly_report_payload"].parent
    report_path = output_dir / DEFAULT_REPORT_PATH.name
    write_inputs_parts: list[str | Path] = [
        "py",
        "-3",
        "scripts/write_weekly_smoke_inputs.py",
        "--output-dir",
        output_dir,
    ]
    if manifest_output is not None:
        write_inputs_parts.extend(["--manifest-output", manifest_output])
    if self_check:
        write_inputs_parts.append("--self-check")
    commands = {
        "write_inputs": _format_command(write_inputs_parts),
        "review_summary": _format_command(
            [
                "py",
                "-3",
                "scripts/review_experiment_dry_run.py",
                "--input-mode",
                "review-records",
                "--input",
                paths["review_records"],
                "--min-items",
                "1",
                "--max-missing-rate",
                "0.25",
                "--summary-only",
            ]
        ),
        "build_report": _format_command(
            [
                "py",
                "-3",
                "scripts/build_weekly_report.py",
                "--payload-input",
                paths["weekly_report_payload"],
                "--review-experiment-input",
                paths["review_experiment"],
                "--source-preflight-trend-input",
                paths["source_preflight_trend"],
                "--source-preflight-strategy-input",
                paths["source_preflight_strategy"],
                "--recompute-contract-input",
                paths["recompute_contract"],
                "--output",
                report_path,
            ]
        ),
        "verify_text": _format_command(
            [
                "py",
                "-3",
                "scripts/verify_weekly_smoke.py",
                "--report",
                report_path,
                "--review-experiment",
                paths["review_experiment"],
                "--source-preflight-trend",
                paths["source_preflight_trend"],
                "--source-preflight-strategy",
                paths["source_preflight_strategy"],
                "--recompute-contract",
                paths["recompute_contract"],
            ]
        ),
        "verify_json": _format_command(
            [
                "py",
                "-3",
                "scripts/verify_weekly_smoke.py",
                "--report",
                report_path,
                "--review-experiment",
                paths["review_experiment"],
                "--source-preflight-trend",
                paths["source_preflight_trend"],
                "--source-preflight-strategy",
                paths["source_preflight_strategy"],
                "--recompute-contract",
                paths["recompute_contract"],
                "--json",
            ]
        ),
    }
    if manifest_output is not None:
        commands["verify_manifest"] = _format_command(
            [
                "py",
                "-3",
                "scripts/verify_weekly_smoke.py",
                "--manifest",
                manifest_output,
                "--verify-review-summary",
                "--verify-strategy-summary",
            ]
        )
    return commands


def build_result_payload(
    paths: dict[str, Path],
    *,
    manifest_output: Path | None = None,
    self_check: bool = False,
) -> dict[str, Any]:
    report_path = paths["weekly_report_payload"].parent / DEFAULT_REPORT_PATH.name
    output_dir = paths["weekly_report_payload"].parent
    payload = {
        "ok": True,
        "status": "ok",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "profile": SMOKE_PROFILE,
        "safety_contract": dict(SAFETY_CONTRACT),
        "paths": {name: path.as_posix() for name, path in paths.items()},
        "expected_outputs": {"report": report_path.as_posix()},
        "commands": build_followup_commands(paths, manifest_output=manifest_output, self_check=self_check),
        "expected_report_fragments": list(EXPECTED_REPORT_FRAGMENTS),
        "expected_review_stdout_fragments": list(EXPECTED_REVIEW_STDOUT_FRAGMENTS),
        "expected_strategy_stdout_fragments": list(EXPECTED_STRATEGY_STDOUT_FRAGMENTS),
        "expected_repair_queue": expected_repair_queue(output_dir),
    }
    if manifest_output is not None:
        payload["manifest"] = manifest_output.as_posix()
    return payload


def build_self_check_payload(
    *,
    paths: dict[str, Path],
    manifest_payload: dict[str, Any],
    manifest_output: Path | None = None,
) -> dict[str, Any]:
    errors = validate_manifest_contract(manifest_payload)
    errors.extend(validate_manifest_repair_queue_contract(manifest_payload))
    errors.extend(validate_manifest_strategy_summary_contract(manifest_payload))
    for name, path in paths.items():
        if not path.exists():
            errors.append(f"self_check_missing_file:{name}:{path.as_posix()}")
    output_dir = paths["weekly_report_payload"].parent
    for name, path in source_preflight_repair_input_paths(output_dir).items():
        if not path.exists():
            errors.append(f"self_check_missing_source_preflight_repair_input:{name}:{path.as_posix()}")
    if manifest_output is not None and not manifest_output.exists():
        errors.append(f"self_check_missing_manifest:{manifest_output.as_posix()}")
    return {
        "ok": not errors,
        "status": "ok" if not errors else "fail",
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write local weekly smoke input JSON files.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=None,
        help="Optional path for writing the machine-readable smoke input manifest.",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Validate the generated manifest contract and written input files before exiting.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable payload with written paths.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = write_weekly_smoke_inputs(args.output_dir)
    payload = build_result_payload(paths, manifest_output=args.manifest_output, self_check=args.self_check)
    if args.manifest_output is not None:
        _write_json(args.manifest_output, payload)
    self_check = None
    if args.self_check:
        self_check = build_self_check_payload(
            paths=paths, manifest_payload=payload, manifest_output=args.manifest_output
        )
        payload["self_check"] = self_check
        if args.manifest_output is not None:
            _write_json(args.manifest_output, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if self_check is None or self_check["ok"] else 1
    path_list = ",".join(path.as_posix() for path in paths.values())
    manifest_part = f" manifest={args.manifest_output.as_posix()}" if args.manifest_output is not None else ""
    self_check_part = ""
    if self_check is not None:
        self_check_part = f" self_check={self_check['status']}"
        if not self_check["ok"]:
            self_check_part += f" reason={';'.join(self_check['errors'])}"
    print(
        f"weekly_smoke_inputs=written output_dir={args.output_dir.as_posix()}{manifest_part}"
        f"{self_check_part} files={path_list}"
    )
    return 0 if self_check is None or self_check["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
