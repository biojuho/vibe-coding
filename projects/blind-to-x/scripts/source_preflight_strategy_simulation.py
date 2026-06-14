from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BTX_ROOT = Path(__file__).resolve().parents[1]
if str(BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(BTX_ROOT))

from scripts.source_preflight_trend_report import (  # noqa: E402
    DEFAULT_GLOB,
    DEFAULT_INPUT_PATH,
    build_trend_payload,
)

OBJECTIVE_METRICS = (
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
)

DEFAULT_OUTPUT = Path(".tmp/source_preflight_strategy_simulation.json")
GATE_BLOCKED_EXIT = 2


def _resolve_path(value: str | Path, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def _resolve_explicit_input_path(value: str | Path, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    try:
        path.resolve(strict=False).relative_to(base_dir)
    except ValueError:
        return base_dir / path
    return path


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _input_paths(args: argparse.Namespace, base_dir: Path) -> list[Path]:
    explicit_input_requested = bool(args.input or args.input_dir)
    paths = [_resolve_explicit_input_path(path, base_dir) for path in (args.input or [])]
    max_files = max(0, int(args.max_files or 0))
    for input_dir in args.input_dir or []:
        resolved_dir = _resolve_explicit_input_path(input_dir, base_dir)
        if not resolved_dir.exists() or not resolved_dir.is_dir():
            paths.append(resolved_dir)
            continue
        matches = sorted(
            resolved_dir.glob(args.glob),
            key=lambda path: (path.stat().st_mtime if path.exists() else 0.0, str(path)),
            reverse=True,
        )
        paths.extend(matches[:max_files])
    if not paths and not explicit_input_requested:
        paths.append(_resolve_path(DEFAULT_INPUT_PATH, base_dir))
    return _unique_paths(paths)


def _safety_contract() -> dict[str, bool]:
    return {
        "read_only": True,
        "browser_launches": False,
        "notion_writes": False,
        "x_posts": False,
        "auto_publish_default": False,
        "manual_publish_required": True,
    }


def _gate_counts(summary: dict[str, Any]) -> Counter[str]:
    counts = summary.get("evidence_gate_status_counts")
    counter: Counter[str] = Counter()
    if isinstance(counts, dict):
        for key, value in counts.items():
            try:
                counter[str(key)] += int(value or 0)
            except (TypeError, ValueError):
                continue
    return counter


def _operator_recommendation(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("operator_recommendation")
    return value if isinstance(value, dict) else {}


def _current_strategy_signals(summary: dict[str, Any], gate_counts: Counter[str]) -> dict[str, Any]:
    problem_count = int(summary.get("problem_action_count") or 0)
    error_count = int(summary.get("error_count") or 0)
    warning_count = int(summary.get("warning_count") or 0)
    repair_command_count = int(summary.get("repair_command_count") or 0)
    fallback_only_count = int(gate_counts.get("fallback_only", 0))
    fix_evidence_count = int(gate_counts.get("fix_evidence_first", 0))
    strategy_ready_count = int(gate_counts.get("strategy_review_ready", 0))
    unsafe_strategy_change_count = fallback_only_count + fix_evidence_count + repair_command_count
    safety_flags = []
    if unsafe_strategy_change_count:
        safety_flags.append("ungated_strategy_change")
    if error_count:
        safety_flags.append("invalid_evidence")
    if warning_count:
        safety_flags.append("incomplete_evidence")
    if repair_command_count:
        safety_flags.append("repair_command_debt")
    score = max(
        0,
        50
        + (0 if problem_count else 20)
        - unsafe_strategy_change_count * 8
        - fix_evidence_count * 6
        - repair_command_count * 3
        - error_count * 10
        - warning_count * 4
        + strategy_ready_count * 2,
    )
    return {
        "success": bool(problem_count == 0 and error_count == 0 and warning_count == 0),
        "latency_ms": None,
        "provider": "source_preflight",
        "model": "current_top_source_action",
        "token_cost_estimate": 0.0,
        "final_rank_score": round(float(score), 2),
        "draft_quality_score": None,
        "safety_risk_flags": safety_flags,
        "duplicate_or_near_duplicate": False,
        "operator_action_required": bool(problem_count),
        "problem_action_count": problem_count,
        "strategy_review_count": strategy_ready_count,
        "fallback_only_count": fallback_only_count,
        "evidence_repair_count": fix_evidence_count,
        "repair_command_count": repair_command_count,
        "unsafe_strategy_change_count": unsafe_strategy_change_count,
    }


def _candidate_strategy_signals(summary: dict[str, Any], gate_counts: Counter[str]) -> dict[str, Any]:
    recommendation = _operator_recommendation(summary)
    action = str(recommendation.get("action") or "no_source_action")
    problem_count = int(summary.get("problem_action_count") or 0)
    error_count = int(summary.get("error_count") or 0)
    warning_count = int(summary.get("warning_count") or 0)
    repair_command_count = int(summary.get("repair_command_count") or 0)
    fallback_only_count = int(gate_counts.get("fallback_only", 0))
    fix_evidence_count = int(gate_counts.get("fix_evidence_first", 0))
    strategy_ready_count = int(gate_counts.get("strategy_review_ready", 0))
    safety_flags = []
    if action == "repair_evidence":
        safety_flags.append("evidence_repair_required")
    if error_count:
        safety_flags.append("invalid_evidence")
    if warning_count:
        safety_flags.append("incomplete_evidence")
    if repair_command_count:
        safety_flags.append("repair_command_debt")
    score = max(
        0,
        50
        + (12 if action in {"review_source_strategy", "split_fallback_and_strategy_review"} else 0)
        + (10 if problem_count == 0 else 0)
        + strategy_ready_count * 4
        + fallback_only_count * 2
        - fix_evidence_count * 5
        - repair_command_count * 4
        - error_count * 10
        - warning_count * 3,
    )
    return {
        "success": bool(
            error_count == 0 and warning_count == 0 and repair_command_count == 0 and action != "repair_evidence"
        ),
        "latency_ms": None,
        "provider": "source_preflight",
        "model": "gate_directed_operator_recommendation",
        "token_cost_estimate": 0.0,
        "final_rank_score": round(float(score), 2),
        "draft_quality_score": None,
        "safety_risk_flags": safety_flags,
        "duplicate_or_near_duplicate": False,
        "operator_action_required": bool(action != "no_source_action"),
        "recommendation_action": action,
        "strategy_review_count": strategy_ready_count,
        "fallback_only_count": fallback_only_count,
        "evidence_repair_count": fix_evidence_count,
        "repair_command_count": repair_command_count,
        "unsafe_strategy_change_count": 0,
    }


def _missing_metrics(signals: dict[str, Any]) -> list[str]:
    missing = []
    for metric in OBJECTIVE_METRICS:
        value = signals.get(metric)
        if metric == "safety_risk_flags" and value == []:
            continue
        if value in (None, "", [], {}):
            missing.append(metric)
    return missing


def _metric_coverage(current: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    current_missing = current["missing_required_metrics"]
    candidate_missing = candidate["missing_required_metrics"]
    metric_total = len(OBJECTIVE_METRICS)
    current_missing_count = len(current_missing)
    candidate_missing_count = len(candidate_missing)
    return {
        "metric_total": metric_total,
        "metric_missing": (
            f"current:{current_missing_count}/{metric_total},candidate:{candidate_missing_count}/{metric_total}"
        ),
        "missing_metric_counts": {
            "current": current_missing_count,
            "candidate": candidate_missing_count,
        },
        "missing_metric_names": {
            "current": current_missing,
            "candidate": candidate_missing,
        },
        "measurement_scope": {
            "mode": "local_preflight_evidence",
            "external_llm_calls": False,
            "costed_generation": False,
            "not_measured_metrics": ["latency_ms", "draft_quality_score"],
            "deterministic_defaults": {
                "token_cost_estimate": 0.0,
                "duplicate_or_near_duplicate": False,
            },
        },
    }


def _variant(name: str, signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "signals": signals,
        "missing_required_metrics": _missing_metrics(signals),
    }


def _compare(current: dict[str, Any], candidate: dict[str, Any], *, problem_count: int) -> dict[str, Any]:
    current_signals = current["signals"]
    candidate_signals = candidate["signals"]
    score_delta = round(float(candidate_signals["final_rank_score"]) - float(current_signals["final_rank_score"]), 2)
    unsafe_strategy_change_delta = int(candidate_signals["unsafe_strategy_change_count"]) - int(
        current_signals["unsafe_strategy_change_count"]
    )
    strategy_review_delta = int(candidate_signals["strategy_review_count"]) - int(
        current_signals["strategy_review_count"]
    )
    repair_command_count = int(candidate_signals.get("repair_command_count") or 0)
    if repair_command_count:
        recommendation = "repair_evidence_first"
    elif problem_count == 0:
        recommendation = "insufficient_evidence"
    elif unsafe_strategy_change_delta < 0 and score_delta >= 0:
        recommendation = "adopt_candidate"
    elif score_delta < -5:
        recommendation = "keep_current"
    else:
        recommendation = "insufficient_evidence"
    return {
        "recommendation": recommendation,
        "score_delta": score_delta,
        "unsafe_strategy_change_delta": unsafe_strategy_change_delta,
        "strategy_review_delta": strategy_review_delta,
        "operator_action_required_delta": int(candidate_signals["operator_action_required"])
        - int(current_signals["operator_action_required"]),
    }


def _rollout_gate(summary: dict[str, Any], comparison: dict[str, Any], gate_counts: Counter[str]) -> dict[str, Any]:
    error_count = int(summary.get("error_count") or 0)
    warning_count = int(summary.get("warning_count") or 0)
    problem_count = int(summary.get("problem_action_count") or 0)
    repair_command_count = int(summary.get("repair_command_count") or 0)
    fallback_only_count = int(gate_counts.get("fallback_only", 0))
    fix_evidence_count = int(gate_counts.get("fix_evidence_first", 0))
    strategy_ready_count = int(gate_counts.get("strategy_review_ready", 0))
    blocked_by: list[str] = []
    if error_count:
        blocked_by.append("invalid_evidence")
    if warning_count or fix_evidence_count:
        blocked_by.append("repair_evidence_first")
    if repair_command_count:
        blocked_by.append("repair_command_debt")
    if fallback_only_count:
        blocked_by.append("fallback_only_sources_present")
    if problem_count == 0:
        blocked_by.append("no_problem_actions")

    ready_for_manual_strategy_review = (
        problem_count > 0
        and strategy_ready_count > 0
        and error_count == 0
        and warning_count == 0
        and fix_evidence_count == 0
        and repair_command_count == 0
    )
    if problem_count == 0:
        status = "no_problem_actions"
        operator_action = "No source-preflight strategy action is needed from this dry-run."
    elif error_count or warning_count or fix_evidence_count or repair_command_count:
        status = "blocked_repair_evidence"
        operator_action = "Run the recommended repair commands and fix invalid failure evidence before reviewing selector, timeout, or source strategy changes."
    elif fallback_only_count and strategy_ready_count:
        status = "split_manual_review"
        operator_action = (
            "Use ready fallback sources for fallback-only failures, then manually review only strategy-ready evidence."
        )
    elif fallback_only_count:
        status = "fallback_only"
        operator_action = (
            "Use ready fallback sources for this run; do not change selector, timeout, or source strategy."
        )
    elif ready_for_manual_strategy_review:
        status = "strategy_review_ready"
        operator_action = "Manual source strategy review is allowed for the strategy-ready evidence; keep implementation and publish manual."
    else:
        status = "insufficient_evidence"
        operator_action = "Collect or inspect more local preflight evidence before changing source strategy."

    return {
        "status": status,
        "ready_for_manual_strategy_review": ready_for_manual_strategy_review,
        "auto_apply_allowed": False,
        "manual_review_required": True,
        "blocked_by": blocked_by,
        "operator_action": operator_action,
        "safety_note": "This dry-run never applies selector, timeout, source, Notion, or publish changes automatically.",
    }


def _repair_command_queue_consistency(summary: dict[str, Any]) -> dict[str, Any]:
    try:
        repair_command_count = int(summary.get("repair_command_count") or 0)
    except (TypeError, ValueError):
        repair_command_count = 0
    repair_command_queue = (
        summary.get("repair_command_queue") if isinstance(summary.get("repair_command_queue"), list) else []
    )
    top_repair_commands = (
        summary.get("top_repair_commands") if isinstance(summary.get("top_repair_commands"), list) else []
    )
    queue_count_total = 0
    for item in repair_command_queue:
        if not isinstance(item, dict):
            continue
        try:
            queue_count_total += int(item.get("count") or 0)
        except (TypeError, ValueError):
            continue
    status = "ok" if repair_command_count == queue_count_total else "mismatch"
    return {
        "status": status,
        "repair_command_count": repair_command_count,
        "queue_count_total": queue_count_total,
        "queue_item_count": len(repair_command_queue),
        "top_item_count": len(top_repair_commands),
    }


def build_strategy_simulation(
    input_paths: list[Path],
    *,
    base_dir: Path | None = None,
    max_json_bytes: int = 2_000_000,
) -> dict[str, Any]:
    base_dir = (base_dir or Path.cwd()).resolve()
    trend = build_trend_payload(input_paths, base_dir=base_dir, max_json_bytes=max_json_bytes)
    summary = trend.get("summary") if isinstance(trend.get("summary"), dict) else {}
    gate_counts = _gate_counts(summary)
    current = _variant("current_top_source_action", _current_strategy_signals(summary, gate_counts))
    candidate = _variant(
        "candidate_gate_directed_operator_recommendation",
        _candidate_strategy_signals(summary, gate_counts),
    )
    problem_count = int(summary.get("problem_action_count") or 0)
    comparison = _compare(current, candidate, problem_count=problem_count)
    metric_coverage = _metric_coverage(current, candidate)
    repair_command_queue_consistency = _repair_command_queue_consistency(summary)
    return {
        "dry_run": True,
        "input_paths": [str(path) for path in input_paths],
        "base_dir": str(base_dir),
        "objective_metrics": list(OBJECTIVE_METRICS),
        "safety": _safety_contract(),
        "trend_status": trend.get("status"),
        "summary": {
            "report_count": int(summary.get("report_count") or 0),
            "problem_action_count": problem_count,
            "error_count": int(summary.get("error_count") or 0),
            "warning_count": int(summary.get("warning_count") or 0),
            "evidence_gate_status_counts": dict(gate_counts),
            "evidence_field_counts": (
                summary.get("evidence_field_counts") if isinstance(summary.get("evidence_field_counts"), dict) else {}
            ),
            "repair_command_count": int(summary.get("repair_command_count") or 0),
            "repair_command_type_counts": (
                summary.get("repair_command_type_counts")
                if isinstance(summary.get("repair_command_type_counts"), dict)
                else {}
            ),
            "top_repair_commands": (
                summary.get("top_repair_commands") if isinstance(summary.get("top_repair_commands"), list) else []
            ),
            "repair_command_queue": (
                summary.get("repair_command_queue") if isinstance(summary.get("repair_command_queue"), list) else []
            ),
            "repair_command_queue_consistency": repair_command_queue_consistency,
            "operator_action_counts": (
                summary.get("operator_action_counts") if isinstance(summary.get("operator_action_counts"), dict) else {}
            ),
            "top_operator_actions": (
                summary.get("top_operator_actions") if isinstance(summary.get("top_operator_actions"), list) else []
            ),
            "operator_action_mismatch_count": int(summary.get("operator_action_mismatch_count") or 0),
            "operator_action_mismatch_source_counts": (
                summary.get("operator_action_mismatch_source_counts")
                if isinstance(summary.get("operator_action_mismatch_source_counts"), dict)
                else {}
            ),
            "operator_recommendation": _operator_recommendation(summary),
            **metric_coverage,
        },
        "variants": {
            "current": current,
            "candidate": candidate,
        },
        "comparison": comparison,
        "rollout_gate": _rollout_gate(summary, comparison, gate_counts),
    }


def _format_summary(payload: dict[str, Any], destination: str) -> str:
    comparison = payload["comparison"]
    rollout_gate = payload.get("rollout_gate") if isinstance(payload.get("rollout_gate"), dict) else {}
    manual_ready_gate = payload.get("manual_ready_gate") if isinstance(payload.get("manual_ready_gate"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    top_action = _top_operator_action_summary(summary)
    missing_counts = (
        summary.get("missing_metric_counts") if isinstance(summary.get("missing_metric_counts"), dict) else {}
    )
    measurement_scope = summary.get("measurement_scope") if isinstance(summary.get("measurement_scope"), dict) else {}
    metric_total = len(payload.get("objective_metrics") or OBJECTIVE_METRICS)
    metric_missing = str(
        summary.get("metric_missing")
        or f"current:{missing_counts.get('current', '-')}/{metric_total},"
        f"candidate:{missing_counts.get('candidate', '-')}/{metric_total}"
    )
    mismatch_count = int(summary.get("operator_action_mismatch_count") or 0)
    mismatch_sources = (
        summary.get("operator_action_mismatch_source_counts")
        if isinstance(summary.get("operator_action_mismatch_source_counts"), dict)
        else {}
    )
    evidence_fields = (
        summary.get("evidence_field_counts") if isinstance(summary.get("evidence_field_counts"), dict) else {}
    )
    repair_queue_consistency = (
        summary.get("repair_command_queue_consistency")
        if isinstance(summary.get("repair_command_queue_consistency"), dict)
        else {}
    )
    primary_repair_target = _primary_repair_target(summary, manual_ready_gate)
    primary_repair_parts = _primary_repair_target_summary(primary_repair_target)
    current = payload["variants"]["current"]["signals"]
    candidate = payload["variants"]["candidate"]["signals"]
    return (
        "source_preflight_strategy_simulation="
        f"{destination} recommendation={comparison['recommendation']} "
        f"gate={rollout_gate.get('status', '-')} "
        f"manual_ready_gate={manual_ready_gate.get('status', '-')} "
        f"repair_command_count={summary.get('repair_command_count', 0)} "
        f"repair_queue={repair_queue_consistency.get('status', '-')} "
        f"primary_repair_type={primary_repair_parts['type']} "
        f"primary_repair_count={primary_repair_parts['count']} "
        f"primary_repair_buckets={primary_repair_parts['buckets']} "
        f"primary_repair_sources={primary_repair_parts['sources']} "
        f"repair_remaining={_repair_remaining_count(manual_ready_gate)} "
        f"metric_missing={metric_missing} "
        f"operator_action_mismatch_count={mismatch_count} "
        f"operator_action_mismatch_sources={_format_compact_counts(mismatch_sources)} "
        f"evidence_fields={_format_compact_counts(evidence_fields)} "
        f"scope={measurement_scope.get('mode', '-')} "
        f"score_delta={comparison['score_delta']} "
        f"unsafe_strategy_change_delta={comparison['unsafe_strategy_change_delta']} "
        f"current_unsafe={current['unsafe_strategy_change_count']} "
        f"candidate_unsafe={candidate['unsafe_strategy_change_count']} "
        f"top_operator_action_count={top_action['count']} "
        f"top_operator_action_sources={top_action['sources']} "
        f"top_operator_action={top_action['action']}"
    )


def _top_operator_action_summary(summary: dict[str, Any]) -> dict[str, Any]:
    actions = summary.get("top_operator_actions") if isinstance(summary.get("top_operator_actions"), list) else []
    for item in actions:
        if not isinstance(item, dict):
            continue
        action = str(item.get("operator_action") or "").strip()
        if not action:
            continue
        sources = item.get("sources") if isinstance(item.get("sources"), dict) else {}
        return {
            "count": item.get("count", 0),
            "sources": _format_compact_counts(sources),
            "action": action,
        }
    return {"count": 0, "sources": "-", "action": "-"}


def _primary_repair_target(summary: dict[str, Any], manual_ready_gate: dict[str, Any]) -> dict[str, Any]:
    repair_command = str(manual_ready_gate.get("primary_repair_command") or "").strip()
    queue = summary.get("repair_command_queue") if isinstance(summary.get("repair_command_queue"), list) else []
    fallback: dict[str, Any] | None = None
    for item in queue:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        if fallback is None:
            fallback = item
        if repair_command and command == repair_command:
            return item
    return fallback or {}


def _primary_repair_target_summary(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict) or not item:
        return {"type": "-", "count": 0, "buckets": "-", "sources": "-"}
    sources = item.get("sources") if isinstance(item.get("sources"), dict) else {}
    buckets = item.get("buckets") if isinstance(item.get("buckets"), dict) else {}
    return {
        "type": str(item.get("type") or "-"),
        "count": item.get("count", 0),
        "buckets": _format_compact_counts(buckets),
        "sources": _format_compact_counts(sources),
    }


def _format_compact_counts(counts: dict[str, Any]) -> str:
    parts = []
    for key, value in sorted(counts.items(), key=lambda item: str(item[0])):
        parts.append(f"{key}={value}")
    return ",".join(parts) if parts else "-"


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
        return default
    return bool(value)


def _repair_remaining_count(manual_ready_gate: dict[str, Any]) -> int:
    remaining = manual_ready_gate.get("repair_command_remaining_count")
    if isinstance(remaining, int) and not isinstance(remaining, bool):
        return max(0, remaining)
    count = manual_ready_gate.get("repair_command_count")
    if isinstance(count, int) and not isinstance(count, bool):
        return max(0, count - 1)
    commands = manual_ready_gate.get("repair_commands")
    if isinstance(commands, list):
        return max(0, len(commands) - 1)
    return 0


def _manual_repair_commands(payload: dict[str, Any]) -> list[str]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    commands: list[str] = []
    top_repair_commands = (
        summary.get("top_repair_commands") if isinstance(summary.get("top_repair_commands"), list) else []
    )
    repair_command_queue = (
        summary.get("repair_command_queue") if isinstance(summary.get("repair_command_queue"), list) else []
    )
    repair_command_items = repair_command_queue or top_repair_commands
    for item in repair_command_items:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        if command and command not in commands:
            commands.append(command)
    return commands


def _manual_ready_gate_result(payload: dict[str, Any], *, required: bool) -> dict[str, Any]:
    rollout_gate = payload.get("rollout_gate") if isinstance(payload.get("rollout_gate"), dict) else {}
    ready = _as_bool(rollout_gate.get("ready_for_manual_strategy_review"))
    if not required:
        return {
            "required": False,
            "passed": True,
            "status": "not_required",
            "exit_code": 0,
            "reason": "Manual-ready gate was not requested.",
        }
    if ready:
        return {
            "required": True,
            "passed": True,
            "status": "pass",
            "exit_code": 0,
            "reason": f"Manual strategy review is ready: {rollout_gate.get('status', '-')}.",
        }
    reason = rollout_gate.get("operator_action") or "Manual strategy review is not ready."
    repair_commands = _manual_repair_commands(payload)
    return {
        "required": True,
        "passed": False,
        "status": "blocked",
        "exit_code": GATE_BLOCKED_EXIT,
        "reason": reason,
        "primary_repair_command": repair_commands[0] if repair_commands else "",
        "repair_command_count": len(repair_commands),
        "repair_command_remaining_count": max(0, len(repair_commands) - 1),
        "repair_commands": repair_commands,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run A/B simulation for source preflight strategy changes.")
    parser.add_argument("--input", action="append", type=Path, help="Source preflight JSON report. Repeatable.")
    parser.add_argument("--input-dir", action="append", type=Path, help="Directory of source preflight JSON reports.")
    parser.add_argument(
        "--glob", default=DEFAULT_GLOB, help="Glob for --input-dir. Default: source_browser_preflight*.json"
    )
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="Base directory for relative evidence paths.")
    parser.add_argument("--max-files", type=int, default=20, help="Maximum files per --input-dir.")
    parser.add_argument("--max-json-bytes", type=int, default=2_000_000, help="Safety limit per JSON file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="JSON output path.")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
    parser.add_argument("--no-write", action="store_true", help="Build without writing output.")
    parser.add_argument("--summary-only", action="store_true", help="Print one-line summary without writing output.")
    parser.add_argument(
        "--require-manual-ready",
        action="store_true",
        help="Exit 2 unless rollout_gate.ready_for_manual_strategy_review is true.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_dir = args.base_dir.resolve()
    paths = _input_paths(args, base_dir)
    payload = build_strategy_simulation(paths, base_dir=base_dir, max_json_bytes=max(1, args.max_json_bytes))
    payload["manual_ready_gate"] = _manual_ready_gate_result(payload, required=args.require_manual_ready)
    skip_write = args.no_write or args.summary_only
    payload["output"] = {
        "path": str(args.output),
        "written": not skip_write,
        "write_suppressed": skip_write,
        "suppression_flags": [
            name for name, enabled in (("no_write", args.no_write), ("summary_only", args.summary_only)) if enabled
        ],
    }
    if not skip_write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    else:
        destination = "(not written)" if skip_write else str(args.output)
        print(_format_summary(payload, destination))
    return int(payload["manual_ready_gate"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
