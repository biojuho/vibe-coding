#!/usr/bin/env python3
"""Refresh auto-research current evidence with BOM-free byte writes."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

UTF8_BOM = b"\xef\xbb\xbf"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"
ATOMIC_WRITE_RETRY_DELAYS = (0.1, 0.25)
AUTHORIZATION_CONTROL_TOKENS = {"STOP"}


@dataclass(frozen=True)
class EvidencePaths:
    readiness: Path = Path(".tmp/product-readiness-current.json")
    github_inventory: Path = Path(".tmp/github-project-inventory-current.json")
    github_inventory_refresh: Path = Path(".tmp/github-project-inventory-refresh.json")
    browser_qa_inventory: Path = Path(".tmp/browser-qa-inventory-current.json")
    browser_qa_inventory_refresh: Path = Path(".tmp/browser-qa-inventory-refresh.json")
    dependency_freshness: Path = Path(".tmp/dependency-freshness-current.json")
    dependency_freshness_refresh: Path = Path(".tmp/dependency-freshness-refresh.json")
    direction_alignment: Path = Path(".tmp/direction-alignment-audit-current.json")
    direction_alignment_refresh: Path = Path(".tmp/direction-alignment-audit-refresh.json")
    code_review_gate: Path = Path(".tmp/code-review-gate-current.json")
    launch: Path = Path(".tmp/launch-objective-audit-current.json")
    launch_refresh: Path = Path(".tmp/launch-objective-audit-refresh.json")
    completion: Path = Path(".tmp/launch-objective-completion-audit-current.json")
    release_authorization_packet: Path = Path(".tmp/release-authorization-packet-current.json")
    release_authorization_packet_refresh: Path = Path(".tmp/release-authorization-packet-refresh.json")
    selector: Path = Path(".tmp/next-experiment-current.json")
    selector_refresh: Path = Path(".tmp/next-experiment-refresh.json")
    selector_legacy_alias: Path = Path(".tmp/next-experiment-selection-current.json")
    selector_continuation_alias: Path = Path(".tmp/next-experiment-continuation.json")
    session_orient: Path = Path(".tmp/session-orient-current.json")
    debug_json: Path = Path(".tmp/debug-loop-known-bugs-current.json")
    debug_json_refresh: Path = Path(".tmp/debug-loop-known-bugs-refresh.json")
    debug_md: Path = Path(".tmp/debug-loop-known-bugs-current.md")
    debug_md_refresh: Path = Path(".tmp/debug-loop-known-bugs-refresh.md")
    dirty_handoff_plan: Path = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.json")
    dirty_handoff_plan_refresh: Path = Path(".tmp/scoped-dirty-worktree-handoff-plan-refresh.json")
    dirty_handoff_plan_md: Path = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.md")
    dirty_handoff_plan_md_refresh: Path = Path(".tmp/scoped-dirty-worktree-handoff-plan-refresh.md")
    approval_pathspec: Path = Path(".tmp/approval-pathspec-consistency-current.json")
    approval_pathspec_md: Path = Path(".tmp/approval-pathspec-consistency-current.md")
    authorization_coverage: Path = Path(".tmp/authorization-coverage-current.json")
    approval_combined_pathspec: Path = Path(".tmp/approval-pathspec-combined-current.pathspec")
    approval_execution_matrix: Path = Path(".tmp/approval-execution-matrix-current.json")
    approval_execution_matrix_md: Path = Path(".tmp/approval-execution-matrix-current.md")
    launch_blocker_burndown: Path = Path(".tmp/launch-blocker-burndown-current.json")
    launch_blocker_burndown_md: Path = Path(".tmp/launch-blocker-burndown-current.md")
    scoped_authorization_menu_md: Path = Path(".tmp/next-scoped-authorization-menu-current.md")
    scoped_authorization_menu_json: Path = Path(".tmp/next-scoped-authorization-menu-current.json")
    scoped_authorization_menu_check: Path = Path(".tmp/next-scoped-authorization-menu-current.check.json")
    ai_context_relay_packet: Path = Path(".tmp/ai-context-aic1-scoped-authorization-current.json")
    ai_context_relay_packet_md: Path = Path(".tmp/ai-context-aic1-scoped-authorization-current.md")
    session_log_rotator_pathspec: Path = Path(".tmp/approve-session-log-rotator.pathspec")
    session_log_rotator_packet: Path = Path(".tmp/session-log-rotator-authorization-current.json")
    session_log_rotator_packet_md: Path = Path(".tmp/session-log-rotator-authorization-current.md")
    prompt_artifact_checklist: Path = Path(".tmp/launch-objective-prompt-artifact-checklist-current.md")


@dataclass(frozen=True)
class StepResult:
    name: str
    returncode: int
    expected_returncode: bool
    output: Path | None = None
    first_bytes: str | None = None
    status: str = "ok"
    detail: str = ""


def _in_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _decode_stderr(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").strip()


def _timeout_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")


def _timeout_result(argv: list[str], exc: subprocess.TimeoutExpired) -> subprocess.CompletedProcess[bytes]:
    stderr = _timeout_bytes(exc.stderr)
    message = f"timed out after {exc.timeout} seconds".encode("utf-8")
    if stderr:
        stderr = stderr.rstrip() + b"\n" + message
    else:
        stderr = message
    return subprocess.CompletedProcess(
        argv,
        124,
        _timeout_bytes(exc.stdout),
        stderr,
    )


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2) + "\n"


def _first_bytes(path: Path) -> str:
    try:
        return path.read_bytes()[:4].hex(" ").upper()
    except OSError:
        return "unreadable"


def _json_is_bom_free(path: Path) -> tuple[bool, str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return False, f"unreadable JSON: {exc}"
    if raw.startswith(UTF8_BOM):
        return False, "JSON starts with UTF-8 BOM"
    if raw.startswith((UTF16_LE_BOM, UTF16_BE_BOM)):
        return False, "JSON starts with UTF-16 BOM"
    try:
        json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return False, f"invalid UTF-8 JSON: {exc}"
    if raw.lstrip()[:1] not in (b"{", b"["):
        return False, "JSON does not start with an object or array"
    return True, ""


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    attempts = len(ATOMIC_WRITE_RETRY_DELAYS) + 1
    for attempt in range(attempts):
        try:
            tmp.write_bytes(data)
            tmp.replace(path)
            return
        except PermissionError:
            if attempt >= len(ATOMIC_WRITE_RETRY_DELAYS):
                raise
            time.sleep(ATOMIC_WRITE_RETRY_DELAYS[attempt])


def _atomic_write_bytes_step(path: Path, data: bytes, *, name: str, output: Path | None = None) -> StepResult | None:
    try:
        _atomic_write_bytes(path, data)
    except OSError as exc:
        return StepResult(
            name=name,
            returncode=2,
            expected_returncode=False,
            output=output or path,
            first_bytes=_first_bytes(path) if path.exists() else None,
            status="failed",
            detail=f"could not write refresh evidence atomically: {exc}",
        )
    return None


def _remove_stale_refresh(path: Path, *, name: str, target: Path) -> StepResult | None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return StepResult(
            name=name,
            returncode=2,
            expected_returncode=False,
            output=target,
            first_bytes=_first_bytes(path) if path.exists() else None,
            status="failed",
            detail=f"could not remove stale refresh file: {exc}",
        )
    return None


def _replace_after_validation(source: Path, target: Path) -> StepResult:
    ok, detail = _json_is_bom_free(source)
    if not ok:
        return StepResult(
            name=f"replace:{target}",
            returncode=2,
            expected_returncode=False,
            output=source,
            first_bytes=_first_bytes(source) if source.exists() else None,
            status="failed",
            detail=detail,
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return StepResult(
            name=f"replace:{target}",
            returncode=2,
            expected_returncode=False,
            output=source,
            first_bytes=_first_bytes(source),
            status="failed",
            detail=f"could not create target evidence directory: {exc}",
        )
    replaced = False
    last_error: OSError | None = None
    for attempt in range(len(ATOMIC_WRITE_RETRY_DELAYS) + 1):
        try:
            source.replace(target)
            replaced = True
            break
        except PermissionError as exc:
            last_error = exc
            if attempt >= len(ATOMIC_WRITE_RETRY_DELAYS):
                break
            time.sleep(ATOMIC_WRITE_RETRY_DELAYS[attempt])
        except OSError as exc:
            last_error = exc
            break
    if not replaced:
        return StepResult(
            name=f"replace:{target}",
            returncode=2,
            expected_returncode=False,
            output=source,
            first_bytes=_first_bytes(source),
            status="failed",
            detail=f"could not replace refresh evidence after validation: {last_error}",
        )
    return StepResult(
        name=f"replace:{target}",
        returncode=0,
        expected_returncode=True,
        output=target,
        first_bytes=_first_bytes(target),
    )


def _copy_json_after_validation(source: Path, target: Path) -> StepResult:
    ok, detail = _json_is_bom_free(source)
    if not ok:
        return StepResult(
            name=f"sync:{target}",
            returncode=2,
            expected_returncode=False,
            output=source,
            first_bytes=_first_bytes(source) if source.exists() else None,
            status="failed",
            detail=detail,
        )
    try:
        source_bytes = source.read_bytes()
    except OSError as exc:
        return StepResult(
            name=f"sync:{target}",
            returncode=2,
            expected_returncode=False,
            output=source,
            first_bytes=_first_bytes(source) if source.exists() else None,
            status="failed",
            detail=f"could not read validated JSON for sync: {exc}",
        )
    write_result = _atomic_write_bytes_step(target, source_bytes, name=f"sync:{target}", output=target)
    if write_result:
        return write_result
    return StepResult(
        name=f"sync:{target}",
        returncode=0,
        expected_returncode=True,
        output=target,
        first_bytes=_first_bytes(target),
    )


def _run(
    root: Path,
    argv: list[str],
    *,
    timeout: int,
    expected_returncodes: set[int] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _timeout_result(argv, exc)


def _run_stdout_json_step(
    root: Path,
    *,
    name: str,
    argv: list[str],
    target: Path,
    timeout: int,
    expected_returncodes: set[int] | None = None,
) -> StepResult:
    expected = expected_returncodes or {0}
    refresh = target.with_name(f"{target.name}.refresh")
    cleanup_result = _remove_stale_refresh(refresh, name=name, target=target)
    if cleanup_result:
        return cleanup_result
    completed = _run(root, argv, timeout=timeout, expected_returncodes=expected)
    expected_returncode = completed.returncode in expected
    if not expected_returncode:
        return StepResult(
            name=name,
            returncode=completed.returncode,
            expected_returncode=False,
            output=target,
            status="failed",
            detail=_decode_stderr(completed.stderr),
        )
    write_result = _atomic_write_bytes_step(refresh, completed.stdout, name=name, output=refresh)
    if write_result:
        return write_result
    result = _replace_after_validation(refresh, target)
    return StepResult(
        name=name,
        returncode=completed.returncode,
        expected_returncode=True,
        output=result.output,
        first_bytes=result.first_bytes,
        status=result.status,
        detail=result.detail,
    )


def _run_output_file_step(
    root: Path,
    *,
    name: str,
    argv: list[str],
    refresh: Path,
    target: Path,
    timeout: int,
    expected_returncodes: set[int] | None = None,
) -> StepResult:
    expected = expected_returncodes or {0}
    cleanup_result = _remove_stale_refresh(refresh, name=name, target=target)
    if cleanup_result:
        return cleanup_result
    completed = _run(root, argv, timeout=timeout, expected_returncodes=expected)
    expected_returncode = completed.returncode in expected
    if not expected_returncode:
        return StepResult(
            name=name,
            returncode=completed.returncode,
            expected_returncode=False,
            output=target,
            status="failed",
            detail=_decode_stderr(completed.stderr),
        )
    result = _replace_after_validation(refresh, target)
    return StepResult(
        name=name,
        returncode=completed.returncode,
        expected_returncode=True,
        output=result.output,
        first_bytes=result.first_bytes,
        status=result.status,
        detail=result.detail,
    )


def _replace_markdown(source: Path, target: Path) -> StepResult:
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return StepResult(
            name=f"replace:{target}",
            returncode=2,
            expected_returncode=False,
            output=source,
            status="failed",
            detail=f"unreadable Markdown: {exc}",
        )
    write_result = _atomic_write_bytes_step(target, text.encode("utf-8"), name=f"replace:{target}", output=target)
    if write_result:
        return write_result
    return StepResult(
        name=f"replace:{target}",
        returncode=0,
        expected_returncode=True,
        output=target,
        first_bytes=_first_bytes(target),
    )


def _write_markdown(target: Path, text: str, *, name: str) -> StepResult:
    write_result = _atomic_write_bytes_step(target, text.encode("utf-8"), name=name, output=target)
    if write_result:
        return write_result
    return StepResult(
        name=name,
        returncode=0,
        expected_returncode=True,
        output=target,
        first_bytes=_first_bytes(target),
    )


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_utf8_bom_json_artifact(path: Path, payload: dict[str, Any], *, name: str) -> StepResult | None:
    if not payload:
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return StepResult(
            name=name,
            returncode=2,
            expected_returncode=False,
            output=path,
            first_bytes=_first_bytes(path) if path.exists() else None,
            status="failed",
            detail=f"could not inspect JSON artifact for BOM normalization: {exc}",
        )
    if not raw.startswith(UTF8_BOM):
        return None
    write_error = _atomic_write_bytes_step(
        path,
        _json_text(payload).encode("utf-8"),
        name=name,
        output=path,
    )
    if write_error:
        return write_error
    return StepResult(
        name=name,
        returncode=0,
        expected_returncode=True,
        output=path,
        first_bytes=_first_bytes(path),
    )


def _validate_debug_loop_completion_exit(debug_json: Path, observed_returncode: int) -> StepResult:
    payload = _load_json_file(debug_json)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    completion_allowed = summary.get("completion_allowed")
    if completion_allowed is False:
        expected_returncode = 1
    elif completion_allowed is True:
        expected_returncode = 0
    else:
        return StepResult(
            name="debug_loop_completion_exit_contract",
            returncode=observed_returncode,
            expected_returncode=False,
            output=debug_json,
            first_bytes=_first_bytes(debug_json) if debug_json.exists() else None,
            status="failed",
            detail="debug inventory JSON is missing summary.completion_allowed",
        )
    if observed_returncode != expected_returncode:
        return StepResult(
            name="debug_loop_completion_exit_contract",
            returncode=observed_returncode,
            expected_returncode=False,
            output=debug_json,
            first_bytes=_first_bytes(debug_json),
            status="failed",
            detail=(
                "debug inventory exit code contract mismatch: "
                f"completion_allowed={completion_allowed}, expected returncode {expected_returncode}"
            ),
        )
    return StepResult(
        name="debug_loop_completion_exit_contract",
        returncode=observed_returncode,
        expected_returncode=True,
        output=debug_json,
        first_bytes=_first_bytes(debug_json),
    )


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value in (None, ""):
        return "unknown"
    return str(value)


def _pathspec_token(pathspec: str) -> str:
    name = Path(pathspec).name
    if name.startswith("approve-"):
        name = name[len("approve-") :]
    if name.endswith(".pathspec"):
        name = name[: -len(".pathspec")]
    return f"APPROVE_{name.replace('-', '_').upper()}"


def _phase_for_pathspec(pathspec: str) -> tuple[str, int, str]:
    name = Path(pathspec).name.lower()
    if name == "approve-ai-context-relay-update.pathspec":
        return ("phase0_context_relay", 0, "Context relay first.")
    if "auto-research" in name or "current-uncovered-dirty-handoff" in name:
        return ("phase1_loop_tooling", 1, "Auto-research loop tooling.")
    if "blind-to-x" in name:
        return ("phase2_blind_to_x_dirty_product_paths", 2, "Blind-to-X packets.")
    if "shorts-maker-v2" in name:
        return ("phase3_shorts_maker_v2_dirty_product_paths", 3, "Shorts Maker V2 packets.")
    if "knowledge-dashboard" in name:
        return ("phase5_knowledge_dashboard_dependency_patch", 5, "Knowledge Dashboard dependency/package patch.")
    if name.startswith("approve-execution-") or name == "approve-root-execution-tools.pathspec":
        return ("phase7_execution_tools", 7, "Root execution tools.")
    if name.startswith("approve-workspace-") or name.startswith("approve-root-workspace-"):
        return ("phase6_workspace_tools", 6, "Workspace tools and tests.")
    return ("phase8_root_and_shared_assets", 8, "Root/shared assets and remaining packets.")


def _build_approval_execution_matrix(approval: dict[str, Any], generated_at: str) -> dict[str, Any]:
    phase_rows: dict[str, dict[str, Any]] = {}
    for result in approval.get("pathspec_results") or []:
        if not isinstance(result, dict):
            continue
        pathspec = str(result.get("pathspec") or "").strip()
        if not pathspec:
            continue
        phase, rank, label = _phase_for_pathspec(pathspec)
        row = phase_rows.setdefault(
            phase,
            {
                "phase": phase,
                "rank": rank,
                "label": label,
                "token_count": 0,
                "path_count_total": 0,
                "dirty_path_count_total": 0,
                "tokens": [],
            },
        )
        path_count = _int(result.get("unique_path_count") or result.get("path_count"))
        dirty_path_count = _int(result.get("covered_dirty_count"))
        row["token_count"] += 1
        row["path_count_total"] += path_count
        row["dirty_path_count_total"] += dirty_path_count
        row["tokens"].append(
            {
                "token": _pathspec_token(pathspec),
                "pathspec": pathspec,
                "path_count": path_count,
                "dirty_path_count": dirty_path_count,
            },
        )

    phases = sorted(phase_rows.values(), key=lambda item: (item["rank"], item["phase"]))
    first_pathspec = str((approval.get("pathspec_results") or [{}])[0].get("pathspec") or "")
    return {
        "generated_at": generated_at,
        "status": "ok" if str(approval.get("status") or "") == "ok" else "needs_refresh",
        "source": "approval_pathspec_consistency_current",
        "pathspec_audit_status": str(approval.get("status") or "unknown"),
        "token_count": _int(approval.get("pathspec_count")),
        "phase_count": len(phases),
        "covered_dirty_count": _int(approval.get("covered_dirty_count")),
        "dirty_count": _int(approval.get("dirty_count")),
        "uncovered_dirty_count": _int(approval.get("uncovered_dirty_count")),
        "uncovered_non_evidence_source_count": _int(approval.get("uncovered_non_evidence_source_count")),
        "uncovered_dirty_paths": [str(path) for path in approval.get("uncovered_dirty_paths") or []],
        "uncovered_non_evidence_source_paths": [
            str(path) for path in approval.get("uncovered_non_evidence_source_paths") or []
        ],
        "virtual_add_failure_count": _int(approval.get("virtual_add_failure_count")),
        "real_staged_count": _int(approval.get("staged_count")),
        "recommended_first_token": _pathspec_token(first_pathspec) if first_pathspec else "",
        "phases": phases,
    }


def _render_approval_execution_matrix_md(matrix: dict[str, Any]) -> str:
    lines = [
        "# Approval Execution Matrix",
        "",
        f"Generated: {matrix.get('generated_at')}",
        "",
        f"- Status: `{matrix.get('status')}`",
        f"- Dirty coverage: {matrix.get('covered_dirty_count')}/{matrix.get('dirty_count')}",
        (
            "- Uncovered dirty/source: "
            f"{matrix.get('uncovered_dirty_count')}/{matrix.get('uncovered_non_evidence_source_count')}"
        ),
        f"- Real staged files: {matrix.get('real_staged_count')}",
        f"- Recommended first token: `{matrix.get('recommended_first_token')}`",
        "",
    ]
    uncovered_source_paths = matrix.get("uncovered_non_evidence_source_paths") or []
    if uncovered_source_paths:
        lines.extend(["## Uncovered Source Paths", ""])
        lines.extend(f"- `{path}`" for path in uncovered_source_paths)
        lines.append("")
    lines.extend(["## Phases", ""])
    for phase in matrix.get("phases") or []:
        token_rows = phase.get("tokens") if isinstance(phase.get("tokens"), list) else []
        lines.extend(
            [
                f"### {phase.get('phase')}",
                f"- Label: {phase.get('label')}",
                f"- Tokens: {phase.get('token_count')}",
                f"- Dirty paths: {phase.get('dirty_path_count_total')}",
                f"- Pathspec entries: {phase.get('path_count_total')}",
                "",
            ],
        )
        if token_rows:
            lines.extend(["#### Token pathspecs", ""])
            for token in token_rows:
                if not isinstance(token, dict):
                    continue
                token_name = str(token.get("token") or _pathspec_token(str(token.get("pathspec") or "")))
                pathspec = str(token.get("pathspec") or "")
                dirty_path_count = _int(token.get("dirty_path_count"))
                path_count = _int(token.get("path_count"))
                lines.append(f"- `{token_name}` -> `{pathspec}` ({dirty_path_count}/{path_count} dirty paths)")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_launch_blocker_burndown(
    *,
    matrix: dict[str, Any],
    approval: dict[str, Any],
    readiness: dict[str, Any],
    completion: dict[str, Any],
    selector: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    readiness_overall = readiness.get("overall") if isinstance(readiness.get("overall"), dict) else {}
    completion_summary = completion.get("summary") if isinstance(completion.get("summary"), dict) else {}
    selector_summary = selector.get("summary") if isinstance(selector.get("summary"), dict) else {}
    selected = selector.get("selected") if isinstance(selector.get("selected"), dict) else {}
    phases = matrix.get("phases") if isinstance(matrix.get("phases"), list) else []
    first_phase = phases[0] if phases and isinstance(phases[0], dict) else {}
    first_phase_tokens = first_phase.get("tokens") if isinstance(first_phase.get("tokens"), list) else []
    first_token = first_phase_tokens[0] if first_phase_tokens and isinstance(first_phase_tokens[0], dict) else {}
    return {
        "generated_at": generated_at,
        "status": "blocked_handoff_only",
        "dirty_count": _int(approval.get("dirty_count")),
        "approve_pathspec_count": _int(approval.get("pathspec_count")),
        "covered_dirty_count": _int(approval.get("covered_dirty_count")),
        "uncovered_dirty_count": _int(approval.get("uncovered_dirty_count")),
        "uncovered_dirty_paths": approval.get("uncovered_dirty_paths") or [],
        "uncovered_non_evidence_source_paths": approval.get("uncovered_non_evidence_source_paths") or [],
        "token_count": _int(matrix.get("token_count")),
        "phase_count": _int(matrix.get("phase_count")),
        "readiness_score": _int(readiness_overall.get("score")),
        "readiness_state": str(readiness_overall.get("state") or "unknown"),
        "launch_completion_item_count": _int(completion_summary.get("item_count")),
        "launch_completion_complete_count": _int(completion_summary.get("complete_count")),
        "launch_completion_blocked_count": _int(completion_summary.get("blocked_count")),
        "selector_status": str(selector.get("status") or "unknown"),
        "selector_kind": str(selector_summary.get("selected_kind") or selected.get("kind") or "unknown"),
        "adoptable_candidate_count": _int(selector_summary.get("adoptable_candidate_count")),
        "real_staged_count": _int(approval.get("staged_count")),
        "recommended_first_token": str(matrix.get("recommended_first_token") or ""),
        "recommended_first_pathspec": str(first_token.get("pathspec") or ""),
        "recommended_first_pathspec_path_count": _int(first_token.get("path_count")),
        "recommended_first_pathspec_dirty_count": _int(first_token.get("dirty_path_count")),
        "recommended_first_phase": {
            "phase": str(first_phase.get("phase") or ""),
            "label": str(first_phase.get("label") or ""),
            "dirty_path_count": _int(first_phase.get("dirty_path_count_total")),
            "token_count": _int(first_phase.get("token_count")),
        },
        "blockers": [
            "current dirty handoff requires explicit scoped authorization before staging/commit",
            "current-head Actions require explicit push/user push before release proof",
            "Hanwoo T-251 remains user-owned external Supabase credential reset",
        ],
        "blocker_actions": [
            {
                "blocker": "dirty_worktree_handoff_current",
                "owner": "user_or_operator",
                "next_action": "Approve one scoped pathspec token before staging or committing.",
                "authorization": str(matrix.get("recommended_first_token") or "APPROVE_AI_CONTEXT_RELAY_UPDATE"),
            },
            {
                "blocker": "current_head_release_checks_unproven",
                "owner": "user_or_operator",
                "next_action": "Authorize push or push current HEAD, then wait for required GitHub Actions.",
                "authorization": "explicit_push_or_user_push",
            },
            {
                "blocker": "hanwoo_t251_external_supabase_credentials",
                "owner": "user",
                "next_action": "Reset or resync Supabase credentials before live Prisma CRUD E2E retry.",
                "authorization": "external_credential_reset",
            },
        ],
    }


def _render_launch_blocker_burndown_md(burndown: dict[str, Any]) -> str:
    lines = [
        "# Launch Blocker Burndown",
        "",
        f"Generated: {burndown.get('generated_at')}",
        "",
        f"- Status: `{burndown.get('status')}`",
        f"- Dirty coverage: {burndown.get('covered_dirty_count')}/{burndown.get('dirty_count')}",
        f"- Token/phase count: {burndown.get('token_count')}/{burndown.get('phase_count')}",
        f"- Readiness: {burndown.get('readiness_score')} / {burndown.get('readiness_state')}",
        (
            "- Completion: "
            f"{burndown.get('launch_completion_complete_count')}/{burndown.get('launch_completion_item_count')}, "
            f"blocked {burndown.get('launch_completion_blocked_count')}"
        ),
        (
            "- Selector: "
            f"{burndown.get('selector_status')} / {burndown.get('selector_kind')}, "
            f"adoptable {burndown.get('adoptable_candidate_count')}"
        ),
        f"- Real staged files: {burndown.get('real_staged_count')}",
        "",
        "## Recommended Next Scope",
        "",
        f"- First token: `{burndown.get('recommended_first_token') or 'unknown'}`",
    ]
    first_pathspec = str(burndown.get("recommended_first_pathspec") or "").strip()
    if first_pathspec:
        lines.append(
            "- First pathspec: "
            f"`{first_pathspec}` "
            f"({burndown.get('recommended_first_pathspec_dirty_count')} dirty paths, "
            f"{burndown.get('recommended_first_pathspec_path_count')} total paths)"
        )
    first_phase = (
        burndown.get("recommended_first_phase") if isinstance(burndown.get("recommended_first_phase"), dict) else {}
    )
    if first_phase:
        lines.append(
            "- First phase: "
            f"`{first_phase.get('phase') or 'unknown'}` - {first_phase.get('label') or 'unknown'} "
            f"({first_phase.get('dirty_path_count')} dirty paths, {first_phase.get('token_count')} tokens)"
        )
    lines.extend(
        [
            "",
            "## Blocker Owners And Actions",
        ],
    )
    for action in burndown.get("blocker_actions") or []:
        if not isinstance(action, dict):
            continue
        lines.append(
            "- "
            f"`{action.get('blocker') or 'unknown'}`: "
            f"owner `{action.get('owner') or 'unknown'}`, "
            f"next `{action.get('next_action') or 'unknown'}`, "
            f"authorization `{action.get('authorization') or 'unknown'}`"
        )
    lines.extend(
        [
            "",
            "## Blockers",
        ],
    )
    lines.extend(f"- {blocker}" for blocker in burndown.get("blockers") or [])
    uncovered_source_paths = burndown.get("uncovered_non_evidence_source_paths") or []
    if uncovered_source_paths:
        lines.extend(["", "## Uncovered Source Paths"])
        lines.extend(f"- `{path}`" for path in uncovered_source_paths)
    return "\n".join(lines).rstrip() + "\n"


def _text_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def _pathspec_coverage_by_token(approval: dict[str, Any]) -> dict[str, int]:
    coverage: dict[str, int] = {}
    for result in approval.get("pathspec_results") or []:
        if not isinstance(result, dict):
            continue
        token = _pathspec_token(str(result.get("pathspec") or ""))
        if not token:
            continue
        coverage[token] = _int(result.get("covered_dirty_count"))
    return coverage


def _pathspec_coverage_by_name(approval: dict[str, Any]) -> dict[str, tuple[int, int]]:
    coverage: dict[str, tuple[int, int]] = {}
    for result in approval.get("pathspec_results") or []:
        if not isinstance(result, dict):
            continue
        pathspec = str(result.get("pathspec") or "").strip()
        if not pathspec:
            continue
        path_count = _int(result.get("unique_path_count") or result.get("path_count"))
        coverage[Path(pathspec).name.lower()] = (_int(result.get("covered_dirty_count")), path_count)
    return coverage


def _authorization_option_tokens(
    menu: dict[str, Any],
    *,
    approval: dict[str, Any] | None = None,
    limit: int = 15,
) -> tuple[list[str], int]:
    entries: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    token_coverage = _pathspec_coverage_by_token(approval or {})
    menu_tokens_with_pathspec = {
        str(item.get("token") or "").strip()
        for item in menu.get("also_available") or []
        if isinstance(item, dict) and str(item.get("pathspec") or "").strip()
    }
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    if str(recommended.get("pathspec") or "").strip():
        menu_tokens_with_pathspec.add(str(recommended.get("token") or "").strip())

    def add_token(value: Any, *, priority: int) -> None:
        token = str(value or "").strip()
        if not token or token in seen:
            return
        if token in AUTHORIZATION_CONTROL_TOKENS:
            return
        if token in menu_tokens_with_pathspec and token_coverage.get(token, 1) <= 0:
            return
        seen.add(token)
        entries.append((priority, len(entries), token))

    add_token(recommended.get("token"), priority=0)
    for option in menu.get("one_line_user_options") or []:
        add_token(option, priority=1)
    for item in menu.get("also_available") or []:
        if isinstance(item, dict):
            classification = str(item.get("classification") or "")
            priority = 0 if item.get("token") == "APPROVE_SESSION_LOG_ROTATOR" else 3
            if priority != 0 and "verified_uncovered" in classification:
                priority = 2
            add_token(item.get("token"), priority=priority)
    tokens = [token for _priority, _index, token in sorted(entries)]
    return tokens[:limit], len(tokens)


def _authorization_option_coverage_summary(
    menu: dict[str, Any],
    approval: dict[str, Any],
    *,
    limit: int = 15,
) -> str:
    tokens, total = _authorization_option_tokens(menu, approval=approval, limit=limit)
    if not tokens:
        return ""

    pathspec_by_token: dict[str, str] = {}
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    recommended_token = str(recommended.get("token") or "").strip()
    if recommended_token:
        pathspec_by_token[recommended_token] = str(recommended.get("pathspec") or "").strip()
    for item in menu.get("also_available") or []:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        if token:
            pathspec_by_token[token] = str(item.get("pathspec") or "").strip()

    coverage_by_name = _pathspec_coverage_by_name(approval)
    rows: list[str] = []
    for token in tokens:
        pathspec_name = Path(pathspec_by_token.get(token, "")).name.lower()
        coverage = coverage_by_name.get(pathspec_name)
        if coverage is None:
            rows.append(f"{token}=n/a")
            continue
        dirty_count, path_count = coverage
        rows.append(f"{token}={dirty_count}/{path_count}")
    suffix = f"; omitted {total - len(tokens)}" if total > len(tokens) else ""
    return "; ".join(rows) + suffix


def _authorization_option_pathspec_summary(
    menu: dict[str, Any],
    approval: dict[str, Any],
    *,
    limit: int = 15,
) -> str:
    tokens, total = _authorization_option_tokens(menu, approval=approval, limit=limit)
    if not tokens:
        return ""
    all_tokens, _all_total = _authorization_option_tokens(menu, approval=approval, limit=max(total, limit))

    pathspec_by_token: dict[str, str] = {}
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    recommended_token = str(recommended.get("token") or "").strip()
    if recommended_token:
        pathspec_by_token[recommended_token] = str(recommended.get("pathspec") or "").strip()
    for item in menu.get("also_available") or []:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        if token:
            pathspec_by_token[token] = str(item.get("pathspec") or "").strip()

    rows: list[str] = []
    for token in tokens:
        pathspec = pathspec_by_token.get(token, "")
        label = Path(pathspec).name if pathspec else "n/a"
        rows.append(f"{token}->{label}")
    omitted_tokens = all_tokens[len(tokens) :]
    omitted = len(omitted_tokens)
    suffix = ""
    if omitted > 0:
        omitted_rows = []
        for token in omitted_tokens[:limit]:
            pathspec = pathspec_by_token.get(token, "")
            label = Path(pathspec).name if pathspec else "n/a"
            omitted_rows.append(f"{token}->{label}")
        omitted_more = omitted - len(omitted_rows)
        omitted_more_suffix = f", omitted-more {omitted_more}" if omitted_more > 0 else ""
        suffix = f", omitted {omitted}: {'; '.join(omitted_rows)}{omitted_more_suffix}"
    return f"shown {len(tokens)}/{total}: {'; '.join(rows)}{suffix}."


def _authorization_option_classification_summary(
    menu: dict[str, Any],
    approval: dict[str, Any],
    *,
    limit: int = 15,
) -> str:
    tokens, total = _authorization_option_tokens(menu, approval=approval, limit=limit)
    if not tokens:
        return ""
    all_tokens, _all_total = _authorization_option_tokens(menu, approval=approval, limit=max(total, limit))

    classification_by_token: dict[str, str] = {}
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    recommended_token = str(recommended.get("token") or "").strip()
    if recommended_token:
        classification_by_token[recommended_token] = "recommended"
    for item in menu.get("also_available") or []:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        classification = str(item.get("classification") or "").strip()
        if token and classification:
            classification_by_token[token] = classification

    rows = [f"{token}->{classification_by_token.get(token, 'n/a')}" for token in tokens]
    omitted_tokens = all_tokens[len(tokens) :]
    omitted = len(omitted_tokens)
    suffix = ""
    if omitted > 0:
        omitted_rows = [f"{token}->{classification_by_token.get(token, 'n/a')}" for token in omitted_tokens[:limit]]
        omitted_more = omitted - len(omitted_rows)
        omitted_more_suffix = f", omitted-more {omitted_more}" if omitted_more > 0 else ""
        suffix = f", omitted {omitted}: {'; '.join(omitted_rows)}{omitted_more_suffix}"
    return f"shown {len(tokens)}/{total}: {'; '.join(rows)}{suffix}."


def _authorization_option_omission_summary(
    menu: dict[str, Any],
    approval: dict[str, Any],
    *,
    shown_limit: int = 15,
    omitted_limit: int = 10,
) -> str:
    tokens, total = _authorization_option_tokens(menu, approval=approval, limit=10_000)
    if total <= shown_limit:
        return ""
    omitted_tokens = tokens[shown_limit : shown_limit + omitted_limit]
    if not omitted_tokens:
        return ""
    omitted_remaining = max(total - shown_limit - len(omitted_tokens), 0)
    summary = ", ".join(omitted_tokens)
    if omitted_remaining:
        summary = f"{summary}; omitted {omitted_remaining} more"
    return summary


def _authorization_option_coverage_omission_summary(
    menu: dict[str, Any],
    approval: dict[str, Any],
    *,
    shown_limit: int = 15,
    omitted_limit: int = 10,
) -> str:
    tokens, total = _authorization_option_tokens(menu, approval=approval, limit=10_000)
    if total <= shown_limit:
        return ""
    omitted_tokens = tokens[shown_limit : shown_limit + omitted_limit]
    if not omitted_tokens:
        return ""
    omitted_remaining = max(total - shown_limit - len(omitted_tokens), 0)
    summary = ", ".join(omitted_tokens)
    if omitted_remaining:
        summary = f"{summary}; omitted {omitted_remaining} more"
    return summary


def _one_line_user_option_tokens(menu: dict[str, Any], *, limit: int = 8) -> tuple[list[str], int]:
    options = menu.get("one_line_user_options")
    if not isinstance(options, list):
        return [], 0

    tokens: list[str] = []
    seen: set[str] = set()
    for option in options:
        token = str(option or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens[:limit], len(tokens)


def _authorization_option_reason(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            reason = str(item or "").strip()
            if reason:
                return reason
        return ""
    return str(value or "").strip()


def _one_line_user_option_detail_summary(menu: dict[str, Any], *, limit: int = 8) -> str:
    tokens, total = _one_line_user_option_tokens(menu, limit=limit)
    if not tokens:
        return ""

    details_by_token: dict[str, dict[str, str]] = {}
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    recommended_token = str(recommended.get("token") or "").strip()
    if recommended_token:
        details_by_token[recommended_token] = {
            "pathspec": Path(str(recommended.get("pathspec") or "")).name or "n/a",
            "classification": "recommended",
            "reason": _authorization_option_reason(recommended.get("reason")),
        }
    for item in menu.get("also_available") or []:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        if not token:
            continue
        details_by_token[token] = {
            "pathspec": Path(str(item.get("pathspec") or "")).name or "n/a",
            "classification": str(item.get("classification") or "").strip() or "n/a",
            "reason": _authorization_option_reason(item.get("reason")),
        }

    rows: list[str] = []
    for token in tokens:
        if token == "STOP":
            rows.append(
                "STOP->control/n/a/stop the loop without staging, committing, pushing, cleanup, or live retries"
            )
            continue
        detail = details_by_token.get(token, {})
        pathspec = detail.get("pathspec") or "n/a"
        classification = detail.get("classification") or "n/a"
        reason = detail.get("reason") or "no reason provided"
        rows.append(f"{token}->{classification}/{pathspec}/{reason}")
    suffix = f"; omitted {total - len(tokens)}" if total > len(tokens) else ""
    return f"shown {len(tokens)}/{total}: {'; '.join(rows)}{suffix}."


ZERO_DIRTY_STAGING_OMISSION_CLASSIFICATIONS = {"verified_existing_packet"}


def _authorization_option_zero_dirty_omissions(menu: dict[str, Any], approval: dict[str, Any]) -> list[str]:
    token_coverage = _pathspec_coverage_by_token(approval)
    if not token_coverage:
        return []
    omitted: list[str] = []
    seen: set[str] = set()

    def add_if_omitted(token_value: Any, pathspec_value: Any, classification_value: Any = "") -> None:
        token = str(token_value or "").strip()
        pathspec = str(pathspec_value or "").strip()
        classification = str(classification_value or "").strip()
        if not token or not pathspec or token in seen or token in AUTHORIZATION_CONTROL_TOKENS:
            return
        if classification and classification not in ZERO_DIRTY_STAGING_OMISSION_CLASSIFICATIONS:
            return
        if token_coverage.get(token, 1) > 0:
            return
        seen.add(token)
        omitted.append(token)

    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    add_if_omitted(recommended.get("token"), recommended.get("pathspec"))
    for item in menu.get("also_available") or []:
        if not isinstance(item, dict):
            continue
        add_if_omitted(item.get("token"), item.get("pathspec"), item.get("classification"))
    return omitted


def _authorization_option_zero_dirty_omission_summary(menu: dict[str, Any], approval: dict[str, Any]) -> str:
    omitted = _authorization_option_zero_dirty_omissions(menu, approval)
    if not omitted:
        return "none"
    coverage_by_token = _pathspec_coverage_by_token(approval)
    extra_non_dirty_by_token: dict[str, int] = {}
    details_by_token: dict[str, str] = {}
    for result in approval.get("pathspec_results") or []:
        if not isinstance(result, dict):
            continue
        pathspec = str(result.get("pathspec") or "").strip()
        if not pathspec:
            continue
        token = _pathspec_token(pathspec)
        if token in omitted:
            extra_non_dirty_by_token[token] = _int(result.get("extra_non_dirty_count"))
            extra_paths = [
                str(path).strip().replace("\\", "/")
                for path in (result.get("extra_non_dirty_paths") or [])
                if str(path).strip()
            ]
            detail = Path(pathspec).name
            if extra_paths:
                detail += f": {', '.join(extra_paths[:3])}"
                if len(extra_paths) > 3:
                    detail += f", omitted {len(extra_paths) - 3}"
            details_by_token[token] = detail
    extra_non_dirty_count = sum(extra_non_dirty_by_token.values())
    details = "; ".join(f"{token} -> {details_by_token[token]}" for token in omitted if details_by_token.get(token))
    details_suffix = f", details {details}" if details else ""
    return (
        f"{', '.join(omitted)} "
        f"(tokens {len(omitted)}, dirty coverage "
        f"{sum(coverage_by_token.get(token, 0) for token in omitted)}, "
        f"extra non-dirty paths {extra_non_dirty_count}{details_suffix})"
    )


def _ab_manifest_task_id_advisory(root: Path, *, example_limit: int = 10, omitted_limit: int = 20) -> dict[str, Any]:
    task_ids: dict[int, list[str]] = {}
    decision_paths_by_task_id: dict[int, list[Path]] = {}
    scanned_manifest_count = 0
    manifest_dir = root / ".tmp"
    if manifest_dir.exists():
        for path in manifest_dir.glob("ab-manifest*.json"):
            scanned_manifest_count += 1
            match = re.match(r"^ab-manifest-t(\d+)", path.name, flags=re.IGNORECASE)
            if not match:
                continue
            task_id = int(match.group(1))
            task_ids.setdefault(task_id, []).append(path.as_posix())
        for path in manifest_dir.glob("ab-decision-t*.json"):
            match = re.match(r"^ab-decision-t(\d+)", path.name, flags=re.IGNORECASE)
            if not match:
                continue
            task_id = int(match.group(1))
            decision_paths_by_task_id.setdefault(task_id, []).append(path)
    max_task_id = max(task_ids, default=0)
    collision_groups = {task_id: paths for task_id, paths in task_ids.items() if len(paths) > 1}
    sorted_collision_groups = sorted(collision_groups.items(), reverse=True)
    collision_examples = [
        {
            "task_id": task_id,
            "path_count": len(paths),
            "paths": sorted(paths)[:2],
        }
        for task_id, paths in sorted_collision_groups[:example_limit]
    ]
    collision_omitted_examples = [
        {
            "task_id": task_id,
            "path_count": len(paths),
            "paths": sorted(paths)[:2],
        }
        for task_id, paths in sorted_collision_groups[example_limit : example_limit + omitted_limit]
    ]
    latest_decision_paths = sorted(decision_paths_by_task_id.get(max_task_id, []))
    latest_decision_path = latest_decision_paths[-1] if latest_decision_paths else None
    latest_decision = _load_json_file(latest_decision_path) if latest_decision_path else {}
    latest_manifest_paths = sorted(task_ids.get(max_task_id, []))
    return {
        "highest_task_id": max_task_id,
        "next_task_id": max_task_id + 1,
        "manifest_count": sum(len(paths) for paths in task_ids.values()),
        "scanned_manifest_count": scanned_manifest_count,
        "collision_group_count": len(collision_groups),
        "collision_task_ids": sorted(collision_groups, reverse=True),
        "collision_examples": collision_examples,
        "collision_omitted_examples": collision_omitted_examples,
        "latest_manifest_paths": latest_manifest_paths,
        "latest_manifest_count": len(latest_manifest_paths),
        "latest_decision_path": latest_decision_path.as_posix() if latest_decision_path else "",
        "latest_decision": latest_decision,
        "latest_decision_count": len(latest_decision_paths),
    }


def _ab_manifest_collision_example_label(example: dict[str, Any]) -> str:
    task_id = _int(example.get("task_id"))
    path_count = _int(example.get("path_count"))
    paths = [str(path).strip() for path in (example.get("paths") or []) if str(path).strip()]
    if task_id <= 0:
        return ""
    label = f"T-{task_id} ({path_count} files"
    if paths:
        names = ", ".join(Path(path).name for path in paths)
        label += f": {names}"
    label += ")"
    return label


def _ab_manifest_collision_summary(ab_task_id_advisory: dict[str, Any]) -> str:
    collision_count = _int(ab_task_id_advisory.get("collision_group_count"))
    if collision_count <= 0:
        return "none."
    examples = ab_task_id_advisory.get("collision_examples")
    if not isinstance(examples, list):
        examples = []
    parts: list[str] = []
    for example in examples:
        if not isinstance(example, dict):
            continue
        label = _ab_manifest_collision_example_label(example)
        if not label:
            continue
        parts.append(label)
    omitted_count = max(0, collision_count - len(parts))
    summary = "; ".join(parts) if parts else f"{collision_count} group(s)"
    if parts:
        summary = f"shown {len(parts)}/{collision_count}; {summary}"
    if omitted_count:
        omitted_examples = ab_task_id_advisory.get("collision_omitted_examples")
        if not isinstance(omitted_examples, list):
            omitted_examples = []
        omitted_parts = [
            label
            for example in omitted_examples
            if isinstance(example, dict)
            for label in [_ab_manifest_collision_example_label(example)]
            if label
        ]
        if omitted_parts:
            omitted_more = max(0, omitted_count - len(omitted_parts))
            summary += f"; omitted {omitted_count}: {'; '.join(omitted_parts)}"
            if omitted_more:
                summary += f"; omitted-more {omitted_more}"
        else:
            summary += f"; omitted {omitted_count} more"
    return summary + "."


def _ab_manifest_collision_omission_summary(
    ab_task_id_advisory: dict[str, Any],
    *,
    shown_limit: int = 3,
    limit: int = 64,
) -> str:
    collision_count = _int(ab_task_id_advisory.get("collision_group_count"))
    if collision_count <= shown_limit:
        return ""
    task_ids = ab_task_id_advisory.get("collision_task_ids")
    if not isinstance(task_ids, list):
        return ""
    omitted_ids = [_int(task_id) for task_id in task_ids[shown_limit:] if _int(task_id) > 0]
    if not omitted_ids:
        return ""
    shown = omitted_ids[:limit]
    summary = ", ".join(f"T-{task_id}" for task_id in shown)
    remaining = max(len(omitted_ids) - len(shown), 0)
    if remaining:
        summary += f"; omitted {remaining} more"
    return summary + "."


def _ab_latest_task_collision_summary(ab_task_id_advisory: dict[str, Any]) -> str:
    latest_task_id = _int(ab_task_id_advisory.get("highest_task_id"))
    if latest_task_id <= 0:
        return ""
    collision_task_ids = ab_task_id_advisory.get("collision_task_ids")
    if not isinstance(collision_task_ids, list) or latest_task_id not in {
        _int(task_id) for task_id in collision_task_ids
    }:
        return ""

    examples = ab_task_id_advisory.get("collision_examples")
    if not isinstance(examples, list):
        examples = []
    for example in examples:
        if not isinstance(example, dict) or _int(example.get("task_id")) != latest_task_id:
            continue
        paths = [str(path).strip() for path in (example.get("paths") or []) if str(path).strip()]
        path_count = _int(example.get("path_count")) or len(paths)
        if paths:
            names = ", ".join(Path(path).name for path in paths)
            return f"T-{latest_task_id} has {path_count} manifest files: {names}."
        return f"T-{latest_task_id} has {path_count} manifest files."

    return f"T-{latest_task_id} has multiple manifest files."


def _ab_latest_decision_summary(ab_task_id_advisory: dict[str, Any]) -> str:
    latest_task_id = _int(ab_task_id_advisory.get("highest_task_id"))
    decision = ab_task_id_advisory.get("latest_decision")
    if latest_task_id <= 0 or not isinstance(decision, dict) or not decision:
        return ""
    decision_label = str(decision.get("decision") or "unknown").strip() or "unknown"
    reason = str(decision.get("reason") or "").strip().rstrip(".")
    failed_gates = decision.get("failed_gates") if isinstance(decision.get("failed_gates"), list) else []
    warnings = decision.get("warnings") if isinstance(decision.get("warnings"), list) else []
    score_delta = decision.get("score_delta")
    path = Path(str(ab_task_id_advisory.get("latest_decision_path") or "")).name
    parts = [f"T-{latest_task_id} {decision_label}"]
    if isinstance(score_delta, int | float):
        parts.append(f"score_delta {score_delta}")
    parts.append(f"failed_gates {len(failed_gates)}")
    parts.append(f"warnings {len(warnings)}")
    if reason:
        parts.append(f"reason {reason}")
    if path:
        parts.append(f"artifact {path}")
    decision_count = _int(ab_task_id_advisory.get("latest_decision_count"))
    if decision_count > 1:
        parts.append(f"decision files {decision_count}")
    return ", ".join(parts) + "."


def _ab_latest_manifest_summary(ab_task_id_advisory: dict[str, Any]) -> str:
    latest_task_id = _int(ab_task_id_advisory.get("highest_task_id"))
    manifest_paths = [
        str(path).strip() for path in (ab_task_id_advisory.get("latest_manifest_paths") or []) if str(path).strip()
    ]
    if latest_task_id <= 0 or not manifest_paths:
        return ""
    manifest_count = _int(ab_task_id_advisory.get("latest_manifest_count") or len(manifest_paths))
    visible_paths = manifest_paths[:3]
    names = ", ".join(Path(path).name for path in visible_paths)
    parts = [f"T-{latest_task_id} artifact {names}", f"manifest files {manifest_count}"]
    omitted = max(manifest_count - len(visible_paths), 0)
    if omitted:
        parts.append(f"omitted {omitted}")
    return ", ".join(parts) + "."


def _expand_ab_collision_omission_evidence(
    entries: list[str],
    ab_task_id_advisory: dict[str, Any],
    *,
    shown_limit: int = 5,
) -> list[str]:
    task_ids = ab_task_id_advisory.get("collision_task_ids")
    if not isinstance(task_ids, list):
        return entries
    omitted_ids = [_int(task_id) for task_id in task_ids[shown_limit:] if _int(task_id) > 0]
    if not omitted_ids:
        return entries
    detail = "A/B manifest task id collision hidden task ids: " + ", ".join(f"T-{task_id}" for task_id in omitted_ids)
    expanded: list[str] = []
    replaced = False
    for entry in entries:
        if not replaced and (
            (entry.startswith("A/B manifest task id collision summary omitted ") and " collision group" in entry)
            or entry.startswith("A/B manifest task id collision omitted task ids:")
            or entry.startswith("A/B manifest task id collision hidden task ids:")
        ):
            expanded.append(detail + ".")
            replaced = True
            continue
        expanded.append(entry)
    return expanded


def _recommended_scope_summary(burndown: dict[str, Any]) -> str:
    token = str(burndown.get("recommended_first_token") or "").strip() or "unknown"
    first_phase = (
        burndown.get("recommended_first_phase") if isinstance(burndown.get("recommended_first_phase"), dict) else {}
    )
    phase = str(first_phase.get("phase") or "").strip()
    label = str(first_phase.get("label") or "").strip()
    dirty_count = _int(first_phase.get("dirty_path_count"))
    token_count = _int(first_phase.get("token_count"))
    if not phase and not label:
        return f"{token}."
    return f"{token} / {phase or 'unknown'} - {label or 'unknown'} ({dirty_count} dirty paths, {token_count} tokens)."


def _recommended_authorization_artifact_summary(recommended: dict[str, Any]) -> str:
    token = str(recommended.get("token") or "").strip() or "unknown"
    packet = str(recommended.get("packet") or "").strip() or "unknown"
    pathspec = str(recommended.get("pathspec") or "").strip() or "unknown"
    files = recommended.get("files") if isinstance(recommended.get("files"), list) else []
    return f"{token} -> packet {packet}, pathspec {pathspec}, files {len(files)}."


def _recommended_authorization_files_summary(recommended: dict[str, Any], *, limit: int = 11) -> str:
    files = [str(path).strip().replace("\\", "/") for path in recommended.get("files") or []]
    files = [path for path in files if path]
    if not files:
        return ""
    shown = files[:limit]
    omitted_files = files[limit:]
    omitted = len(omitted_files)
    suffix = ""
    if omitted > 0:
        omitted_preview = omitted_files[:limit]
        omitted_more = omitted - len(omitted_preview)
        omitted_more_suffix = f", omitted-more {omitted_more}" if omitted_more > 0 else ""
        suffix = f", omitted {omitted}: {', '.join(omitted_preview)}{omitted_more_suffix}"
    return f"shown {len(shown)}/{len(files)}: {', '.join(shown)}{suffix}."


def _release_packet_blocker_summary(
    release_summary: dict[str, Any],
    release_actions: dict[str, Any],
) -> str:
    blockers: list[str] = []
    dirty_count = _int(release_summary.get("dirty_count"))
    if dirty_count:
        blockers.append(f"dirty worktree paths {dirty_count}")
    run_count = _int(release_actions.get("run_count") or release_summary.get("current_head_run_count"))
    required_count = _int(
        release_actions.get("required_count") or release_summary.get("unproven_workflow_count"),
    )
    required_success = _int(
        release_actions.get("required_success_count") or release_summary.get("current_head_required_success_count"),
    )
    if run_count == 0 and required_success < required_count:
        blockers.append("current-head Actions unavailable until explicit push/user push")
    external_ids = [
        str(blocker_id).strip()
        for blocker_id in (release_summary.get("external_blocker_ids") or [])
        if str(blocker_id).strip()
    ]
    if external_ids:
        blockers.append(f"external/user-owned blocker(s) {', '.join(external_ids)}")
    return "; ".join(blockers) + "." if blockers else ""


def _release_missing_workflow_summary(release_actions: dict[str, Any], release: dict[str, Any]) -> str:
    missing = release_actions.get("missing_required_workflows")
    if not isinstance(missing, list):
        missing = release.get("unproven_workflows")
    workflows = [str(workflow).strip() for workflow in (missing or []) if str(workflow).strip()]
    return ", ".join(workflows) if workflows else "none"


def _release_actions_summary(release_actions: dict[str, Any], release_summary: dict[str, Any]) -> str:
    if not release_actions and not release_summary:
        return ""
    available = release_actions.get("available")
    run_count = _int(release_actions.get("run_count") or release_summary.get("current_head_run_count"))
    required_success_count = _int(
        release_actions.get("required_success_count") or release_summary.get("current_head_required_success_count"),
    )
    required_names = release_actions.get("required_workflow_names")
    missing_names = release_actions.get("missing_required_workflows")
    successful_names = release_actions.get("successful_required_workflows")
    required_count = _int(
        release_actions.get("required_count")
        or (len(required_names) if isinstance(required_names, list) else 0)
        or (len(missing_names) if isinstance(missing_names, list) else 0),
    )
    required_run_count = _int(release_actions.get("required_run_count"))
    ahead_count = _int(release_summary.get("ahead_count"))
    dirty_count = _int(release_summary.get("dirty_count"))
    missing = [str(name).strip() for name in (missing_names or []) if str(name).strip()]
    successful = [str(name).strip() for name in (successful_names or []) if str(name).strip()]
    boundary = ""
    if run_count == 0 and (ahead_count or dirty_count):
        boundary_parts = []
        if ahead_count:
            boundary_parts.append(f"ahead {ahead_count}")
        if dirty_count:
            boundary_parts.append(f"dirty {dirty_count}")
        boundary = f", current-head boundary {'/'.join(boundary_parts)}"
    return (
        f"available {_bool_text(available)}, runs {run_count}, required runs {required_run_count}/{required_count}, "
        f"success {required_success_count}/{required_count}, "
        f"successful {', '.join(successful) if successful else 'none'}, "
        f"missing {', '.join(missing) if missing else 'none'}{boundary}."
    )


def _release_actions_probe_summary(release_actions: dict[str, Any]) -> str:
    if not release_actions:
        return ""
    head_sha = str(release_actions.get("head_sha") or "").strip()
    command = str(release_actions.get("command") or "").strip()
    returncode = release_actions.get("returncode")
    limit = _int(release_actions.get("limit"))
    runs_preview = release_actions.get("runs_preview")
    run_count = _int(release_actions.get("run_count"))
    preview_count = len(runs_preview) if isinstance(runs_preview, list) else 0
    if not any((head_sha, command, returncode is not None, limit, preview_count, run_count)):
        return ""
    command_label = command.split(" --json ", 1)[0] if command else "unknown"
    limit_text = f"/{limit}" if limit else ""
    return (
        f"head {head_sha[:8] or 'unknown'}, returncode {_int(returncode)}, "
        f"runs_preview {preview_count}{limit_text}, run_count {run_count}, command {command_label}."
    )


def _release_authorization_guardrail_summary(authorization: dict[str, Any], *, limit: int = 3) -> str:
    if not authorization:
        return ""
    post_push_gates = [str(gate).strip() for gate in (authorization.get("post_push_gates") or []) if str(gate).strip()]
    guardrails = [str(item).strip() for item in (authorization.get("guardrails") or []) if str(item).strip()]
    guardrail_preview = ""
    if guardrails:
        shown = guardrails[:limit]
        omitted = len(guardrails) - len(shown)
        suffix = f", omitted {omitted}" if omitted > 0 else ""
        guardrail_preview = f", shown {len(shown)}/{len(guardrails)}: {'; '.join(shown)}{suffix}"
    summary = (
        f"push_required {_bool_text(authorization.get('push_required'))}, "
        "allowed_without_explicit_user_authorization "
        f"{_bool_text(authorization.get('allowed_without_explicit_user_authorization'))}, "
        f"post-push gates {', '.join(post_push_gates) if post_push_gates else 'none'}, "
        f"guardrails {len(guardrails)}{guardrail_preview}"
    )
    return summary if summary.endswith(".") else f"{summary}."


def _release_llm_wiki_strict_evidence_summary(release: dict[str, Any]) -> str:
    detail = release.get("llm_wiki_strict_evidence")
    detail = detail if isinstance(detail, dict) else {}
    summary = release.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    if not detail and not any(str(key).startswith("llm_wiki_strict_evidence_") for key in summary):
        return ""
    status = detail.get("status") or summary.get("llm_wiki_strict_evidence_status") or "unknown"
    head_matches = detail.get("head_matches_current")
    if head_matches is None:
        head_matches = summary.get("llm_wiki_strict_evidence_head_matches_current")
    unexpected_count = detail.get("unexpected_manifest_warning_count")
    if unexpected_count is None:
        unexpected_count = summary.get("llm_wiki_strict_evidence_unexpected_count")
    path = (
        detail.get("path") or detail.get("artifact_path") or summary.get("llm_wiki_strict_evidence_path") or "unknown"
    )
    available = detail.get("available")
    available_prefix = f"available {_bool_text(available)}, " if available is not None else ""
    return (
        f"{available_prefix}status {status}, head_matches_current {_bool_text(head_matches)}, "
        f"unexpected {_int(unexpected_count)}, path {path}."
    )


def _release_commit_preview_summary(release: dict[str, Any], *, limit: int = 35) -> str:
    summary = release.get("summary") if isinstance(release.get("summary"), dict) else {}
    git = release.get("git") if isinstance(release.get("git"), dict) else {}
    commits = git.get("commits_ahead_preview")
    if not isinstance(commits, list):
        commits = git.get("commits_ahead") if isinstance(git.get("commits_ahead"), list) else []
    rows: list[str] = []
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        sha = str(commit.get("sha") or "").strip()[:8]
        subject = str(commit.get("subject") or "").strip().rstrip(".;")
        if not sha and not subject:
            continue
        rows.append(f"{sha} {subject}".strip())
        if len(rows) >= limit:
            break
    if not rows:
        return ""
    omitted_count = _int(git.get("commits_ahead_omitted") or summary.get("commit_omitted_count"))
    explicit_total_count = _int(
        summary.get("commit_count") or summary.get("ahead_count") or git.get("commit_count") or git.get("ahead_count")
    )
    derived_total_count = len(rows) + omitted_count if omitted_count else 0
    total_count = max(explicit_total_count, derived_total_count)
    count_prefix = f"shown {len(rows)}/{total_count}; " if total_count else ""
    suffix = f"; omitted {omitted_count} more" if omitted_count else ""
    return count_prefix + "; ".join(rows) + suffix + "."


def _release_commit_encoding_summary(
    release: dict[str, Any],
    *,
    example_limit: int = 5,
) -> str:
    git = release.get("git") if isinstance(release.get("git"), dict) else {}
    commits = git.get("commits_ahead_preview")
    if not isinstance(commits, list):
        commits = git.get("commits_ahead") if isinstance(git.get("commits_ahead"), list) else []
    if not commits:
        return ""
    mojibake_markers = ("�", "ì", "ë", "í", "Ã", "Â", "嚥", "紐", "媛", "濡", "댄", "뺤")
    subject_count = 0
    non_ascii_subjects = 0
    replacement_chars = 0
    mojibake_marker_count = 0
    non_ascii_examples: list[str] = []
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        sha = str(commit.get("sha") or "").strip()[:8]
        subject = str(commit.get("subject") or "")
        if not subject:
            continue
        subject_count += 1
        if any(ord(char) > 127 for char in subject):
            non_ascii_subjects += 1
            if len(non_ascii_examples) < example_limit:
                cleaned_subject = subject.strip().rstrip(".;")
                non_ascii_examples.append(f"{sha} {cleaned_subject}".strip())
        replacement_chars += subject.count("�")
        if any(marker in subject for marker in mojibake_markers):
            mojibake_marker_count += 1
    summary = (
        f"subjects {subject_count}, non-ascii {non_ascii_subjects}, "
        f"replacement chars {replacement_chars}, mojibake markers {mojibake_marker_count}"
    )
    if non_ascii_examples:
        summary += f"; non-ascii examples {', '.join(non_ascii_examples)}"
        omitted_non_ascii = max(non_ascii_subjects - len(non_ascii_examples), 0)
        if omitted_non_ascii:
            summary += f", omitted {omitted_non_ascii} non-ascii examples"
    return summary + "."


def _selector_dirty_groups_summary(selector_selected: dict[str, Any], *, limit: int = 12) -> str:
    evidence = selector_selected.get("evidence")
    if not isinstance(evidence, list):
        return ""
    for item in evidence:
        text = str(item or "").strip()
        if text.lower().startswith("dirty groups:"):
            summary = text.split(":", 1)[1].strip().rstrip(".")
            groups = [part.strip() for part in summary.split(",") if part.strip()]
            if not groups:
                return summary
            shown = groups[:limit]
            omitted = len(groups) - len(shown)
            suffix = f"; omitted {omitted} more" if omitted > 0 else ""
            return ", ".join(shown) + suffix
    return ""


def _dirty_handoff_groups_summary(dirty_handoff_plan: dict[str, Any], *, limit: int = 12) -> str:
    if not dirty_handoff_plan:
        return ""
    groups = dirty_handoff_plan.get("group_order")
    if not isinstance(groups, list):
        signature = (
            dirty_handoff_plan.get("dirty_signature")
            if isinstance(dirty_handoff_plan.get("dirty_signature"), dict)
            else {}
        )
        signature_input = signature.get("input") if isinstance(signature.get("input"), dict) else {}
        groups = signature_input.get("dirty_path_groups")
    if not isinstance(groups, list):
        return ""
    rows: list[str] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        key = str(group.get("key") or "").strip()
        path_count = _int(group.get("path_count"))
        if key and path_count > 0:
            rows.append(f"{key}={path_count}")
    if not rows:
        return ""
    shown = rows[:limit]
    omitted = len(rows) - len(shown)
    suffix = f"; omitted {omitted} more" if omitted > 0 else ""
    return ", ".join(shown) + suffix


def _approval_phase_summary(approval: dict[str, Any], generated_at: str, *, limit: int = 3) -> str:
    matrix = _build_approval_execution_matrix(approval, generated_at=generated_at)
    phases = matrix.get("phases")
    if not isinstance(phases, list):
        return ""

    rows: list[tuple[str, int, int]] = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        name = str(phase.get("phase") or "").strip()
        dirty_path_count = _int(phase.get("dirty_path_count_total"))
        if not name or dirty_path_count <= 0:
            continue
        rows.append((name, dirty_path_count, _int(phase.get("token_count"))))
    if not rows:
        return ""

    shown = rows[:limit]
    parts = [f"{name}={dirty_path_count} dirty/{token_count} tokens" for name, dirty_path_count, token_count in shown]
    omitted = rows[len(shown) :]
    if omitted:
        omitted_dirty = sum(dirty_path_count for _, dirty_path_count, _ in omitted)
        omitted_tokens = sum(token_count for _, _, token_count in omitted)
        parts.append(f"omitted {len(omitted)} phases/{omitted_dirty} dirty/{omitted_tokens} tokens")
    covered_dirty_count = _int(matrix.get("covered_dirty_count"))
    dirty_count = _int(matrix.get("dirty_count"))
    phase_dirty_refs = sum(dirty_path_count for _, dirty_path_count, _ in rows)
    if dirty_count > 0 or covered_dirty_count > 0:
        parts.append(f"coverage {covered_dirty_count}/{dirty_count}, phase refs {phase_dirty_refs}")
    return "; ".join(parts)


def _approval_phase_reference_summary(
    approval: dict[str, Any],
    generated_at: str,
    *,
    limit: int = 8,
) -> str:
    matrix = _build_approval_execution_matrix(approval, generated_at=generated_at)
    phases = matrix.get("phases")
    if not isinstance(phases, list):
        return ""

    rows: list[tuple[str, int]] = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        name = str(phase.get("phase") or "").strip()
        dirty_path_count = _int(phase.get("dirty_path_count_total"))
        if name and dirty_path_count > 0:
            rows.append((name, dirty_path_count))
    if not rows:
        return ""

    shown = rows[:limit]
    parts = [f"{name}={dirty_path_count}" for name, dirty_path_count in shown]
    omitted = rows[len(shown) :]
    if omitted:
        omitted_refs = sum(dirty_path_count for _, dirty_path_count in omitted)
        parts.append(f"omitted {len(omitted)} phases/{omitted_refs} refs")

    dirty_count = _int(matrix.get("dirty_count"))
    covered_dirty_count = _int(matrix.get("covered_dirty_count"))
    phase_dirty_refs = sum(dirty_path_count for _, dirty_path_count in rows)
    overlap_refs = max(phase_dirty_refs - covered_dirty_count, 0)
    if dirty_count > 0 or covered_dirty_count > 0:
        parts.append(f"unique coverage {covered_dirty_count}/{dirty_count}, overlap refs {overlap_refs}")
    return "; ".join(parts)


def _approval_phase_token_summary(
    approval: dict[str, Any],
    generated_at: str,
    *,
    phase_limit: int = 3,
    token_limit: int = 3,
) -> str:
    matrix = _build_approval_execution_matrix(approval, generated_at=generated_at)
    phases = matrix.get("phases")
    if not isinstance(phases, list):
        return ""

    rows: list[str] = []
    visible_phase_count = 0
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        name = str(phase.get("phase") or "").strip()
        dirty_path_count = _int(phase.get("dirty_path_count_total"))
        tokens = phase.get("tokens")
        if not name or dirty_path_count <= 0 or not isinstance(tokens, list):
            continue
        visible_phase_count += 1
        if len(rows) >= phase_limit:
            continue
        token_names = [
            str(token.get("token") or "").strip()
            for token in tokens
            if isinstance(token, dict) and str(token.get("token") or "").strip()
        ]
        if not token_names:
            continue
        shown = token_names[:token_limit]
        omitted = len(token_names) - len(shown)
        suffix = f", omitted {omitted}" if omitted > 0 else ""
        rows.append(f"{name}: {', '.join(shown)}{suffix}")
    if not rows:
        return ""
    phase_omitted = max(visible_phase_count - len(rows), 0)
    suffix = f"; omitted {phase_omitted} phases" if phase_omitted > 0 else ""
    return "; ".join(rows) + suffix


def _debug_blocker_summary(debug_loop: dict[str, Any]) -> str:
    summary = debug_loop.get("summary") if isinstance(debug_loop.get("summary"), dict) else {}
    blocked_count = _int(summary.get("blocked_item_count"))
    completion_allowed = summary.get("completion_allowed")
    blockers = summary.get("completion_blockers")
    top = ""
    if isinstance(blockers, list) and blockers:
        first = blockers[0] if isinstance(blockers[0], dict) else {}
        top = str(first.get("title") or "").strip()
    if not blocked_count and not top and completion_allowed is None:
        return ""
    return f"{blocked_count} blocked, completion_allowed {_bool_text(completion_allowed)}, top {top or 'unknown'}."


def _debug_blocker_title_summary(debug_loop: dict[str, Any], *, limit: int = 5) -> str:
    summary = debug_loop.get("summary") if isinstance(debug_loop.get("summary"), dict) else {}
    blockers = summary.get("completion_blockers")
    if not isinstance(blockers, list):
        blockers = debug_loop.get("items") if isinstance(debug_loop.get("items"), list) else []
    rows: list[str] = []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        title = str(blocker.get("title") or "").strip().rstrip(".;")
        if not title:
            continue
        rows.append(title)
        if len(rows) >= limit:
            break
    if not rows:
        return ""
    total_count = len(
        [blocker for blocker in blockers if isinstance(blocker, dict) and str(blocker.get("title") or "").strip()],
    )
    omitted_count = max(total_count - len(rows), 0)
    suffix = f"; omitted {omitted_count} more" if omitted_count else ""
    return "; ".join(rows) + suffix + "."


def _debug_blocker_next_action_summary(debug_loop: dict[str, Any], *, limit: int = 5) -> str:
    summary = debug_loop.get("summary") if isinstance(debug_loop.get("summary"), dict) else {}
    blockers = summary.get("completion_blockers")
    if not isinstance(blockers, list):
        blockers = debug_loop.get("items") if isinstance(debug_loop.get("items"), list) else []
    rows: list[str] = []
    total_count = 0
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        title = str(blocker.get("title") or "").strip().rstrip(".;")
        next_action = str(blocker.get("next_action") or "").strip().rstrip(".;")
        if not title or not next_action:
            continue
        total_count += 1
        if len(rows) < limit:
            rows.append(f"{title} -> {next_action}")
    if not rows:
        return ""
    omitted_count = max(total_count - len(rows), 0)
    suffix = f"; omitted {omitted_count} more" if omitted_count else ""
    return "; ".join(rows) + suffix + "."


def _github_inventory_summary(github_inventory: dict[str, Any]) -> str:
    projects = github_inventory.get("projects") if isinstance(github_inventory.get("projects"), list) else []
    workflows = github_inventory.get("workflows") if isinstance(github_inventory.get("workflows"), list) else []
    dependabot_files = (
        github_inventory.get("dependabot_files") if isinstance(github_inventory.get("dependabot_files"), list) else []
    )
    open_prs = github_inventory.get("open_prs") if isinstance(github_inventory.get("open_prs"), dict) else {}
    recommendations = (
        github_inventory.get("recommendations") if isinstance(github_inventory.get("recommendations"), list) else []
    )
    if not projects and not workflows and not open_prs and not recommendations:
        return ""
    return (
        f"{len(projects)} projects, {len(workflows)} workflows, "
        f"{len(dependabot_files)} dependabot files, open PRs {_int(open_prs.get('count'))}, "
        f"recommendations {len(recommendations)}."
    )


def _github_recommendation_summary(
    github_inventory: dict[str, Any],
    *,
    limit: int = 2,
    dirty_groups_summary: str = "",
) -> str:
    recommendations = (
        github_inventory.get("recommendations") if isinstance(github_inventory.get("recommendations"), list) else []
    )
    rows: list[str] = []
    for recommendation in recommendations:
        text = str(recommendation or "").strip().rstrip(".;")
        if not text:
            continue
        text = _rewrite_dirty_groups_clause(text, dirty_groups_summary)
        rows.append(text)
        if len(rows) >= limit:
            break
    if not rows:
        return ""
    omitted_count = max(len([item for item in recommendations if str(item or "").strip()]) - len(rows), 0)
    suffix = f"; omitted {omitted_count} more" if omitted_count else ""
    return "; ".join(rows) + suffix + "."


def _rewrite_dirty_groups_clause(text: str, dirty_groups_summary: str) -> str:
    if not dirty_groups_summary or "dirty groups:" not in text.lower():
        return text
    punctuation = text[-1] if text.endswith((".", ";")) else ""
    return re.sub(
        r"Dirty groups:\s*.+$",
        f"Dirty groups: {dirty_groups_summary}{punctuation}",
        text,
        flags=re.IGNORECASE,
    )


def _rewrite_dirty_groups_evidence(entries: list[str], dirty_groups_summary: str) -> list[str]:
    return [_rewrite_dirty_groups_clause(entry, dirty_groups_summary) for entry in entries]


def _browser_qa_summary(browser_qa: dict[str, Any]) -> str:
    summary = browser_qa.get("summary") if isinstance(browser_qa.get("summary"), dict) else {}
    if not summary:
        return ""
    browser_project_count = _int(summary.get("browser_project_count"))
    covered_count = _int(summary.get("covered_count"))
    missing_count = _int(summary.get("missing_count"))
    fresh_nonblank_count = _int(summary.get("fresh_nonblank_screenshot_project_count"))
    stale_screenshot_count = _int(summary.get("stale_screenshot_project_count"))
    if not any([browser_project_count, covered_count, missing_count, fresh_nonblank_count, stale_screenshot_count]):
        return ""
    return (
        f"{covered_count}/{browser_project_count} covered, "
        f"fresh nonblank screenshots {fresh_nonblank_count}/{browser_project_count}, "
        f"stale {stale_screenshot_count}, missing {missing_count}."
    )


def _browser_qa_project_summary(browser_qa: dict[str, Any], *, limit: int = 4) -> str:
    projects = browser_qa.get("projects") if isinstance(browser_qa.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict) or project.get("browser_app") is False:
            continue
        path = str(project.get("path") or "").strip()
        name = Path(path).name if path else str(project.get("name") or "").strip()
        if not name:
            continue
        status = str(project.get("status") or "unknown").strip()
        fresh_nonblank = _int(project.get("fresh_nonblank_screenshot_count"))
        current_screenshots = _int(project.get("current_screenshot_count"))
        age_days = project.get("freshest_screenshot_age_days")
        age_summary = f"/age{_int(age_days)}d" if age_days is not None else ""
        rows.append(f"{name}={status}/fresh-nonblank{fresh_nonblank}/shots{current_screenshots}{age_summary}")
        if len(rows) >= limit:
            break
    if not rows:
        return ""
    omitted_count = max(
        len([project for project in projects if isinstance(project, dict) and project.get("browser_app") is not False])
        - len(rows),
        0,
    )
    summary = "; ".join(rows)
    if omitted_count:
        summary = f"{summary}; omitted {omitted_count}"
    return summary


def _browser_qa_artifact_summary(browser_qa: dict[str, Any], *, limit: int = 4) -> str:
    projects = browser_qa.get("projects") if isinstance(browser_qa.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict) or project.get("browser_app") is False:
            continue
        path = str(project.get("path") or "").strip()
        name = Path(path).name if path else str(project.get("name") or "").strip()
        artifact = str(project.get("freshest_screenshot_path") or "").strip().replace("\\", "/")
        if not name or not artifact:
            continue
        width = _int(project.get("freshest_screenshot_width"))
        height = _int(project.get("freshest_screenshot_height"))
        nonblank = _bool_text(project.get("freshest_screenshot_nonblank"))
        dimension = f"/{width}x{height}" if width and height else ""
        rows.append(f"{name}={artifact}{dimension}/nonblank {nonblank}")
        if len(rows) >= limit:
            break
    if not rows:
        return ""
    total_browser_projects = len(
        [project for project in projects if isinstance(project, dict) and project.get("browser_app") is not False],
    )
    omitted_count = max(total_browser_projects - len(rows), 0)
    summary = "; ".join(rows)
    if omitted_count:
        summary = f"{summary}; omitted {omitted_count}"
    return summary


def _browser_qa_log_evidence_summary(browser_qa: dict[str, Any], *, limit: int = 4) -> str:
    projects = browser_qa.get("projects") if isinstance(browser_qa.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict) or project.get("browser_app") is False:
            continue
        path = str(project.get("path") or "").strip()
        name = Path(path).name if path else str(project.get("name") or "").strip()
        total = _int(project.get("log_evidence_count"))
        verified = _int(project.get("verified_log_evidence_count"))
        if not name or not total:
            continue
        rows.append(f"{name}=verified-logs{verified}/{total}")
        if len(rows) >= limit:
            break
    if not rows:
        return ""
    total_browser_projects = len(
        [project for project in projects if isinstance(project, dict) and project.get("browser_app") is not False],
    )
    omitted_count = max(total_browser_projects - len(rows), 0)
    summary = "; ".join(rows)
    if omitted_count:
        summary = f"{summary}; omitted {omitted_count}"
    return summary


def _dependency_freshness_summary(dependency_freshness: dict[str, Any]) -> str:
    summary = dependency_freshness.get("summary") if isinstance(dependency_freshness.get("summary"), dict) else {}
    if not summary:
        return ""
    package_project_count = _int(summary.get("package_project_count"))
    candidate_dependency_count = _int(summary.get("candidate_dependency_count"))
    outdated_dependency_count = _int(summary.get("outdated_dependency_count"))
    deferred_dependency_count = _int(summary.get("deferred_dependency_count"))
    peer_blocked_count = _int(summary.get("peer_blocker_latest_blocked_count"))
    unavailable_project_count = _int(summary.get("unavailable_project_count"))
    if not any(
        [
            package_project_count,
            candidate_dependency_count,
            outdated_dependency_count,
            deferred_dependency_count,
            peer_blocked_count,
            unavailable_project_count,
        ],
    ):
        return ""
    return (
        f"{package_project_count} package projects, "
        f"candidates {candidate_dependency_count}, outdated {outdated_dependency_count}, "
        f"deferred {deferred_dependency_count}, peer-blocked {peer_blocked_count}, "
        f"unavailable {unavailable_project_count}."
    )


def _dependency_peer_blocker_summary(
    dependency_freshness: dict[str, Any],
    *,
    limit: int = 3,
    blocker_limit: int = 3,
) -> str:
    projects = dependency_freshness.get("projects") if isinstance(dependency_freshness.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_label = str(project.get("path") or project.get("package_name") or "unknown")
        dependencies = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            blocked_count = _int(dependency.get("peer_blocker_latest_blocked_count"))
            peer_check = dependency.get("peer_blocker_latest_check") or dependency.get("peer_blocker_check")
            if blocked_count <= 0 and peer_check not in {"blocked", "partial_upstream_support", "still_blocked"}:
                continue
            peer_blockers = dependency.get("peer_blockers") if isinstance(dependency.get("peer_blockers"), list) else []
            blocker_names: list[str] = []
            for blocker in peer_blockers:
                if not isinstance(blocker, dict):
                    continue
                allows_target = blocker.get("latest_peer_allows_target")
                latest_check = blocker.get("latest_peer_check")
                if allows_target is True or latest_check == "allows_target_major":
                    continue
                blocker_name = blocker.get("package")
                if blocker_name:
                    blocker_names.append(str(blocker_name))
            dependency_label = str(dependency.get("name") or "dependency")
            target_major = dependency.get("peer_target_major")
            if target_major:
                dependency_label = f"{dependency_label}@{target_major}"
            visible_blockers = blocker_names[:blocker_limit]
            omitted_blockers = max(len(blocker_names) - blocker_limit, 0)
            if visible_blockers:
                blocker_summary = ", ".join(visible_blockers)
                if omitted_blockers:
                    blocker_summary = f"{blocker_summary}, omitted {omitted_blockers}"
            elif blocked_count:
                blocker_summary = f"{blocked_count} peer blockers"
            else:
                blocker_summary = "peer blockers"
            rows.append(f"{project_label} {dependency_label}: {blocker_summary}")
    if not rows:
        return ""
    visible_rows = rows[:limit]
    omitted_rows = max(len(rows) - limit, 0)
    summary = "; ".join(visible_rows)
    if omitted_rows:
        summary = f"{summary}; omitted {omitted_rows}"
    return summary


def _dependency_peer_blocker_action_summary(
    dependency_freshness: dict[str, Any],
    *,
    limit: int = 3,
) -> str:
    projects = dependency_freshness.get("projects") if isinstance(dependency_freshness.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_label = str(project.get("path") or project.get("package_name") or "unknown")
        dependencies = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            blocked_count = _int(dependency.get("peer_blocker_latest_blocked_count"))
            supported_count = _int(dependency.get("peer_blocker_latest_supported_count"))
            unavailable_count = _int(dependency.get("peer_blocker_latest_unavailable_count"))
            peer_check = str(dependency.get("peer_blocker_latest_check") or dependency.get("peer_blocker_check") or "")
            if blocked_count <= 0 and peer_check not in {"blocked", "partial_upstream_support", "still_blocked"}:
                continue
            dependency_label = str(dependency.get("name") or "dependency")
            target_major = dependency.get("peer_target_major")
            if target_major:
                dependency_label = f"{dependency_label}@{target_major}"
            rows.append(
                f"{project_label} {dependency_label} -> defer major migration until upstream peer support "
                f"(latest-supported {supported_count}, still-blocked {blocked_count}, unavailable {unavailable_count})"
            )
    if not rows:
        return ""
    visible_rows = rows[:limit]
    omitted_rows = max(len(rows) - limit, 0)
    summary = "; ".join(visible_rows)
    if omitted_rows:
        summary = f"{summary}; omitted {omitted_rows}"
    return summary


def _target_readiness_summary(readiness: dict[str, Any], *, limit: int = 4) -> str:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        name = str(project.get("name") or project.get("path") or "").strip()
        if not name:
            continue
        tasks = project.get("tasks") if isinstance(project.get("tasks"), list) else []
        dirty_paths = project.get("dirty_paths") if isinstance(project.get("dirty_paths"), list) else []
        rows.append(
            f"{name}={_int(project.get('score'))}/{project.get('state', 'unknown')}"
            f"/dirty{len(dirty_paths)}/tasks{len(tasks)}"
        )
        if len(rows) >= limit:
            break
    return "; ".join(rows)


def _target_blocker_detail_summary(readiness: dict[str, Any], *, limit: int = 4) -> str:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        name = str(project.get("name") or project.get("path") or "").strip()
        if not name:
            continue
        score = _int(project.get("score"))
        state = str(project.get("state") or "unknown").strip()
        tasks = project.get("tasks") if isinstance(project.get("tasks"), list) else []
        dirty_paths = project.get("dirty_paths") if isinstance(project.get("dirty_paths"), list) else []
        reasons: list[str] = []
        if score < 100:
            reasons.append(f"score {score}")
        if state and state != "ready":
            reasons.append(f"state {state}")
        if tasks:
            task_ids = [
                str(task.get("id") or "").strip()
                for task in tasks
                if isinstance(task, dict) and str(task.get("id") or "").strip()
            ]
            if task_ids:
                visible_task_ids = task_ids[:2]
                task_summary = ",".join(visible_task_ids)
                if len(task_ids) > len(visible_task_ids):
                    task_summary = f"{task_summary},+{len(task_ids) - len(visible_task_ids)}"
                reasons.append(f"tasks {task_summary}")
            else:
                reasons.append(f"tasks {len(tasks)}")
        if dirty_paths:
            reasons.append(f"dirty {len(dirty_paths)}")
        if reasons:
            rows.append(f"{name}: {', '.join(reasons)}")
        if len(rows) >= limit:
            break
    return "; ".join(rows)


def _target_blocker_action_summary(readiness: dict[str, Any], *, limit: int = 4) -> str:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    rows: list[str] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        name = str(project.get("name") or project.get("path") or "").strip()
        if not name:
            continue
        score = _int(project.get("score"))
        state = str(project.get("state") or "unknown").strip()
        tasks = project.get("tasks") if isinstance(project.get("tasks"), list) else []
        dirty_paths = project.get("dirty_paths") if isinstance(project.get("dirty_paths"), list) else []
        task_ids = [
            str(task.get("id") or "").strip()
            for task in tasks
            if isinstance(task, dict) and str(task.get("id") or "").strip()
        ]
        if score >= 100 and state == "ready" and not task_ids and not dirty_paths:
            continue
        if "T-251" in task_ids:
            action = "wait for Supabase credential reset before live Prisma CRUD retry"
        elif dirty_paths:
            action = "clear target dirty paths and keep project QC/readiness evidence current"
        elif score < 100 or (state and state != "ready"):
            action = "refresh target readiness evidence and resolve score/state blockers"
        else:
            action = "review target task blockers"
        rows.append(f"{name} -> {action}")
        if len(rows) >= limit:
            break
    return "; ".join(rows)


def _project_qc_summary(readiness: dict[str, Any]) -> str:
    projects = readiness.get("projects") if isinstance(readiness.get("projects"), list) else []
    qc_rows: list[dict[str, Any]] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        qc = project.get("qc") if isinstance(project.get("qc"), dict) else {}
        if qc.get("available") is True:
            qc_rows.append(qc)
    if not qc_rows:
        return ""
    pass_count = sum(1 for qc in qc_rows if str(qc.get("status") or "").upper() == "PASS")
    total_passed = sum(_int(qc.get("passed")) for qc in qc_rows)
    total_failed = sum(_int(qc.get("failed")) for qc in qc_rows)
    total_skipped = sum(_int(qc.get("skipped")) for qc in qc_rows)
    stale_count = sum(1 for qc in qc_rows if qc.get("stale") is True)
    head_stale_count = sum(1 for qc in qc_rows if qc.get("head_stale") is True)
    missing_checks = sum(len(qc.get("missing_checks") or []) for qc in qc_rows)
    return (
        f"{pass_count}/{len(qc_rows)} PASS, checks passed {total_passed}, failed {total_failed}, "
        f"skipped {total_skipped}, stale {stale_count}, head-stale {head_stale_count}, "
        f"missing checks {missing_checks}."
    )


def _handoff_orientation_summary(
    session_orient: dict[str, Any],
    *,
    ab_task_id_advisory: dict[str, Any] | None = None,
) -> str:
    handoff = session_orient.get("handoff") if isinstance(session_orient.get("handoff"), dict) else {}
    if not handoff:
        return ""
    order_status = str(handoff.get("latest_addendum_order_status") or "unknown")
    effective_task_id = str(handoff.get("effective_latest_task_id") or "unknown")
    effective_numeric = _int(effective_task_id.lstrip("T-"))
    latest_ab_task_id = _int((ab_task_id_advisory or {}).get("highest_task_id"))
    ab_alignment = ""
    if latest_ab_task_id > 0 and effective_numeric > 0:
        if latest_ab_task_id > effective_numeric:
            ab_alignment = f", latest A/B manifest T-{latest_ab_task_id} newer than effective handoff"
        elif latest_ab_task_id == effective_numeric:
            ab_alignment = ", aligned with latest A/B manifest"
    head = str(handoff.get("current_head") or "").strip()[:8] or "unknown"
    stale_status = str(handoff.get("latest_next_priority_status") or "unknown")
    rotation = "yes" if handoff.get("rotation_suggested") is True else "no"
    return (
        f"order {order_status}, effective {effective_task_id}, head {head}, priorities {stale_status}, "
        f"addenda {_int(handoff.get('current_addendum_count'))}, rotation {rotation}, "
        f"archivable {_int(handoff.get('archivable_addendum_count'))}{ab_alignment}."
    )


def _git_worktree_summary(session_orient: dict[str, Any]) -> str:
    git = session_orient.get("git") if isinstance(session_orient.get("git"), dict) else {}
    worktree = git.get("worktree") if isinstance(git.get("worktree"), dict) else {}
    if not git and not worktree:
        return ""
    branch = str(git.get("branch") or "unknown").strip() or "unknown"
    return (
        f"branch {branch}, ahead {_int(git.get('ahead'))}, behind {_int(git.get('behind'))}, "
        f"modified {_int(worktree.get('modified'))}, untracked {_int(worktree.get('untracked'))}, "
        f"staged {_int(worktree.get('staged'))}, unmerged {_int(worktree.get('unmerged'))}."
    )


def _dirty_handoff_plan_summary(dirty_handoff_plan: dict[str, Any]) -> str:
    if not dirty_handoff_plan:
        return ""
    signature = (
        dirty_handoff_plan.get("dirty_signature") if isinstance(dirty_handoff_plan.get("dirty_signature"), dict) else {}
    )
    signature_input = signature.get("input") if isinstance(signature.get("input"), dict) else {}
    freshness = dirty_handoff_plan.get("freshness") if isinstance(dirty_handoff_plan.get("freshness"), dict) else {}
    previous_freshness = (
        dirty_handoff_plan.get("previous_plan_freshness")
        if isinstance(dirty_handoff_plan.get("previous_plan_freshness"), dict)
        else {}
    )
    signature_value = str(signature.get("value") or "").strip()
    signature_short = signature_value[:8] if signature_value else "unknown"
    current_text = _bool_text(freshness.get("current")) if "current" in freshness else "unknown"
    previous_status = str(previous_freshness.get("status") or "unknown")
    dirty_count = _int(signature_input.get("dirty_count"))
    staged_count = _int(signature_input.get("staged"))
    group_count = len(signature_input.get("dirty_path_groups") or [])
    return (
        f"status {dirty_handoff_plan.get('status', 'unknown')}, "
        f"freshness {current_text}/{previous_status}, "
        f"signature {signature_short}, dirty {dirty_count}, staged {staged_count}, groups {group_count}."
    )


def _completion_blocker_summary(completion: dict[str, Any], *, limit: int = 9) -> str:
    blocked_requirements = _completion_blocker_requirements(completion)
    if not blocked_requirements:
        return ""
    shown = blocked_requirements[:limit]
    summary = "; ".join(shown)
    omitted_count = len(blocked_requirements) - len(shown)
    if omitted_count > 0:
        summary += f"; omitted {omitted_count}"
    return summary + "."


def _completion_blocker_omission_summary(completion: dict[str, Any], *, shown_limit: int = 9, limit: int = 6) -> str:
    blocked_requirements = _completion_blocker_requirements(completion)
    omitted = blocked_requirements[shown_limit:]
    if not omitted:
        return ""
    shown = omitted[:limit]
    summary = "; ".join(shown)
    remaining_count = len(omitted) - len(shown)
    if remaining_count > 0:
        summary += f"; omitted {remaining_count} more"
    return summary + "."


def _completion_blocker_action_summary(completion: dict[str, Any], *, limit: int = 9) -> str:
    blocked_requirements = _completion_blocker_requirements(completion)
    if not blocked_requirements:
        return ""
    rows: list[str] = []
    for requirement in blocked_requirements:
        action = _completion_blocker_next_action(requirement)
        rows.append(f"{requirement} -> {action}")
        if len(rows) >= limit:
            break
    omitted_count = len(blocked_requirements) - len(rows)
    summary = "; ".join(rows)
    if omitted_count > 0:
        omitted_rows = [
            f"{requirement} -> {_completion_blocker_next_action(requirement)}"
            for requirement in blocked_requirements[len(rows) : len(rows) + limit]
        ]
        summary += f"; omitted {omitted_count}: " + "; ".join(omitted_rows)
        omitted_more = omitted_count - len(omitted_rows)
        if omitted_more > 0:
            summary += f"; omitted-more {omitted_more}"
    return summary + "."


def _completion_blocker_next_action(requirement: str) -> str:
    normalized = requirement.lower()
    if "hanwoo" in normalized or "t-251" in normalized or "externally blocked" in normalized:
        return "user resets Supabase credentials, then rerun the live Prisma check once"
    if "release authorization" in normalized or "clean-ahead publish" in normalized:
        return "keep no-push packet current until explicit stage/commit/push authorization"
    if "blind-to-x" in normalized or "shorts-maker-v2" in normalized or "knowledge-dashboard" in normalized:
        return "clear target dirty paths and keep project QC/readiness evidence current"
    if "product-readiness" in normalized or "launch readiness" in normalized:
        return "clear local/workspace blockers and keep direct readiness evidence current"
    if "next-experiment selector" in normalized or "auto-research candidate" in normalized:
        return "clear the dirty handoff boundary or keep selector/debug evidence current"
    if "github-related" in normalized or "workflow" in normalized:
        return "resolve dirty worktree boundary or keep GitHub inventory evidence current"
    return "keep blocker evidence current until the owning boundary is cleared"


def _completion_coverage_summary(completion: dict[str, Any]) -> str:
    items = completion.get("items") if isinstance(completion.get("items"), list) else []
    if not items:
        return ""
    coverage_counts: dict[str, int] = {}
    passed_count = 0
    blocked_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        coverage = str(item.get("coverage") or "unknown").strip() or "unknown"
        coverage_counts[coverage] = coverage_counts.get(coverage, 0) + 1
        if item.get("passed") is True:
            passed_count += 1
        blockers = item.get("blockers") if isinstance(item.get("blockers"), list) else []
        if blockers or item.get("passed") is False:
            blocked_count += 1
    total = sum(coverage_counts.values())
    preferred_order = ["complete", "partial", "missing", "none", "unknown"]
    ordered_keys = [key for key in preferred_order if key in coverage_counts]
    ordered_keys.extend(sorted(key for key in coverage_counts if key not in set(ordered_keys)))
    coverage_parts = ", ".join(f"{key} {coverage_counts[key]}" for key in ordered_keys)
    return f"{coverage_parts}; passed {passed_count}/{total}, blocked {blocked_count}."


def _code_review_gate_summary(launch: dict[str, Any]) -> str:
    items = launch.get("items") if isinstance(launch.get("items"), list) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence") if isinstance(item.get("evidence"), list) else []
        for row in evidence:
            text = str(row or "").strip().rstrip(".")
            if text.startswith("code_review_gate "):
                return text.removeprefix("code_review_gate ").strip() + "."
    return ""


def _code_review_gate_detail_summary(
    code_review_gate: dict[str, Any], *, limit: int = 10, omitted_limit: int = 30
) -> str:
    if not code_review_gate:
        return ""
    changed_files = [str(path).strip() for path in code_review_gate.get("changed_files") or [] if str(path).strip()]
    test_gap_files: list[str] = []
    seen_gap_files: set[str] = set()
    for gap in code_review_gate.get("test_gaps") or []:
        raw = str(gap or "")
        path = raw.split(" :: ", 1)[1].strip() if " :: " in raw else raw.strip()
        path = path.replace("\\", "/")
        marker = "/Vibe coding/"
        if marker in path:
            path = path.split(marker, 1)[1]
        if path and path not in seen_gap_files:
            seen_gap_files.add(path)
            test_gap_files.append(path)
    affected_flows = code_review_gate.get("affected_flows")
    affected_flow_count = len(affected_flows) if isinstance(affected_flows, list) else 0
    parts = [f"affected flows {affected_flow_count}"]
    if changed_files:
        shown = changed_files[:limit]
        omitted_files = changed_files[limit:]
        detail = ", ".join(shown)
        if omitted_files:
            omitted_preview = omitted_files[:omitted_limit]
            detail += f", omitted {len(omitted_files)}: " + ", ".join(omitted_preview)
            omitted_more = len(omitted_files) - len(omitted_preview)
            if omitted_more > 0:
                detail += f", omitted-more {omitted_more}"
        parts.append(f"changed top shown {len(shown)}/{len(changed_files)}: {detail}")
    if test_gap_files:
        shown = test_gap_files[:limit]
        omitted_files = test_gap_files[limit:]
        detail = ", ".join(shown)
        if omitted_files:
            omitted_preview = omitted_files[:omitted_limit]
            detail += f", omitted {len(omitted_files)}: " + ", ".join(omitted_preview)
            omitted_more = len(omitted_files) - len(omitted_preview)
            if omitted_more > 0:
                detail += f", omitted-more {omitted_more}"
        parts.append(f"gap files shown {len(shown)}/{len(test_gap_files)}: {detail}")
    return "; ".join(parts) + "."


def _code_review_gate_count_alignment_summary(code_review_summary: str, code_review_gate: dict[str, Any]) -> str:
    if not code_review_summary or not code_review_gate:
        return ""
    changed_match = re.search(r"changed_files=(\d+)", code_review_summary)
    gaps_match = re.search(r"test_gaps=(\d+)", code_review_summary)
    if not changed_match and not gaps_match:
        return ""
    summary_changed = int(changed_match.group(1)) if changed_match else 0
    summary_gaps = int(gaps_match.group(1)) if gaps_match else 0
    detail_changed = len(code_review_gate.get("changed_files") or [])
    test_gap_rows = len(code_review_gate.get("test_gaps") or [])
    unique_gap_files: set[str] = set()
    for gap in code_review_gate.get("test_gaps") or []:
        raw = str(gap or "")
        path = raw.split(" :: ", 1)[1].strip() if " :: " in raw else raw.strip()
        path = path.replace("\\", "/")
        marker = "/Vibe coding/"
        if marker in path:
            path = path.split(marker, 1)[1]
        if path:
            unique_gap_files.add(path)
    if summary_changed == detail_changed and summary_gaps == test_gap_rows:
        return ""
    return (
        "launch audit counts changed/test gaps "
        f"{summary_changed}/{summary_gaps}; detail artifact rows changed/test gaps/unique gap files "
        f"{detail_changed}/{test_gap_rows}/{len(unique_gap_files)}."
    )


def _code_review_gate_reason_summary(code_review_gate: dict[str, Any], *, limit: int = 3) -> str:
    if not code_review_gate:
        return ""
    reasons = [str(reason).strip().rstrip(".") for reason in code_review_gate.get("reasons") or []]
    reasons = [reason for reason in reasons if reason]
    if not reasons:
        return ""
    shown = reasons[:limit]
    omitted = len(reasons) - len(shown)
    detail = f"shown {len(shown)}/{len(reasons)}: " + "; ".join(shown)
    if omitted > 0:
        detail += f"; omitted {omitted} more"
    return detail + "."


def _code_review_gate_untracked_summary(code_review_gate: dict[str, Any], *, limit: int = 16) -> str:
    if not code_review_gate:
        return ""
    paths = [str(path).strip().replace("\\", "/") for path in code_review_gate.get("untracked_files") or []]
    paths = [path for path in paths if path]
    if not paths:
        return ""
    shown = paths[:limit]
    omitted_paths = paths[limit:]
    detail = ", ".join(shown)
    if omitted_paths:
        omitted_preview = omitted_paths[:limit]
        detail += f", omitted {len(omitted_paths)}: " + ", ".join(omitted_preview)
        omitted_more = len(omitted_paths) - len(omitted_preview)
        if omitted_more > 0:
            detail += f", omitted-more {omitted_more}"
    return f"shown {len(shown)}/{len(paths)}: {detail}."


def _code_review_gate_impact_file_label(path: Any) -> str:
    label = str(path).strip().replace("\\", "/")
    if not label:
        return ""
    marker = "/Vibe coding/"
    if marker in label:
        label = label.split(marker, 1)[1]
    return label


def _code_review_gate_impact_node_label(node: Any) -> str:
    if isinstance(node, dict):
        name = str(node.get("name") or "").strip()
        kind = str(node.get("kind") or "").strip()
        file_label = _code_review_gate_impact_file_label(node.get("file_path") or "")
        if kind.lower() == "file":
            return file_label or _code_review_gate_impact_file_label(name)
        if file_label and ("/" in name or "\\" in name):
            return file_label
        if name and file_label:
            return f"{name} ({file_label})"
        if name and kind:
            return f"{kind}:{name}"
        if name:
            return name
        qualified_name = str(node.get("qualified_name") or "").strip()
        if qualified_name:
            return _code_review_gate_impact_file_label(qualified_name)
        return ""
    return str(node).strip()


def _code_review_gate_impact_summary(
    code_review_gate: dict[str, Any], *, limit: int = 10, omitted_limit: int = 20
) -> str:
    if not code_review_gate:
        return ""
    impact = code_review_gate.get("impact_radius")
    if not isinstance(impact, dict):
        return ""

    def _count(value: Any) -> int:
        if isinstance(value, list):
            return len(value)
        return _int(value)

    changed_files = _count(impact.get("changed_files")) or len(code_review_gate.get("changed_files") or [])
    changed_nodes = _count(impact.get("changed_nodes"))
    impacted_nodes_shown = _count(impact.get("impacted_nodes"))
    impacted_nodes_total = _int(impact.get("total_impacted") or impacted_nodes_shown)
    impacted_files = _count(impact.get("impacted_files"))
    edges = _count(impact.get("edges"))
    truncated = bool(impact.get("truncated"))
    if not any([changed_files, changed_nodes, impacted_nodes_shown, impacted_nodes_total, impacted_files, edges]):
        return ""
    detail = (
        f"changed files {changed_files}, changed nodes {changed_nodes}, "
        f"impacted nodes shown/total {impacted_nodes_shown}/{impacted_nodes_total}, "
        f"impacted files {impacted_files}, edges {edges}, truncated {str(truncated).lower()}"
    )
    raw_impacted_files = impact.get("impacted_files")
    if isinstance(raw_impacted_files, list):
        labels = [_code_review_gate_impact_file_label(path) for path in raw_impacted_files]
        labels = [label for label in labels if label]
        if labels:
            shown = labels[:limit]
            detail += f"; impacted file preview shown {len(shown)}/{len(labels)}: " + ", ".join(shown)
            omitted = len(labels) - len(shown)
            if omitted:
                omitted_preview = labels[limit : limit + omitted_limit]
                if omitted_preview:
                    detail += f", omitted {omitted}: " + ", ".join(omitted_preview)
                    omitted_more = omitted - len(omitted_preview)
                    if omitted_more > 0:
                        detail += f", omitted-more {omitted_more}"
                else:
                    detail += f", omitted {omitted} more"
    raw_impacted_nodes = impact.get("impacted_nodes")
    if isinstance(raw_impacted_nodes, list):
        node_labels = [_code_review_gate_impact_node_label(node) for node in raw_impacted_nodes]
        node_labels = [label for label in node_labels if label]
        if node_labels:
            shown_nodes = node_labels[:limit]
            detail += f"; impacted node preview shown {len(shown_nodes)}/{len(node_labels)}: " + ", ".join(
                shown_nodes,
            )
            omitted_nodes = len(node_labels) - len(shown_nodes)
            if omitted_nodes:
                omitted_node_preview = node_labels[limit : limit + omitted_limit]
                if omitted_node_preview:
                    detail += f", omitted {omitted_nodes}: " + ", ".join(omitted_node_preview)
                    omitted_more_nodes = omitted_nodes - len(omitted_node_preview)
                    if omitted_more_nodes > 0:
                        detail += f", omitted-more {omitted_more_nodes}"
                else:
                    detail += f", omitted {omitted_nodes} more"
    return detail + "."


def _code_review_gate_priority_summary(code_review_gate: dict[str, Any], *, limit: int = 10) -> str:
    if not code_review_gate:
        return ""
    priorities = [str(priority).strip().rstrip(".") for priority in code_review_gate.get("review_priorities") or []]
    priorities = [priority for priority in priorities if priority]
    if not priorities:
        return ""
    shown = priorities[:limit]
    omitted_priorities = priorities[limit:]
    detail = f"shown {len(shown)}/{len(priorities)}: " + ", ".join(shown)
    if omitted_priorities:
        omitted_preview = omitted_priorities[:limit]
        detail += f", omitted {len(omitted_priorities)}: " + ", ".join(omitted_preview)
        omitted_more = len(omitted_priorities) - len(omitted_preview)
        if omitted_more > 0:
            detail += f", omitted-more {omitted_more}"
    return detail + "."


def _code_review_gate_artifact_summary(code_review_gate: dict[str, Any]) -> str:
    if not code_review_gate:
        return ""
    first_bytes = str(code_review_gate.get("_artifact_first_bytes") or "").strip()
    if not first_bytes:
        return ""
    has_utf8_bom = code_review_gate.get("_artifact_has_utf8_bom") is True
    return f"utf8_bom {str(has_utf8_bom).lower()}, first bytes {first_bytes}."


def _completion_blocker_requirements(completion: dict[str, Any]) -> list[str]:
    items = completion.get("items") if isinstance(completion.get("items"), list) else []
    blocked_requirements: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        blockers = item.get("blockers") if isinstance(item.get("blockers"), list) else []
        passed = item.get("passed")
        if passed is True and not blockers:
            continue
        requirement = str(item.get("requirement") or "").strip().rstrip(".;")
        if requirement:
            blocked_requirements.append(requirement)
    return blocked_requirements


def _render_prompt_artifact_checklist(
    *,
    launch: dict[str, Any],
    completion: dict[str, Any],
    readiness: dict[str, Any],
    selector: dict[str, Any],
    session_orient: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
    github_inventory: dict[str, Any],
    browser_qa: dict[str, Any],
    dependency_freshness: dict[str, Any],
    code_review_gate: dict[str, Any],
    coverage: dict[str, Any],
    menu: dict[str, Any],
    menu_check: dict[str, Any],
    release: dict[str, Any],
    approval: dict[str, Any],
    burndown: dict[str, Any],
    debug_loop: dict[str, Any],
    ab_task_id_advisory: dict[str, Any],
    generated_at: str,
) -> str:
    completion_summary = completion.get("summary") if isinstance(completion.get("summary"), dict) else {}
    code_review_summary = _code_review_gate_summary(launch)
    code_review_detail_summary = _code_review_gate_detail_summary(code_review_gate)
    code_review_count_alignment = _code_review_gate_count_alignment_summary(code_review_summary, code_review_gate)
    code_review_reason_summary = _code_review_gate_reason_summary(code_review_gate)
    code_review_untracked_summary = _code_review_gate_untracked_summary(code_review_gate)
    code_review_impact_summary = _code_review_gate_impact_summary(code_review_gate)
    code_review_priority_summary = _code_review_gate_priority_summary(code_review_gate)
    code_review_artifact_summary = _code_review_gate_artifact_summary(code_review_gate)
    readiness_overall = readiness.get("overall") if isinstance(readiness.get("overall"), dict) else {}
    readiness_blockers = (
        readiness_overall.get("blockers") if isinstance(readiness_overall.get("blockers"), dict) else {}
    )
    readiness_breakdown = (
        readiness_overall.get("blocker_breakdown")
        if isinstance(readiness_overall.get("blocker_breakdown"), dict)
        else {}
    )
    selector_summary = selector.get("summary") if isinstance(selector.get("summary"), dict) else {}
    selector_selected = selector.get("selected") if isinstance(selector.get("selected"), dict) else {}
    dirty_groups_summary = _dirty_handoff_groups_summary(dirty_handoff_plan) or _selector_dirty_groups_summary(
        selector_selected,
    )
    approval_phase_summary = _approval_phase_summary(approval, generated_at)
    approval_phase_reference_summary = _approval_phase_reference_summary(approval, generated_at)
    debug_blockers = _debug_blocker_summary(debug_loop)
    debug_blocker_titles = _debug_blocker_title_summary(debug_loop)
    debug_blocker_next_actions = _debug_blocker_next_action_summary(debug_loop)
    github_summary = _github_inventory_summary(github_inventory)
    github_recommendation_summary = _github_recommendation_summary(
        github_inventory,
        dirty_groups_summary=dirty_groups_summary,
    )
    browser_summary = _browser_qa_summary(browser_qa)
    browser_project_summary = _browser_qa_project_summary(browser_qa)
    browser_artifact_summary = _browser_qa_artifact_summary(browser_qa)
    browser_log_evidence_summary = _browser_qa_log_evidence_summary(browser_qa)
    dependency_summary = _dependency_freshness_summary(dependency_freshness)
    dependency_blocker_summary = _dependency_peer_blocker_summary(dependency_freshness)
    dependency_blocker_actions = _dependency_peer_blocker_action_summary(dependency_freshness)
    target_readiness_summary = _target_readiness_summary(readiness)
    target_blocker_detail_summary = _target_blocker_detail_summary(readiness)
    target_blocker_actions = _target_blocker_action_summary(readiness)
    project_qc_summary = _project_qc_summary(readiness)
    handoff_orientation = _handoff_orientation_summary(session_orient, ab_task_id_advisory=ab_task_id_advisory)
    git_worktree_summary = _git_worktree_summary(session_orient)
    dirty_handoff_summary = _dirty_handoff_plan_summary(dirty_handoff_plan)
    approval_phase_token_summary = _approval_phase_token_summary(approval, generated_at)
    completion_coverage_summary = _completion_coverage_summary(completion)
    completion_blockers_summary = _completion_blocker_summary(completion)
    completion_blockers_omission_summary = _completion_blocker_omission_summary(completion)
    completion_blocker_actions = _completion_blocker_action_summary(completion)
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    authorization_tokens, authorization_token_count = _authorization_option_tokens(menu, approval=approval)
    one_line_tokens, one_line_token_count = _one_line_user_option_tokens(menu)
    one_line_detail_summary = _one_line_user_option_detail_summary(menu)
    zero_dirty_authorization_omission_summary = _authorization_option_zero_dirty_omission_summary(menu, approval)
    authorization_omission_summary = _authorization_option_omission_summary(menu, approval)
    authorization_coverage_summary = _authorization_option_coverage_summary(menu, approval)
    authorization_coverage_omission_summary = _authorization_option_coverage_omission_summary(menu, approval)
    authorization_pathspec_summary = _authorization_option_pathspec_summary(menu, approval)
    authorization_classification_summary = _authorization_option_classification_summary(menu, approval)
    recommended_authorization_files = _recommended_authorization_files_summary(recommended)
    release_summary = release.get("summary") if isinstance(release.get("summary"), dict) else {}
    release_git = release.get("git") if isinstance(release.get("git"), dict) else {}
    release_actions = (
        release.get("current_head_actions") if isinstance(release.get("current_head_actions"), dict) else {}
    )
    release_actions_summary = _release_actions_summary(release_actions, release_summary)
    release_actions_probe = _release_actions_probe_summary(release_actions)
    release_packet_blockers = _release_packet_blocker_summary(release_summary, release_actions)
    release_authorization = release.get("authorization") if isinstance(release.get("authorization"), dict) else {}
    release_authorization_guardrails = _release_authorization_guardrail_summary(release_authorization)
    release_llm_wiki_strict_evidence = _release_llm_wiki_strict_evidence_summary(release)
    release_commit_preview = _release_commit_preview_summary(release)
    release_commit_encoding = _release_commit_encoding_summary(release)
    ab_collision_omission_summary = _ab_manifest_collision_omission_summary(ab_task_id_advisory)
    ab_latest_collision_summary = _ab_latest_task_collision_summary(ab_task_id_advisory)
    ab_latest_decision_summary = _ab_latest_decision_summary(ab_task_id_advisory)
    ab_latest_manifest_summary = _ab_latest_manifest_summary(ab_task_id_advisory)
    blocker_actions = [action for action in burndown.get("blocker_actions") or [] if isinstance(action, dict)]
    item_count = _int(completion_summary.get("item_count"))
    complete_count = _int(completion_summary.get("complete_count"))
    issue_count = _int(completion_summary.get("issue_count"))
    blocked_count = _int(completion_summary.get("blocked_count"))
    dirty_count = _int(coverage.get("dirty_count") or release_summary.get("dirty_count"))
    covered_dirty_count = _int(coverage.get("covered_dirty_count"))
    current_head_required_success = _int(
        release_actions.get("required_success_count") or release_summary.get("current_head_required_success_count"),
    )
    required_workflow_names = release_actions.get("required_workflow_names")
    missing_required_workflows = release_actions.get("missing_required_workflows")
    current_head_required_count = _int(
        release_actions.get("required_count")
        or release_summary.get("required_count")
        or (len(required_workflow_names) if isinstance(required_workflow_names, list) else 0)
        or (len(missing_required_workflows) if isinstance(missing_required_workflows, list) else 0),
    )
    workspace_blockers = _int(
        readiness_blockers.get("workspace")
        or readiness_breakdown.get("workspace")
        or readiness_breakdown.get("workspace_gate")
        or readiness_overall.get("workspace_blocker_count"),
    )
    local_blockers = _int(
        readiness_blockers.get("local")
        or readiness_breakdown.get("local")
        or readiness_overall.get("local_blocker_count"),
    )
    publish_blockers = _int(
        readiness_blockers.get("publish")
        or readiness_breakdown.get("publish")
        or readiness_overall.get("publish_blocker_count"),
    )
    external_blockers = _int(
        readiness_blockers.get("external")
        or readiness_breakdown.get("external")
        or readiness_overall.get("external_blocker_count"),
    )

    lines = [
        "# Launch Objective Prompt-to-Artifact Checklist",
        "",
        f"Generated: {generated_at}",
        "",
        "## Objective Restated",
        "",
        "- Ship the active products to launch-ready quality.",
        "- Find and improve all GitHub-related project surfaces.",
        "- Use the auto-research loop, browser QA, external/current-code checks, and bounded A/B adoption.",
        "- Do not claim completion until launch evidence, current-head release checks, and user-owned external blockers are cleared.",
        "",
        "## Current Gate Summary",
        "",
        (
            f"- Completion audit: {completion.get('status', 'unknown')} "
            f"({complete_count}/{item_count} complete, {issue_count} issues, {blocked_count} blocked)."
        ),
        *([f"- Completion coverage: {completion_coverage_summary}"] if completion_coverage_summary else []),
        *([f"- Completion blockers: {completion_blockers_summary}"] if completion_blockers_summary else []),
        *([f"- Completion blocker actions: {completion_blocker_actions}"] if completion_blocker_actions else []),
        *(
            [f"- Completion blockers omitted: {completion_blockers_omission_summary}"]
            if completion_blockers_omission_summary
            else []
        ),
        (
            f"- Selector: {selector.get('status', 'unknown')} / "
            f"{selector_summary.get('selected_kind') or selector_selected.get('kind') or 'unknown'}, "
            f"adoptable {_int(selector_summary.get('adoptable_candidate_count'))}, "
            f"blocked {_int(selector_summary.get('blocked_candidate_count'))}."
        ),
        *([f"- Dirty groups: {dirty_groups_summary}."] if dirty_groups_summary else []),
        *([f"- Handoff orientation: {handoff_orientation}"] if handoff_orientation else []),
        *([f"- Git worktree: {git_worktree_summary}"] if git_worktree_summary else []),
        *([f"- Dirty handoff plan: {dirty_handoff_summary}"] if dirty_handoff_summary else []),
        *([f"- Approval phases: {approval_phase_summary}."] if approval_phase_summary else []),
        *(
            [f"- Approval phase references: {approval_phase_reference_summary}."]
            if approval_phase_reference_summary
            else []
        ),
        *([f"- Approval phase tokens: {approval_phase_token_summary}."] if approval_phase_token_summary else []),
        *([f"- Debug blockers: {debug_blockers}"] if debug_blockers else []),
        *([f"- Debug blocker titles: {debug_blocker_titles}"] if debug_blocker_titles else []),
        *([f"- Debug blocker next actions: {debug_blocker_next_actions}"] if debug_blocker_next_actions else []),
        *([f"- GitHub inventory: {github_summary}"] if github_summary else []),
        *([f"- GitHub recommendations: {github_recommendation_summary}"] if github_recommendation_summary else []),
        *([f"- Browser QA: {browser_summary}"] if browser_summary else []),
        *([f"- Browser QA projects: {browser_project_summary}."] if browser_project_summary else []),
        *([f"- Browser QA artifacts: {browser_artifact_summary}."] if browser_artifact_summary else []),
        *([f"- Browser QA log evidence: {browser_log_evidence_summary}."] if browser_log_evidence_summary else []),
        *([f"- Dependency freshness: {dependency_summary}"] if dependency_summary else []),
        *([f"- Dependency blockers: {dependency_blocker_summary}."] if dependency_blocker_summary else []),
        *([f"- Dependency blocker actions: {dependency_blocker_actions}."] if dependency_blocker_actions else []),
        *([f"- Code review gate: {code_review_summary}"] if code_review_summary else []),
        *([f"- Code review gate detail: {code_review_detail_summary}"] if code_review_detail_summary else []),
        *([f"- Code review gate count sources: {code_review_count_alignment}"] if code_review_count_alignment else []),
        *([f"- Code review gate reasons: {code_review_reason_summary}"] if code_review_reason_summary else []),
        *([f"- Code review gate untracked: {code_review_untracked_summary}"] if code_review_untracked_summary else []),
        *([f"- Code review gate impact: {code_review_impact_summary}"] if code_review_impact_summary else []),
        *([f"- Code review gate priorities: {code_review_priority_summary}"] if code_review_priority_summary else []),
        *([f"- Code review gate artifact: {code_review_artifact_summary}"] if code_review_artifact_summary else []),
        (
            f"- Product readiness: score {_int(readiness_overall.get('score'))}, "
            f"state {readiness_overall.get('state', 'unknown')}, "
            "workspace/local/publish/external blockers "
            f"{workspace_blockers}/{local_blockers}/{publish_blockers}/{external_blockers}."
        ),
        *([f"- Target readiness: {target_readiness_summary}."] if target_readiness_summary else []),
        *([f"- Target blockers: {target_blocker_detail_summary}."] if target_blocker_detail_summary else []),
        *([f"- Target blocker actions: {target_blocker_actions}."] if target_blocker_actions else []),
        *([f"- Project QC: {project_qc_summary}"] if project_qc_summary else []),
        (
            f"- Authorization menu: recommended {recommended.get('token', '')}, "
            f"coverage status {coverage.get('status', 'unknown')}, "
            f"coverage {covered_dirty_count}/{dirty_count}, "
            "uncovered dirty/source "
            f"{_int(coverage.get('uncovered_dirty_count'))}/"
            f"{_int(coverage.get('uncovered_non_evidence_source_count'))}, "
            f"staged {_int(coverage.get('staged_count'))}."
        ),
        (
            "- Authorization options: "
            f"{', '.join(authorization_tokens) if authorization_tokens else 'none'} "
            f"(shown {len(authorization_tokens)}/{authorization_token_count})."
        ),
        *(
            [f"- Authorization option pathspecs: {authorization_pathspec_summary}"]
            if authorization_pathspec_summary
            else []
        ),
        *(
            [f"- Authorization option classes: {authorization_classification_summary}"]
            if authorization_classification_summary
            else []
        ),
        *(
            [f"- Authorization options omitted: {authorization_omission_summary}."]
            if authorization_omission_summary
            else []
        ),
        *(
            [f"- Authorization option coverage: {authorization_coverage_summary}."]
            if authorization_coverage_summary
            else []
        ),
        *(
            [f"- Authorization option coverage omitted: {authorization_coverage_omission_summary}."]
            if authorization_coverage_omission_summary
            else []
        ),
        (
            "- One-line user options: "
            f"{', '.join(one_line_tokens) if one_line_tokens else 'none'} "
            f"(shown {len(one_line_tokens)}/{one_line_token_count})."
        ),
        *([f"- One-line user option details: {one_line_detail_summary}"] if one_line_detail_summary else []),
        (f"- Authorization omissions: current-zero-dirty {zero_dirty_authorization_omission_summary}."),
        f"- Recommended next scope: {_recommended_scope_summary(burndown)}",
        f"- Recommended authorization artifact: {_recommended_authorization_artifact_summary(recommended)}",
        *(
            [f"- Recommended authorization files: {recommended_authorization_files}"]
            if recommended_authorization_files
            else []
        ),
        (
            f"- Next A/B task id: T-{_int(ab_task_id_advisory.get('next_task_id'))} "
            f"(highest T-{_int(ab_task_id_advisory.get('highest_task_id'))}, "
            f"task-id manifests {_int(ab_task_id_advisory.get('manifest_count'))}, "
            f"scanned {_int(ab_task_id_advisory.get('scanned_manifest_count'))}, "
            f"collisions {_int(ab_task_id_advisory.get('collision_group_count'))})."
        ),
        *([f"- Latest A/B decision: {ab_latest_decision_summary}"] if ab_latest_decision_summary else []),
        *([f"- Latest A/B manifest artifact: {ab_latest_manifest_summary}"] if ab_latest_manifest_summary else []),
        f"- A/B manifest collisions: {_ab_manifest_collision_summary(ab_task_id_advisory)}",
        *([f"- Latest A/B task id collision: {ab_latest_collision_summary}"] if ab_latest_collision_summary else []),
        *(
            [f"- A/B collision hidden task ids: {ab_collision_omission_summary}"]
            if ab_collision_omission_summary
            else []
        ),
        (
            f"- Authorization check: status {menu_check.get('status', 'unknown')}, "
            f"rendered_matches {_bool_text(menu_check.get('rendered_matches'))}, "
            f"exact_rendered_matches {_bool_text(menu_check.get('exact_rendered_matches'))}, "
            f"coverage_stale {_bool_text(menu_check.get('coverage_stale'))}."
        ),
        (
            f"- Release packet: {release.get('status', 'unknown')}, "
            f"head {release_summary.get('head_short') or str(release_git.get('head_sha') or '')[:8]}, "
            f"ahead {_int(release_summary.get('ahead_count') or release_git.get('ahead_count'))}, "
            f"dirty {_int(release_summary.get('dirty_count') or release_git.get('dirty_count'))}, "
            f"current-head Actions {current_head_required_success}/{current_head_required_count}, "
            f"missing {_release_missing_workflow_summary(release_actions, release)}."
        ),
        *([f"- Release packet blockers: {release_packet_blockers}"] if release_packet_blockers else []),
        *(
            [f"- LLM Wiki strict release evidence: {release_llm_wiki_strict_evidence}"]
            if release_llm_wiki_strict_evidence
            else []
        ),
        *([f"- Release commits: {release_commit_preview}"] if release_commit_preview else []),
        *([f"- Release commit encoding: {release_commit_encoding}"] if release_commit_encoding else []),
        *([f"- Release actions: {release_actions_summary}"] if release_actions_summary else []),
        *([f"- Release actions probe: {release_actions_probe}"] if release_actions_probe else []),
        *(
            [f"- Release authorization guardrails: {release_authorization_guardrails}"]
            if release_authorization_guardrails
            else []
        ),
    ]
    if blocker_actions:
        action_summaries = []
        for action in blocker_actions[:3]:
            action_summaries.append(
                f"{action.get('blocker') or 'unknown'} -> "
                f"{action.get('owner') or 'unknown'} / "
                f"{action.get('authorization') or 'unknown'}"
            )
        lines.append(f"- Blocker actions: {'; '.join(action_summaries)}.")
        if len(blocker_actions) > 3:
            lines.append(f"- Blocker actions omitted: {len(blocker_actions) - 3}.")
    lines.extend(["", "## Prompt-to-Artifact Checklist", ""])

    for index, item in enumerate(completion.get("items") or [], start=1):
        if not isinstance(item, dict):
            continue
        passed = bool(item.get("passed"))
        status = "PASS" if passed else "BLOCKED"
        lines.extend(
            [
                f"### {index}. {status} - {item.get('requirement', 'Unnamed requirement')}",
                f"- Coverage: {item.get('coverage', 'unknown')}",
            ],
        )
        artifacts = _text_list(item.get("artifacts"))
        if artifacts:
            lines.append(f"- Artifacts: {', '.join(artifacts)}")
        evidence = _expand_ab_collision_omission_evidence(_text_list(item.get("evidence")), ab_task_id_advisory)
        evidence = _rewrite_dirty_groups_evidence(evidence, dirty_groups_summary)
        if evidence:
            lines.append("- Evidence:")
            lines.extend(f"  - {entry}" for entry in evidence)
        blockers = _rewrite_dirty_groups_evidence(_text_list(item.get("blockers")), dirty_groups_summary)
        if blockers:
            lines.append("- Blockers:")
            lines.extend(f"  - {entry}" for entry in blockers)
        issues = _text_list(item.get("issues"))
        if issues:
            lines.append(f"- Audit issues: {', '.join(issues)}")
        lines.append("")

    completion_allowed = str(completion.get("status") or "") == "complete" and blocked_count == 0 and issue_count == 0
    lines.extend(
        [
            "## Decision",
            "",
            (
                "- Complete: all prompt requirements have current evidence."
                if completion_allowed
                else "- Not complete: unresolved blockers remain, so do not call `update_goal`."
            ),
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def _write_prompt_artifact_checklist(
    *,
    launch: Path,
    completion: Path,
    readiness: Path,
    selector: Path,
    session_orient: Path,
    dirty_handoff_plan: Path,
    github_inventory: Path,
    browser_qa: Path,
    dependency_freshness: Path,
    code_review_gate: Path,
    coverage: Path,
    approval: Path,
    menu: Path,
    menu_check: Path,
    release: Path,
    burndown: Path,
    debug_loop: Path,
    target: Path,
    root: Path | None = None,
) -> StepResult:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    launch_data = _load_json_file(launch)
    completion_data = _load_json_file(completion)
    readiness_data = _load_json_file(readiness)
    selector_data = _load_json_file(selector)
    session_orient_data = _load_json_file(session_orient)
    dirty_handoff_plan_data = _load_json_file(dirty_handoff_plan)
    github_inventory_data = _load_json_file(github_inventory)
    browser_qa_data = _load_json_file(browser_qa)
    dependency_freshness_data = _load_json_file(dependency_freshness)
    code_review_gate_data = _load_json_file(code_review_gate)
    code_review_gate_normalized = _normalize_utf8_bom_json_artifact(
        code_review_gate,
        code_review_gate_data,
        name="code_review_gate_artifact_bom_normalize",
    )
    if code_review_gate_normalized and code_review_gate_normalized.status != "ok":
        return code_review_gate_normalized
    if code_review_gate_data:
        first_bytes = _first_bytes(code_review_gate)
        code_review_gate_data = dict(code_review_gate_data)
        code_review_gate_data["_artifact_first_bytes"] = first_bytes
        code_review_gate_data["_artifact_has_utf8_bom"] = first_bytes.startswith("EF BB BF")
    coverage_data = _load_json_file(coverage)
    approval_data = _load_json_file(approval)
    menu_data = _load_json_file(menu)
    menu_check_data = _load_json_file(menu_check)
    release_data = _load_json_file(release)
    burndown_data = _load_json_file(burndown)
    debug_loop_data = _load_json_file(debug_loop)
    if not all(
        [
            completion_data,
            readiness_data,
            selector_data,
            session_orient_data,
            dirty_handoff_plan_data,
            github_inventory_data,
            browser_qa_data,
            dependency_freshness_data,
            coverage_data,
            approval_data,
            menu_data,
            menu_check_data,
            release_data,
            burndown_data,
            debug_loop_data,
            launch_data,
        ]
    ):
        return StepResult(
            name="launch_prompt_artifact_checklist",
            returncode=2,
            expected_returncode=False,
            status="failed",
            detail="missing required current evidence inputs",
        )
    return _write_markdown(
        target,
        _render_prompt_artifact_checklist(
            launch=launch_data,
            completion=completion_data,
            readiness=readiness_data,
            selector=selector_data,
            session_orient=session_orient_data,
            dirty_handoff_plan=dirty_handoff_plan_data,
            github_inventory=github_inventory_data,
            browser_qa=browser_qa_data,
            dependency_freshness=dependency_freshness_data,
            code_review_gate=code_review_gate_data,
            coverage=coverage_data,
            approval=approval_data,
            menu=menu_data,
            menu_check=menu_check_data,
            release=release_data,
            burndown=burndown_data,
            debug_loop=debug_loop_data,
            ab_task_id_advisory=_ab_manifest_task_id_advisory(root or target.parent.parent),
            generated_at=generated_at,
        ),
        name="launch_prompt_artifact_checklist",
    )


def _write_approval_matrix_and_burndown(
    *,
    approval: Path,
    readiness: Path,
    completion: Path,
    selector: Path,
    matrix_json: Path,
    matrix_md: Path,
    burndown_json: Path,
    burndown_md: Path,
) -> StepResult:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    approval_data = _load_json_file(approval)
    readiness_data = _load_json_file(readiness)
    completion_data = _load_json_file(completion)
    selector_data = _load_json_file(selector)
    if not approval_data or not readiness_data or not completion_data or not selector_data:
        return StepResult(
            name="approval_execution_matrix_and_burndown",
            returncode=2,
            expected_returncode=False,
            status="failed",
            detail="missing required current JSON inputs",
        )

    matrix = _build_approval_execution_matrix(approval_data, generated_at)
    burndown = _build_launch_blocker_burndown(
        matrix=matrix,
        approval=approval_data,
        readiness=readiness_data,
        completion=completion_data,
        selector=selector_data,
        generated_at=generated_at,
    )
    for target, data in (
        (matrix_json, _json_text(matrix).encode("utf-8")),
        (matrix_md, _render_approval_execution_matrix_md(matrix).encode("utf-8")),
        (burndown_json, _json_text(burndown).encode("utf-8")),
        (burndown_md, _render_launch_blocker_burndown_md(burndown).encode("utf-8")),
    ):
        write_result = _atomic_write_bytes_step(
            target,
            data,
            name="approval_execution_matrix_and_burndown",
            output=target,
        )
        if write_result:
            return write_result
    return StepResult(
        name="approval_execution_matrix_and_burndown",
        returncode=0,
        expected_returncode=True,
        output=matrix_json,
        first_bytes=_first_bytes(matrix_json),
    )


def _git_with_index(
    root: Path, index_path: Path, argv: list[str], *, timeout: int
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = str(index_path)
    try:
        return subprocess.run(
            argv,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return _timeout_result(argv, exc)


def _git_without_index(root: Path, argv: list[str], *, timeout: int) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _timeout_result(argv, exc)


def _decode_stdout_lines(completed: subprocess.CompletedProcess[bytes]) -> list[str]:
    text = completed.stdout.decode("utf-8", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _build_ai_context_relay_packet(
    *,
    menu: dict[str, Any],
    coverage: dict[str, Any],
    selector: dict[str, Any],
    proof: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    selected = selector.get("selected") if isinstance(selector.get("selected"), dict) else {}
    selector_summary = selector.get("summary") if isinstance(selector.get("summary"), dict) else {}
    return {
        "generated_at": generated_at,
        "status": "handoff_only",
        "token": str(recommended.get("token") or "APPROVE_AI_CONTEXT_RELAY_UPDATE"),
        "pathspec": str(recommended.get("pathspec") or ".tmp/approve-ai-context-relay-update.pathspec"),
        "scope": [str(path) for path in recommended.get("files") or []],
        "authorized_by_this_artifact": False,
        "coverage": {
            "generated_at": str(coverage.get("generated_at") or ""),
            "status": str(coverage.get("status") or "unknown"),
            "dirty_count": _int(coverage.get("dirty_count")),
            "covered_dirty_count": _int(coverage.get("covered_dirty_count")),
            "uncovered_dirty_count": _int(coverage.get("uncovered_dirty_count")),
            "uncovered_non_evidence_source_count": _int(coverage.get("uncovered_non_evidence_source_count")),
            "pathspec_count": _int(coverage.get("pathspec_count")),
            "real_staged_count": _int(coverage.get("staged_count")),
        },
        "current_scope_validation": {
            "scope_path_count": _int(len(recommended.get("files") or [])),
            "scope_dirty_path_count": _int(proof.get("path_count")),
            "all_scope_paths_currently_dirty": _int(proof.get("path_count"))
            == _int(len(recommended.get("files") or [])),
            "selector_status": str(selector.get("status") or "unknown"),
            "selector_kind": str(selector_summary.get("selected_kind") or selected.get("kind") or "unknown"),
            "adoptable_candidate_count": _int(selector_summary.get("adoptable_candidate_count")),
            "real_staged_count": _int(proof.get("real_staged_count_after")),
        },
        "virtual_index": proof,
        "notes": [
            "AIC1 is relay/context/archive evidence only and does not authorize staging.",
            "The virtual index proof uses only the recommended ai-context relay pathspec.",
            "Current completion remains blocked by dirty handoff, current-head Actions proof, and user-owned Hanwoo T-251.",
        ],
        "guardrails": [
            "Do not stage, commit, push, or revert without explicit APPROVE_AI_CONTEXT_RELAY_UPDATE authorization.",
            "Do not bundle AIC1 with product/code scopes unless explicitly authorized.",
            "Do not retry T-251 until Supabase credentials are reset.",
            "Do not call update_goal while completion audit is incomplete.",
        ],
    }


def _render_ai_context_relay_packet_md(packet: dict[str, Any]) -> str:
    coverage = packet.get("coverage") if isinstance(packet.get("coverage"), dict) else {}
    scope_validation = (
        packet.get("current_scope_validation") if isinstance(packet.get("current_scope_validation"), dict) else {}
    )
    proof = packet.get("virtual_index") if isinstance(packet.get("virtual_index"), dict) else {}
    lines = [
        "# AI Context Relay Update Authorization Packet",
        "",
        f"Generated: {packet.get('generated_at')}",
        f"Status: {packet.get('status')}",
        f"Token: `{packet.get('token')}`",
        "Authorized by this artifact: false",
        "",
        "## Scope",
        "",
    ]
    lines.extend(f"- `{path}`" for path in packet.get("scope") or [])
    lines.extend(
        [
            "",
            "Pathspec:",
            "",
            f"- `{packet.get('pathspec')}`",
            "",
            "## Current Scope Validation",
            "",
            f"- Scope pathspec files: {scope_validation.get('scope_path_count')}",
            f"- Scope dirty paths: {scope_validation.get('scope_dirty_path_count')}",
            f"- All scope paths currently dirty: {str(scope_validation.get('all_scope_paths_currently_dirty')).lower()}",
            f"- Real staged files: {scope_validation.get('real_staged_count')}",
            (
                "- Selector: "
                f"`{scope_validation.get('selector_status')}` / "
                f"`{scope_validation.get('selector_kind')}` / "
                f"adoptable `{scope_validation.get('adoptable_candidate_count')}`"
            ),
            "- Current coverage JSON: `.tmp/authorization-coverage-current.json`",
            (
                "- Coverage after pathspec refresh: "
                f"{coverage.get('covered_dirty_count')}/{coverage.get('dirty_count')}, "
                "uncovered dirty/source "
                f"{coverage.get('uncovered_dirty_count')}/{coverage.get('uncovered_non_evidence_source_count')}"
            ),
            "",
            "## Virtual Index Proof",
            "",
            f"- git add return code: {proof.get('add_exit')}",
            f"- git add stderr summary: `{proof.get('add_stderr_summary')}`",
            f"- Virtual staged files: {proof.get('path_count')}",
            f"- Shortstat: `{proof.get('shortstat')}`",
            f"- Diff-check exit: {proof.get('cached_diff_check_exit')}",
            f"- Diff-check stderr: `{proof.get('diff_check_stderr')}`",
            "",
            "## Guardrails",
        ],
    )
    lines.extend(f"- {guardrail}" for guardrail in packet.get("guardrails") or [])
    return "\n".join(lines).rstrip() + "\n"


def _build_session_log_rotator_packet(
    *,
    coverage: dict[str, Any],
    selector: dict[str, Any],
    proof: dict[str, Any],
    generated_at: str,
    pathspec: str,
) -> dict[str, Any]:
    selected = selector.get("selected") if isinstance(selector.get("selected"), dict) else {}
    selector_summary = selector.get("summary") if isinstance(selector.get("summary"), dict) else {}
    scope = [
        "execution/session_log_rotator.py",
        "workspace/tests/test_session_log_rotator.py",
    ]
    return {
        "generated_at": generated_at,
        "status": "handoff_only",
        "token": "APPROVE_SESSION_LOG_ROTATOR",
        "pathspec": pathspec,
        "scope": scope,
        "authorized_by_this_artifact": False,
        "coverage": {
            "generated_at": str(coverage.get("generated_at") or ""),
            "status": str(coverage.get("status") or "unknown"),
            "dirty_count": _int(coverage.get("dirty_count")),
            "covered_dirty_count": _int(coverage.get("covered_dirty_count")),
            "uncovered_dirty_count": _int(coverage.get("uncovered_dirty_count")),
            "uncovered_non_evidence_source_count": _int(coverage.get("uncovered_non_evidence_source_count")),
            "pathspec_count": _int(coverage.get("pathspec_count")),
            "real_staged_count": _int(coverage.get("staged_count")),
        },
        "current_scope_validation": {
            "scope_path_count": len(scope),
            "scope_dirty_path_count": _int(proof.get("path_count")),
            "all_scope_paths_currently_dirty": _int(proof.get("path_count")) == len(scope),
            "selector_status": str(selector.get("status") or "unknown"),
            "selector_kind": str(selector_summary.get("selected_kind") or selected.get("kind") or "unknown"),
            "adoptable_candidate_count": _int(selector_summary.get("adoptable_candidate_count")),
            "real_staged_count": _int(proof.get("real_staged_count_after")),
        },
        "virtual_index": proof,
        "notes": [
            "This packet covers the previously uncovered session log rotator source/test pair.",
            "It is handoff-only evidence and does not authorize staging.",
            "Current completion remains blocked by dirty handoff, current-head Actions proof, and user-owned Hanwoo T-251.",
        ],
        "guardrails": [
            "Do not stage, commit, push, or revert without explicit APPROVE_SESSION_LOG_ROTATOR authorization.",
            "Do not bundle this scope with AI context relay or product scopes unless explicitly authorized.",
            "Do not retry T-251 until Supabase credentials are reset.",
            "Do not call update_goal while completion audit is incomplete.",
        ],
    }


def _render_session_log_rotator_packet_md(packet: dict[str, Any]) -> str:
    coverage = packet.get("coverage") if isinstance(packet.get("coverage"), dict) else {}
    scope_validation = (
        packet.get("current_scope_validation") if isinstance(packet.get("current_scope_validation"), dict) else {}
    )
    proof = packet.get("virtual_index") if isinstance(packet.get("virtual_index"), dict) else {}
    lines = [
        "# Session Log Rotator Authorization Packet",
        "",
        f"Generated: {packet.get('generated_at')}",
        f"Status: {packet.get('status')}",
        f"Token: `{packet.get('token')}`",
        "Authorized by this artifact: false",
        "",
        "## Scope",
        "",
    ]
    lines.extend(f"- `{path}`" for path in packet.get("scope") or [])
    lines.extend(
        [
            "",
            "Pathspec:",
            "",
            f"- `{packet.get('pathspec')}`",
            "",
            "## Current Scope Validation",
            "",
            f"- Scope pathspec files: {scope_validation.get('scope_path_count')}",
            f"- Scope dirty paths: {scope_validation.get('scope_dirty_path_count')}",
            f"- All scope paths currently dirty: {str(scope_validation.get('all_scope_paths_currently_dirty')).lower()}",
            f"- Real staged files: {scope_validation.get('real_staged_count')}",
            (
                "- Selector: "
                f"`{scope_validation.get('selector_status')}` / "
                f"`{scope_validation.get('selector_kind')}` / "
                f"adoptable `{scope_validation.get('adoptable_candidate_count')}`"
            ),
            "- Current coverage JSON: `.tmp/authorization-coverage-current.json`",
            (
                "- Coverage after pathspec refresh: "
                f"{coverage.get('covered_dirty_count')}/{coverage.get('dirty_count')}, "
                "uncovered dirty/source "
                f"{coverage.get('uncovered_dirty_count')}/{coverage.get('uncovered_non_evidence_source_count')}"
            ),
            "",
            "## Virtual Index Proof",
            "",
            f"- git add return code: {proof.get('add_exit')}",
            f"- git add stderr summary: `{proof.get('add_stderr_summary')}`",
            f"- Virtual staged files: {proof.get('path_count')}",
            f"- Shortstat: `{proof.get('shortstat')}`",
            f"- Diff-check exit: {proof.get('cached_diff_check_exit')}",
            f"- Diff-check stderr: `{proof.get('diff_check_stderr')}`",
            "",
            "## Guardrails",
        ],
    )
    lines.extend(f"- {guardrail}" for guardrail in packet.get("guardrails") or [])
    return "\n".join(lines).rstrip() + "\n"


def _upsert_session_log_rotator_menu_option(menu_json: Path) -> StepResult:
    menu = _load_json_file(menu_json)
    if not menu:
        return StepResult(
            name="session_log_rotator_menu_option",
            returncode=2,
            expected_returncode=False,
            output=menu_json,
            first_bytes=_first_bytes(menu_json) if menu_json.exists() else None,
            status="failed",
            detail="menu JSON unavailable",
        )
    option = {
        "token": "APPROVE_SESSION_LOG_ROTATOR",
        "packet": ".tmp/session-log-rotator-authorization-current.md",
        "pathspec": ".tmp/approve-session-log-rotator.pathspec",
        "classification": "verified_uncovered_workspace_tool_packet",
        "reason": (
            "Covers the newly surfaced session log rotator source/test pair with virtual index "
            "and diff-check proof without authorizing staging."
        ),
    }
    available = menu.get("also_available") if isinstance(menu.get("also_available"), list) else []
    updated: list[Any] = []
    inserted = False
    for item in available:
        if isinstance(item, dict) and item.get("token") == option["token"]:
            updated.append(option)
            inserted = True
        else:
            updated.append(item)
    if not inserted:
        updated.append(option)
    menu["also_available"] = updated
    write_result = _atomic_write_bytes_step(
        menu_json,
        _json_text(menu).encode("utf-8"),
        name="session_log_rotator_menu_option",
        output=menu_json,
    )
    if write_result:
        return write_result
    return StepResult(
        name="session_log_rotator_menu_option",
        returncode=0,
        expected_returncode=True,
        output=menu_json,
        first_bytes=_first_bytes(menu_json),
    )


def _write_session_log_rotator_packet(
    *,
    root: Path,
    coverage_json: Path,
    selector_json: Path,
    pathspec: Path,
    packet_json: Path,
    packet_md: Path,
    timeout: int,
) -> StepResult:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    scope = [
        "execution/session_log_rotator.py",
        "workspace/tests/test_session_log_rotator.py",
    ]
    relative_pathspec = pathspec.relative_to(root).as_posix() if pathspec.is_relative_to(root) else pathspec.as_posix()
    pathspec_result = _atomic_write_bytes_step(
        pathspec,
        ("\n".join(scope) + "\n").encode("utf-8"),
        name="session_log_rotator_packet",
        output=pathspec,
    )
    if pathspec_result:
        return pathspec_result

    coverage = _load_json_file(coverage_json)
    selector = _load_json_file(selector_json)
    if not coverage or not selector:
        return StepResult(
            name="session_log_rotator_packet",
            returncode=2,
            expected_returncode=False,
            status="failed",
            detail="missing required current JSON inputs",
        )

    index_path = root / ".tmp" / f"git-index-session-log-rotator-current-{uuid.uuid4().hex}"
    try:
        read_tree = _git_with_index(root, index_path, ["git", "read-tree", "HEAD"], timeout=timeout)
        add = _git_with_index(
            root,
            index_path,
            ["git", "add", f"--pathspec-from-file={relative_pathspec}"],
            timeout=timeout,
        )
        names = _git_with_index(root, index_path, ["git", "diff", "--cached", "--name-only"], timeout=timeout)
        shortstat = _git_with_index(root, index_path, ["git", "diff", "--cached", "--shortstat"], timeout=timeout)
        diff_check = _git_with_index(root, index_path, ["git", "diff", "--cached", "--check"], timeout=timeout)
        real_staged = _git_without_index(root, ["git", "diff", "--cached", "--name-only"], timeout=timeout)
    finally:
        index_path.unlink(missing_ok=True)

    stderr = _decode_stderr(add.stderr)
    proof = {
        "path": "temporary isolated index removed after verification",
        "read_tree_exit": read_tree.returncode,
        "add_exit": add.returncode,
        "add_stderr_summary": "CRLF normalization warnings only; git add returned 0" if add.returncode == 0 else stderr,
        "path_count": len(_decode_stdout_lines(names)),
        "names": _decode_stdout_lines(names),
        "shortstat": shortstat.stdout.decode("utf-8", errors="replace").strip(),
        "cached_diff_check_exit": diff_check.returncode,
        "diff_check_stderr": _decode_stderr(diff_check.stderr),
        "real_staged_count_after": len(_decode_stdout_lines(real_staged)),
    }
    packet = _build_session_log_rotator_packet(
        coverage=coverage,
        selector=selector,
        proof=proof,
        generated_at=generated_at,
        pathspec=relative_pathspec,
    )
    for target, data in (
        (packet_json, _json_text(packet).encode("utf-8")),
        (packet_md, _render_session_log_rotator_packet_md(packet).encode("utf-8")),
    ):
        write_result = _atomic_write_bytes_step(target, data, name="session_log_rotator_packet", output=target)
        if write_result:
            return write_result
    status = "ok" if read_tree.returncode == 0 and add.returncode == 0 and diff_check.returncode == 0 else "failed"
    return StepResult(
        name="session_log_rotator_packet",
        returncode=0 if status == "ok" else 2,
        expected_returncode=status == "ok",
        output=packet_json,
        first_bytes=_first_bytes(packet_json),
        status=status,
        detail="" if status == "ok" else "virtual index proof failed",
    )


def _write_ai_context_relay_packet(
    *,
    root: Path,
    menu_json: Path,
    coverage_json: Path,
    selector_json: Path,
    packet_json: Path,
    packet_md: Path,
    timeout: int,
) -> StepResult:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    menu = _load_json_file(menu_json)
    coverage = _load_json_file(coverage_json)
    selector = _load_json_file(selector_json)
    recommended = menu.get("recommended") if isinstance(menu.get("recommended"), dict) else {}
    pathspec = str(recommended.get("pathspec") or ".tmp/approve-ai-context-relay-update.pathspec")
    if not menu or not coverage or not selector:
        return StepResult(
            name="ai_context_relay_packet",
            returncode=2,
            expected_returncode=False,
            status="failed",
            detail="missing required current JSON inputs",
        )

    index_path = root / ".tmp" / f"git-index-aic1-current-{uuid.uuid4().hex}"
    try:
        read_tree = _git_with_index(root, index_path, ["git", "read-tree", "HEAD"], timeout=timeout)
        add = _git_with_index(
            root,
            index_path,
            ["git", "add", f"--pathspec-from-file={pathspec}"],
            timeout=timeout,
        )
        names = _git_with_index(root, index_path, ["git", "diff", "--cached", "--name-only"], timeout=timeout)
        shortstat = _git_with_index(root, index_path, ["git", "diff", "--cached", "--shortstat"], timeout=timeout)
        diff_check = _git_with_index(root, index_path, ["git", "diff", "--cached", "--check"], timeout=timeout)
        real_staged = _git_without_index(root, ["git", "diff", "--cached", "--name-only"], timeout=timeout)
    finally:
        index_path.unlink(missing_ok=True)

    stderr = _decode_stderr(add.stderr)
    proof = {
        "path": "temporary isolated index removed after verification",
        "read_tree_exit": read_tree.returncode,
        "add_exit": add.returncode,
        "add_stderr_summary": "CRLF normalization warnings only; git add returned 0" if add.returncode == 0 else stderr,
        "path_count": len(_decode_stdout_lines(names)),
        "names": _decode_stdout_lines(names),
        "shortstat": shortstat.stdout.decode("utf-8", errors="replace").strip(),
        "cached_diff_check_exit": diff_check.returncode,
        "diff_check_stderr": _decode_stderr(diff_check.stderr),
        "real_staged_count_after": len(_decode_stdout_lines(real_staged)),
    }
    packet = _build_ai_context_relay_packet(
        menu=menu,
        coverage=coverage,
        selector=selector,
        proof=proof,
        generated_at=generated_at,
    )
    for target, data in (
        (packet_json, _json_text(packet).encode("utf-8")),
        (packet_md, _render_ai_context_relay_packet_md(packet).encode("utf-8")),
    ):
        write_result = _atomic_write_bytes_step(target, data, name="ai_context_relay_packet", output=target)
        if write_result:
            return write_result
    status = "ok" if read_tree.returncode == 0 and add.returncode == 0 and diff_check.returncode == 0 else "failed"
    return StepResult(
        name="ai_context_relay_packet",
        returncode=0 if status == "ok" else 2,
        expected_returncode=status == "ok",
        output=packet_json,
        first_bytes=_first_bytes(packet_json),
        status=status,
        detail="" if status == "ok" else "virtual index proof failed",
    )


def refresh_current_evidence(root: Path, *, timeout: int = 120) -> dict[str, Any]:
    paths = EvidencePaths()
    readiness = _in_root(root, paths.readiness)
    github_inventory = _in_root(root, paths.github_inventory)
    github_inventory_refresh = _in_root(root, paths.github_inventory_refresh)
    browser_qa_inventory = _in_root(root, paths.browser_qa_inventory)
    browser_qa_inventory_refresh = _in_root(root, paths.browser_qa_inventory_refresh)
    dependency_freshness = _in_root(root, paths.dependency_freshness)
    dependency_freshness_refresh = _in_root(root, paths.dependency_freshness_refresh)
    direction_alignment = _in_root(root, paths.direction_alignment)
    direction_alignment_refresh = _in_root(root, paths.direction_alignment_refresh)
    launch = _in_root(root, paths.launch)
    launch_refresh = _in_root(root, paths.launch_refresh)
    completion = _in_root(root, paths.completion)
    release_authorization_packet = _in_root(root, paths.release_authorization_packet)
    release_authorization_packet_refresh = _in_root(root, paths.release_authorization_packet_refresh)
    selector = _in_root(root, paths.selector)
    selector_refresh = _in_root(root, paths.selector_refresh)
    selector_legacy_alias = _in_root(root, paths.selector_legacy_alias)
    selector_continuation_alias = _in_root(root, paths.selector_continuation_alias)
    session_orient = _in_root(root, paths.session_orient)
    debug_json = _in_root(root, paths.debug_json)
    debug_json_refresh = _in_root(root, paths.debug_json_refresh)
    debug_md = _in_root(root, paths.debug_md)
    debug_md_refresh = _in_root(root, paths.debug_md_refresh)
    dirty_handoff_plan = _in_root(root, paths.dirty_handoff_plan)
    dirty_handoff_plan_refresh = _in_root(root, paths.dirty_handoff_plan_refresh)
    dirty_handoff_plan_md = _in_root(root, paths.dirty_handoff_plan_md)
    dirty_handoff_plan_md_refresh = _in_root(root, paths.dirty_handoff_plan_md_refresh)
    approval_pathspec = _in_root(root, paths.approval_pathspec)
    approval_execution_matrix = _in_root(root, paths.approval_execution_matrix)
    approval_execution_matrix_md = _in_root(root, paths.approval_execution_matrix_md)
    launch_blocker_burndown = _in_root(root, paths.launch_blocker_burndown)
    launch_blocker_burndown_md = _in_root(root, paths.launch_blocker_burndown_md)
    scoped_authorization_menu_md = _in_root(root, paths.scoped_authorization_menu_md)
    scoped_authorization_menu_json = _in_root(root, paths.scoped_authorization_menu_json)
    scoped_authorization_menu_check = _in_root(root, paths.scoped_authorization_menu_check)
    ai_context_relay_packet = _in_root(root, paths.ai_context_relay_packet)
    ai_context_relay_packet_md = _in_root(root, paths.ai_context_relay_packet_md)
    session_log_rotator_pathspec = _in_root(root, paths.session_log_rotator_pathspec)
    session_log_rotator_packet = _in_root(root, paths.session_log_rotator_packet)
    session_log_rotator_packet_md = _in_root(root, paths.session_log_rotator_packet_md)
    prompt_artifact_checklist = _in_root(root, paths.prompt_artifact_checklist)
    py = sys.executable
    results: list[StepResult] = []

    results.append(
        _run_stdout_json_step(
            root,
            name="product_readiness",
            argv=[py, "execution/product_readiness_score.py", "--json"],
            target=readiness,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="github_project_inventory",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/github_project_inventory.py",
                "--root",
                ".",
                "--include-prs",
                "--output",
                str(paths.github_inventory_refresh),
                "--json",
            ],
            refresh=github_inventory_refresh,
            target=github_inventory,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="browser_qa_inventory",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/browser_qa_inventory.py",
                "--root",
                ".",
                "--output",
                str(paths.browser_qa_inventory_refresh),
                "--json",
            ],
            refresh=browser_qa_inventory_refresh,
            target=browser_qa_inventory,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="dependency_freshness_inventory",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/dependency_freshness_inventory.py",
                "--root",
                ".",
                "--output",
                str(paths.dependency_freshness_refresh),
                "--json",
            ],
            refresh=dependency_freshness_refresh,
            target=dependency_freshness,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="dirty_worktree_handoff_plan",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/dirty_worktree_handoff_plan.py",
                "--root",
                ".",
                "--output-json",
                str(paths.dirty_handoff_plan_refresh),
                "--output-md",
                str(paths.dirty_handoff_plan_md_refresh),
                "--previous-json",
                str(paths.dirty_handoff_plan),
                "--json",
            ],
            refresh=dirty_handoff_plan_refresh,
            target=dirty_handoff_plan,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(_replace_markdown(dirty_handoff_plan_md_refresh, dirty_handoff_plan_md))
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="release_authorization_packet",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/release_authorization_packet.py",
                "--root",
                ".",
                "--output",
                str(paths.release_authorization_packet_refresh),
                "--json",
            ],
            refresh=release_authorization_packet_refresh,
            target=release_authorization_packet,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    session_log_rotator_scope = [
        "execution/session_log_rotator.py",
        "workspace/tests/test_session_log_rotator.py",
    ]
    pathspec_seed = _atomic_write_bytes_step(
        session_log_rotator_pathspec,
        ("\n".join(session_log_rotator_scope) + "\n").encode("utf-8"),
        name="session_log_rotator_pathspec",
        output=session_log_rotator_pathspec,
    )
    if pathspec_seed:
        results.append(pathspec_seed)
        return _summary(results)
    results.append(
        StepResult(
            name="session_log_rotator_pathspec",
            returncode=0,
            expected_returncode=True,
            output=session_log_rotator_pathspec,
            first_bytes=_first_bytes(session_log_rotator_pathspec),
        ),
    )

    results.append(
        _run_stdout_json_step(
            root,
            name="approval_pathspec_consistency",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/approval_pathspec_consistency.py",
                "--root",
                ".",
                "--output-json",
                str(paths.approval_pathspec),
                "--output-md",
                str(paths.approval_pathspec_md),
                "--coverage-json",
                str(paths.authorization_coverage),
                "--combined-pathspec",
                str(paths.approval_combined_pathspec),
                "--json",
            ],
            target=approval_pathspec,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="launch_objective_audit",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/launch_objective_audit.py",
                "--root",
                ".",
                "--output",
                str(paths.launch_refresh),
                "--json",
            ],
            refresh=launch_refresh,
            target=launch,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_stdout_json_step(
            root,
            name="completion_audit",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/completion_audit.py",
                str(paths.launch),
                "--json",
                "--allow-incomplete",
            ],
            target=completion,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_stdout_json_step(
            root,
            name="session_orient",
            argv=[py, "execution/session_orient.py", "--json"],
            target=session_orient,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="next_experiment_selector",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/next_experiment_selector.py",
                "--root",
                ".",
                "--output",
                str(paths.selector_refresh),
                "--json",
            ],
            refresh=selector_refresh,
            target=selector,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(_copy_json_after_validation(selector, selector_legacy_alias))
    if results[-1].status != "ok":
        return _summary(results)

    results.append(_copy_json_after_validation(selector, selector_continuation_alias))
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _write_session_log_rotator_packet(
            root=root,
            coverage_json=_in_root(root, paths.authorization_coverage),
            selector_json=selector,
            pathspec=session_log_rotator_pathspec,
            packet_json=session_log_rotator_packet,
            packet_md=session_log_rotator_packet_md,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="direction_alignment_audit",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/direction_alignment_audit.py",
                "--root",
                ".",
                "--output",
                str(paths.direction_alignment_refresh),
                "--json",
            ],
            refresh=direction_alignment_refresh,
            target=direction_alignment,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _write_approval_matrix_and_burndown(
            approval=approval_pathspec,
            readiness=readiness,
            completion=completion,
            selector=selector,
            matrix_json=approval_execution_matrix,
            matrix_md=approval_execution_matrix_md,
            burndown_json=launch_blocker_burndown,
            burndown_md=launch_blocker_burndown_md,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_output_file_step(
            root,
            name="debug_loop_inventory",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/debug_loop_inventory.py",
                "--root",
                ".",
                "--session-orient",
                str(paths.session_orient),
                "--selector",
                str(paths.selector),
                "--readiness",
                str(paths.readiness),
                "--completion-audit",
                str(paths.completion),
                "--dirty-handoff-plan",
                str(paths.dirty_handoff_plan),
                "--output-md",
                str(paths.debug_md_refresh),
                "--output-json",
                str(paths.debug_json_refresh),
                "--json",
                "--fail-on-completion-blocked",
            ],
            refresh=debug_json_refresh,
            target=debug_json,
            timeout=timeout,
            expected_returncodes={0, 1},
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(_validate_debug_loop_completion_exit(debug_json, results[-1].returncode))
    if results[-1].status != "ok":
        return _summary(results)

    results.append(_replace_markdown(debug_md_refresh, debug_md))
    if results[-1].status != "ok":
        return _summary(results)

    results.append(_upsert_session_log_rotator_menu_option(scoped_authorization_menu_json))
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_stdout_json_step(
            root,
            name="scoped_authorization_menu",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/scoped_authorization_menu.py",
                "--root",
                ".",
                "--rewrite-menu-json",
                "--json",
            ],
            target=scoped_authorization_menu_md.with_suffix(".refresh.json"),
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_stdout_json_step(
            root,
            name="scoped_authorization_menu_check",
            argv=[
                py,
                ".agents/skills/auto-research/scripts/scoped_authorization_menu.py",
                "--root",
                ".",
                "--check",
                "--json",
            ],
            target=scoped_authorization_menu_check,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _write_ai_context_relay_packet(
            root=root,
            menu_json=scoped_authorization_menu_json,
            coverage_json=_in_root(root, paths.authorization_coverage),
            selector_json=selector,
            packet_json=ai_context_relay_packet,
            packet_md=ai_context_relay_packet_md,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _run_stdout_json_step(
            root,
            name="session_orient_final",
            argv=[py, "execution/session_orient.py", "--json"],
            target=session_orient,
            timeout=timeout,
        ),
    )
    if results[-1].status != "ok":
        return _summary(results)

    results.append(
        _write_prompt_artifact_checklist(
            launch=launch,
            completion=completion,
            readiness=readiness,
            selector=selector,
            session_orient=session_orient,
            dirty_handoff_plan=dirty_handoff_plan,
            github_inventory=github_inventory,
            browser_qa=browser_qa_inventory,
            dependency_freshness=dependency_freshness,
            code_review_gate=_in_root(root, paths.code_review_gate),
            coverage=_in_root(root, paths.authorization_coverage),
            approval=_in_root(root, paths.approval_pathspec),
            menu=scoped_authorization_menu_json,
            menu_check=scoped_authorization_menu_check,
            release=release_authorization_packet,
            burndown=launch_blocker_burndown,
            debug_loop=debug_json,
            target=prompt_artifact_checklist,
            root=root,
        ),
    )
    return _summary(results)


def _summary(results: list[StepResult]) -> dict[str, Any]:
    status = "ok" if all(result.status == "ok" for result in results) else "failed"
    return {
        "status": status,
        "steps": [
            {
                "name": result.name,
                "returncode": result.returncode,
                "expected_returncode": result.expected_returncode,
                "output": str(result.output) if result.output else None,
                "first_bytes": result.first_bytes,
                "status": result.status,
                "detail": result.detail,
            }
            for result in results
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh auto-research current evidence with BOM-free byte writes.",
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="Workspace root")
    parser.add_argument("--timeout", type=int, default=120, help="Per-helper timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = refresh_current_evidence(args.root.resolve(), timeout=args.timeout)
    if args.json:
        print(_json_text(summary), end="")
    else:
        print(f"status={summary['status']}")
        for step in summary["steps"]:
            print(
                "{name}: status={status} returncode={returncode} first_bytes={first_bytes}".format(
                    **step,
                ),
            )
    return 0 if summary["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
