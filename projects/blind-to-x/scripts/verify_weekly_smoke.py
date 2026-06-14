from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

BTX_ROOT = Path(__file__).resolve().parent.parent
if str(BTX_ROOT) not in sys.path:
    sys.path.insert(0, str(BTX_ROOT))

from scripts.source_preflight_strategy_simulation import _format_summary as _format_strategy_summary  # noqa: E402

DEFAULT_REPORT_PATH = Path(".tmp/weekly_report_smoke.md")
DEFAULT_REVIEW_RECORDS_PATH = Path(".tmp/review_queue_report_sample.json")
DEFAULT_REVIEW_EXPERIMENT_PATH = Path(".tmp/weekly_report_experiment_smoke.json")
DEFAULT_SOURCE_PREFLIGHT_TREND_PATH = Path(".tmp/source_preflight_trend.json")
DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH = Path(".tmp/source_preflight_strategy_simulation.json")
DEFAULT_RECOMPUTE_CONTRACT_PATH = Path(".tmp/recompute_scores_runtime_contract_smoke.json")
REVIEW_SUMMARY_TIMEOUT_SECONDS = 30
REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS = 4000
EXPECTED_MANIFEST_SCHEMA_VERSION = 1
EXPECTED_MANIFEST_PROFILE = "weekly_report_ab_source_preflight"
EXPECTED_MANIFEST_SAFETY_CONTRACT = {
    "read_only": True,
    "browser_launches": False,
    "notion_writes": False,
    "x_posts": False,
    "provider_calls": False,
    "db_writes": False,
    "writes_local_json_only": True,
}
EXPECTED_MANIFEST_REPORT_FRAGMENTS = [
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
EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS = [
    "missing_metric_rate=0.7",
    "top_missing_metric=latency_ms",
    "operator_actions_total=5",
    "provider_failure_categories=auth=1,rate_limit=1",
    "provider_failure_providers=gemini=1,openai=1",
    "primary_provider_failure_categories=auth=1",
    "primary_provider_failure_providers=openai=1",
    "rollout_blocker_count=2",
    "rollout_blocker_codes=missing_metric_rate_high,operator_action_noise_high",
    "top_rollout_blocker_action=provider_telemetry: Include latency_ms from generation telemetry in review records.",
]
EXPECTED_MANIFEST_STRATEGY_STDOUT_FRAGMENTS = [
    "source_preflight_strategy_simulation=(not written)",
    "recommendation=repair_evidence_first",
    "gate=blocked_repair_evidence",
    "manual_ready_gate=blocked",
    "repair_command_count=6",
    "repair_queue=ok",
    "primary_repair_type=evidence_doctor",
    "primary_repair_count=1",
    "primary_repair_buckets=blind|blocked=1",
    "primary_repair_sources=blind=1",
    "repair_remaining=5",
    "metric_missing=current:2/10,candidate:2/10",
    "operator_action_mismatch_count=1",
    "operator_action_mismatch_sources=ppomppu=1",
    "scope=local_preflight_evidence",
]
EXPECTED_MANIFEST_COMMAND_KEYS = [
    "write_inputs",
    "review_summary",
    "build_report",
    "verify_text",
    "verify_json",
]
METRIC_MISSING_FRAGMENT_PATTERN = re.compile(r"\bmetric_missing=current:\d+/\d+,candidate:\d+/\d+\b")


def _path_from_mapping(mapping: dict[str, Any], key: str) -> Path | None:
    value = mapping.get(key)
    if isinstance(value, str) and value.strip():
        return Path(value)
    return None


def _read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"read_failed:{path}:{exc.__class__.__name__}")
    return ""


def _read_json_object(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"json_read_failed:{path}:{exc.__class__.__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"json_not_object:{path}")
        return {}
    return payload


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    return summary if isinstance(summary, dict) else {}


def _first_mapping(items: Any) -> dict[str, Any]:
    if not isinstance(items, list) or not items:
        return {}
    item = items[0]
    return item if isinstance(item, dict) else {}


def _count_sort_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _manifest_value_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def _repair_queue_count_total(items: Any) -> int:
    if not isinstance(items, list):
        return 0
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        count = _count_sort_value(item.get("count"))
        if count > 0:
            total += count
    return total


def _repair_queue_consistency(summary: dict[str, Any]) -> dict[str, Any]:
    consistency = summary.get("repair_command_queue_consistency")
    return consistency if isinstance(consistency, dict) else {}


def _repair_queue_primary_target_payload(
    strategy_repair_queue: list[Any], manual_ready_gate: dict[str, Any]
) -> dict[str, Any]:
    primary_repair_command = str(manual_ready_gate.get("primary_repair_command") or "").strip()
    fallback: dict[str, Any] | None = None
    for item in strategy_repair_queue:
        if not isinstance(item, dict):
            continue
        if fallback is None:
            fallback = item
        if primary_repair_command and str(item.get("command") or "").strip() == primary_repair_command:
            fallback = item
            break
    if not fallback:
        return {"present": False}
    sources = fallback.get("sources") if isinstance(fallback.get("sources"), dict) else {}
    buckets = fallback.get("buckets") if isinstance(fallback.get("buckets"), dict) else {}
    return {
        "present": True,
        "command": str(fallback.get("command") or "").strip(),
        "type": str(fallback.get("type") or "").strip(),
        "count": _count_sort_value(fallback.get("count")),
        "buckets": dict(sorted((str(key), value) for key, value in buckets.items())),
        "sources": dict(sorted((str(key), value) for key, value in sources.items())),
    }


def _repair_queue_payload(source_strategy: dict[str, Any]) -> dict[str, Any]:
    strategy_summary = _summary(source_strategy)
    manual_ready_gate = source_strategy.get("manual_ready_gate")
    manual_ready_gate = manual_ready_gate if isinstance(manual_ready_gate, dict) else {}
    repair_commands = manual_ready_gate.get("repair_commands")
    repair_commands = repair_commands if isinstance(repair_commands, list) else []
    strategy_repair_queue = strategy_summary.get("repair_command_queue")
    strategy_repair_queue = strategy_repair_queue if isinstance(strategy_repair_queue, list) else []
    strategy_repair_queue_consistency = _repair_queue_consistency(strategy_summary)
    repair_command_count = _count_sort_value(manual_ready_gate.get("repair_command_count"))
    queue_count_total = _repair_queue_count_total(strategy_repair_queue)
    consistency_status = str(strategy_repair_queue_consistency.get("status") or "").strip()
    if not consistency_status and (repair_command_count or queue_count_total):
        consistency_status = "ok" if queue_count_total == repair_command_count else "mismatch"
    consistency_repair_command_count = _count_sort_value(strategy_repair_queue_consistency.get("repair_command_count"))
    consistency_queue_count_total = _count_sort_value(strategy_repair_queue_consistency.get("queue_count_total"))
    if not consistency_repair_command_count and repair_command_count:
        consistency_repair_command_count = repair_command_count
    if not consistency_queue_count_total and queue_count_total:
        consistency_queue_count_total = queue_count_total
    present = bool(
        repair_command_count or repair_commands or strategy_repair_queue or strategy_repair_queue_consistency
    )
    if not present:
        return {}
    return {
        "present": True,
        "total": repair_command_count,
        "listed": len(repair_commands),
        "count_total": queue_count_total,
        "consistency": consistency_status or "not_available",
        "full_queue_available": (
            consistency_status == "ok"
            and queue_count_total >= repair_command_count
            and consistency_repair_command_count == repair_command_count
            and consistency_queue_count_total == queue_count_total
        ),
        "queue_item_count": len(strategy_repair_queue),
        "primary_repair_command_present": bool(str(manual_ready_gate.get("primary_repair_command") or "").strip()),
        "primary_repair_target": _repair_queue_primary_target_payload(strategy_repair_queue, manual_ready_gate),
        "source": "manual_ready_gate.repair_commands",
    }


def _read_repair_queue_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return _repair_queue_payload(payload)


def build_manifest_repair_queue_payload(manifest: dict[str, Any]) -> dict[str, Any] | None:
    expected = manifest.get("expected_repair_queue")
    if expected is None:
        return None

    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    strategy_path = paths.get("source_preflight_strategy")
    strategy_path_text = strategy_path.strip() if isinstance(strategy_path, str) else ""
    expected_is_object = isinstance(expected, dict)
    expected_keys = sorted(expected.keys()) if expected_is_object else []
    actual = _read_repair_queue_payload(Path(strategy_path_text)) if strategy_path_text else {}

    matched_key_count = 0
    mismatched_keys: list[str] = []
    if expected_is_object and actual:
        for key in expected_keys:
            if actual.get(key) == expected[key]:
                matched_key_count += 1
            else:
                mismatched_keys.append(key)

    checked = expected_is_object and bool(strategy_path_text) and bool(actual)
    ok = checked and not mismatched_keys
    return {
        "ok": ok,
        "status": "ok" if ok else "fail",
        "expected_present": True,
        "expected_is_object": expected_is_object,
        "checked": checked,
        "actual_present": bool(actual),
        "expected_key_count": len(expected_keys),
        "actual_key_count": len(actual),
        "matched_key_count": matched_key_count,
        "mismatch_count": len(mismatched_keys) if checked else 0,
        "mismatched_keys": mismatched_keys if checked else [],
        "source_preflight_strategy": strategy_path_text or None,
    }


def read_manifest_repair_queue_payload(manifest_path: Path) -> dict[str, Any] | None:
    errors: list[str] = []
    manifest = _read_json_object(manifest_path, errors)
    if errors or not manifest:
        return None
    return build_manifest_repair_queue_payload(manifest)


def validate_manifest_contract(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_version = manifest.get("schema_version")
    if schema_version != EXPECTED_MANIFEST_SCHEMA_VERSION:
        errors.append(f"manifest_schema_version_mismatch:expected=1,actual={schema_version}")
    profile = manifest.get("profile")
    if profile != EXPECTED_MANIFEST_PROFILE:
        errors.append(f"manifest_profile_mismatch:expected={EXPECTED_MANIFEST_PROFILE},actual={profile}")

    safety_contract = manifest.get("safety_contract")
    if not isinstance(safety_contract, dict):
        errors.append("manifest_missing_safety_contract")
    else:
        for key, expected in EXPECTED_MANIFEST_SAFETY_CONTRACT.items():
            actual = safety_contract.get(key)
            if actual is not expected:
                errors.append(f"manifest_safety_mismatch:{key}=expected_{str(expected).lower()},actual_{actual}")

    expected_fragments = manifest.get("expected_report_fragments")
    if not isinstance(expected_fragments, list):
        errors.append("manifest_missing_expected_report_fragments")
    else:
        for fragment in EXPECTED_MANIFEST_REPORT_FRAGMENTS:
            if fragment not in expected_fragments:
                errors.append(f"manifest_missing_expected_fragment:{fragment}")

    expected_review_stdout_fragments = manifest.get("expected_review_stdout_fragments")
    if not isinstance(expected_review_stdout_fragments, list):
        errors.append("manifest_missing_expected_review_stdout_fragments")
    else:
        for fragment in EXPECTED_MANIFEST_REVIEW_STDOUT_FRAGMENTS:
            if fragment not in expected_review_stdout_fragments:
                errors.append(f"manifest_missing_expected_review_stdout_fragment:{fragment}")
    _validate_manifest_commands(manifest, errors)
    return errors


def validate_manifest_repair_queue_contract(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _validate_manifest_expected_repair_queue(manifest, errors)
    return errors


def _validate_manifest_expected_repair_queue(manifest: dict[str, Any], errors: list[str]) -> None:
    expected = manifest.get("expected_repair_queue")
    if expected is None:
        return
    if not isinstance(expected, dict):
        errors.append("manifest_expected_repair_queue_not_object")
        return

    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    strategy_path = paths.get("source_preflight_strategy")
    if not isinstance(strategy_path, str) or not strategy_path.strip():
        errors.append("manifest_expected_repair_queue_missing_strategy_path")
        return

    actual = _read_repair_queue_payload(Path(strategy_path))
    if not actual:
        errors.append("manifest_expected_repair_queue_unavailable")
        return

    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            errors.append(
                "manifest_expected_repair_queue_mismatch:"
                f"{key}=expected_{_manifest_value_text(expected_value)},"
                f"actual_{_manifest_value_text(actual_value)}"
            )


def _validate_manifest_commands(manifest: dict[str, Any], errors: list[str]) -> None:
    commands = manifest.get("commands")
    if not isinstance(commands, dict):
        errors.append("manifest_missing_commands")
        return

    expected_keys = list(EXPECTED_MANIFEST_COMMAND_KEYS)
    manifest_path = manifest.get("manifest")
    if isinstance(manifest_path, str) and manifest_path.strip():
        expected_keys.append("verify_manifest")

    command_values: dict[str, str] = {}
    for key in expected_keys:
        value = commands.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"manifest_missing_command:{key}")
            continue
        command_values[key] = value

    write_inputs_command = command_values.get("write_inputs", "")
    if write_inputs_command:
        _require_command_fragment(
            errors=errors,
            key="write_inputs",
            command=write_inputs_command,
            fragment="scripts/write_weekly_smoke_inputs.py",
        )
        _require_command_fragment(
            errors=errors,
            key="write_inputs",
            command=write_inputs_command,
            fragment="--output-dir",
        )
        if isinstance(manifest_path, str) and manifest_path.strip():
            _require_command_option_value(
                errors=errors,
                key="write_inputs",
                command=write_inputs_command,
                option="--manifest-output",
                value=manifest_path,
            )
        if "self_check" in manifest:
            _require_command_fragment(
                errors=errors,
                key="write_inputs",
                command=write_inputs_command,
                fragment="--self-check",
            )

    review_summary_command = command_values.get("review_summary", "")
    if review_summary_command:
        _require_command_fragment(
            errors=errors,
            key="review_summary",
            command=review_summary_command,
            fragment="scripts/review_experiment_dry_run.py",
        )
        _require_command_fragment(
            errors=errors,
            key="review_summary",
            command=review_summary_command,
            fragment="--input-mode review-records",
        )
        _require_command_fragment(
            errors=errors,
            key="review_summary",
            command=review_summary_command,
            fragment="--max-missing-rate 0.25",
        )
        _require_command_fragment(
            errors=errors,
            key="review_summary",
            command=review_summary_command,
            fragment="--summary-only",
        )
        paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
        review_records_path = paths.get("review_records")
        if isinstance(review_records_path, str) and review_records_path.strip():
            _require_command_option_value(
                errors=errors,
                key="review_summary",
                command=review_summary_command,
                option="--input",
                value=review_records_path,
            )

    verify_json_command = command_values.get("verify_json", "")
    if verify_json_command:
        _require_command_fragment(errors=errors, key="verify_json", command=verify_json_command, fragment="--json")

    verify_manifest_command = command_values.get("verify_manifest", "")
    if verify_manifest_command and isinstance(manifest_path, str) and manifest_path.strip():
        _require_command_option_value(
            errors=errors,
            key="verify_manifest",
            command=verify_manifest_command,
            option="--manifest",
            value=manifest_path,
        )
        _require_command_fragment(
            errors=errors,
            key="verify_manifest",
            command=verify_manifest_command,
            fragment="--verify-review-summary",
        )
        if manifest.get("expected_strategy_stdout_fragments") is not None:
            _require_command_fragment(
                errors=errors,
                key="verify_manifest",
                command=verify_manifest_command,
                fragment="--verify-strategy-summary",
            )


def _require_command_fragment(*, errors: list[str], key: str, command: str, fragment: str) -> None:
    if fragment not in command:
        errors.append(f"manifest_command_missing_fragment:{key}:{fragment}")


def _require_command_option_value(
    *,
    errors: list[str],
    key: str,
    command: str,
    option: str,
    value: str,
) -> None:
    fragment = f"{option} {value}"
    quoted_fragment = f'{option} "{value}"'
    powershell_value = value.replace("'", "''")
    powershell_quoted_fragment = f"{option} '{powershell_value}'"
    if fragment not in command and quoted_fragment not in command and powershell_quoted_fragment not in command:
        errors.append(f"manifest_command_missing_fragment:{key}:{fragment}")


def resolve_manifest_paths(
    manifest_path: Path,
) -> tuple[Path, Path, Path, Path, Path, list[str]]:
    errors: list[str] = []
    manifest = _read_json_object(manifest_path, errors)
    if manifest:
        errors.extend(validate_manifest_contract(manifest))
        errors.extend(validate_manifest_repair_queue_contract(manifest))
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    expected_outputs = manifest.get("expected_outputs") if isinstance(manifest.get("expected_outputs"), dict) else {}

    resolved = {
        "report": _path_from_mapping(expected_outputs, "report") or _path_from_mapping(paths, "report"),
        "review_experiment": _path_from_mapping(paths, "review_experiment"),
        "source_preflight_trend": _path_from_mapping(paths, "source_preflight_trend"),
        "source_preflight_strategy": _path_from_mapping(paths, "source_preflight_strategy"),
        "recompute_contract": _path_from_mapping(paths, "recompute_contract"),
    }
    missing = [name for name, path in resolved.items() if path is None]
    for name in missing:
        errors.append(f"manifest_missing_path:{name}")

    return (
        resolved["report"] or DEFAULT_REPORT_PATH,
        resolved["review_experiment"] or DEFAULT_REVIEW_EXPERIMENT_PATH,
        resolved["source_preflight_trend"] or DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
        resolved["source_preflight_strategy"] or DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
        resolved["recompute_contract"] or DEFAULT_RECOMPUTE_CONTRACT_PATH,
        errors,
    )


def resolve_manifest_review_summary_contract(manifest_path: Path) -> tuple[Path, list[str], list[str]]:
    errors: list[str] = []
    manifest = _read_json_object(manifest_path, errors)
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    review_records_path = _path_from_mapping(paths, "review_records")
    if review_records_path is None:
        errors.append("manifest_missing_path:review_records")

    expected_review_stdout_fragments = manifest.get("expected_review_stdout_fragments")
    fragments: list[str] = []
    if not isinstance(expected_review_stdout_fragments, list):
        errors.append("manifest_missing_expected_review_stdout_fragments")
    else:
        for fragment in expected_review_stdout_fragments:
            if not isinstance(fragment, str) or not fragment.strip():
                errors.append(f"manifest_invalid_expected_review_stdout_fragment:{fragment}")
                continue
            fragments.append(fragment)
    return review_records_path or DEFAULT_REVIEW_RECORDS_PATH, fragments, errors


def resolve_manifest_strategy_summary_contract(manifest_path: Path) -> tuple[Path, list[str], list[str], bool]:
    errors: list[str] = []
    manifest = _read_json_object(manifest_path, errors)
    if errors:
        return DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH, [], errors, False
    return resolve_manifest_strategy_summary_contract_from_payload(manifest)


def build_review_summary_verification_payload(
    *,
    review_records_path: Path,
    expected_fragments: list[str],
    errors: list[str],
    executed: bool,
    returncode: int | None,
    child_error_tail: str | None = None,
    child_error_tail_source: str | None = None,
    child_error_tail_truncated: bool = False,
) -> dict[str, Any]:
    missing_stdout_fragment_count = sum(
        1 for error in errors if error.startswith("missing_review_summary_stdout_fragment:")
    )
    failure_reasons = _review_summary_failure_reasons(errors)
    matched_stdout_fragment_count = (
        max(len(expected_fragments) - missing_stdout_fragment_count, 0)
        if executed and "timeout" not in failure_reasons
        else 0
    )
    payload: dict[str, Any] = {
        "ok": not errors,
        "status": "ok" if not errors else "fail",
        "diagnosis": failure_reasons[0] if failure_reasons else "ok",
        "failure_reasons": failure_reasons,
        "executed": executed,
        "review_records": review_records_path.as_posix(),
        "expected_stdout_fragment_count": len(expected_fragments),
        "matched_stdout_fragment_count": matched_stdout_fragment_count,
        "missing_stdout_fragment_count": missing_stdout_fragment_count,
        "missing_stdout_fragments": _review_summary_missing_stdout_fragments(errors),
        "missing_input": "missing_input" in failure_reasons,
        "stdout_drift": "stdout_drift" in failure_reasons,
        "timeout": "timeout" in failure_reasons,
        "nonzero_exit": "nonzero_exit" in failure_reasons,
        "run_failed": "run_failed" in failure_reasons,
        "manifest_contract_error": "manifest_contract" in failure_reasons,
        "returncode": returncode,
        "timeout_seconds": REVIEW_SUMMARY_TIMEOUT_SECONDS,
    }
    if child_error_tail:
        payload["child_error_tail"] = child_error_tail
        payload["child_error_tail_source"] = child_error_tail_source or "unknown"
        payload["child_error_tail_truncated"] = child_error_tail_truncated
    return payload


def build_strategy_summary_verification_payload(
    *,
    source_preflight_strategy_path: Path,
    expected_fragments: list[str],
    errors: list[str],
    executed: bool,
) -> dict[str, Any]:
    missing_stdout_fragment_count = sum(1 for error in errors if error.startswith("missing_strategy_stdout_fragment:"))
    failure_reasons = _strategy_summary_failure_reasons(errors)
    matched_stdout_fragment_count = max(len(expected_fragments) - missing_stdout_fragment_count, 0) if executed else 0
    return {
        "ok": not errors,
        "status": "ok" if not errors else "fail",
        "diagnosis": failure_reasons[0] if failure_reasons else "ok",
        "failure_reasons": failure_reasons,
        "executed": executed,
        "source_preflight_strategy": source_preflight_strategy_path.as_posix(),
        "expected_stdout_fragment_count": len(expected_fragments),
        "matched_stdout_fragment_count": matched_stdout_fragment_count,
        "missing_stdout_fragment_count": missing_stdout_fragment_count,
        "missing_stdout_fragments": _strategy_summary_missing_stdout_fragments(errors),
        "missing_input": "missing_input" in failure_reasons,
        "stdout_drift": "stdout_drift" in failure_reasons,
        "format_failed": "format_failed" in failure_reasons,
        "manifest_contract_error": "manifest_contract" in failure_reasons,
    }


def _review_summary_missing_stdout_fragments(errors: list[str]) -> list[str]:
    prefix = "missing_review_summary_stdout_fragment:"
    return [error.removeprefix(prefix) for error in errors if error.startswith(prefix)]


def _strategy_summary_missing_stdout_fragments(errors: list[str]) -> list[str]:
    prefix = "missing_strategy_stdout_fragment:"
    return [error.removeprefix(prefix) for error in errors if error.startswith(prefix)]


def _review_summary_failure_reasons(errors: list[str]) -> list[str]:
    reasons: list[str] = []
    if any(error.startswith("review_summary_missing_input:") for error in errors):
        reasons.append("missing_input")
    if any(error.startswith("manifest_") for error in errors):
        reasons.append("manifest_contract")
    if "review_summary_timeout" in errors:
        reasons.append("timeout")
    if any(error.startswith("review_summary_run_failed:") for error in errors):
        reasons.append("run_failed")
    if any(error.startswith("review_summary_exit_code:") for error in errors):
        reasons.append("nonzero_exit")
    if any(error.startswith("missing_review_summary_stdout_fragment:") for error in errors):
        reasons.append("stdout_drift")
    if errors and not reasons:
        reasons.append("unknown")
    return reasons


def _strategy_summary_failure_reasons(errors: list[str]) -> list[str]:
    reasons: list[str] = []
    if any(error.startswith("strategy_summary_missing_input:") for error in errors):
        reasons.append("missing_input")
    if any(error.startswith("manifest_") for error in errors):
        reasons.append("manifest_contract")
    if any(error.startswith("strategy_summary_format_failed:") for error in errors):
        reasons.append("format_failed")
    if any(error.startswith("missing_strategy_stdout_fragment:") for error in errors):
        reasons.append("stdout_drift")
    if errors and not reasons:
        reasons.append("unknown")
    return reasons


def _review_summary_child_output_text(raw_output: str | bytes | None) -> str:
    if raw_output is None:
        return ""
    if isinstance(raw_output, bytes):
        return raw_output.decode("utf-8", errors="replace")
    return raw_output


def _bounded_review_summary_tail(*, raw_output: str | bytes | None, source: str) -> tuple[str | None, str | None, bool]:
    normalized = _review_summary_child_output_text(raw_output).strip()
    if not normalized:
        return None, None, False
    truncated = len(normalized) > REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS
    if truncated:
        normalized = normalized[-REVIEW_SUMMARY_CHILD_ERROR_TAIL_MAX_CHARS:]
    return normalized, source, truncated


def _bounded_review_summary_child_error_tail(
    *, stderr: str | bytes | None, stdout: str | bytes | None
) -> tuple[str | None, str | None, bool]:
    for source, raw_output in (("stderr", stderr), ("stdout", stdout)):
        tail = _bounded_review_summary_tail(raw_output=raw_output, source=source)
        if tail[0]:
            return tail
    return None, None, False


def _bounded_review_summary_exception_tail(exc: BaseException) -> tuple[str | None, str | None, bool]:
    exception_text = f"{exc.__class__.__name__}: {exc}".strip()
    if exception_text.endswith(":"):
        exception_text = exc.__class__.__name__
    return _bounded_review_summary_tail(raw_output=exception_text, source="exception")


def run_review_summary_stdout_verification(
    *, review_records_path: Path, expected_fragments: list[str]
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if not review_records_path.exists():
        errors.append(f"review_summary_missing_input:{review_records_path}")
        return errors, build_review_summary_verification_payload(
            review_records_path=review_records_path,
            expected_fragments=expected_fragments,
            errors=errors,
            executed=False,
            returncode=None,
        )

    command = [
        sys.executable,
        "scripts/review_experiment_dry_run.py",
        "--input-mode",
        "review-records",
        "--input",
        str(review_records_path),
        "--min-items",
        "1",
        "--max-missing-rate",
        "0.25",
        "--summary-only",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=BTX_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=REVIEW_SUMMARY_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        errors.append("review_summary_timeout")
        child_error_tail, child_error_tail_source, child_error_tail_truncated = (
            _bounded_review_summary_child_error_tail(stderr=exc.stderr, stdout=exc.stdout)
        )
        return errors, build_review_summary_verification_payload(
            review_records_path=review_records_path,
            expected_fragments=expected_fragments,
            errors=errors,
            executed=True,
            returncode=None,
            child_error_tail=child_error_tail,
            child_error_tail_source=child_error_tail_source,
            child_error_tail_truncated=child_error_tail_truncated,
        )
    except OSError as exc:
        errors.append(f"review_summary_run_failed:{exc.__class__.__name__}")
        child_error_tail, child_error_tail_source, child_error_tail_truncated = _bounded_review_summary_exception_tail(
            exc
        )
        return errors, build_review_summary_verification_payload(
            review_records_path=review_records_path,
            expected_fragments=expected_fragments,
            errors=errors,
            executed=False,
            returncode=None,
            child_error_tail=child_error_tail,
            child_error_tail_source=child_error_tail_source,
            child_error_tail_truncated=child_error_tail_truncated,
        )

    child_error_tail = None
    child_error_tail_source = None
    child_error_tail_truncated = False
    if result.returncode != 0:
        errors.append(f"review_summary_exit_code:{result.returncode}")
        (
            child_error_tail,
            child_error_tail_source,
            child_error_tail_truncated,
        ) = _bounded_review_summary_child_error_tail(stderr=result.stderr, stdout=result.stdout)
    stdout = result.stdout or ""
    for fragment in expected_fragments:
        if fragment not in stdout:
            errors.append(f"missing_review_summary_stdout_fragment:{fragment}")
    return errors, build_review_summary_verification_payload(
        review_records_path=review_records_path,
        expected_fragments=expected_fragments,
        errors=errors,
        executed=True,
        returncode=result.returncode,
        child_error_tail=child_error_tail,
        child_error_tail_source=child_error_tail_source,
        child_error_tail_truncated=child_error_tail_truncated,
    )


def verify_review_summary_stdout(*, review_records_path: Path, expected_fragments: list[str]) -> list[str]:
    errors, _payload = run_review_summary_stdout_verification(
        review_records_path=review_records_path,
        expected_fragments=expected_fragments,
    )
    return errors


def run_strategy_summary_stdout_verification(
    *, source_preflight_strategy_path: Path, expected_fragments: list[str]
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if not source_preflight_strategy_path.exists():
        errors.append(f"strategy_summary_missing_input:{source_preflight_strategy_path}")
        return errors, build_strategy_summary_verification_payload(
            source_preflight_strategy_path=source_preflight_strategy_path,
            expected_fragments=expected_fragments,
            errors=errors,
            executed=False,
        )

    source_strategy = _read_json_object(source_preflight_strategy_path, errors)
    stdout = ""
    executed = False
    if source_strategy:
        try:
            stdout = _format_strategy_summary(source_strategy, "(not written)")
            executed = True
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"strategy_summary_format_failed:{exc.__class__.__name__}")

    for fragment in expected_fragments:
        if fragment not in stdout:
            errors.append(f"missing_strategy_stdout_fragment:{fragment}")
    return errors, build_strategy_summary_verification_payload(
        source_preflight_strategy_path=source_preflight_strategy_path,
        expected_fragments=expected_fragments,
        errors=errors,
        executed=executed,
    )


def verify_strategy_summary_stdout(*, source_preflight_strategy_path: Path, expected_fragments: list[str]) -> list[str]:
    errors, _payload = run_strategy_summary_stdout_verification(
        source_preflight_strategy_path=source_preflight_strategy_path,
        expected_fragments=expected_fragments,
    )
    return errors


def validate_manifest_strategy_summary_contract(manifest: dict[str, Any]) -> list[str]:
    strategy_path, expected_fragments, errors, enabled = resolve_manifest_strategy_summary_contract_from_payload(
        manifest
    )
    if not enabled:
        return errors
    if errors:
        return errors
    verification_errors, _payload = run_strategy_summary_stdout_verification(
        source_preflight_strategy_path=strategy_path,
        expected_fragments=expected_fragments,
    )
    return errors + verification_errors


def resolve_manifest_strategy_summary_contract_from_payload(
    manifest: dict[str, Any],
) -> tuple[Path, list[str], list[str], bool]:
    errors: list[str] = []
    expected_strategy_stdout_fragments = manifest.get("expected_strategy_stdout_fragments")
    enabled = expected_strategy_stdout_fragments is not None
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    strategy_path = _path_from_mapping(paths, "source_preflight_strategy")
    if not enabled:
        return strategy_path or DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH, [], errors, False
    if strategy_path is None:
        errors.append("manifest_missing_path:source_preflight_strategy")

    fragments: list[str] = []
    if not isinstance(expected_strategy_stdout_fragments, list):
        errors.append("manifest_missing_expected_strategy_stdout_fragments")
    else:
        for fragment in expected_strategy_stdout_fragments:
            if not isinstance(fragment, str) or not fragment.strip():
                errors.append(f"manifest_invalid_expected_strategy_stdout_fragment:{fragment}")
                continue
            fragments.append(fragment)
    return strategy_path or DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH, fragments, errors, True


def verify_weekly_smoke(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
    review_experiment_path: Path = DEFAULT_REVIEW_EXPERIMENT_PATH,
    source_preflight_trend_path: Path = DEFAULT_SOURCE_PREFLIGHT_TREND_PATH,
    source_preflight_strategy_path: Path = DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH,
    recompute_contract_path: Path = DEFAULT_RECOMPUTE_CONTRACT_PATH,
) -> list[str]:
    errors: list[str] = []
    if recompute_contract_path == DEFAULT_RECOMPUTE_CONTRACT_PATH and report_path != DEFAULT_REPORT_PATH:
        recompute_contract_path = report_path.parent / DEFAULT_RECOMPUTE_CONTRACT_PATH.name
    text = _read_text(report_path, errors)
    review_experiment = _read_json_object(review_experiment_path, errors)
    source_trend = _read_json_object(source_preflight_trend_path, errors)
    source_strategy = _read_json_object(source_preflight_strategy_path, errors)
    recompute_contract = _read_json_object(recompute_contract_path, errors)

    review_summary = _summary(review_experiment)
    review_top = _first_mapping(review_summary.get("candidate_top_operator_actions"))
    trend_top = _first_mapping(_summary(source_trend).get("top_operator_actions"))
    strategy_summary = _summary(source_strategy)

    if text and not METRIC_MISSING_FRAGMENT_PATTERN.search(text):
        errors.append("missing_metric_coverage")
    if text and "Source operator actions:" not in text:
        errors.append("missing_source_strategy_operator_actions")
    if "top_operator_actions" not in strategy_summary:
        errors.append("missing_strategy_top_operator_actions")
    if recompute_contract and text:
        runtime_contract = recompute_contract.get("runtime_contract")
        runtime_contract = runtime_contract if isinstance(runtime_contract, dict) else {}
        validation = runtime_contract.get("validation")
        validation = validation if isinstance(validation, dict) else {}
        scoring_dry_run = runtime_contract.get("scoring_dry_run")
        scoring_dry_run = scoring_dry_run if isinstance(scoring_dry_run, dict) else {}
        safety = recompute_contract.get("safety")
        safety = safety if isinstance(safety, dict) else {}
        gate_errors = recompute_contract.get("gate_errors")
        gate_errors = gate_errors if isinstance(gate_errors, list) else []
        recompute_fragments = [
            "Recompute Scores Runtime Contract (dry-run)",
            f"ok={_bool_text(recompute_contract.get('ok'))}",
            f"gate_errors={len(gate_errors)}",
            f"validation_scoring_runs={_bool_text(validation.get('scoring_runs'))}",
            "scoring_dependencies_may_initialize="
            f"{_bool_text(scoring_dry_run.get('scoring_dependencies_may_initialize'))}",
            f"notion_writes={_bool_text(safety.get('notion_writes'))}",
            "Recompute command:",
        ]
        for fragment in recompute_fragments:
            if fragment not in text:
                errors.append(f"missing_recompute_contract_fragment:{fragment}")
    strategy_mismatch_count = int(strategy_summary.get("operator_action_mismatch_count") or 0)
    if strategy_mismatch_count and text:
        strategy_mismatch_sources = strategy_summary.get("operator_action_mismatch_source_counts")
        strategy_mismatch_fragments = [
            "Strategy operator action mismatches:",
            f"count={strategy_mismatch_count}",
        ]
        if isinstance(strategy_mismatch_sources, dict) and strategy_mismatch_sources:
            first_source, first_count = sorted(
                strategy_mismatch_sources.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
            )[0]
            strategy_mismatch_fragments.append(f"{first_source}={first_count}")
        for fragment in strategy_mismatch_fragments:
            if fragment not in text:
                errors.append(f"missing_strategy_mismatch_fragment:{fragment}")

    manual_ready_gate = source_strategy.get("manual_ready_gate")
    manual_ready_gate = manual_ready_gate if isinstance(manual_ready_gate, dict) else {}
    repair_command_count = int(manual_ready_gate.get("repair_command_count") or 0)
    if repair_command_count:
        repair_commands = manual_ready_gate.get("repair_commands")
        repair_commands = repair_commands if isinstance(repair_commands, list) else []
        primary_repair_command = str(manual_ready_gate.get("primary_repair_command") or "").strip()
        strategy_repair_queue = strategy_summary.get("repair_command_queue")
        strategy_repair_queue = strategy_repair_queue if isinstance(strategy_repair_queue, list) else []
        strategy_repair_queue_count_total = _repair_queue_count_total(strategy_repair_queue)
        expected_repair_queue_status = "ok" if strategy_repair_queue_count_total == repair_command_count else "mismatch"
        strategy_repair_queue_consistency = _repair_queue_consistency(strategy_summary)
        if not repair_commands:
            errors.append("missing_manual_ready_repair_commands")
        if primary_repair_command and primary_repair_command not in repair_commands:
            errors.append("manual_ready_primary_repair_command_missing_from_queue")
        if not strategy_repair_queue:
            errors.append("missing_strategy_repair_command_queue")
        elif strategy_repair_queue_count_total != repair_command_count:
            errors.append(
                "strategy_repair_command_queue_count_mismatch:"
                f"expected={repair_command_count},actual={strategy_repair_queue_count_total}"
            )
        if not strategy_repair_queue_consistency:
            errors.append("missing_strategy_repair_command_queue_consistency")
        else:
            consistency_repair_command_count = _count_sort_value(
                strategy_repair_queue_consistency.get("repair_command_count")
            )
            consistency_queue_count_total = _count_sort_value(
                strategy_repair_queue_consistency.get("queue_count_total")
            )
            consistency_status = str(strategy_repair_queue_consistency.get("status") or "").strip()
            if consistency_repair_command_count != repair_command_count:
                errors.append(
                    "strategy_repair_command_queue_consistency_count_mismatch:"
                    f"expected={repair_command_count},actual={consistency_repair_command_count}"
                )
            if consistency_queue_count_total != strategy_repair_queue_count_total:
                errors.append(
                    "strategy_repair_command_queue_consistency_total_mismatch:"
                    f"expected={strategy_repair_queue_count_total},actual={consistency_queue_count_total}"
                )
            if consistency_status != expected_repair_queue_status:
                errors.append(
                    "strategy_repair_command_queue_consistency_status_mismatch:"
                    f"expected={expected_repair_queue_status},actual={consistency_status}"
                )
        if text:
            repair_queue_fragments = [
                "Repair queue:",
                f"total={repair_command_count}",
                f"listed={len(repair_commands)}",
                f"count_total={strategy_repair_queue_count_total}",
                f"consistency={expected_repair_queue_status}",
                "source=manual_ready_gate.repair_commands",
            ]
            for fragment in repair_queue_fragments:
                if fragment not in text:
                    errors.append(f"missing_strategy_repair_queue_fragment:{fragment}")
            primary_repair_target = _first_mapping(strategy_repair_queue)
            if primary_repair_command:
                for item in strategy_repair_queue:
                    if not isinstance(item, dict):
                        continue
                    if str(item.get("command") or "").strip() == primary_repair_command:
                        primary_repair_target = item
                        break
            if primary_repair_target:
                target_fragments = ["Primary repair target:"]
                target_type = str(primary_repair_target.get("type") or "").strip()
                if target_type:
                    target_fragments.append(f"type={target_type}")
                target_count = primary_repair_target.get("count")
                target_fragments.append(f"count={target_count}")
                buckets = primary_repair_target.get("buckets")
                if isinstance(buckets, dict) and buckets:
                    first_bucket, first_count = sorted(
                        buckets.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
                    )[0]
                    target_fragments.append(f"{first_bucket}={first_count}")
                sources = primary_repair_target.get("sources")
                if isinstance(sources, dict) and sources:
                    first_source, first_count = sorted(
                        sources.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
                    )[0]
                    target_fragments.append(f"{first_source}={first_count}")
                for fragment in target_fragments:
                    if fragment not in text:
                        errors.append(f"missing_strategy_primary_repair_target_fragment:{fragment}")

    if not review_top:
        errors.append("missing_review_top_operator_action")
    elif text:
        review_fragments = [
            "Review top operator actions:",
            f"{review_top.get('count')}x {review_top.get('action')}",
            f"reason={review_top.get('reason')}",
        ]
        for fragment in review_fragments:
            if fragment not in text:
                errors.append(f"missing_review_fragment:{fragment}")

    review_missing_owner = _first_mapping(review_summary.get("candidate_top_missing_metric_owners"))
    if review_missing_owner and text:
        missing_owner_fragments = [
            "Missing metric owners:",
            f"{review_missing_owner.get('count')}x {review_missing_owner.get('owner')}",
            f"top_metric={review_missing_owner.get('top_metric')}",
        ]
        for fragment in missing_owner_fragments:
            if fragment not in text:
                errors.append(f"missing_review_missing_owner_fragment:{fragment}")

    review_blocker_action = _first_mapping(review_summary.get("candidate_rollout_blocker_actions"))
    if review_blocker_action and text:
        blocker_fragments = ["Rollout blocker actions:"]
        code = str(review_blocker_action.get("code") or "").strip()
        if code:
            blocker_fragments.append(code)
        source = str(review_blocker_action.get("source") or "").strip()
        if source:
            blocker_fragments.append(f"source={source}")
        owner = str(review_blocker_action.get("owner") or "").strip()
        if owner:
            blocker_fragments.append(f"owner={owner}")
        top_metric = str(review_blocker_action.get("top_metric") or "").strip()
        if top_metric:
            blocker_fragments.append(f"top_metric={top_metric}")
        operator_action = str(review_blocker_action.get("operator_action") or "").strip()
        if operator_action:
            blocker_fragments.append(f"action={operator_action}")
        for fragment in blocker_fragments:
            if fragment not in text:
                errors.append(f"missing_review_rollout_blocker_action_fragment:{fragment}")
    safety_risk_item_count = int(review_summary.get("candidate_safety_risk_item_count") or 0)
    if safety_risk_item_count and text:
        safety_risk_fragments = [
            "Safety risk flags:",
            f"items={safety_risk_item_count}",
        ]
        safety_risk_flags = review_summary.get("candidate_safety_risk_flag_counts")
        if isinstance(safety_risk_flags, dict) and safety_risk_flags:
            first_flag, first_count = sorted(
                safety_risk_flags.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
            )[0]
            safety_risk_fragments.append(f"{first_flag}={first_count}")
        for fragment in safety_risk_fragments:
            if fragment not in text:
                errors.append(f"missing_review_safety_risk_fragment:{fragment}")

    provider_failure_categories = review_summary.get("candidate_provider_failure_category_counts")
    provider_failure_providers = review_summary.get("candidate_provider_failure_provider_counts")
    primary_provider_failure_categories = review_summary.get("candidate_primary_provider_failure_category_counts")
    primary_provider_failure_providers = review_summary.get("candidate_primary_provider_failure_provider_counts")
    primary_provider_failure_actions = review_summary.get("candidate_primary_provider_failure_actions")
    has_provider_failure_categories = isinstance(provider_failure_categories, dict) and bool(
        provider_failure_categories
    )
    has_provider_failure_providers = isinstance(provider_failure_providers, dict) and bool(provider_failure_providers)
    has_primary_provider_failure_categories = isinstance(primary_provider_failure_categories, dict) and bool(
        primary_provider_failure_categories
    )
    has_primary_provider_failure_providers = isinstance(primary_provider_failure_providers, dict) and bool(
        primary_provider_failure_providers
    )
    if (
        has_provider_failure_categories
        or has_provider_failure_providers
        or has_primary_provider_failure_categories
        or has_primary_provider_failure_providers
    ) and text:
        provider_failure_fragments = ["Provider failures:"]
        if has_provider_failure_categories:
            first_category, first_count = sorted(
                provider_failure_categories.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
            )[0]
            provider_failure_fragments.append(f"{first_category}={first_count}")
        if has_provider_failure_providers:
            first_provider, first_count = sorted(
                provider_failure_providers.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
            )[0]
            provider_failure_fragments.append(f"{first_provider}={first_count}")
        if has_primary_provider_failure_categories:
            first_category, first_count = sorted(
                primary_provider_failure_categories.items(),
                key=lambda item: (-_count_sort_value(item[1]), str(item[0])),
            )[0]
            provider_failure_fragments.extend(["primary_categories=", f"{first_category}={first_count}"])
        if has_primary_provider_failure_providers:
            first_provider, first_count = sorted(
                primary_provider_failure_providers.items(),
                key=lambda item: (-_count_sort_value(item[1]), str(item[0])),
            )[0]
            provider_failure_fragments.extend(["primary_providers=", f"{first_provider}={first_count}"])
        seen_provider_failure_fragments: set[str] = set()
        for fragment in provider_failure_fragments:
            if fragment in seen_provider_failure_fragments:
                continue
            seen_provider_failure_fragments.add(fragment)
            if fragment not in text:
                errors.append(f"missing_review_provider_failure_fragment:{fragment}")
    primary_repair_action = _first_mapping(primary_provider_failure_actions)
    if primary_repair_action and text:
        repair_fragments = ["Provider failure repair:"]
        provider = str(primary_repair_action.get("provider") or "").strip()
        if provider:
            repair_fragments.append(f"provider={provider}")
        category = str(primary_repair_action.get("category") or "").strip()
        if category:
            repair_fragments.append(f"category={category}")
        operator_action = str(primary_repair_action.get("operator_action") or "").strip()
        if operator_action:
            repair_fragments.append(f"action={operator_action}")
        for fragment in repair_fragments:
            if fragment not in text:
                errors.append(f"missing_review_provider_failure_repair_fragment:{fragment}")

    if not trend_top:
        errors.append("missing_trend_top_operator_action")
    elif text:
        trend_fragments = [
            "Source trend operator actions:",
            f"{trend_top.get('count')}x ",
            f"action={trend_top.get('operator_action')}",
        ]
        for fragment in trend_fragments:
            if fragment not in text:
                errors.append(f"missing_trend_fragment:{fragment}")
    trend_evidence_field_counts = _summary(source_trend).get("evidence_field_counts")
    if isinstance(trend_evidence_field_counts, dict) and trend_evidence_field_counts and text:
        first_field, first_count = sorted(
            trend_evidence_field_counts.items(),
            key=lambda item: (-_count_sort_value(item[1]), str(item[0])),
        )[0]
        evidence_field_fragments = [
            "Evidence fields:",
            f"{first_field}={first_count}",
        ]
        for fragment in evidence_field_fragments:
            if fragment not in text:
                errors.append(f"missing_trend_evidence_field_fragment:{fragment}")
    trend_top_evidence = _summary(source_trend).get("top_source_evidence")
    if isinstance(trend_top_evidence, dict) and trend_top_evidence and text:
        source = str(trend_top_evidence.get("source") or "").strip()
        status = str(trend_top_evidence.get("status") or "").strip()
        open_first_field = str(trend_top_evidence.get("open_first_field") or "").strip()
        open_first = str(trend_top_evidence.get("open_first") or "").strip()
        evidence_fragments = ["Top source evidence:"]
        if source:
            evidence_fragments.append(f"source={source}")
        if status:
            evidence_fragments.append(f"status={status}")
        if open_first_field and open_first:
            evidence_fragments.append(f"open_first={open_first_field}={open_first}")
        for fragment in evidence_fragments:
            if fragment not in text:
                errors.append(f"missing_trend_top_evidence_fragment:{fragment}")
    mismatch_count = int(_summary(source_trend).get("operator_action_mismatch_count") or 0)
    if mismatch_count and text:
        mismatch_sources = _summary(source_trend).get("operator_action_mismatch_source_counts")
        mismatch_fragments = [
            "Operator action mismatches:",
            f"count={mismatch_count}",
        ]
        if isinstance(mismatch_sources, dict) and mismatch_sources:
            first_source, first_count = sorted(
                mismatch_sources.items(), key=lambda item: (-_count_sort_value(item[1]), str(item[0]))
            )[0]
            mismatch_fragments.append(f"{first_source}={first_count}")
        for fragment in mismatch_fragments:
            if fragment not in text:
                errors.append(f"missing_mismatch_fragment:{fragment}")

    return errors


def build_result_payload(
    *,
    errors: list[str],
    report_path: Path,
    review_experiment_path: Path,
    source_preflight_trend_path: Path,
    source_preflight_strategy_path: Path,
    recompute_contract_path: Path,
    review_summary_payload: dict[str, Any] | None = None,
    strategy_summary_payload: dict[str, Any] | None = None,
    manifest_repair_queue_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "ok": not errors,
        "status": "ok" if not errors else "fail",
        "errors": errors,
        "paths": {
            "report": report_path.as_posix(),
            "review_experiment": review_experiment_path.as_posix(),
            "source_preflight_trend": source_preflight_trend_path.as_posix(),
            "source_preflight_strategy": source_preflight_strategy_path.as_posix(),
            "recompute_contract": recompute_contract_path.as_posix(),
        },
    }
    if review_summary_payload is not None:
        payload["review_summary"] = review_summary_payload
    if strategy_summary_payload is not None:
        payload["strategy_summary"] = strategy_summary_payload
    if manifest_repair_queue_payload is not None:
        payload["manifest_repair_queue"] = manifest_repair_queue_payload
    repair_queue_payload = _read_repair_queue_payload(source_preflight_strategy_path)
    if repair_queue_payload:
        payload["repair_queue"] = repair_queue_payload
    if errors:
        payload["error_categories"] = _error_categories(errors)
    return payload


def _error_categories(errors: list[str]) -> list[str]:
    return sorted({_error_category(error) for error in errors})


def _error_category(error: str) -> str:
    if error.startswith("manifest_"):
        return "manifest"
    if error.startswith(("review_summary_", "missing_review_summary_stdout_fragment:")):
        return "review_summary"
    if error.startswith(("strategy_summary_", "missing_strategy_stdout_fragment:")):
        return "strategy_summary"
    if error.startswith(("read_failed:", "json_read_failed:", "json_not_object:")):
        return "input"
    return "report"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify local weekly report smoke output.")
    parser.add_argument("--manifest", type=Path, default=None, help="Read paths from write_weekly_smoke_inputs JSON.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--review-experiment", type=Path, default=DEFAULT_REVIEW_EXPERIMENT_PATH)
    parser.add_argument("--source-preflight-trend", type=Path, default=DEFAULT_SOURCE_PREFLIGHT_TREND_PATH)
    parser.add_argument("--source-preflight-strategy", type=Path, default=DEFAULT_SOURCE_PREFLIGHT_STRATEGY_PATH)
    parser.add_argument("--recompute-contract", type=Path, default=DEFAULT_RECOMPUTE_CONTRACT_PATH)
    parser.add_argument(
        "--verify-review-summary",
        action="store_true",
        help=(
            "With --manifest, run the local review summary dry-run child command and verify "
            "expected_review_stdout_fragments."
        ),
    )
    parser.add_argument(
        "--verify-strategy-summary",
        action="store_true",
        help=(
            "With --manifest, explicitly show source strategy summary verification: format "
            "paths.source_preflight_strategy locally and verify expected_strategy_stdout_fragments; "
            "does not run browser, Notion, providers, X, or the manifest command string."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable verification payload.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest_errors: list[str] = []
    report_path = args.report
    review_experiment_path = args.review_experiment
    source_preflight_trend_path = args.source_preflight_trend
    source_preflight_strategy_path = args.source_preflight_strategy
    recompute_contract_path = args.recompute_contract
    if recompute_contract_path == DEFAULT_RECOMPUTE_CONTRACT_PATH and report_path != DEFAULT_REPORT_PATH:
        recompute_contract_path = report_path.parent / DEFAULT_RECOMPUTE_CONTRACT_PATH.name
    if args.manifest is not None:
        (
            report_path,
            review_experiment_path,
            source_preflight_trend_path,
            source_preflight_strategy_path,
            recompute_contract_path,
            manifest_errors,
        ) = resolve_manifest_paths(args.manifest)
    errors = verify_weekly_smoke(
        report_path=report_path,
        review_experiment_path=review_experiment_path,
        source_preflight_trend_path=source_preflight_trend_path,
        source_preflight_strategy_path=source_preflight_strategy_path,
        recompute_contract_path=recompute_contract_path,
    )
    errors = manifest_errors + errors
    review_summary_payload: dict[str, Any] | None = None
    strategy_summary_payload: dict[str, Any] | None = None
    manifest_repair_queue_payload = (
        read_manifest_repair_queue_payload(args.manifest) if args.manifest is not None else None
    )
    if args.manifest is not None and not manifest_errors:
        (
            strategy_path,
            expected_strategy_fragments,
            strategy_contract_errors,
            strategy_summary_enabled,
        ) = resolve_manifest_strategy_summary_contract(args.manifest)
        if strategy_summary_enabled:
            errors.extend(strategy_contract_errors)
            if not strategy_contract_errors:
                strategy_summary_errors, strategy_summary_payload = run_strategy_summary_stdout_verification(
                    source_preflight_strategy_path=strategy_path,
                    expected_fragments=expected_strategy_fragments,
                )
                errors.extend(strategy_summary_errors)
            else:
                strategy_summary_payload = build_strategy_summary_verification_payload(
                    source_preflight_strategy_path=strategy_path,
                    expected_fragments=expected_strategy_fragments,
                    errors=strategy_contract_errors,
                    executed=False,
                )
    if args.manifest is not None and args.verify_review_summary and not manifest_errors:
        review_records_path, expected_fragments, contract_errors = resolve_manifest_review_summary_contract(
            args.manifest
        )
        errors.extend(contract_errors)
        if not contract_errors:
            review_summary_errors, review_summary_payload = run_review_summary_stdout_verification(
                review_records_path=review_records_path,
                expected_fragments=expected_fragments,
            )
            errors.extend(review_summary_errors)
        else:
            review_summary_payload = build_review_summary_verification_payload(
                review_records_path=review_records_path,
                expected_fragments=expected_fragments,
                errors=contract_errors,
                executed=False,
                returncode=None,
            )
    if args.json:
        payload = build_result_payload(
            errors=errors,
            report_path=report_path,
            review_experiment_path=review_experiment_path,
            source_preflight_trend_path=source_preflight_trend_path,
            source_preflight_strategy_path=source_preflight_strategy_path,
            recompute_contract_path=recompute_contract_path,
            review_summary_payload=review_summary_payload,
            strategy_summary_payload=strategy_summary_payload,
            manifest_repair_queue_payload=manifest_repair_queue_payload,
        )
        if args.manifest is not None:
            payload["manifest"] = args.manifest.as_posix()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if payload["ok"] else 1
    if errors:
        categories = _error_categories(errors)
        category_text = f" category={','.join(categories)}" if "manifest" in categories else ""
        print(f"weekly_smoke=fail{category_text} reason={';'.join(errors)}")
        return 1
    print("weekly_smoke=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
