from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_weekly_smoke import (  # noqa: E402
    DEFAULT_RECOMPUTE_CONTRACT_PATH,
    EXPECTED_MANIFEST_PROFILE,
    EXPECTED_MANIFEST_REPORT_FRAGMENTS,
    EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
    EXPECTED_MANIFEST_SAFETY_CONTRACT,
    EXPECTED_MANIFEST_SCHEMA_VERSION,
    EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS,
    REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS,
    REVIEW_SUMMARY_TIMEOUT_SECONDS,
    _bounded_review_summary_child_error_tail,
    _review_summary_failure_reasons,
    build_parser,
    build_review_summary_verification_payload,
    build_strategy_summary_verification_payload,
    main,
    run_review_summary_stdout_verification,
    run_strategy_summary_stdout_verification,
    validate_manifest_contract,
    verify_weekly_smoke,
)
from scripts.write_weekly_smoke_inputs import source_preflight_strategy_payload  # noqa: E402


def test_verify_weekly_smoke_help_distinguishes_summary_verifier_side_effects():
    actions = {action.dest: action.help for action in build_parser()._actions}

    review_help = actions["verify_review_summary"]
    assert "review summary dry-run child command" in review_help
    assert "expected_review_stdout_fragments" in review_help

    strategy_help = actions["verify_strategy_summary"]
    assert "format paths.source_preflight_strategy locally" in strategy_help
    assert "expected_strategy_stdout_fragments" in strategy_help
    assert "does not run browser, Notion, providers, X, or the manifest command string" in strategy_help


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_smoke_files(tmp_path: Path, *, report_text: str | None = None) -> dict[str, Path]:
    paths = {
        "report": tmp_path / "weekly_report_smoke.md",
        "review_records": tmp_path / "review_queue_report_sample.json",
        "review": tmp_path / "weekly_report_experiment_smoke.json",
        "trend": tmp_path / "source_preflight_trend.json",
        "strategy": tmp_path / "source_preflight_strategy_simulation.json",
        "recompute": tmp_path / DEFAULT_RECOMPUTE_CONTRACT_PATH.name,
    }
    paths["report"].write_text(
        report_text
        or "\n".join(
            [
                "# Blind-to-X Weekly Report",
                "- Review top operator actions: 3x repair_provider_access priority=10 reason=Check provider API key",
                "- Missing metric owners: 2x cost_tracking top_metric=token_cost_estimate action=Include token_cost_estimate from the generation cost tracker.",
                "- Safety risk flags: items=2; flags=privacy=2, legal=1",
                "- Provider failures: categories=auth=1, rate_limit=1; providers=gemini=1, openai=1; "
                "primary_categories=auth=1; primary_providers=openai=1",
                "- Provider failure repair: 1x provider=openai category=auth model=gpt-4.1-mini "
                "retryable=false circuit_breaker=true action=Check provider API key",
                "- Rollout blocker actions: missing_metric_rate_high source=confidence owner=cost_tracking top_metric=token_cost_estimate action=cost_tracking: Include token_cost_estimate from the generation cost tracker.",
                "- Source trend operator actions: 2x sources=ppomppu=2 action=Inspect captured evidence",
                "- Evidence fields: failure_report_path=3, html_snapshot_path=3, screenshot_path=3, error=1, trace_path=1",
                "- Top source evidence: source=ppomppu; status=timeout; count=2; "
                "open_first=failure_report_path=.tmp/failures/source_preflight/ppomppu-timeout.json",
                "- Source operator actions: 1x sources=blind=1 action=Inspect captured evidence",
                "- Recompute Scores Runtime Contract (dry-run)",
                "- Gate: status=ok; ok=true; validation_ok=true; gate_errors=0; records=2",
                "- Runtime: validation_loads_runtime_dependencies=false; validation_scoring_runs=false; scoring_dependencies_may_initialize=true",
                "- Safety: notion_reads=false; notion_writes=false; x_posts=false; manual_publish_required=true",
                "- Recompute command: `scripts/recompute_scores.py --assert-runtime-contract --input <path> --json`",
                "- Metric coverage: metric_missing=current:2/10,candidate:2/10",
            ]
        ),
        encoding="utf-8",
    )
    _write_json(
        paths["review_records"],
        {
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
        },
    )
    _write_json(
        paths["review"],
        {
            "summary": {
                "candidate_top_operator_actions": [
                    {
                        "action": "repair_provider_access",
                        "count": 3,
                        "priority": 10,
                        "reason": "Check provider API key",
                    }
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
                "candidate_top_missing_metric_owners": [
                    {
                        "owner": "cost_tracking",
                        "count": 2,
                        "top_metric": "token_cost_estimate",
                        "operator_action": "Include token_cost_estimate from the generation cost tracker.",
                    }
                ],
                "candidate_rollout_blocker_actions": [
                    {
                        "code": "missing_metric_rate_high",
                        "source": "confidence",
                        "operator_action": "cost_tracking: Include token_cost_estimate from the generation cost tracker.",
                        "owner": "cost_tracking",
                        "owner_count": 2,
                        "top_metric": "token_cost_estimate",
                        "top_metric_count": 2,
                        "owner_operator_action": "Include token_cost_estimate from the generation cost tracker.",
                    }
                ],
            }
        },
    )
    _write_json(
        paths["trend"],
        {
            "summary": {
                "evidence_field_counts": {
                    "failure_report_path": 3,
                    "screenshot_path": 3,
                    "html_snapshot_path": 3,
                    "trace_path": 1,
                    "error": 1,
                },
                "top_operator_actions": [
                    {
                        "operator_action": "Inspect captured evidence",
                        "count": 2,
                        "sources": {"ppomppu": 2},
                    }
                ],
                "top_source_evidence": {
                    "source": "ppomppu",
                    "status": "timeout",
                    "count": 2,
                    "open_first_field": "failure_report_path",
                    "open_first": ".tmp/failures/source_preflight/ppomppu-timeout.json",
                },
            }
        },
    )
    _write_json(paths["strategy"], {"summary": {"top_operator_actions": [{"operator_action": "Inspect"}]}})
    _write_json(
        paths["recompute"],
        {
            "ok": True,
            "gate_errors": [],
            "runtime_contract": {
                "validation": {"scoring_runs": False},
                "scoring_dry_run": {
                    "scoring_dependencies_may_initialize": True,
                    "runtime_contract_gate_command": (
                        "scripts/recompute_scores.py --assert-runtime-contract --input <path> --json"
                    ),
                },
            },
            "safety": {"notion_writes": False},
        },
    )
    return paths


def _write_manifest(path: Path, smoke_paths: dict[str, Path], *, safety_contract: dict | None = None) -> None:
    report_path = smoke_paths["report"].as_posix()
    review_records_path = smoke_paths["review_records"].as_posix()
    review_path = smoke_paths["review"].as_posix()
    trend_path = smoke_paths["trend"].as_posix()
    strategy_path = smoke_paths["strategy"].as_posix()
    recompute_path = smoke_paths["recompute"].as_posix()
    manifest_path = path.as_posix()
    _write_json(
        path,
        {
            "schema_version": EXPECTED_MANIFEST_SCHEMA_VERSION,
            "profile": EXPECTED_MANIFEST_PROFILE,
            "safety_contract": safety_contract or EXPECTED_MANIFEST_SAFETY_CONTRACT,
            "expected_report_fragments": EXPECTED_MANIFEST_REPORT_FRAGMENTS,
            "manifest": manifest_path,
            "paths": {
                "review_records": review_records_path,
                "review_experiment": review_path,
                "source_preflight_trend": trend_path,
                "source_preflight_strategy": strategy_path,
                "recompute_contract": recompute_path,
            },
            "expected_outputs": {"report": report_path},
            "expected_review_stdout_fragments": EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
            "commands": {
                "write_inputs": (
                    "py -3 scripts/write_weekly_smoke_inputs.py "
                    f"--output-dir {path.parent.as_posix()} --manifest-output {manifest_path}"
                ),
                "review_summary": (
                    "py -3 scripts/review_experiment_dry_run.py "
                    f"--input-mode review-records --input {review_records_path} "
                    "--min-items 1 --max-missing-rate 0.25 --summary-only"
                ),
                "build_report": (
                    "py -3 scripts/build_weekly_report.py "
                    f"--payload-input {path.parent.as_posix()}/weekly_report_payload_smoke.json "
                    f"--review-experiment-input {review_path} "
                    f"--source-preflight-trend-input {trend_path} "
                    f"--source-preflight-strategy-input {strategy_path} "
                    f"--recompute-contract-input {recompute_path} "
                    f"--output {report_path}"
                ),
                "verify_text": (
                    "py -3 scripts/verify_weekly_smoke.py "
                    f"--report {report_path} "
                    f"--review-experiment {review_path} "
                    f"--source-preflight-trend {trend_path} "
                    f"--source-preflight-strategy {strategy_path} "
                    f"--recompute-contract {recompute_path}"
                ),
                "verify_json": (
                    "py -3 scripts/verify_weekly_smoke.py "
                    f"--report {report_path} "
                    f"--review-experiment {review_path} "
                    f"--source-preflight-trend {trend_path} "
                    f"--source-preflight-strategy {strategy_path} "
                    f"--recompute-contract {recompute_path} "
                    "--json"
                ),
                "verify_manifest": (
                    f"py -3 scripts/verify_weekly_smoke.py --manifest {manifest_path} --verify-review-summary"
                ),
            },
        },
    )


def _add_repair_queue_fixture(paths: dict[str, Path]) -> dict[str, object]:
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report + "\n- Repair queue: total=2; listed=1; count_total=2; consistency=ok; "
        "full_queue_available=true; source=manual_ready_gate.repair_commands\n"
        "- Primary repair target: type=evidence_doctor; count=2; buckets=blind|blocked=2; sources=blind=2\n",
        encoding="utf-8",
    )
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_command = (
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json"
    )
    strategy["summary"]["repair_command_queue"] = [
        {
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "sources": {"blind": 2},
            "buckets": {"blind|blocked": 2},
        }
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "ok",
        "repair_command_count": 2,
        "queue_count_total": 2,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_command,
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [repair_command],
    }
    _write_json(paths["strategy"], strategy)
    return {
        "present": True,
        "total": 2,
        "listed": 1,
        "count_total": 2,
        "consistency": "ok",
        "full_queue_available": True,
        "queue_item_count": 1,
        "primary_repair_command_present": True,
        "primary_repair_target": {
            "present": True,
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "buckets": {"blind|blocked": 2},
            "sources": {"blind": 2},
        },
        "source": "manual_ready_gate.repair_commands",
    }


def _expected_manifest_repair_queue_payload(
    expected_repair_queue: dict[str, object],
    strategy_path: Path,
    *,
    ok: bool,
    matched_key_count: int,
    mismatched_keys: list[str],
) -> dict[str, object]:
    return {
        "ok": ok,
        "status": "ok" if ok else "fail",
        "expected_present": True,
        "expected_is_object": True,
        "checked": True,
        "actual_present": True,
        "expected_key_count": len(expected_repair_queue),
        "actual_key_count": len(expected_repair_queue),
        "matched_key_count": matched_key_count,
        "mismatch_count": len(mismatched_keys),
        "mismatched_keys": mismatched_keys,
        "source_preflight_strategy": strategy_path.as_posix(),
    }


def test_verify_weekly_smoke_accepts_report_with_review_and_source_actions(tmp_path):
    paths = _write_smoke_files(tmp_path)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert errors == []


def test_verify_weekly_smoke_accepts_non_default_metric_denominator(tmp_path):
    paths = _write_smoke_files(
        tmp_path,
        report_text="\n".join(
            [
                "# Blind-to-X Weekly Report",
                "- Review top operator actions: 3x repair_provider_access priority=10 reason=Check provider API key",
                "- Missing metric owners: 2x cost_tracking top_metric=token_cost_estimate action=Include token_cost_estimate from the generation cost tracker.",
                "- Safety risk flags: items=2; flags=privacy=2, legal=1",
                "- Provider failures: categories=auth=1, rate_limit=1; providers=gemini=1, openai=1; "
                "primary_categories=auth=1; primary_providers=openai=1",
                "- Provider failure repair: 1x provider=openai category=auth model=gpt-4.1-mini "
                "retryable=false circuit_breaker=true action=Check provider API key",
                "- Rollout blocker actions: missing_metric_rate_high source=confidence owner=cost_tracking top_metric=token_cost_estimate action=cost_tracking: Include token_cost_estimate from the generation cost tracker.",
                "- Source trend operator actions: 2x sources=ppomppu=2 action=Inspect captured evidence",
                "- Evidence fields: failure_report_path=3, html_snapshot_path=3, screenshot_path=3, error=1, trace_path=1",
                "- Top source evidence: source=ppomppu; status=timeout; count=2; "
                "open_first=failure_report_path=.tmp/failures/source_preflight/ppomppu-timeout.json",
                "- Source operator actions: 1x sources=blind=1 action=Inspect captured evidence",
                "- Recompute Scores Runtime Contract (dry-run)",
                "- Gate: status=ok; ok=true; validation_ok=true; gate_errors=0; records=2",
                "- Runtime: validation_loads_runtime_dependencies=false; validation_scoring_runs=false; scoring_dependencies_may_initialize=true",
                "- Safety: notion_reads=false; notion_writes=false; x_posts=false; manual_publish_required=true",
                "- Recompute command: `scripts/recompute_scores.py --assert-runtime-contract --input <path> --json`",
                "- Metric coverage: metric_missing=current:1/7,candidate:3/7",
            ]
        ),
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert errors == []


def test_verify_weekly_smoke_reports_missing_review_rollout_blocker_action(tmp_path):
    paths = _write_smoke_files(
        tmp_path,
        report_text="\n".join(
            [
                "# Blind-to-X Weekly Report",
                "- Review top operator actions: 3x repair_provider_access priority=10 reason=Check provider API key",
                "- Missing metric owners: 2x cost_tracking top_metric=token_cost_estimate action=Include token_cost_estimate from the generation cost tracker.",
                "- Safety risk flags: items=2; flags=privacy=2, legal=1",
                "- Provider failures: categories=auth=1, rate_limit=1; providers=gemini=1, openai=1; "
                "primary_categories=auth=1; primary_providers=openai=1",
                "- Source trend operator actions: 2x sources=ppomppu=2 action=Inspect captured evidence",
                "- Source operator actions: 1x sources=blind=1 action=Inspect captured evidence",
                "- Recompute Scores Runtime Contract (dry-run)",
                "- Gate: status=ok; ok=true; validation_ok=true; gate_errors=0; records=2",
                "- Runtime: validation_loads_runtime_dependencies=false; validation_scoring_runs=false; scoring_dependencies_may_initialize=true",
                "- Safety: notion_reads=false; notion_writes=false; x_posts=false; manual_publish_required=true",
                "- Recompute command: `scripts/recompute_scores.py --assert-runtime-contract --input <path> --json`",
                "- Metric coverage: metric_missing=current:2/10,candidate:2/10",
            ]
        ),
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_review_rollout_blocker_action_fragment:Rollout blocker actions:" in errors
    assert "missing_review_rollout_blocker_action_fragment:missing_metric_rate_high" in errors
    assert "missing_review_rollout_blocker_action_fragment:source=confidence" in errors
    assert (
        "missing_review_rollout_blocker_action_fragment:"
        "action=cost_tracking: Include token_cost_estimate from the generation cost tracker."
    ) in errors


def test_verify_weekly_smoke_reports_missing_operator_action_mismatch_fragment(tmp_path):
    paths = _write_smoke_files(tmp_path)
    trend = json.loads(paths["trend"].read_text(encoding="utf-8"))
    trend["summary"]["operator_action_mismatch_count"] = 1
    trend["summary"]["operator_action_mismatch_source_counts"] = {"ppomppu": 1}
    _write_json(paths["trend"], trend)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_mismatch_fragment:Operator action mismatches:" in errors
    assert "missing_mismatch_fragment:count=1" in errors
    assert "missing_mismatch_fragment:ppomppu=1" in errors


def test_verify_weekly_smoke_reports_missing_trend_evidence_fields(tmp_path):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report.replace(
            "- Evidence fields: failure_report_path=3, html_snapshot_path=3, screenshot_path=3, error=1, trace_path=1\n",
            "",
        ),
        encoding="utf-8",
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_trend_evidence_field_fragment:Evidence fields:" in errors
    assert "missing_trend_evidence_field_fragment:failure_report_path=3" in errors


def test_verify_weekly_smoke_reports_missing_top_source_evidence(tmp_path):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report.replace(
            "- Top source evidence: source=ppomppu; status=timeout; count=2; "
            "open_first=failure_report_path=.tmp/failures/source_preflight/ppomppu-timeout.json\n",
            "",
        ),
        encoding="utf-8",
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_trend_top_evidence_fragment:Top source evidence:" in errors
    assert (
        "missing_trend_top_evidence_fragment:"
        "open_first=failure_report_path=.tmp/failures/source_preflight/ppomppu-timeout.json"
    ) in errors


def test_verify_weekly_smoke_reports_missing_strategy_operator_action_mismatch_fragment(tmp_path):
    paths = _write_smoke_files(tmp_path)
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    strategy["summary"]["operator_action_mismatch_count"] = 1
    strategy["summary"]["operator_action_mismatch_source_counts"] = {"ppomppu": 1}
    _write_json(paths["strategy"], strategy)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_strategy_mismatch_fragment:Strategy operator action mismatches:" in errors
    assert "missing_strategy_mismatch_fragment:count=1" in errors
    assert "missing_strategy_mismatch_fragment:ppomppu=1" in errors


def test_verify_weekly_smoke_reports_missing_manual_ready_repair_queue_fragment(tmp_path):
    paths = _write_smoke_files(tmp_path)
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_commands = [
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json",
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-ppomppu.json",
    ]
    strategy["summary"]["repair_command_queue"] = [
        {"command": command, "type": "evidence_doctor", "count": 1, "sources": {"blind": 1}}
        for command in repair_commands
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "ok",
        "repair_command_count": len(repair_commands),
        "queue_count_total": len(repair_commands),
        "queue_item_count": len(repair_commands),
        "top_item_count": len(repair_commands),
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_commands[0],
        "repair_command_count": len(repair_commands),
        "repair_command_remaining_count": 1,
        "repair_commands": repair_commands,
    }
    _write_json(paths["strategy"], strategy)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_strategy_repair_queue_fragment:Repair queue:" in errors
    assert "missing_strategy_repair_queue_fragment:total=2" in errors
    assert "missing_strategy_repair_queue_fragment:listed=2" in errors
    assert "missing_strategy_repair_queue_fragment:count_total=2" in errors
    assert "missing_strategy_repair_queue_fragment:consistency=ok" in errors


def test_verify_weekly_smoke_accepts_aggregated_repair_queue_counts(tmp_path):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report + "\n- Repair queue: total=2; listed=1; count_total=2; consistency=ok; "
        "full_queue_available=true; source=manual_ready_gate.repair_commands\n"
        "- Primary repair target: type=evidence_doctor; count=2; buckets=blind|blocked=2; sources=blind=2\n",
        encoding="utf-8",
    )
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_command = (
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json"
    )
    strategy["summary"]["repair_command_queue"] = [
        {
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "sources": {"blind": 2},
            "buckets": {"blind|blocked": 2},
        }
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "ok",
        "repair_command_count": 2,
        "queue_count_total": 2,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_command,
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [repair_command],
    }
    _write_json(paths["strategy"], strategy)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert errors == []


def test_verify_weekly_smoke_reports_aggregated_repair_queue_count_mismatch(tmp_path):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report + "\n- Repair queue: total=2; listed=1; count_total=1; consistency=mismatch; "
        "full_queue_available=false; source=manual_ready_gate.repair_commands\n",
        encoding="utf-8",
    )
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_command = (
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json"
    )
    strategy["summary"]["repair_command_queue"] = [
        {"command": repair_command, "type": "evidence_doctor", "count": 1, "sources": {"blind": 1}}
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "mismatch",
        "repair_command_count": 2,
        "queue_count_total": 1,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_command,
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [repair_command],
    }
    _write_json(paths["strategy"], strategy)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "strategy_repair_command_queue_count_mismatch:expected=2,actual=1" in errors


def test_verify_weekly_smoke_reports_stale_repair_queue_consistency(tmp_path):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report + "\n- Repair queue: total=2; listed=1; count_total=2; consistency=ok; "
        "full_queue_available=true; source=manual_ready_gate.repair_commands\n"
        "- Primary repair target: type=evidence_doctor; count=2; buckets=blind|blocked=2; sources=blind=2\n",
        encoding="utf-8",
    )
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_command = (
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json"
    )
    strategy["summary"]["repair_command_queue"] = [
        {
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "sources": {"blind": 2},
            "buckets": {"blind|blocked": 2},
        }
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "mismatch",
        "repair_command_count": 2,
        "queue_count_total": 1,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_command,
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [repair_command],
    }
    _write_json(paths["strategy"], strategy)

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "strategy_repair_command_queue_consistency_total_mismatch:expected=2,actual=1" in errors
    assert "strategy_repair_command_queue_consistency_status_mismatch:expected=ok,actual=mismatch" in errors


def test_verify_weekly_smoke_reports_missing_review_safety_risk_fragment(tmp_path):
    paths = _write_smoke_files(
        tmp_path,
        report_text="\n".join(
            [
                "# Blind-to-X Weekly Report",
                "- Review top operator actions: 3x repair_provider_access priority=10 reason=Check provider API key",
                "- Source trend operator actions: 2x sources=ppomppu=2 action=Inspect captured evidence",
                "- Source operator actions: 1x sources=blind=1 action=Inspect captured evidence",
                "- Metric coverage: metric_missing=current:2/10,candidate:2/10",
            ]
        ),
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_review_safety_risk_fragment:Safety risk flags:" in errors
    assert "missing_review_safety_risk_fragment:items=2" in errors
    assert "missing_review_safety_risk_fragment:privacy=2" in errors


def test_verify_weekly_smoke_reports_missing_review_provider_failure_fragment(tmp_path):
    paths = _write_smoke_files(
        tmp_path,
        report_text="\n".join(
            [
                "# Blind-to-X Weekly Report",
                "- Review top operator actions: 3x repair_provider_access priority=10 reason=Check provider API key",
                "- Safety risk flags: items=2; flags=privacy=2, legal=1",
                "- Source trend operator actions: 2x sources=ppomppu=2 action=Inspect captured evidence",
                "- Source operator actions: 1x sources=blind=1 action=Inspect captured evidence",
                "- Metric coverage: metric_missing=current:2/10,candidate:2/10",
            ]
        ),
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_review_provider_failure_fragment:Provider failures:" in errors
    assert "missing_review_provider_failure_fragment:auth=1" in errors
    assert "missing_review_provider_failure_fragment:gemini=1" in errors
    assert "missing_review_provider_failure_fragment:primary_categories=" in errors
    assert "missing_review_provider_failure_fragment:primary_providers=" in errors
    assert "missing_review_provider_failure_fragment:openai=1" in errors


def test_verify_weekly_smoke_reports_missing_review_top_action(tmp_path):
    paths = _write_smoke_files(
        tmp_path, report_text="- Source operator actions:\nmetric_missing=current:1/10,candidate:1/10"
    )

    errors = verify_weekly_smoke(
        report_path=paths["report"],
        review_experiment_path=paths["review"],
        source_preflight_trend_path=paths["trend"],
        source_preflight_strategy_path=paths["strategy"],
    )

    assert "missing_review_fragment:Review top operator actions:" in errors
    assert "missing_trend_fragment:Source trend operator actions:" in errors


def test_verify_weekly_smoke_reports_missing_strategy_top_actions(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    _write_json(paths["strategy"], {"summary": {"operator_action_counts": {"Inspect": 1}}})

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
        ]
    )

    assert exit_code == 1
    assert capsys.readouterr().out.strip() == "weekly_smoke=fail reason=missing_strategy_top_operator_actions"


def test_verify_weekly_smoke_reports_malformed_json(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    paths["trend"].write_text("{not-json", encoding="utf-8")

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
        ]
    )

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output.startswith("weekly_smoke=fail reason=")
    assert f"json_read_failed:{paths['trend']}:JSONDecodeError" in output


def test_verify_weekly_smoke_reports_non_object_json(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    _write_json(paths["review"], [{"summary": {}}])

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
        ]
    )

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output.startswith("weekly_smoke=fail reason=")
    assert f"json_not_object:{paths['review']}" in output


def test_verify_weekly_smoke_cli_prints_stable_status(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "weekly_smoke=ok"


def test_verify_weekly_smoke_json_output_includes_paths_and_errors(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "errors": [],
        "ok": True,
        "paths": {
            "report": paths["report"].as_posix(),
            "recompute_contract": paths["recompute"].as_posix(),
            "review_experiment": paths["review"].as_posix(),
            "source_preflight_strategy": paths["strategy"].as_posix(),
            "source_preflight_trend": paths["trend"].as_posix(),
        },
        "status": "ok",
    }


def test_verify_weekly_smoke_json_output_includes_repair_queue_metadata(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report + "\n- Repair queue: total=2; listed=1; count_total=2; consistency=ok; "
        "full_queue_available=true; source=manual_ready_gate.repair_commands\n"
        "- Primary repair target: type=evidence_doctor; count=2; buckets=blind|blocked=2; sources=blind=2\n",
        encoding="utf-8",
    )
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_command = (
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json"
    )
    strategy["summary"]["repair_command_queue"] = [
        {
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "sources": {"blind": 2},
            "buckets": {"blind|blocked": 2},
        }
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "ok",
        "repair_command_count": 2,
        "queue_count_total": 2,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_command,
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [repair_command],
    }
    _write_json(paths["strategy"], strategy)

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["repair_queue"] == {
        "present": True,
        "total": 2,
        "listed": 1,
        "count_total": 2,
        "consistency": "ok",
        "full_queue_available": True,
        "queue_item_count": 1,
        "primary_repair_command_present": True,
        "primary_repair_target": {
            "present": True,
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "buckets": {"blind|blocked": 2},
            "sources": {"blind": 2},
        },
        "source": "manual_ready_gate.repair_commands",
    }


def test_verify_weekly_smoke_json_output_marks_stale_repair_queue_metadata(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    report = paths["report"].read_text(encoding="utf-8")
    paths["report"].write_text(
        report + "\n- Repair queue: total=2; listed=1; count_total=2; consistency=ok; "
        "full_queue_available=true; source=manual_ready_gate.repair_commands\n",
        encoding="utf-8",
    )
    strategy = json.loads(paths["strategy"].read_text(encoding="utf-8"))
    repair_command = (
        "py -3 scripts/source_preflight_evidence_doctor.py --input .tmp/source_browser_preflight-blind.json"
    )
    strategy["summary"]["repair_command_queue"] = [
        {"command": repair_command, "type": "evidence_doctor", "count": 2, "sources": {"blind": 2}}
    ]
    strategy["summary"]["repair_command_queue_consistency"] = {
        "status": "mismatch",
        "repair_command_count": 2,
        "queue_count_total": 1,
        "queue_item_count": 1,
        "top_item_count": 1,
    }
    strategy["manual_ready_gate"] = {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": 2,
        "reason": "Run repair commands first.",
        "primary_repair_command": repair_command,
        "repair_command_count": 2,
        "repair_command_remaining_count": 1,
        "repair_commands": [repair_command],
    }
    _write_json(paths["strategy"], strategy)

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["repair_queue"] == {
        "present": True,
        "total": 2,
        "listed": 1,
        "count_total": 2,
        "consistency": "mismatch",
        "full_queue_available": False,
        "queue_item_count": 1,
        "primary_repair_command_present": True,
        "primary_repair_target": {
            "present": True,
            "command": repair_command,
            "type": "evidence_doctor",
            "count": 2,
            "buckets": {},
            "sources": {"blind": 2},
        },
        "source": "manual_ready_gate.repair_commands",
    }
    assert "strategy_repair_command_queue_consistency_total_mismatch:expected=2,actual=1" in payload["errors"]


def test_verify_weekly_smoke_json_output_preserves_failure_details(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    _write_json(paths["strategy"], {"summary": {}})

    exit_code = main(
        [
            "--report",
            str(paths["report"]),
            "--review-experiment",
            str(paths["review"]),
            "--source-preflight-trend",
            str(paths["trend"]),
            "--source-preflight-strategy",
            str(paths["strategy"]),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "fail"
    assert payload["errors"] == ["missing_strategy_top_operator_actions"]
    assert payload["error_categories"] == ["report"]
    assert payload["paths"]["source_preflight_strategy"] == paths["strategy"].as_posix()


def test_verify_weekly_smoke_manifest_json_output_uses_manifest_paths(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["manifest"] == manifest_path.as_posix()
    assert payload["paths"] == {
        "report": paths["report"].as_posix(),
        "recompute_contract": paths["recompute"].as_posix(),
        "review_experiment": paths["review"].as_posix(),
        "source_preflight_strategy": paths["strategy"].as_posix(),
        "source_preflight_trend": paths["trend"].as_posix(),
    }


def test_verify_weekly_smoke_manifest_validates_expected_repair_queue(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    expected_repair_queue = _add_repair_queue_fixture(paths)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_repair_queue"] = expected_repair_queue
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["errors"] == []
    assert payload["repair_queue"] == expected_repair_queue
    assert payload["manifest_repair_queue"] == _expected_manifest_repair_queue_payload(
        expected_repair_queue,
        paths["strategy"],
        ok=True,
        matched_key_count=len(expected_repair_queue),
        mismatched_keys=[],
    )


def test_verify_weekly_smoke_manifest_rejects_stale_expected_repair_queue(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    expected_repair_queue = _add_repair_queue_fixture(paths)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_repair_queue"] = {**expected_repair_queue, "total": 3}
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert payload["errors"] == ["manifest_expected_repair_queue_mismatch:total=expected_3,actual_2"]
    assert payload["repair_queue"] == expected_repair_queue
    assert payload["manifest_repair_queue"] == _expected_manifest_repair_queue_payload(
        manifest["expected_repair_queue"],
        paths["strategy"],
        ok=False,
        matched_key_count=len(expected_repair_queue) - 1,
        mismatched_keys=["total"],
    )


def test_verify_weekly_smoke_manifest_can_verify_review_summary_stdout(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["errors"] == []
    assert payload["review_summary"] == {
        "ok": True,
        "status": "ok",
        "diagnosis": "ok",
        "failure_reasons": [],
        "executed": True,
        "review_records": paths["review_records"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 0,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }
    assert "repair_queue" not in payload
    assert "manifest_repair_queue" not in payload


def test_manifest_review_summary_fragments_include_primary_provider_axis():
    assert "primary_provider_failure_categories=auth=1" in EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS
    assert "primary_provider_failure_providers=openai=1" in EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS


def test_verify_weekly_smoke_manifest_review_summary_reports_missing_stdout_fragment(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_review_stdout_fragments"] = [
        *manifest["expected_review_stdout_fragments"],
        "not-present-in-review-summary",
    ]
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["review_summary"]
    assert "missing_review_summary_stdout_fragment:not-present-in-review-summary" in payload["errors"]
    assert payload["review_summary"] == {
        "ok": False,
        "status": "fail",
        "diagnosis": "stdout_drift",
        "failure_reasons": ["stdout_drift"],
        "executed": True,
        "review_records": paths["review_records"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS) + 1,
        "matched_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 1,
        "missing_stdout_fragments": ["not-present-in-review-summary"],
        "missing_input": False,
        "stdout_drift": True,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 0,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_verify_weekly_smoke_manifest_review_summary_text_mode_reports_review_summary_reason(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_review_stdout_fragments"] = [
        *manifest["expected_review_stdout_fragments"],
        "not-present-in-review-summary",
    ]
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output.startswith("weekly_smoke=fail reason=")
    assert "missing_review_summary_stdout_fragment:not-present-in-review-summary" in output
    assert "category=manifest" not in output


def test_verify_weekly_smoke_manifest_review_summary_reports_manifest_contract_error(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_review_stdout_fragments"] = [
        *manifest["expected_review_stdout_fragments"],
        42,
    ]
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert payload["errors"] == ["manifest_invalid_expected_review_stdout_fragment:42"]
    assert payload["review_summary"] == {
        "ok": False,
        "status": "fail",
        "diagnosis": "manifest_contract",
        "failure_reasons": ["manifest_contract"],
        "executed": False,
        "review_records": paths["review_records"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": True,
        "returncode": None,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_verify_weekly_smoke_manifest_review_summary_text_mode_reports_manifest_category(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_review_stdout_fragments"] = [
        *manifest["expected_review_stdout_fragments"],
        42,
    ]
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output.startswith("weekly_smoke=fail category=manifest reason=")
    assert "manifest_invalid_expected_review_stdout_fragment:42" in output
    assert "category=review_summary" not in output


def test_verify_weekly_smoke_manifest_review_summary_reports_missing_input(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    missing_review_records_path = tmp_path / "missing_review_queue_report_sample.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["paths"]["review_records"] = missing_review_records_path.as_posix()
    manifest["commands"]["review_summary"] = (
        "py -3 scripts/review_experiment_dry_run.py "
        f"--input-mode review-records --input {missing_review_records_path.as_posix()} "
        "--min-items 1 --max-missing-rate 0.25 --summary-only"
    )
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["review_summary"]
    assert f"review_summary_missing_input:{missing_review_records_path}" in payload["errors"]
    assert payload["review_summary"] == {
        "ok": False,
        "status": "fail",
        "diagnosis": "missing_input",
        "failure_reasons": ["missing_input"],
        "executed": False,
        "review_records": missing_review_records_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": True,
        "stdout_drift": False,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": None,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_verify_weekly_smoke_manifest_review_summary_text_mode_reports_missing_input_reason(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    missing_review_records_path = tmp_path / "missing_review_queue_report_sample.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["paths"]["review_records"] = missing_review_records_path.as_posix()
    manifest["commands"]["review_summary"] = (
        "py -3 scripts/review_experiment_dry_run.py "
        f"--input-mode review-records --input {missing_review_records_path.as_posix()} "
        "--min-items 1 --max-missing-rate 0.25 --summary-only"
    )
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output.startswith("weekly_smoke=fail reason=")
    assert f"review_summary_missing_input:{missing_review_records_path}" in output
    assert "category=manifest" not in output


def test_verify_weekly_smoke_manifest_review_summary_reports_malformed_input_nonzero_and_stdout_drift(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    paths["review_records"].write_text("{not-json", encoding="utf-8")
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary", "--json"])

    payload = json.loads(capsys.readouterr().out)
    expected_missing_stdout_errors = [
        f"missing_review_summary_stdout_fragment:{fragment}" for fragment in EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS
    ]
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["review_summary"]
    assert payload["errors"] == ["review_summary_exit_code:1", *expected_missing_stdout_errors]
    review_summary = payload["review_summary"]
    child_error_tail = review_summary.pop("child_error_tail")
    assert "JSONDecodeError" in child_error_tail
    assert len(child_error_tail) <= REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS
    assert review_summary.pop("child_error_tail_source") == "stderr"
    assert isinstance(review_summary.pop("child_error_tail_truncated"), bool)
    assert review_summary == {
        "ok": False,
        "status": "fail",
        "diagnosis": "nonzero_exit",
        "failure_reasons": ["nonzero_exit", "stdout_drift"],
        "executed": True,
        "review_records": paths["review_records"].as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "missing_stdout_fragments": EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
        "missing_input": False,
        "stdout_drift": True,
        "timeout": False,
        "nonzero_exit": True,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 1,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_verify_weekly_smoke_manifest_review_summary_text_mode_reports_nonzero_reason_without_child_tail(
    tmp_path, capsys
):
    paths = _write_smoke_files(tmp_path)
    paths["review_records"].write_text("{not-json", encoding="utf-8")
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output.startswith("weekly_smoke=fail reason=")
    assert "review_summary_exit_code:1" in output
    assert "missing_review_summary_stdout_fragment:" in output
    assert "JSONDecodeError" not in output
    assert "child_error_tail" not in output
    assert "category=manifest" not in output


def test_verify_weekly_smoke_manifest_review_summary_text_mode_reports_timeout_reason_without_child_tail(
    tmp_path, capsys, monkeypatch
):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=kwargs["timeout"],
            output=b"stdout fallback detail",
            stderr=b"\n  timeout stderr detail  \n",
        )

    monkeypatch.setattr("scripts.verify_weekly_smoke.subprocess.run", raise_timeout)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output == "weekly_smoke=fail reason=review_summary_timeout"
    assert "timeout stderr detail" not in output
    assert "child_error_tail" not in output
    assert "category=manifest" not in output


def test_run_review_summary_stdout_verification_reports_malformed_input_nonzero_and_stdout_drift(tmp_path):
    review_records_path = tmp_path / "review_queue_report_sample.json"
    review_records_path.write_text("{not-json", encoding="utf-8")
    expected_fragments = ["missing_metric_rate=0.7"]

    errors, payload = run_review_summary_stdout_verification(
        review_records_path=review_records_path,
        expected_fragments=expected_fragments,
    )

    assert errors == [
        "review_summary_exit_code:1",
        "missing_review_summary_stdout_fragment:missing_metric_rate=0.7",
    ]
    child_error_tail = payload.pop("child_error_tail")
    assert "JSONDecodeError" in child_error_tail
    assert len(child_error_tail) <= REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS
    assert payload.pop("child_error_tail_source") == "stderr"
    assert isinstance(payload.pop("child_error_tail_truncated"), bool)
    assert payload == {
        "ok": False,
        "status": "fail",
        "diagnosis": "nonzero_exit",
        "failure_reasons": ["nonzero_exit", "stdout_drift"],
        "executed": True,
        "review_records": review_records_path.as_posix(),
        "expected_stdout_fragment_count": 1,
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 1,
        "missing_stdout_fragments": ["missing_metric_rate=0.7"],
        "missing_input": False,
        "stdout_drift": True,
        "timeout": False,
        "nonzero_exit": True,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 1,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_run_review_summary_stdout_verification_diagnosis_follows_first_failure_reason(tmp_path, monkeypatch):
    review_records_path = tmp_path / "review_queue_report_sample.json"
    review_records_path.write_text("[]", encoding="utf-8")
    expected_fragments = [
        "missing_metric_rate=0.7",
        "top_missing_metric=latency_ms",
    ]

    def return_partial_nonzero_summary(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="missing_metric_rate=0.7\n",
            stderr="dry-run child failed after partial summary\n",
        )

    monkeypatch.setattr("scripts.verify_weekly_smoke.subprocess.run", return_partial_nonzero_summary)

    errors, payload = run_review_summary_stdout_verification(
        review_records_path=review_records_path,
        expected_fragments=expected_fragments,
    )

    assert errors == [
        "review_summary_exit_code:1",
        "missing_review_summary_stdout_fragment:top_missing_metric=latency_ms",
    ]
    child_error_tail = payload.pop("child_error_tail")
    assert child_error_tail == "dry-run child failed after partial summary"
    assert payload.pop("child_error_tail_source") == "stderr"
    assert payload.pop("child_error_tail_truncated") is False
    assert payload["failure_reasons"] == ["nonzero_exit", "stdout_drift"]
    assert payload["diagnosis"] == payload["failure_reasons"][0]
    assert payload["diagnosis"] == "nonzero_exit"
    assert payload["matched_stdout_fragment_count"] == 1
    assert payload["missing_stdout_fragments"] == ["top_missing_metric=latency_ms"]


def test_bounded_review_summary_child_error_tail_prefers_stderr():
    tail, source, truncated = _bounded_review_summary_child_error_tail(
        stderr="\n  stderr traceback tail  \n",
        stdout="stdout fallback",
    )

    assert tail == "stderr traceback tail"
    assert source == "stderr"
    assert truncated is False


def test_bounded_review_summary_child_error_tail_decodes_timeout_bytes():
    tail, source, truncated = _bounded_review_summary_child_error_tail(
        stderr=b"\n  byte stderr detail \xff  \n",
        stdout=b"stdout fallback",
    )

    assert tail == "byte stderr detail \ufffd"
    assert source == "stderr"
    assert truncated is False


def test_bounded_review_summary_child_error_tail_falls_back_to_stdout_when_stderr_is_blank():
    tail, source, truncated = _bounded_review_summary_child_error_tail(
        stderr=" \n\t ",
        stdout="\n  stdout failure detail  \n",
    )

    assert tail == "stdout failure detail"
    assert source == "stdout"
    assert truncated is False


def test_bounded_review_summary_child_error_tail_truncates_from_the_end():
    stderr = "prefix-" + ("x" * (REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS + 5))

    tail, source, truncated = _bounded_review_summary_child_error_tail(stderr=stderr, stdout=None)

    assert tail == stderr[-REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS:]
    assert len(tail) == REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS
    assert source == "stderr"
    assert truncated is True


def test_bounded_review_summary_child_error_tail_returns_empty_metadata_for_blank_output():
    tail, source, truncated = _bounded_review_summary_child_error_tail(stderr=" \n", stdout="\t ")

    assert tail is None
    assert source is None
    assert truncated is False


def test_run_review_summary_stdout_verification_reports_timeout_child_error_tail(tmp_path, monkeypatch):
    review_records_path = tmp_path / "review_queue_report_sample.json"
    review_records_path.write_text("[]", encoding="utf-8")

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=kwargs["timeout"],
            output=b"stdout fallback detail",
            stderr=b"\n  timeout stderr detail  \n",
        )

    monkeypatch.setattr("scripts.verify_weekly_smoke.subprocess.run", raise_timeout)

    errors, payload = run_review_summary_stdout_verification(
        review_records_path=review_records_path,
        expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
    )

    assert errors == ["review_summary_timeout"]
    child_error_tail = payload.pop("child_error_tail")
    assert child_error_tail == "timeout stderr detail"
    assert payload.pop("child_error_tail_source") == "stderr"
    assert payload.pop("child_error_tail_truncated") is False
    assert payload == {
        "ok": False,
        "status": "fail",
        "diagnosis": "timeout",
        "failure_reasons": ["timeout"],
        "executed": True,
        "review_records": review_records_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": True,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": None,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_run_review_summary_stdout_verification_reports_run_failed_exception_tail(tmp_path, monkeypatch):
    review_records_path = tmp_path / "review_queue_report_sample.json"
    review_records_path.write_text("[]", encoding="utf-8")

    def raise_os_error(*args, **kwargs):
        raise OSError("CreateProcess failed for review summary")

    monkeypatch.setattr("scripts.verify_weekly_smoke.subprocess.run", raise_os_error)

    errors, payload = run_review_summary_stdout_verification(
        review_records_path=review_records_path,
        expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
    )

    assert errors == ["review_summary_run_failed:OSError"]
    child_error_tail = payload.pop("child_error_tail")
    assert child_error_tail == "OSError: CreateProcess failed for review summary"
    assert payload.pop("child_error_tail_source") == "exception"
    assert payload.pop("child_error_tail_truncated") is False
    assert payload == {
        "ok": False,
        "status": "fail",
        "diagnosis": "run_failed",
        "failure_reasons": ["run_failed"],
        "executed": False,
        "review_records": review_records_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": False,
        "nonzero_exit": False,
        "run_failed": True,
        "manifest_contract_error": False,
        "returncode": None,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_verify_weekly_smoke_manifest_review_summary_text_mode_reports_run_failed_reason_without_child_tail(
    tmp_path, capsys, monkeypatch
):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)

    def raise_os_error(*args, **kwargs):
        raise OSError("CreateProcess failed for review summary")

    monkeypatch.setattr("scripts.verify_weekly_smoke.subprocess.run", raise_os_error)

    exit_code = main(["--manifest", str(manifest_path), "--verify-review-summary"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 1
    assert output == "weekly_smoke=fail reason=review_summary_run_failed:OSError"
    assert "CreateProcess failed for review summary" not in output
    assert "child_error_tail" not in output
    assert "category=manifest" not in output


def test_build_review_summary_payload_reports_timeout(tmp_path):
    review_records_path = tmp_path / "review_queue_report_sample.json"

    payload = build_review_summary_verification_payload(
        review_records_path=review_records_path,
        expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
        errors=["review_summary_timeout"],
        executed=True,
        returncode=None,
    )

    assert payload == {
        "ok": False,
        "status": "fail",
        "diagnosis": "timeout",
        "failure_reasons": ["timeout"],
        "executed": True,
        "review_records": review_records_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": True,
        "nonzero_exit": False,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": None,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_build_review_summary_payload_reports_nonzero_exit(tmp_path):
    review_records_path = tmp_path / "review_queue_report_sample.json"

    payload = build_review_summary_verification_payload(
        review_records_path=review_records_path,
        expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
        errors=["review_summary_exit_code:2"],
        executed=True,
        returncode=2,
    )

    assert payload == {
        "ok": False,
        "status": "fail",
        "diagnosis": "nonzero_exit",
        "failure_reasons": ["nonzero_exit"],
        "executed": True,
        "review_records": review_records_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": len(EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "timeout": False,
        "nonzero_exit": True,
        "run_failed": False,
        "manifest_contract_error": False,
        "returncode": 2,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }


def test_build_review_summary_payload_prefers_nonzero_exit_over_stdout_drift(tmp_path):
    review_records_path = tmp_path / "review_queue_report_sample.json"
    missing_fragment_error = "missing_review_summary_stdout_fragment:missing_metric_rate=0.7"

    payload = build_review_summary_verification_payload(
        review_records_path=review_records_path,
        expected_fragments=EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS,
        errors=["review_summary_exit_code:1", missing_fragment_error],
        executed=True,
        returncode=1,
    )

    assert payload["diagnosis"] == "nonzero_exit"
    assert payload["failure_reasons"] == ["nonzero_exit", "stdout_drift"]
    assert payload["nonzero_exit"] is True
    assert payload["stdout_drift"] is True
    assert payload["missing_stdout_fragments"] == ["missing_metric_rate=0.7"]


def test_run_strategy_summary_stdout_verification_reports_ok(tmp_path):
    strategy_path = tmp_path / "source_preflight_strategy_simulation.json"
    _write_json(strategy_path, source_preflight_strategy_payload())

    errors, payload = run_strategy_summary_stdout_verification(
        source_preflight_strategy_path=strategy_path,
        expected_fragments=EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS,
    )

    assert errors == []
    assert payload == {
        "ok": True,
        "status": "ok",
        "diagnosis": "ok",
        "failure_reasons": [],
        "executed": True,
        "source_preflight_strategy": strategy_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": len(EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS),
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "format_failed": False,
        "manifest_contract_error": False,
    }


def test_run_strategy_summary_stdout_verification_reports_stdout_drift(tmp_path):
    strategy_path = tmp_path / "source_preflight_strategy_simulation.json"
    _write_json(strategy_path, source_preflight_strategy_payload())

    errors, payload = run_strategy_summary_stdout_verification(
        source_preflight_strategy_path=strategy_path,
        expected_fragments=[*EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS, "not-present-in-strategy-summary"],
    )

    assert errors == ["missing_strategy_stdout_fragment:not-present-in-strategy-summary"]
    assert payload["diagnosis"] == "stdout_drift"
    assert payload["failure_reasons"] == ["stdout_drift"]
    assert payload["expected_stdout_fragment_count"] == len(EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS) + 1
    assert payload["matched_stdout_fragment_count"] == len(EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS)
    assert payload["missing_stdout_fragments"] == ["not-present-in-strategy-summary"]


def test_build_strategy_summary_payload_reports_manifest_contract_error(tmp_path):
    strategy_path = tmp_path / "source_preflight_strategy_simulation.json"

    payload = build_strategy_summary_verification_payload(
        source_preflight_strategy_path=strategy_path,
        expected_fragments=EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS,
        errors=["manifest_invalid_expected_strategy_stdout_fragment:42"],
        executed=False,
    )

    assert payload == {
        "ok": False,
        "status": "fail",
        "diagnosis": "manifest_contract",
        "failure_reasons": ["manifest_contract"],
        "executed": False,
        "source_preflight_strategy": strategy_path.as_posix(),
        "expected_stdout_fragment_count": len(EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS),
        "matched_stdout_fragment_count": 0,
        "missing_stdout_fragment_count": 0,
        "missing_stdout_fragments": [],
        "missing_input": False,
        "stdout_drift": False,
        "format_failed": False,
        "manifest_contract_error": True,
    }


@pytest.mark.parametrize(
    ("errors", "expected_reasons"),
    [
        (
            [
                "missing_review_summary_stdout_fragment:missing_metric_rate=0.7",
                "review_summary_exit_code:1",
                "review_summary_run_failed:OSError",
                "review_summary_timeout",
                "review_summary_missing_input:.tmp/missing_review_queue_report_sample.json",
            ],
            ["missing_input", "timeout", "run_failed", "nonzero_exit", "stdout_drift"],
        ),
        (
            [
                "missing_review_summary_stdout_fragment:missing_metric_rate=0.7",
                "review_summary_exit_code:1",
            ],
            ["nonzero_exit", "stdout_drift"],
        ),
        (
            [
                "review_summary_timeout",
                "manifest_missing_expected_review_stdout_fragment:*",
                "review_summary_missing_input:.tmp/missing_review_queue_report_sample.json",
            ],
            ["missing_input", "manifest_contract", "timeout"],
        ),
    ],
)
def test_review_summary_failure_reasons_follow_triage_priority(errors, expected_reasons):
    assert _review_summary_failure_reasons(errors) == expected_reasons


def test_verify_weekly_smoke_manifest_reports_missing_paths(tmp_path, capsys):
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_json(manifest_path, {"paths": {}, "expected_outputs": {}})

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert "manifest_missing_path:report" in payload["errors"]
    assert "manifest_missing_path:review_experiment" in payload["errors"]


def test_verify_weekly_smoke_manifest_rejects_missing_command_contract(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("commands")
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert "manifest_missing_commands" in payload["errors"]


def test_verify_weekly_smoke_manifest_rejects_stale_manifest_verifier_command(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["commands"]["verify_manifest"] = f"py -3 scripts/verify_weekly_smoke.py --manifest {manifest_path}"
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert "manifest_command_missing_fragment:verify_manifest:--verify-review-summary" in payload["errors"]


def test_verify_weekly_smoke_manifest_rejects_stale_strategy_summary_verifier_command(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_strategy_stdout_fragments"] = EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS
    manifest["commands"]["verify_manifest"] = (
        f"py -3 scripts/verify_weekly_smoke.py --manifest {manifest_path} --verify-review-summary"
    )
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert "manifest_command_missing_fragment:verify_manifest:--verify-strategy-summary" in payload["errors"]


def test_verify_weekly_smoke_manifest_rejects_stale_write_inputs_manifest_flag(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["commands"]["write_inputs"] = (
        f"py -3 scripts/write_weekly_smoke_inputs.py --output-dir {tmp_path.as_posix()}"
    )
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert (
        f"manifest_command_missing_fragment:write_inputs:--manifest-output {manifest_path.as_posix()}"
        in payload["errors"]
    )


def test_verify_weekly_smoke_manifest_accepts_quoted_copy_ready_paths(tmp_path):
    output_dir = tmp_path / "weekly smoke"
    output_dir.mkdir()
    paths = _write_smoke_files(output_dir)
    manifest_path = output_dir / "weekly smoke manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest"] = manifest_path.as_posix()
    manifest["commands"]["write_inputs"] = (
        "py -3 scripts/write_weekly_smoke_inputs.py "
        f'--output-dir "{output_dir.as_posix()}" --manifest-output "{manifest_path.as_posix()}"'
    )
    manifest["commands"]["review_summary"] = (
        "py -3 scripts/review_experiment_dry_run.py "
        f'--input-mode review-records --input "{paths["review_records"].as_posix()}" '
        "--min-items 1 --max-missing-rate 0.25 --summary-only"
    )
    manifest["commands"]["verify_manifest"] = (
        f'py -3 scripts/verify_weekly_smoke.py --manifest "{manifest_path.as_posix()}" --verify-review-summary'
    )

    assert validate_manifest_contract(manifest) == []


def test_verify_weekly_smoke_manifest_rejects_self_check_without_writer_flag(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["self_check"] = {"errors": [], "ok": True, "status": "ok"}
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert "manifest_command_missing_fragment:write_inputs:--self-check" in payload["errors"]


def test_verify_weekly_smoke_manifest_rejects_unsafe_safety_contract(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    safety_contract = dict(EXPECTED_MANIFEST_SAFETY_CONTRACT)
    safety_contract["notion_writes"] = True
    _write_manifest(manifest_path, paths, safety_contract=safety_contract)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert "manifest_safety_mismatch:notion_writes=expected_false,actual_True" in payload["errors"]


def test_verify_weekly_smoke_manifest_text_output_includes_manifest_category(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    safety_contract = dict(EXPECTED_MANIFEST_SAFETY_CONTRACT)
    safety_contract["notion_writes"] = True
    _write_manifest(manifest_path, paths, safety_contract=safety_contract)

    exit_code = main(["--manifest", str(manifest_path)])

    assert exit_code == 1
    assert capsys.readouterr().out.strip() == (
        "weekly_smoke=fail category=manifest reason=manifest_safety_mismatch:notion_writes=expected_false,actual_True"
    )


def test_verify_weekly_smoke_manifest_accepts_utf8_sig_json(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    safety_contract = dict(EXPECTED_MANIFEST_SAFETY_CONTRACT)
    safety_contract["notion_writes"] = True
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["safety_contract"] = safety_contract
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8-sig")

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["error_categories"] == ["manifest"]
    assert payload["errors"] == ["manifest_safety_mismatch:notion_writes=expected_false,actual_True"]


def test_verify_weekly_smoke_manifest_rejects_stale_profile_and_fragments(tmp_path, capsys):
    paths = _write_smoke_files(tmp_path)
    manifest_path = tmp_path / "weekly_smoke_manifest.json"
    _write_manifest(manifest_path, paths)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 0
    manifest["profile"] = "old_weekly_smoke"
    manifest["expected_report_fragments"] = ["Review top operator actions:"]
    manifest["expected_review_stdout_fragments"] = ["missing_metric_rate=0.7"]
    _write_json(manifest_path, manifest)

    exit_code = main(["--manifest", str(manifest_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error_categories"] == ["manifest"]
    assert "manifest_schema_version_mismatch:expected=1,actual=0" in payload["errors"]
    assert (
        "manifest_profile_mismatch:expected=weekly_report_ab_source_preflight,actual=old_weekly_smoke"
        in payload["errors"]
    )
    assert "manifest_missing_expected_fragment:Source operator actions:" in payload["errors"]
    assert (
        "manifest_missing_expected_review_stdout_fragment:rollout_blocker_codes=missing_metric_rate_high,operator_action_noise_high"
        in payload["errors"]
    )
