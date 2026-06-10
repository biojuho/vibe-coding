from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
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
    paths = [_resolve_path(path, base_dir) for path in (args.input or [])]
    for input_dir in args.input_dir or []:
        resolved_dir = _resolve_path(input_dir, base_dir)
        if not resolved_dir.exists() or not resolved_dir.is_dir():
            paths.append(resolved_dir)
            continue
        matches = sorted(
            resolved_dir.glob(args.glob),
            key=lambda path: (path.stat().st_mtime if path.exists() else 0.0, str(path)),
            reverse=True,
        )
        paths.extend(matches[: args.max_files])
    if not paths:
        paths.append(_resolve_path(DEFAULT_INPUT_PATH, base_dir))
    return _unique_paths(paths)


def _counter_dict(counter: Counter[str], *, limit: int | None = None) -> dict[str, int]:
    items = counter.most_common(limit) if limit else counter.most_common()
    return {key: count for key, count in items}


def _bucket_report(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    source_status_counts: Counter[tuple[str, str]] = Counter()
    failure_report_status_counts: Counter[str] = Counter()
    operator_action_required_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        source = str(item.get("source") or "unknown")
        failure_report_status = str(item.get("failure_report_status") or "unknown")
        status_counts[status] += 1
        source_counts[source] += 1
        source_status_counts[(source, status)] += 1
        failure_report_status_counts[failure_report_status] += 1
        if status != "ready":
            operator_action_required_count += 1

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
        "status_counts": _counter_dict(status_counts),
        "source_counts": _counter_dict(source_counts),
        "source_status_counts": {
            f"{source}|{status}": count for (source, status), count in source_status_counts.items()
        },
        "failure_report_status_counts": _counter_dict(failure_report_status_counts),
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
    error_count = 0
    warning_count = 0
    problem_action_count = 0
    failure_report_count = 0
    operator_action_required_count = 0

    for summary in report_summaries:
        status_counts.update(summary["status_counts"])
        source_counts.update(summary["source_counts"])
        failure_report_status_counts.update(summary["failure_report_status_counts"])
        error_count += int(summary["error_count"])
        warning_count += int(summary["warning_count"])
        problem_action_count += int(summary["problem_action_count"])
        failure_report_count += int(summary["failure_report_count"])
        operator_action_required_count += int(summary["operator_action_required_count"])

    status = "FAIL" if error_count else "WARN" if warning_count else "PASS"
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
            "error_count": error_count,
            "warning_count": warning_count,
            "status_counts": _counter_dict(status_counts),
            "source_counts": _counter_dict(source_counts),
            "failure_report_status_counts": _counter_dict(failure_report_status_counts),
            "top_issue_codes": _top_issue_codes(reports),
            "top_source_action": _top_source_action(report_summaries),
            "top_source_remediation": _top_source_remediation(report_summaries),
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
    print("[SOURCE PREFLIGHT TREND REPORT]")
    print(f"  status: {payload['status']}")
    print(f"  reports: {summary['report_count']}")
    print(f"  problem_actions: {summary['problem_action_count']}")
    print(f"  failure_reports: {summary['failure_report_count']}")
    print(f"  operator_action_required: {summary['operator_action_required_count']}")
    print(f"  errors: {summary['error_count']}")
    print(f"  warnings: {summary['warning_count']}")
    print(f"  statuses: {_format_counts(summary['status_counts'])}")
    print(f"  sources: {_format_counts(summary['source_counts'])}")
    print(f"  failure_report_statuses: {_format_counts(summary['failure_report_status_counts'])}")
    print(f"  top_issue_codes: {_format_counts(summary['top_issue_codes'])}")
    if top_source_action:
        print(
            "  top_source_action: "
            f"source={top_source_action.get('source')}; "
            f"status={top_source_action.get('status')}; "
            f"count={top_source_action.get('count')}; "
            f"action={top_source_action.get('operator_action')}"
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
