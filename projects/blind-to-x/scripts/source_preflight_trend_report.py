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

from scripts.source_preflight_evidence_doctor import (
    DEFAULT_MAX_JSON_BYTES,
    build_evidence_payload,
    exit_code_for_payload,
)

DEFAULT_INPUT_PATH = Path(".tmp/source_browser_preflight.json")
DEFAULT_GLOB = "source_browser_preflight*.json"


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


def _counter_dict(counter: Counter[str], *, limit: int | None = None) -> dict[str, int]:
    items = counter.most_common(limit) if limit else counter.most_common()
    return {key: count for key, count in items}


def _repair_command_type(command: str) -> str:
    if "source_preflight_evidence_doctor.py" in command:
        return "evidence_doctor"
    if "--source-preflight-trace-dir" in command:
        return "source_preflight_capture_with_trace"
    if "--source-preflight" in command:
        return "source_preflight_capture"
    return "other"


REPAIR_COMMAND_TYPE_PRIORITY = {
    "evidence_doctor": 0,
    "source_preflight_capture": 1,
    "source_preflight_capture_with_trace": 2,
    "other": 3,
}
EVIDENCE_OPEN_PRIORITY = (
    "failure_report_path",
    "trace_path",
    "screenshot_path",
    "html_snapshot_path",
    "click_screenshot_path",
    "error",
    "click_error",
)


def _repair_command_sort_key(command: str, count: int) -> tuple[int, int, str]:
    command_type = _repair_command_type(command)
    priority = REPAIR_COMMAND_TYPE_PRIORITY.get(command_type, REPAIR_COMMAND_TYPE_PRIORITY["other"])
    return (-count, priority, command)


def _bucket_report(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    source_status_counts: Counter[tuple[str, str]] = Counter()
    failure_report_status_counts: Counter[str] = Counter()
    evidence_gate_status_counts: Counter[str] = Counter()
    repair_command_counts: Counter[str] = Counter()
    repair_command_type_counts: Counter[str] = Counter()
    repair_command_source_counts: Counter[tuple[str, str]] = Counter()
    repair_command_bucket_counts: Counter[tuple[str, str, str]] = Counter()
    operator_action_counts: Counter[str] = Counter()
    operator_action_source_counts: Counter[tuple[str, str]] = Counter()
    operator_action_mismatch_source_counts: Counter[str] = Counter()
    evidence_field_counts: Counter[str] = Counter()
    operator_action_required_count = 0
    strategy_change_ready_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        source = str(item.get("source") or "unknown")
        failure_report_status = str(item.get("failure_report_status") or "unknown")
        operator_action = str(item.get("operator_action") or "").strip()
        status_counts[status] += 1
        source_counts[source] += 1
        source_status_counts[(source, status)] += 1
        failure_report_status_counts[failure_report_status] += 1
        if "operator_action_required" in item:
            action_required = bool(item.get("operator_action_required"))
        else:
            action_required = status != "ready"
        if action_required:
            operator_action_required_count += 1
        if operator_action:
            operator_action_counts[operator_action] += 1
            operator_action_source_counts[(operator_action, source)] += 1
        evidence_gate = item.get("evidence_gate") if isinstance(item.get("evidence_gate"), dict) else {}
        evidence_gate_status = str(evidence_gate.get("status") or "unknown")
        evidence_gate_status_counts[evidence_gate_status] += 1
        evidence_fields = evidence_gate.get("evidence_fields")
        if isinstance(evidence_fields, list):
            for field in evidence_fields:
                field_text = str(field or "").strip()
                if field_text:
                    evidence_field_counts[field_text] += 1
        if evidence_gate.get("strategy_change_ready") is True:
            strategy_change_ready_count += 1
        repair_commands = item.get("repair_commands") if isinstance(item.get("repair_commands"), list) else []
        for command in repair_commands:
            command_text = str(command or "").strip()
            if not command_text:
                continue
            repair_command_counts[command_text] += 1
            repair_command_type_counts[_repair_command_type(command_text)] += 1
            repair_command_source_counts[(command_text, source)] += 1
            repair_command_bucket_counts[(command_text, source, status)] += 1

    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("code") != "operator_action_mismatch":
            continue
        source = str(issue.get("source") or "unknown")
        operator_action_mismatch_source_counts[source] += 1

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "input_path": payload.get("input_path"),
        "status": payload.get("status"),
        "ok": payload.get("ok"),
        "problem_action_count": int(summary.get("problem_action_count") or 0),
        "failure_report_count": int(summary.get("failure_report_count") or 0),
        "error_count": int(summary.get("error_count") or 0),
        "warning_count": int(summary.get("warning_count") or 0),
        "operator_action_required_count": operator_action_required_count,
        "strategy_change_ready_count": strategy_change_ready_count,
        "status_counts": _counter_dict(status_counts),
        "source_counts": _counter_dict(source_counts),
        "source_status_counts": {
            f"{source}|{status}": count for (source, status), count in source_status_counts.items()
        },
        "failure_report_status_counts": _counter_dict(failure_report_status_counts),
        "evidence_gate_status_counts": _counter_dict(evidence_gate_status_counts),
        "repair_command_count": sum(repair_command_counts.values()),
        "repair_command_counts": _counter_dict(repair_command_counts),
        "repair_command_type_counts": _counter_dict(repair_command_type_counts),
        "repair_command_source_counts": {
            f"{source}|{command}": count for (command, source), count in repair_command_source_counts.items()
        },
        "repair_command_bucket_counts": {
            f"{source}|{status}|{command}": count
            for (command, source, status), count in repair_command_bucket_counts.items()
        },
        "evidence_field_counts": _counter_dict(evidence_field_counts),
        "operator_action_counts": _counter_dict(operator_action_counts),
        "operator_action_source_counts": {
            f"{source}|{action}": count for (action, source), count in operator_action_source_counts.items()
        },
        "operator_action_mismatch_count": sum(operator_action_mismatch_source_counts.values()),
        "operator_action_mismatch_source_counts": _counter_dict(operator_action_mismatch_source_counts),
        "next_step": payload.get("next_step"),
    }


def _top_issue_codes(reports: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for report in reports:
        issues = report.get("issues") if isinstance(report.get("issues"), list) else []
        for issue in issues:
            if isinstance(issue, dict):
                counter[str(issue.get("code") or "unknown")] += 1
    return _counter_dict(counter, limit=6)


def _source_status_counts(report_summaries: list[dict[str, Any]]) -> Counter[tuple[str, str]]:
    counter: Counter[tuple[str, str]] = Counter()
    for report in report_summaries:
        reports_items = report.get("source_status_counts")
        if isinstance(reports_items, dict):
            for key, count in reports_items.items():
                source, _, status = str(key).partition("|")
                counter[(source or "unknown", status or "unknown")] += int(count or 0)
            continue

        source_counts = report.get("source_counts") if isinstance(report.get("source_counts"), dict) else {}
        status_counts = report.get("status_counts") if isinstance(report.get("status_counts"), dict) else {}
        if len(source_counts) == 1 and len(status_counts) == 1:
            source = next(iter(source_counts))
            status = next(iter(status_counts))
            counter[(str(source), str(status))] += min(int(source_counts[source]), int(status_counts[status]))
    return counter


def _top_source_status_bucket(report_summaries: list[dict[str, Any]]) -> tuple[str, str, int] | None:
    source_status_counts = _source_status_counts(report_summaries)
    if not source_status_counts:
        return None
    (source, status), count = sorted(
        source_status_counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )[0]
    return source, status, count


def _top_source_action(report_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    bucket = _top_source_status_bucket(report_summaries)
    if bucket is None:
        return {}
    source, status, count = bucket
    if status == "timeout":
        action = (
            f"Inspect {source} timeout evidence, then adjust timeout or source fallback only after evidence is valid."
        )
    elif status == "blocked":
        action = f"Use a ready fallback source for this run, then recheck {source} after access controls change."
    elif status == "browser_unavailable":
        action = "Install or repair Playwright Chromium in the active Python environment before rerunning preflight."
    elif status == "click_error":
        action = f"Inspect {source} click-through evidence, then update the detail selector or API verifier."
    elif status == "login_wall":
        action = (
            f"Use a ready fallback source unless {source} authenticated browser context is intentionally configured."
        )
    else:
        action = f"Inspect {source} {status} evidence before changing source strategy."
    return {"source": source, "status": status, "count": count, "operator_action": action}


def _evidence_fields_for_status(status: str) -> list[str]:
    fields = ["failure_report_path", "screenshot_path", "html_snapshot_path", "trace_path", "error"]
    if status == "click_error":
        fields.extend(["click_screenshot_path", "click_error"])
    return fields


def _remediation_checklist(source: str, status: str) -> list[str]:
    evidence = ", ".join(_evidence_fields_for_status(status))
    inspect_step = f"Open {source} evidence fields first: {evidence}."
    if status == "timeout":
        return [
            inspect_step,
            f"Use a ready fallback source for this run if available; do not increase {source} timeout until evidence shows a reachable slow page.",
            f"Rerun {source} preflight with --failure-dir after any timeout or selector change.",
        ]
    if status == "blocked":
        return [
            inspect_step,
            "Use a ready fallback source for this run; do not add aggressive access-bypass logic.",
            f"Recheck {source} only after access controls or source availability change.",
        ]
    if status == "browser_unavailable":
        return [
            "Install or repair Playwright Chromium in the active Python environment.",
            "Rerun source preflight before treating any source as blocked.",
            "Keep browser-install artifacts local and out of commits.",
        ]
    if status == "click_error":
        return [
            inspect_step,
            f"Update the {source} detail selector or API verifier only after click evidence explains the failure.",
            f"Rerun {source} click-through preflight with --failure-dir before changing source strategy.",
        ]
    if status == "login_wall":
        return [
            inspect_step,
            f"Use a ready fallback source unless {source} authenticated browser context is intentionally configured.",
            "Do not store credentials in source preflight reports or failure artifacts.",
        ]
    return [
        inspect_step,
        f"Use a ready fallback source for this run if {source} evidence is inconclusive.",
        f"Change {source} strategy only after the evidence doctor reports structurally complete evidence.",
    ]


def _top_source_remediation(report_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    bucket = _top_source_status_bucket(report_summaries)
    if bucket is None:
        return {}
    source, status, count = bucket
    return {
        "source": source,
        "status": status,
        "count": count,
        "evidence_fields": _evidence_fields_for_status(status),
        "checklist": _remediation_checklist(source, status),
    }


def _evidence_item_value(value: Any) -> str:
    return str(value or "").strip()


def _item_evidence(item: dict[str, Any]) -> dict[str, str]:
    raw_evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    evidence = {
        str(key): _evidence_item_value(value)
        for key, value in raw_evidence.items()
        if str(key).strip() and _evidence_item_value(value)
    }
    failure_report_path = _evidence_item_value(item.get("failure_report_path"))
    if failure_report_path and "failure_report_path" not in evidence:
        evidence["failure_report_path"] = failure_report_path
    return evidence


def _first_evidence_reference(evidence: dict[str, str]) -> tuple[str, str]:
    for key in EVIDENCE_OPEN_PRIORITY:
        value = _evidence_item_value(evidence.get(key))
        if value:
            return key, value
    return "", ""


def _top_source_evidence(reports: list[dict[str, Any]], top_source_action: dict[str, Any]) -> dict[str, Any]:
    source = _evidence_item_value(top_source_action.get("source"))
    status = _evidence_item_value(top_source_action.get("status"))
    if not source or not status:
        return {}

    for report in reports:
        items = report.get("items") if isinstance(report.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            if _evidence_item_value(item.get("source")) != source:
                continue
            if _evidence_item_value(item.get("status")) != status:
                continue
            evidence = _item_evidence(item)
            open_first_field, open_first = _first_evidence_reference(evidence)
            if not open_first:
                continue
            evidence_gate = item.get("evidence_gate") if isinstance(item.get("evidence_gate"), dict) else {}
            result = {
                "source": source,
                "status": status,
                "count": int(top_source_action.get("count") or 0),
                "input_path": _evidence_item_value(report.get("input_path")),
                "operator_action": _evidence_item_value(
                    item.get("operator_action") or top_source_action.get("operator_action")
                ),
                "evidence_gate_status": _evidence_item_value(evidence_gate.get("status")),
                "open_first_field": open_first_field,
                "open_first": open_first,
                "evidence": {
                    key: evidence[key]
                    for key in EVIDENCE_OPEN_PRIORITY
                    if key in evidence and _evidence_item_value(evidence[key])
                },
            }
            trace_viewer_command = _evidence_item_value(item.get("trace_viewer_command"))
            if trace_viewer_command:
                result["trace_viewer_command"] = trace_viewer_command
            return result
    return {}


def _top_repair_commands(
    repair_command_counts: Counter[str],
    repair_command_source_counts: Counter[tuple[str, str]],
    repair_command_bucket_counts: Counter[tuple[str, str, str]],
    *,
    limit: int | None = 4,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sorted_commands = sorted(
        repair_command_counts.items(),
        key=lambda item: _repair_command_sort_key(item[0], item[1]),
    )
    if limit is not None:
        sorted_commands = sorted_commands[:limit]
    for command, count in sorted_commands:
        source_counter: Counter[str] = Counter()
        bucket_counter: Counter[str] = Counter()
        for (candidate_command, source), source_count in repair_command_source_counts.items():
            if candidate_command == command:
                source_counter[source] += source_count
        for (candidate_command, source, status), bucket_count in repair_command_bucket_counts.items():
            if candidate_command == command:
                bucket_counter[f"{source}|{status}"] += bucket_count
        items.append(
            {
                "command": command,
                "type": _repair_command_type(command),
                "count": count,
                "sources": _counter_dict(source_counter, limit=4),
                "buckets": _counter_dict(bucket_counter, limit=4),
            }
        )
    return items


def _top_operator_actions(
    operator_action_counts: Counter[str],
    operator_action_source_counts: Counter[tuple[str, str]],
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for action, count in sorted(operator_action_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]:
        source_counter: Counter[str] = Counter()
        for (candidate_action, source), source_count in operator_action_source_counts.items():
            if candidate_action == action:
                source_counter[source] += source_count
        items.append(
            {
                "operator_action": action,
                "count": count,
                "sources": _counter_dict(source_counter, limit=4),
            }
        )
    return items


def _operator_recommendation(
    *,
    problem_action_count: int,
    error_count: int,
    warning_count: int,
    evidence_gate_status_counts: Counter[str],
    top_source_action: dict[str, Any],
) -> dict[str, Any]:
    fix_evidence_count = int(evidence_gate_status_counts.get("fix_evidence_first", 0))
    fallback_only_count = int(evidence_gate_status_counts.get("fallback_only", 0))
    strategy_ready_count = int(evidence_gate_status_counts.get("strategy_review_ready", 0))
    source = str(top_source_action.get("source") or "").strip()
    status = str(top_source_action.get("status") or "").strip()
    top_action = str(top_source_action.get("operator_action") or "").strip()

    if error_count or warning_count or fix_evidence_count:
        return {
            "action": "repair_evidence",
            "priority": "high" if error_count or fix_evidence_count else "medium",
            "source": source,
            "status": status,
            "reason": "Evidence is missing, invalid, or warning-level incomplete.",
            "operator_action": (
                "Run the evidence doctor for affected reports, restore missing artifacts, then rerun trend reporting "
                "before changing selectors, timeouts, or source strategy."
            ),
            "gate_counts": {
                "fix_evidence_first": fix_evidence_count,
                "fallback_only": fallback_only_count,
                "strategy_review_ready": strategy_ready_count,
            },
        }
    if strategy_ready_count and fallback_only_count:
        return {
            "action": "split_fallback_and_strategy_review",
            "priority": "medium",
            "source": source,
            "status": status,
            "reason": "Some failures need fallback handling while others are ready for strategy review.",
            "operator_action": (
                "Use ready fallback sources for fallback-only failures, then inspect strategy-ready evidence before "
                "selector, timeout, or source-strategy changes."
            ),
            "gate_counts": {
                "fix_evidence_first": fix_evidence_count,
                "fallback_only": fallback_only_count,
                "strategy_review_ready": strategy_ready_count,
            },
        }
    if strategy_ready_count:
        return {
            "action": "review_source_strategy",
            "priority": "medium",
            "source": source,
            "status": status,
            "reason": "Failure evidence is complete enough for selector, timeout, or source-strategy review.",
            "operator_action": top_action
            or "Inspect the strategy-ready evidence, adjust the narrow source strategy, then rerun click-through preflight.",
            "gate_counts": {
                "fix_evidence_first": fix_evidence_count,
                "fallback_only": fallback_only_count,
                "strategy_review_ready": strategy_ready_count,
            },
        }
    if fallback_only_count:
        return {
            "action": "use_ready_fallback",
            "priority": "medium",
            "source": source,
            "status": status,
            "reason": "Failures point to access control or browser environment repair, not selector/timeout tuning.",
            "operator_action": top_action
            or "Use a ready fallback source for this run, then recheck the affected source after conditions change.",
            "gate_counts": {
                "fix_evidence_first": fix_evidence_count,
                "fallback_only": fallback_only_count,
                "strategy_review_ready": strategy_ready_count,
            },
        }
    if problem_action_count:
        return {
            "action": "inspect_source_evidence",
            "priority": "low",
            "source": source,
            "status": status,
            "reason": "Source failures exist but no actionable evidence gate bucket was available.",
            "operator_action": top_action or "Inspect local source evidence before changing source strategy.",
            "gate_counts": {
                "fix_evidence_first": fix_evidence_count,
                "fallback_only": fallback_only_count,
                "strategy_review_ready": strategy_ready_count,
            },
        }
    return {
        "action": "no_source_action",
        "priority": "low",
        "source": "",
        "status": "",
        "reason": "No source preflight failures were present in the selected reports.",
        "operator_action": "No source preflight action required for the selected local reports.",
        "gate_counts": {
            "fix_evidence_first": fix_evidence_count,
            "fallback_only": fallback_only_count,
            "strategy_review_ready": strategy_ready_count,
        },
    }


def build_trend_payload(
    input_paths: list[Path],
    *,
    base_dir: Path | None = None,
    max_json_bytes: int = DEFAULT_MAX_JSON_BYTES,
) -> dict[str, Any]:
    base_dir = (base_dir or Path.cwd()).resolve()
    reports = [
        build_evidence_payload(path, base_dir=base_dir, max_json_bytes=max_json_bytes)
        for path in _unique_paths(input_paths)
    ]
    report_summaries = [_bucket_report(report) for report in reports]
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    failure_report_status_counts: Counter[str] = Counter()
    repair_command_counts: Counter[str] = Counter()
    repair_command_type_counts: Counter[str] = Counter()
    repair_command_source_counts: Counter[tuple[str, str]] = Counter()
    repair_command_bucket_counts: Counter[tuple[str, str, str]] = Counter()
    operator_action_counts: Counter[str] = Counter()
    operator_action_source_counts: Counter[tuple[str, str]] = Counter()
    operator_action_mismatch_source_counts: Counter[str] = Counter()
    evidence_field_counts: Counter[str] = Counter()
    error_count = 0
    warning_count = 0
    problem_action_count = 0
    failure_report_count = 0
    operator_action_required_count = 0
    strategy_change_ready_count = 0
    evidence_gate_status_counts: Counter[str] = Counter()

    for summary in report_summaries:
        status_counts.update(summary["status_counts"])
        source_counts.update(summary["source_counts"])
        failure_report_status_counts.update(summary["failure_report_status_counts"])
        evidence_gate_status_counts.update(summary["evidence_gate_status_counts"])
        repair_command_counts.update(summary["repair_command_counts"])
        repair_command_type_counts.update(summary["repair_command_type_counts"])
        repair_source_counts = summary.get("repair_command_source_counts")
        if isinstance(repair_source_counts, dict):
            for key, count in repair_source_counts.items():
                source, _, command = str(key).partition("|")
                if command:
                    repair_command_source_counts[(command, source or "unknown")] += int(count or 0)
        repair_bucket_counts = summary.get("repair_command_bucket_counts")
        if isinstance(repair_bucket_counts, dict):
            for key, count in repair_bucket_counts.items():
                source, _, status_command = str(key).partition("|")
                status, _, command = status_command.partition("|")
                if command:
                    repair_command_bucket_counts[(command, source or "unknown", status or "unknown")] += int(count or 0)
        evidence_field_counts.update(summary.get("evidence_field_counts") or {})
        operator_action_counts.update(summary.get("operator_action_counts") or {})
        operator_action_mismatch_source_counts.update(summary.get("operator_action_mismatch_source_counts") or {})
        operator_source_counts = summary.get("operator_action_source_counts")
        if isinstance(operator_source_counts, dict):
            for key, count in operator_source_counts.items():
                source, _, action = str(key).partition("|")
                if action:
                    operator_action_source_counts[(action, source or "unknown")] += int(count or 0)
        error_count += int(summary["error_count"])
        warning_count += int(summary["warning_count"])
        problem_action_count += int(summary["problem_action_count"])
        failure_report_count += int(summary["failure_report_count"])
        operator_action_required_count += int(summary["operator_action_required_count"])
        strategy_change_ready_count += int(summary["strategy_change_ready_count"])

    status = "FAIL" if error_count else "WARN" if warning_count else "PASS"
    top_source_action = _top_source_action(report_summaries)
    top_source_remediation = _top_source_remediation(report_summaries)
    top_source_evidence = _top_source_evidence(reports, top_source_action)
    return {
        "ok": error_count == 0,
        "status": status,
        "base_dir": str(base_dir),
        "safety": {
            "read_only": True,
            "browser_launches": False,
            "notion_writes": False,
            "x_posts": False,
            "auto_publish_default": False,
            "manual_publish_required": True,
        },
        "summary": {
            "report_count": len(reports),
            "problem_action_count": problem_action_count,
            "failure_report_count": failure_report_count,
            "operator_action_required_count": operator_action_required_count,
            "strategy_change_ready_count": strategy_change_ready_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "status_counts": _counter_dict(status_counts),
            "source_counts": _counter_dict(source_counts),
            "failure_report_status_counts": _counter_dict(failure_report_status_counts),
            "evidence_gate_status_counts": _counter_dict(evidence_gate_status_counts),
            "evidence_field_counts": _counter_dict(evidence_field_counts),
            "top_issue_codes": _top_issue_codes(reports),
            "repair_command_count": sum(repair_command_counts.values()),
            "repair_command_type_counts": _counter_dict(repair_command_type_counts),
            "repair_command_queue": _top_repair_commands(
                repair_command_counts,
                repair_command_source_counts,
                repair_command_bucket_counts,
                limit=None,
            ),
            "top_repair_commands": _top_repair_commands(
                repair_command_counts,
                repair_command_source_counts,
                repair_command_bucket_counts,
            ),
            "operator_action_counts": _counter_dict(operator_action_counts),
            "top_operator_actions": _top_operator_actions(operator_action_counts, operator_action_source_counts),
            "operator_action_mismatch_count": sum(operator_action_mismatch_source_counts.values()),
            "operator_action_mismatch_source_counts": _counter_dict(operator_action_mismatch_source_counts),
            "top_source_action": top_source_action,
            "top_source_remediation": top_source_remediation,
            "top_source_evidence": top_source_evidence,
            "operator_recommendation": _operator_recommendation(
                problem_action_count=problem_action_count,
                error_count=error_count,
                warning_count=warning_count,
                evidence_gate_status_counts=evidence_gate_status_counts,
                top_source_action=top_source_action,
            ),
        },
        "reports": report_summaries,
        "next_step": _next_step(status, problem_action_count),
    }


def _next_step(status: str, problem_action_count: int) -> str:
    if status == "FAIL":
        return "Fix invalid or missing evidence before changing selectors, timeouts, or source strategy."
    if status == "WARN":
        return "Review warning codes; rerun individual evidence doctor for any unclear report."
    if problem_action_count:
        return "Use the most frequent source/status buckets to choose the next preflight hardening slice."
    return "No source preflight failures in the selected local reports."


def exit_code_for_trend(payload: dict[str, Any], *, fail_on_warning: bool = False) -> int:
    doctor_like = {"summary": payload.get("summary", {})}
    return exit_code_for_payload(doctor_like, fail_on_warning=fail_on_warning)


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in counts.items()) if counts else "-"


def _print_text_report(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    top_source_action = summary.get("top_source_action") if isinstance(summary.get("top_source_action"), dict) else {}
    top_source_remediation = (
        summary.get("top_source_remediation") if isinstance(summary.get("top_source_remediation"), dict) else {}
    )
    top_source_evidence = (
        summary.get("top_source_evidence") if isinstance(summary.get("top_source_evidence"), dict) else {}
    )
    operator_recommendation = (
        summary.get("operator_recommendation") if isinstance(summary.get("operator_recommendation"), dict) else {}
    )
    print("[SOURCE PREFLIGHT TREND REPORT]")
    print(f"  status: {payload['status']}")
    print(f"  reports: {summary['report_count']}")
    print(f"  problem_actions: {summary['problem_action_count']}")
    print(f"  failure_reports: {summary['failure_report_count']}")
    print(f"  operator_action_required: {summary['operator_action_required_count']}")
    print(f"  strategy_change_ready: {summary['strategy_change_ready_count']}")
    print(f"  errors: {summary['error_count']}")
    print(f"  warnings: {summary['warning_count']}")
    print(f"  statuses: {_format_counts(summary['status_counts'])}")
    print(f"  sources: {_format_counts(summary['source_counts'])}")
    print(f"  failure_report_statuses: {_format_counts(summary['failure_report_status_counts'])}")
    print(f"  evidence_gates: {_format_counts(summary['evidence_gate_status_counts'])}")
    print(f"  evidence_fields: {_format_counts(summary['evidence_field_counts'])}")
    print(f"  top_issue_codes: {_format_counts(summary['top_issue_codes'])}")
    print(
        "  repair_commands: "
        f"count={summary.get('repair_command_count', 0)}; "
        f"types={_format_counts(summary.get('repair_command_type_counts') or {})}"
    )
    mismatch_count = int(summary.get("operator_action_mismatch_count") or 0)
    if mismatch_count:
        print(
            "  operator_action_mismatches: "
            f"count={mismatch_count}; "
            f"sources={_format_counts(summary.get('operator_action_mismatch_source_counts') or {})}"
        )
    top_repair_commands = (
        summary.get("top_repair_commands") if isinstance(summary.get("top_repair_commands"), list) else []
    )
    for item in top_repair_commands[:3]:
        if not isinstance(item, dict):
            continue
        print(
            "  top_repair_command: "
            f"count={item.get('count', 0)}; "
            f"type={item.get('type', '-')}; "
            f"sources={_format_counts(item.get('sources') or {})}; "
            f"command={item.get('command', '-')}"
        )
    top_operator_actions = (
        summary.get("top_operator_actions") if isinstance(summary.get("top_operator_actions"), list) else []
    )
    for item in top_operator_actions[:3]:
        if not isinstance(item, dict):
            continue
        print(
            "  top_operator_action: "
            f"count={item.get('count', 0)}; "
            f"sources={_format_counts(item.get('sources') or {})}; "
            f"action={item.get('operator_action', '-')}"
        )
    if top_source_action:
        print(
            "  top_source_action: "
            f"source={top_source_action.get('source')}; "
            f"status={top_source_action.get('status')}; "
            f"count={top_source_action.get('count')}; "
            f"action={top_source_action.get('operator_action')}"
        )
    if top_source_evidence:
        print(
            "  top_source_evidence: "
            f"source={top_source_evidence.get('source')}; "
            f"status={top_source_evidence.get('status')}; "
            f"open_first={top_source_evidence.get('open_first_field')}={top_source_evidence.get('open_first')}"
        )
    if operator_recommendation:
        print(
            "  operator_recommendation: "
            f"action={operator_recommendation.get('action')}; "
            f"priority={operator_recommendation.get('priority')}; "
            f"source={operator_recommendation.get('source') or '-'}; "
            f"status={operator_recommendation.get('status') or '-'}; "
            f"next={operator_recommendation.get('operator_action')}"
        )
    checklist = (
        top_source_remediation.get("checklist") if isinstance(top_source_remediation.get("checklist"), list) else []
    )
    if checklist:
        print(f"  top_source_checklist: {' | '.join(str(item) for item in checklist)}")
    print(
        "  safety: "
        "read_only=true; browser_launches=false; notion_writes=false; x_posts=false; manual_publish_required=true"
    )
    print(f"  next_step: {payload['next_step']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize local source preflight failure evidence trends.")
    parser.add_argument("--input", action="append", type=Path, help="Source preflight JSON report. Repeatable.")
    parser.add_argument("--input-dir", action="append", type=Path, help="Directory of source preflight JSON reports.")
    parser.add_argument(
        "--glob", default=DEFAULT_GLOB, help="Glob for --input-dir. Default: source_browser_preflight*.json"
    )
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="Base directory for relative evidence paths.")
    parser.add_argument("--max-files", type=int, default=20, help="Maximum files per --input-dir.")
    parser.add_argument(
        "--max-json-bytes", type=int, default=DEFAULT_MAX_JSON_BYTES, help="Safety limit per JSON file."
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    parser.add_argument("--json", action="store_true", help="Print a structured JSON report.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit 1 when warnings are present.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_dir = args.base_dir.resolve()
    paths = _input_paths(args, base_dir)
    payload = build_trend_payload(paths, base_dir=base_dir, max_json_bytes=max(1, args.max_json_bytes))
    output = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    if args.json:
        print(output)
    else:
        _print_text_report(payload)
    return exit_code_for_trend(payload, fail_on_warning=args.fail_on_warning)


if __name__ == "__main__":
    raise SystemExit(main())
