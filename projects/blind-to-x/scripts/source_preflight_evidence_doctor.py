from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_INPUT_PATH = Path(".tmp/source_browser_preflight.json")
DEFAULT_MAX_JSON_BYTES = 2_000_000
SAFE_POWERSHELL_ARG_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:\\=-")
_SOURCE_BROWSER_TOOL = "source_browser_probe"
_ARTIFACT_EVIDENCE_KEYS = ("screenshot_path", "html_snapshot_path", "click_screenshot_path", "trace_path")
_FALLBACK_ONLY_STATUSES = {"blocked", "browser_unavailable", "login_wall"}
_STRATEGY_REVIEW_STATUSES = {"browser_error", "click_error", "empty", "http_error", "timeout"}
_TRACE_VIEWER_HINT = (
    "Open the Playwright trace locally and inspect Actions, Console, Network, and DOM snapshots before changing "
    "selectors or timeouts."
)


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


def _issue(severity: str, code: str, message: str, *, source: str = "", path: str = "") -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "source": source,
        "path": path,
        "message": message,
    }


def _read_json_file(path: Path, *, max_bytes: int) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    if not path.exists():
        return None, _issue("error", "missing_json", "JSON file does not exist.", path=str(path))
    if not path.is_file():
        return None, _issue("error", "not_a_file", "Path is not a file.", path=str(path))
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, _issue("error", "stat_failed", str(exc), path=str(path))
    if size > max_bytes:
        return None, _issue(
            "error",
            "json_too_large",
            f"JSON file is {size} bytes, above the {max_bytes} byte safety limit.",
            path=str(path),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return None, _issue("error", "invalid_json", str(exc), path=str(path))
    except UnicodeDecodeError as exc:
        return None, _issue("error", "invalid_encoding", str(exc), path=str(path))
    if not isinstance(payload, dict):
        return None, _issue("error", "json_not_object", "Expected a JSON object.", path=str(path))
    return payload, None


def _validate_artifact_path(
    *,
    key: str,
    value: Any,
    base_dir: Path,
    source: str,
) -> dict[str, str] | None:
    if not value:
        return None
    path = _resolve_path(str(value), base_dir)
    if not path.exists():
        return _issue("error", f"missing_{key}", f"Referenced {key} does not exist.", source=source, path=str(path))
    if not path.is_file():
        return _issue("error", f"{key}_not_file", f"Referenced {key} is not a file.", source=source, path=str(path))
    try:
        if path.stat().st_size == 0:
            return _issue("warning", f"empty_{key}", f"Referenced {key} is empty.", source=source, path=str(path))
    except OSError as exc:
        return _issue("error", f"{key}_stat_failed", str(exc), source=source, path=str(path))
    return None


def _validate_failure_report(
    *,
    failure_report_path: Path,
    action_item: dict[str, Any],
    base_dir: Path,
    max_json_bytes: int,
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    report, load_issue = _read_json_file(failure_report_path, max_bytes=max_json_bytes)
    if load_issue:
        return None, [load_issue]
    assert report is not None

    source = str(action_item.get("source") or report.get("source") or "")
    status = str(action_item.get("status") or "")
    issues: list[dict[str, str]] = []

    metadata = report.get("failure_report")
    if not isinstance(metadata, dict):
        issues.append(
            _issue("error", "missing_failure_report_metadata", "Missing failure_report metadata.", source=source)
        )
    else:
        if metadata.get("schema_version") != 1:
            issues.append(
                _issue("error", "unexpected_schema_version", "Expected failure_report.schema_version=1.", source=source)
            )
        if metadata.get("tool") != _SOURCE_BROWSER_TOOL:
            issues.append(
                _issue("error", "unexpected_tool", "Expected failure_report.tool=source_browser_probe.", source=source)
            )
        if not str(metadata.get("captured_at") or "").strip():
            issues.append(_issue("error", "missing_captured_at", "Missing failure_report.captured_at.", source=source))

    operator = report.get("operator")
    if not isinstance(operator, dict):
        issues.append(_issue("error", "missing_operator", "Missing operator block.", source=source))
    else:
        expected_operator_action = str(action_item.get("operator_action") or action_item.get("action") or "").strip()
        actual_operator_action = str(operator.get("action") or "").strip()
        if not _as_bool(operator.get("action_required")):
            issues.append(
                _issue(
                    "error", "operator_action_not_required", "Expected operator.action_required=true.", source=source
                )
            )
        if not actual_operator_action:
            issues.append(_issue("error", "missing_operator_action", "Missing operator.action.", source=source))
        elif expected_operator_action and actual_operator_action != expected_operator_action:
            issues.append(
                _issue(
                    "error",
                    "operator_action_mismatch",
                    "problem action operator_action does not match failure report operator.action.",
                    source=source,
                )
            )
        operator_evidence = operator.get("evidence")
        if not isinstance(operator_evidence, dict):
            issues.append(
                _issue("error", "missing_operator_evidence", "Missing operator.evidence object.", source=source)
            )
        else:
            failure_report_evidence_path = str(operator_evidence.get("failure_report_path") or "").strip()
            if not failure_report_evidence_path:
                issues.append(
                    _issue(
                        "error",
                        "operator_evidence_missing_failure_report_path",
                        "Missing operator.evidence.failure_report_path.",
                        source=source,
                    )
                )
            elif _resolve_path(failure_report_evidence_path, base_dir).resolve(
                strict=False
            ) != failure_report_path.resolve(strict=False):
                issues.append(
                    _issue(
                        "error",
                        "operator_evidence_failure_report_path_mismatch",
                        "operator.evidence.failure_report_path does not point to this failure report.",
                        source=source,
                        path=str(_resolve_path(failure_report_evidence_path, base_dir)),
                    )
                )

    classification = report.get("classification")
    report_status = classification.get("status") if isinstance(classification, dict) else None
    if status and report_status and status != report_status:
        issues.append(
            _issue(
                "error",
                "status_mismatch",
                f"problem action status {status!r} does not match failure report status {report_status!r}.",
                source=source,
            )
        )
    if source and report.get("source") and source != report.get("source"):
        issues.append(
            _issue(
                "error",
                "source_mismatch",
                f"problem action source {source!r} does not match failure report source {report.get('source')!r}.",
                source=source,
            )
        )

    evidence = action_item.get("evidence")
    if isinstance(evidence, dict):
        for key in _ARTIFACT_EVIDENCE_KEYS:
            issue = _validate_artifact_path(key=key, value=evidence.get(key), base_dir=base_dir, source=source)
            if issue:
                issues.append(issue)

    return report, issues


def _problem_actions(report: dict[str, Any]) -> list[Any]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return []
    actions = summary.get("problem_actions")
    return actions if isinstance(actions, list) else []


def _evidence_snapshot(evidence: Any) -> dict[str, str]:
    if not isinstance(evidence, dict):
        return {}
    snapshot: dict[str, str] = {}
    for key, value in evidence.items():
        if value is None:
            continue
        if not isinstance(value, (str, int, float, bool)):
            continue
        key_text = str(key or "").strip()
        value_text = str(value).strip()
        if key_text and value_text:
            snapshot[key_text] = value_text
    return snapshot


def _present_evidence_fields(evidence: Any) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    return sorted(str(key) for key, value in evidence.items() if value)


def _missing_strategy_evidence(status: str, evidence: Any) -> list[str]:
    if not isinstance(evidence, dict):
        return ["evidence"]
    missing: list[str] = []
    if not evidence.get("failure_report_path"):
        missing.append("failure_report_path")

    if status == "click_error":
        click_keys = ("click_screenshot_path", "click_error", "screenshot_path", "html_snapshot_path", "trace_path")
        if not any(evidence.get(key) for key in click_keys):
            missing.append("one_of:click_screenshot_path|click_error|screenshot_path|html_snapshot_path|trace_path")
    elif status in _STRATEGY_REVIEW_STATUSES:
        diagnostic_keys = ("screenshot_path", "html_snapshot_path", "trace_path", "error", "exception_type")
        if not any(evidence.get(key) for key in diagnostic_keys):
            missing.append("one_of:screenshot_path|html_snapshot_path|trace_path|error|exception_type")
    return missing


def _evidence_gate(
    action_item: dict[str, Any],
    *,
    failure_report_status: str,
    item_issues: list[dict[str, str]],
) -> dict[str, Any]:
    status = str(action_item.get("status") or "unknown")
    evidence = action_item.get("evidence")
    present_fields = _present_evidence_fields(evidence)
    missing_strategy_evidence = _missing_strategy_evidence(status, evidence)
    if failure_report_status != "valid" or item_issues:
        return {
            "status": "fix_evidence_first",
            "strategy_change_ready": False,
            "decision": "fix_evidence_first",
            "reason": "Evidence is missing, invalid, or has doctor warnings/errors.",
            "evidence_fields": present_fields,
            "missing_required_evidence": missing_strategy_evidence,
        }
    if status in _FALLBACK_ONLY_STATUSES:
        return {
            "status": "fallback_only",
            "strategy_change_ready": False,
            "decision": "use_ready_fallback",
            "reason": "This status points to access control or browser environment repair, not selector/timeout tuning.",
            "evidence_fields": present_fields,
            "missing_required_evidence": [],
        }
    if status in _STRATEGY_REVIEW_STATUSES and not missing_strategy_evidence:
        return {
            "status": "strategy_review_ready",
            "strategy_change_ready": True,
            "decision": "review_source_strategy",
            "reason": "Failure evidence is structurally complete enough to review selector, timeout, or source strategy.",
            "evidence_fields": present_fields,
            "missing_required_evidence": [],
        }
    return {
        "status": "fix_evidence_first",
        "strategy_change_ready": False,
        "decision": "fix_evidence_first",
        "reason": "Required strategy-review evidence is missing.",
        "evidence_fields": present_fields,
        "missing_required_evidence": missing_strategy_evidence,
    }


def _format_command(parts: list[str | Path]) -> str:
    return " ".join(_quote_powershell_arg(part) for part in parts)


def _quote_powershell_arg(value: str | Path) -> str:
    text = str(value)
    if not text:
        return "''"
    if any(char not in SAFE_POWERSHELL_ARG_CHARS for char in text):
        return "'" + text.replace("'", "''") + "'"
    return text


def _doctor_rerun_command(*, input_path: Path, base_dir: Path) -> str:
    return _format_command(
        [
            "py",
            "-3",
            "scripts/source_preflight_evidence_doctor.py",
            "--input",
            input_path,
            "--base-dir",
            base_dir,
            "--fail-on-warning",
        ]
    )


def _source_preflight_capture_command(*, source: str, input_path: Path, include_trace: bool) -> str:
    command_parts: list[str | Path] = [
        "py",
        "-3",
        "main.py",
        "--config",
        "config.yaml",
        "--source",
        source,
        "--source-preflight",
        "--source-preflight-click-through",
        "--source-preflight-output",
        input_path,
        "--source-preflight-screenshot-dir",
        Path("screenshots/source_preflight"),
        "--source-preflight-failure-dir",
        Path(".tmp/failures/source_preflight"),
    ]
    if include_trace:
        command_parts.extend(["--source-preflight-trace-dir", Path(".tmp/traces/source_preflight")])
    return _format_command(command_parts)


def _trace_viewer_command(trace_path: str) -> str:
    return _format_command(["playwright", "show-trace", trace_path])


def _trace_viewer_details(action_item: dict[str, Any], failure_report: dict[str, Any] | None) -> dict[str, str]:
    evidence = action_item.get("evidence")
    if not isinstance(evidence, dict):
        return {}
    trace_path = str(evidence.get("trace_path") or "").strip()
    if not trace_path:
        return {}

    operator = failure_report.get("operator") if isinstance(failure_report, dict) else {}
    operator = operator if isinstance(operator, dict) else {}
    command = str(action_item.get("trace_viewer_command") or operator.get("trace_viewer_command") or "").strip()
    hint = str(action_item.get("trace_viewer_hint") or operator.get("trace_viewer_hint") or "").strip()
    return {
        "trace_viewer_command": command or _trace_viewer_command(trace_path),
        "trace_viewer_hint": hint or _TRACE_VIEWER_HINT,
    }


def _repair_commands_for_item(
    *,
    input_path: Path,
    base_dir: Path,
    action_item: dict[str, Any],
    item_issues: list[dict[str, str]],
    evidence_gate: dict[str, Any],
) -> list[str]:
    if evidence_gate.get("status") != "fix_evidence_first":
        return []

    commands = [_doctor_rerun_command(input_path=input_path, base_dir=base_dir)]
    source = str(action_item.get("source") or "").strip()
    if source and source != "unknown":
        issue_codes = {str(issue.get("code") or "") for issue in item_issues}
        evidence = action_item.get("evidence")
        include_trace = any("trace_path" in code for code in issue_codes) or (
            isinstance(evidence, dict) and bool(evidence.get("trace_path"))
        )
        commands.append(
            _source_preflight_capture_command(source=source, input_path=input_path, include_trace=include_trace)
        )
    return commands


def build_evidence_payload(
    input_path: Path,
    *,
    base_dir: Path | None = None,
    max_json_bytes: int = DEFAULT_MAX_JSON_BYTES,
) -> dict[str, Any]:
    base_dir = (base_dir or Path.cwd()).resolve()
    resolved_input = _resolve_explicit_input_path(input_path, base_dir)
    report, load_issue = _read_json_file(resolved_input, max_bytes=max_json_bytes)
    issues: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    if load_issue:
        issues.append(load_issue)
    elif report is not None:
        actions = _problem_actions(report)
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        problem_count = summary.get("problem_count") if isinstance(summary, dict) else None
        if isinstance(problem_count, int) and problem_count > 0 and not actions:
            issues.append(
                _issue(
                    "warning",
                    "problem_actions_missing",
                    "Report has problem_count > 0 but no summary.problem_actions.",
                    path=str(resolved_input),
                )
            )

        for index, action_item in enumerate(actions):
            item_issues: list[dict[str, str]] = []
            if not isinstance(action_item, dict):
                item_issues.append(
                    _issue("error", "problem_action_not_object", "Expected problem action to be an object.")
                )
                repair_commands = [_doctor_rerun_command(input_path=resolved_input, base_dir=base_dir)]
                items.append(
                    {
                        "index": index,
                        "issues": item_issues,
                        "evidence_gate": {
                            "status": "fix_evidence_first",
                            "strategy_change_ready": False,
                            "decision": "fix_evidence_first",
                            "reason": "Problem action is not an object.",
                            "evidence_fields": [],
                            "missing_required_evidence": ["problem_action"],
                        },
                        "repair_commands": repair_commands,
                    }
                )
                issues.extend(item_issues)
                continue

            source = str(action_item.get("source") or "unknown")
            status_text = str(action_item.get("status") or "")
            operator_action_value = str(action_item.get("operator_action") or action_item.get("action") or "").strip()
            explicit_operator_action_required = "operator_action_required" in action_item
            if explicit_operator_action_required:
                operator_action_required = _as_bool(action_item.get("operator_action_required"))
            else:
                operator_action_required = False
            evidence = action_item.get("evidence")
            failure_report_value = evidence.get("failure_report_path") if isinstance(evidence, dict) else None
            failure_report_path = None
            failure_report = None
            failure_report_status = "missing"
            if not isinstance(evidence, dict) or not evidence:
                item_issues.append(
                    _issue("warning", "missing_evidence", "Problem action has no evidence object.", source=source)
                )
            elif not failure_report_value:
                item_issues.append(
                    _issue(
                        "warning",
                        "missing_failure_report_path",
                        "Problem action evidence has no failure_report_path.",
                        source=source,
                    )
                )
            else:
                failure_report_path = _resolve_path(str(failure_report_value), base_dir)
                failure_report, report_issues = _validate_failure_report(
                    failure_report_path=failure_report_path,
                    action_item=action_item,
                    base_dir=base_dir,
                    max_json_bytes=max_json_bytes,
                )
                item_issues.extend(report_issues)
                failure_report_status = "valid" if failure_report and not report_issues else "invalid"

            failure_report_operator = (
                failure_report.get("operator")
                if isinstance(failure_report, dict) and isinstance(failure_report.get("operator"), dict)
                else {}
            )
            if not operator_action_value:
                failure_report_action = str(failure_report_operator.get("action") or "").strip()
                if failure_report_action:
                    operator_action_value = failure_report_action
            if not explicit_operator_action_required:
                if "action_required" in failure_report_operator and failure_report_status == "valid":
                    operator_action_required = _as_bool(failure_report_operator.get("action_required"))
                else:
                    operator_action_required = bool(operator_action_value) or status_text != "ready"

            evidence_gate = _evidence_gate(
                action_item,
                failure_report_status=failure_report_status,
                item_issues=item_issues,
            )
            if (
                evidence_gate["status"] == "fix_evidence_first"
                and not item_issues
                and evidence_gate["missing_required_evidence"]
            ):
                item_issues.append(
                    _issue(
                        "warning",
                        "insufficient_strategy_evidence",
                        "Required strategy-review evidence is missing.",
                        source=source,
                    )
                )
                evidence_gate = _evidence_gate(
                    action_item,
                    failure_report_status=failure_report_status,
                    item_issues=item_issues,
                )
            issues.extend(item_issues)
            repair_commands = _repair_commands_for_item(
                input_path=resolved_input,
                base_dir=base_dir,
                action_item=action_item,
                item_issues=item_issues,
                evidence_gate=evidence_gate,
            )
            trace_viewer_details = _trace_viewer_details(action_item, failure_report)
            items.append(
                {
                    "index": index,
                    "source": source,
                    "status": action_item.get("status"),
                    "operator_action_required": operator_action_required,
                    "operator_action": operator_action_value,
                    "evidence": _evidence_snapshot(evidence),
                    "failure_report_path": str(failure_report_path) if failure_report_path else "",
                    "failure_report_status": failure_report_status,
                    "issue_count": len(item_issues),
                    "issues": item_issues,
                    "evidence_gate": evidence_gate,
                    **trace_viewer_details,
                    "repair_commands": repair_commands,
                }
            )

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    failure_report_count = sum(1 for item in items if item.get("failure_report_path"))
    evidence_gate_status_counts: dict[str, int] = {}
    for item in items:
        gate = item.get("evidence_gate") if isinstance(item.get("evidence_gate"), dict) else {}
        gate_status = str(gate.get("status") or "unknown")
        evidence_gate_status_counts[gate_status] = evidence_gate_status_counts.get(gate_status, 0) + 1
    strategy_change_ready_count = sum(
        1
        for item in items
        if isinstance(item.get("evidence_gate"), dict) and item["evidence_gate"].get("strategy_change_ready") is True
    )
    repair_command_count = sum(len(item.get("repair_commands") or []) for item in items)
    status = "FAIL" if error_count else "WARN" if warning_count else "PASS"
    return {
        "ok": error_count == 0,
        "status": status,
        "input_path": str(resolved_input),
        "base_dir": str(base_dir),
        "summary": {
            "problem_action_count": len(items),
            "failure_report_count": failure_report_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "strategy_change_ready_count": strategy_change_ready_count,
            "evidence_gate_status_counts": evidence_gate_status_counts,
            "repair_command_count": repair_command_count,
        },
        "items": items,
        "issues": issues,
        "next_step": _next_step(status),
    }


def _next_step(status: str) -> str:
    if status == "PASS":
        return "Evidence is structurally complete; inspect operator.action before changing selectors or timeouts."
    if status == "WARN":
        return "Review warnings; rerun with --fail-on-warning in automation if warnings should block the run."
    return "Fix missing or invalid evidence files before changing source strategy."


def exit_code_for_payload(payload: dict[str, Any], *, fail_on_warning: bool = False) -> int:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    error_count = int(summary.get("error_count") or 0)
    warning_count = int(summary.get("warning_count") or 0)
    if error_count:
        return 2
    if fail_on_warning and warning_count:
        return 1
    return 0


def _print_text_report(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    print("[SOURCE PREFLIGHT EVIDENCE DOCTOR]")
    print(f"  input: {payload['input_path']}")
    print(f"  status: {payload['status']}")
    print(f"  problem_actions: {summary['problem_action_count']}")
    print(f"  failure_reports: {summary['failure_report_count']}")
    print(f"  errors: {summary['error_count']}")
    print(f"  warnings: {summary['warning_count']}")
    print(f"  strategy_change_ready: {summary.get('strategy_change_ready_count', 0)}")
    print(f"  evidence_gates: {summary.get('evidence_gate_status_counts') or {}}")
    print(f"  repair_commands: {summary.get('repair_command_count', 0)}")
    for issue in payload["issues"]:
        location = f" path={issue['path']}" if issue.get("path") else ""
        source = f" source={issue['source']}" if issue.get("source") else ""
        print(f"  - {issue['severity']} {issue['code']}{source}{location}: {issue['message']}")
    for item in payload["items"]:
        item_source = f" source={item.get('source')}" if item.get("source") else ""
        if "operator_action_required" in item or item.get("operator_action"):
            required = str(bool(item.get("operator_action_required"))).lower()
            action = str(item.get("operator_action") or "-")
            print(f"  operator_action item={item.get('index')}{item_source}: required={required} action={action}")
        if item.get("trace_viewer_command"):
            print(f"  trace_viewer item={item.get('index')}{item_source}: {item['trace_viewer_command']}")
        commands = item.get("repair_commands") or []
        if not commands:
            continue
        print(f"  repair_commands item={item.get('index')}{item_source}:")
        for index, command in enumerate(commands, start=1):
            print(f"    {index}. {command}")
    print(f"  next_step: {payload['next_step']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate source preflight failure evidence without browser or network IO."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Source preflight JSON report.")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(), help="Base directory for relative evidence paths.")
    parser.add_argument(
        "--max-json-bytes", type=int, default=DEFAULT_MAX_JSON_BYTES, help="Safety limit per JSON file."
    )
    parser.add_argument("--json", action="store_true", help="Print a structured JSON doctor report.")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit 1 when warnings are present.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_evidence_payload(args.input, base_dir=args.base_dir, max_json_bytes=max(1, args.max_json_bytes))
    if args.json:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    else:
        _print_text_report(payload)
    return exit_code_for_payload(payload, fail_on_warning=args.fail_on_warning)


if __name__ == "__main__":
    raise SystemExit(main())
