#!/usr/bin/env python3
"""Generate the debug-loop 0-step bug/anomaly inventory from live evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_MD = Path(".tmp/debug-loop-known-bugs-current.md")
DEFAULT_OUTPUT_JSON = Path(".tmp/debug-loop-known-bugs-current.json")
DEFAULT_LAUNCH_AUDIT = Path(".tmp/launch-objective-audit-current.json")
DEFAULT_LAUNCH_AUDIT_REFRESH = Path(".tmp/launch-objective-audit-refresh.json")
DEFAULT_DIRTY_HANDOFF_PLAN = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.json")
DEFAULT_DIRTY_HANDOFF_PLAN_MD = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.md")
DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH = Path(".tmp/scoped-dirty-worktree-handoff-plan-refresh.json")
DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH_MD = Path(".tmp/scoped-dirty-worktree-handoff-plan-refresh.md")
COMPLETION_BLOCKED_EXIT_CODE = 1
LAUNCH_AUDIT_TIMEOUT_MULTIPLIER = 5
SELECTOR_TIMEOUT_MULTIPLIER = 2
_PROVIDED_INPUT_KEYS = (
    "session_orient",
    "selector",
    "readiness",
    "completion_audit",
    "dirty_handoff_plan",
)


@dataclass(frozen=True)
class InventoryBuildInputs:
    session_orient: dict[str, Any]
    selector: dict[str, Any]
    readiness: dict[str, Any]
    completion_audit: dict[str, Any]
    dirty_handoff_plan: dict[str, Any]


@dataclass(frozen=True)
class InventoryItemContext:
    session_git: dict[str, Any]
    graph: dict[str, Any]
    worktree: dict[str, Any]
    readiness_overall: dict[str, Any]
    signature: dict[str, Any]
    freshness: dict[str, Any]
    completion_summary: dict[str, Any]


@dataclass(frozen=True)
class PrimaryBoundaryState:
    selector_kind: str
    dirty_count: int
    has_dirty_boundary: bool
    has_publish_boundary: bool


@dataclass(frozen=True)
class RefreshPromotionFailure(Exception):
    path: Path
    detail: str


class OutputWriteFailure(Exception):
    def __init__(self, path: Path, error: OSError) -> None:
        super().__init__(f"{type(error).__name__}: {error}")
        self.path = path


@dataclass(frozen=True)
class _PreparedWrite:
    target: Path
    tmp: Path


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _display(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None or value == "":
        return "unknown"
    return str(value).replace("\n", " ").strip()


def _resolve(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else root / path


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        try:
            raw = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            raw = path.read_text(encoding="utf-16")
        parsed = json.loads(raw)
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_payload_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2) + "\n"


def _atomic_write_text(path: Path, text: str) -> None:
    prepared = _prepare_text_write(path, text)
    _commit_prepared_writes([prepared])


def _prepare_text_write(path: Path, text: str) -> _PreparedWrite:
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise OutputWriteFailure(path, exc) from exc
    return _PreparedWrite(path, tmp)


def _commit_prepared_writes(prepared: list[_PreparedWrite]) -> None:
    completed: list[_PreparedWrite] = []
    try:
        for item in prepared:
            item.tmp.replace(item.target)
            completed.append(item)
    except OSError as exc:
        failing = next((item for item in prepared if item not in completed), prepared[-1])
        for item in prepared:
            try:
                if item.tmp.is_file() or item.tmp.is_symlink():
                    item.tmp.unlink()
            except OSError:
                pass
        raise OutputWriteFailure(failing.target, exc) from exc


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, _json_payload_text(payload))


def _replace_refresh_file(refresh_path: Path, current_path: Path) -> None:
    try:
        refresh_path.replace(current_path)
    except OSError as exc:
        raise RefreshPromotionFailure(
            current_path,
            f"{type(exc).__name__}: {exc}",
        ) from exc


def _refresh_promotion_error(exc: RefreshPromotionFailure) -> dict[str, Any]:
    return {
        "reason": "refresh_promotion_failed",
        "returncode": 1,
        "path": exc.path.as_posix(),
        "detail": exc.detail,
    }


def _discard_regenerated_file(path: Path) -> None:
    try:
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
    except OSError:
        pass


def _discard_regenerated_files(*paths: Path) -> None:
    for path in paths:
        _discard_regenerated_file(path)


def _has_input_error(payload: dict[str, Any]) -> bool:
    return bool(_as_dict(payload.get("_input_error")))


def _input_error_line(label: str, payload: dict[str, Any]) -> str:
    error = _as_dict(payload.get("_input_error"))
    if not error:
        return ""
    reason = _display(error.get("reason"))
    returncode = error.get("returncode")
    detail = _display(error.get("detail"))
    parts = [f"{label}: {reason}"]
    if returncode is not None:
        parts.append(f"returncode={returncode}")
    if detail != "unknown":
        parts.append(f"detail={detail}")
    return "; ".join(parts)


def _inventory_input_error_lines(inputs: InventoryBuildInputs) -> list[str]:
    lines = [_input_error_line(key, getattr(inputs, key)) for key in _PROVIDED_INPUT_KEYS]
    return [line for line in lines if line]


def _add_input_error(payload: dict[str, Any], error: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    merged["_input_error"] = error
    return merged


def _input_error_payload(
    reason: str,
    *,
    returncode: int | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"reason": reason}
    if returncode is not None:
        error["returncode"] = returncode
    if detail is not None:
        error["detail"] = detail
    return {"_input_error": error}


def _completed_helper_error(
    reason: str,
    completed: subprocess.CompletedProcess[str],
    detail: str,
) -> dict[str, Any]:
    return _input_error_payload(reason, returncode=completed.returncode, detail=detail)


def _parse_helper_json(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    stdout = completed.stdout.strip()
    if not stdout:
        return _completed_helper_error("empty helper output", completed, completed.stderr.strip())
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return _completed_helper_error("invalid helper JSON", completed, str(exc))
    if completed.returncode != 0:
        parsed = parsed if isinstance(parsed, dict) else {}
        return _add_input_error(
            parsed,
            {
                "reason": "helper returned non-zero",
                "returncode": completed.returncode,
                "detail": completed.stderr.strip(),
            },
        )
    return parsed if isinstance(parsed, dict) else {}


def _run_json(root: Path, args: list[str], timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(root),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return _input_error_payload("helper unavailable", detail=str(exc))

    return _parse_helper_json(completed)


def _project(readiness: dict[str, Any], name: str) -> dict[str, Any]:
    for item in _as_list(readiness.get("projects")):
        project = _as_dict(item)
        if project.get("name") == name:
            return project
    return {}


def _user_task_ids(project: dict[str, Any]) -> list[str]:
    task_ids = []
    for raw_task in _as_list(project.get("tasks")):
        task = _as_dict(raw_task)
        if str(task.get("owner") or "").strip().lower() == "user":
            task_id = str(task.get("id") or "").strip()
            if task_id:
                task_ids.append(task_id)
    return sorted(set(task_ids))


def _required_workflows(readiness: dict[str, Any]) -> list[str]:
    github_release = _as_dict(_as_dict(readiness.get("workspace_gates")).get("github_release"))
    workflows = []
    for raw_workflow in _as_list(github_release.get("required_workflows")):
        workflow = _as_dict(raw_workflow)
        name = str(workflow.get("name") or "").strip()
        status = str(workflow.get("status") or "").strip()
        conclusion = str(workflow.get("conclusion") or "").strip()
        if name:
            workflows.append(f"{name}={status or 'unknown'}:{conclusion or 'none'}")
    return workflows


def _dirty_group_summary(plan: dict[str, Any]) -> str:
    groups = []
    for raw_group in _as_list(plan.get("group_order")):
        group = _as_dict(raw_group)
        key = str(group.get("key") or "").strip()
        count = _int(group.get("path_count"))
        if key:
            groups.append(f"{key}={count}")
    return ", ".join(groups) if groups else "unknown"


def _selector_kind(selector: dict[str, Any]) -> str:
    selected = _as_dict(selector.get("selected"))
    summary = _as_dict(selector.get("summary"))
    return str(selected.get("kind") or summary.get("selected_kind") or "").strip()


def _current_dirty_count(
    *,
    readiness_workspace_gates: dict[str, Any],
    readiness_worktree: dict[str, Any],
    worktree: dict[str, Any],
) -> int:
    dirty_count = _int(readiness_workspace_gates.get("dirty_count"))
    if dirty_count != 0:
        return dirty_count
    dirty_count = _int(readiness_worktree.get("dirty_count"))
    if dirty_count != 0:
        return dirty_count
    return _int(worktree.get("staged")) + _int(worktree.get("modified")) + _int(worktree.get("untracked"))


def _inventory_boundary_state(
    *,
    selector_kind: str,
    current_dirty_count: int,
    plan_dirty_count: int,
) -> tuple[int, bool, bool]:
    dirty_count = current_dirty_count
    if selector_kind.startswith("dirty_worktree") and dirty_count == 0:
        dirty_count = plan_dirty_count
    has_dirty_boundary = dirty_count > 0 or selector_kind.startswith("dirty_worktree")
    has_publish_boundary = selector_kind == "current_head_release_checks_unproven"
    return dirty_count, has_dirty_boundary, has_publish_boundary


def _inventory_boundary_from_inputs(
    *,
    selector_kind: str,
    readiness: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
    worktree: dict[str, Any],
) -> tuple[int, bool, bool]:
    readiness_workspace_gates = _as_dict(readiness.get("workspace_gates"))
    readiness_worktree = _as_dict(readiness_workspace_gates.get("worktree"))
    signature = _as_dict(dirty_handoff_plan.get("dirty_signature"))
    signature_input = _as_dict(signature.get("input"))
    return _inventory_boundary_state(
        selector_kind=selector_kind,
        current_dirty_count=_current_dirty_count(
            readiness_workspace_gates=readiness_workspace_gates,
            readiness_worktree=readiness_worktree,
            worktree=worktree,
        ),
        plan_dirty_count=_int(signature_input.get("dirty_count")),
    )


def _selector_status_line(selector: dict[str, Any]) -> str:
    selected = _as_dict(selector.get("selected"))
    summary = _as_dict(selector.get("summary"))
    return (
        "Selector returns "
        f"`status={_display(selector.get('status'))}`, "
        f"`selected_kind={_display(selected.get('kind') or summary.get('selected_kind'))}`, "
        f"`adoptable_candidate_count={_display(summary.get('adoptable_candidate_count'))}`."
    )


def _selector_gate_expectations(selector: dict[str, Any]) -> list[dict[str, Any]]:
    selected = _as_dict(selector.get("selected"))
    expectations: list[dict[str, Any]] = []
    for raw_expectation in _as_list(selected.get("gate_expectations")):
        expectation = _as_dict(raw_expectation)
        gate = str(expectation.get("gate") or "").strip()
        if not gate:
            continue
        expectations.append(
            {
                "gate": gate,
                "expected_exit_codes": _as_list(expectation.get("expected_exit_codes")),
                "meaning": str(expectation.get("meaning") or "").strip(),
            }
        )
    return expectations


def _session_evidence_freshness(session_orient: dict[str, Any]) -> list[dict[str, Any]]:
    graph = _as_dict(session_orient.get("graph"))
    if not graph:
        return []
    return [
        {
            "source": "code_review_graph",
            "available": graph.get("available"),
            "freshness": graph.get("freshness"),
            "stale": graph.get("stale"),
            "built_at_commit": graph.get("built_at_commit"),
            "current_head": graph.get("current_head"),
            "stale_reason": graph.get("stale_reason"),
        }
    ]


def _handoff_plan_freshness_text(*, freshness_status: str, selector_kind: str) -> str:
    if selector_kind == "dirty_worktree_handoff_current" and freshness_status == "stale":
        return (
            "Current handoff plan previous-signature freshness is "
            f"`{freshness_status}`, accepted by selector as matching the current dirty inventory; "
        )
    if selector_kind == "dirty_worktree_handoff_current":
        return (
            "Current handoff plan freshness is "
            f"`{freshness_status}`, accepted by selector as matching the current dirty inventory; "
        )
    return f"Current handoff plan freshness is `{freshness_status}` with "


def _handoff_plan_status_details(
    *,
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
) -> str:
    return (
        f"dirty count `{dirty_count}`, staged `{_int(worktree.get('staged'))}`, "
        f"branch ahead `{_int(session_git.get('ahead'))}`, signature `{_display(signature.get('value'))}`."
    )


def _handoff_plan_status_line(
    *,
    freshness: dict[str, Any],
    selector_kind: str,
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
) -> str:
    freshness_status = _display(freshness.get("status"))
    return _handoff_plan_freshness_text(
        freshness_status=freshness_status, selector_kind=selector_kind
    ) + _handoff_plan_status_details(
        dirty_count=dirty_count,
        worktree=worktree,
        session_git=session_git,
        signature=signature,
    )


def _dirty_handoff_actuals(
    *,
    selector: dict[str, Any],
    selector_kind: str,
    freshness: dict[str, Any],
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
) -> list[str]:
    return [
        _selector_status_line(selector),
        _handoff_plan_status_line(
            freshness=freshness,
            selector_kind=selector_kind,
            dirty_count=dirty_count,
            worktree=worktree,
            session_git=session_git,
            signature=signature,
        ),
        f"Dirty groups: {_dirty_group_summary(dirty_handoff_plan)}.",
    ]


def _dirty_handoff_root_cause() -> str:
    return (
        "Existing dirty work spans multiple project slices, and a machine-readable handoff plan "
        "already matches the current inventory; starting unrelated product edits would mix scopes "
        "without explicit staging/commit authorization."
    )


def _dirty_handoff_next_action() -> str:
    return "Wait for explicit scoped staging/commit authorization, or keep handoff-only evidence current."


def _dirty_handoff_reproduction() -> list[str]:
    return [
        "Run `python .agents/skills/auto-research/scripts/next_experiment_selector.py --root . --json`.",
        "Run `python execution/session_orient.py --json`.",
    ]


def _dirty_handoff_expected() -> list[str]:
    return ["If a safe local bug candidate exists, selector returns an adoptable experiment."]


def _current_head_publish_actuals(
    *,
    selector: dict[str, Any],
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
    readiness: dict[str, Any],
) -> list[str]:
    return [
        _selector_status_line(selector),
        "Current inventory reports dirty count "
        f"`{dirty_count}`, staged `{_int(worktree.get('staged'))}`, "
        f"branch ahead `{_int(session_git.get('ahead'))}`, signature `{_display(signature.get('value'))}`.",
        "Required workflow status: " + (", ".join(_required_workflows(readiness)) or "missing/unavailable"),
    ]


def _current_head_publish_next_action() -> str:
    return (
        "Generate/review the release authorization packet, then get explicit push authorization "
        "or a user push and wait for required Actions on the exact current HEAD."
    )


def _current_head_publish_root_cause() -> str:
    return "Current local HEAD is not published, so GitHub Actions cannot run against it."


def _current_head_publish_reproduction() -> list[str]:
    return [
        "Run `python .agents/skills/auto-research/scripts/next_experiment_selector.py --root . --json`.",
        "Run `python execution/product_readiness_score.py --json`.",
        "Run `python execution/session_orient.py --json`.",
    ]


def _current_head_publish_expected() -> list[str]:
    return ["If the workspace is launch-complete, required workflows exist and pass for the exact current HEAD."]


def _current_head_publish_base_fields(*, next_action: str) -> dict[str, Any]:
    return {
        "title": "Current-HEAD GitHub Actions Cannot Be Proven Locally",
        "status": "reproduced, publish authorization required",
        "severity": "medium-high",
        "frequency": "always while ahead/unpushed",
        "root_cause": _current_head_publish_root_cause(),
        "next_action": next_action,
        "actionable": False,
        "blockers": ["No push authorization is present."],
    }


def _severity_x_frequency(severity: str, frequency: str) -> str:
    return f"{severity} x {frequency}"


def _item_blockers(blockers: list[str] | None) -> list[str]:
    return blockers or []


def _inventory_item_header_fields(
    *,
    priority: int,
    title: str,
    status: str,
    severity: str,
    frequency: str,
) -> dict[str, Any]:
    return {
        "priority": priority,
        "title": title,
        "status": status,
        "severity": severity,
        "frequency": frequency,
        "severity_x_frequency": _severity_x_frequency(severity, frequency),
    }


def _inventory_item_observation_fields(
    *,
    reproduction: list[str],
    expected: list[str],
    actual: list[str],
) -> dict[str, Any]:
    return {
        "reproduction": reproduction,
        "expected": expected,
        "actual": actual,
    }


def _inventory_item_resolution_fields(
    *,
    root_cause: str,
    next_action: str,
    actionable: bool,
    blockers: list[str] | None,
) -> dict[str, Any]:
    return {
        "root_cause": root_cause,
        "next_action": next_action,
        "actionable": actionable,
        "blockers": _item_blockers(blockers),
    }


def _make_item(
    *,
    priority: int,
    title: str,
    status: str,
    severity: str,
    frequency: str,
    reproduction: list[str],
    expected: list[str],
    actual: list[str],
    root_cause: str,
    next_action: str,
    actionable: bool,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        **_inventory_item_header_fields(
            priority=priority,
            title=title,
            status=status,
            severity=severity,
            frequency=frequency,
        ),
        **_inventory_item_observation_fields(
            reproduction=reproduction,
            expected=expected,
            actual=actual,
        ),
        **_inventory_item_resolution_fields(
            root_cause=root_cause,
            next_action=next_action,
            actionable=actionable,
            blockers=blockers,
        ),
    }


def _graph_freshness_is_degraded(graph: dict[str, Any]) -> bool:
    freshness = str(graph.get("freshness") or "").strip().lower()
    stale = bool(graph.get("stale"))
    available = graph.get("available")
    return available is False or stale or freshness in {"stale", "outdated", "unavailable"}


def _graph_freshness_actuals(graph: dict[str, Any]) -> list[str]:
    built_at_commit = graph.get("built_at_commit")
    current_head = graph.get("current_head")
    stale_reason = graph.get("stale_reason")
    return [
        "Code-review graph reports "
        f"`available={_display(graph.get('available'))}`, `freshness={_display(graph.get('freshness'))}`, "
        f"`stale={_display(graph.get('stale'))}`.",
        f"Graph was built at `{_display(built_at_commit)}` while current HEAD is `{_display(current_head)}`.",
        f"Stale reason: `{_display(stale_reason)}`.",
    ]


def _graph_freshness_reproduction() -> list[str]:
    return [
        "Run `python execution/session_orient.py --json`.",
        "Inspect `graph.available`, `graph.freshness`, `graph.stale`, `graph.built_at_commit`, and `graph.current_head`.",
    ]


def _graph_freshness_expected() -> list[str]:
    return ["Graph evidence used before code review is fresh for the current HEAD or explicitly marked stale."]


def _graph_freshness_root_cause() -> str:
    return (
        "The graph index is older than the live repository HEAD, so graph-first exploration remains useful "
        "but should be treated as evidence with degraded freshness until the graph is updated."
    )


def _graph_freshness_next_action() -> str:
    return (
        "Run `py -3.13 -m code_review_graph update`, or `py -3.13 -m code_review_graph build` if "
        "incremental update cannot reconcile the index, then rerun session orientation and debug inventory."
    )


def _graph_freshness_base_fields() -> dict[str, Any]:
    return {
        "title": "Code Review Graph Evidence Is Stale",
        "status": "reproduced, evidence freshness degraded",
        "severity": "medium",
        "frequency": "until graph is updated for current HEAD",
        "root_cause": _graph_freshness_root_cause(),
        "next_action": _graph_freshness_next_action(),
        "actionable": True,
    }


def _graph_freshness_item_from_graph(graph: dict[str, Any]) -> dict[str, Any] | None:
    if not graph or not _graph_freshness_is_degraded(graph):
        return None

    return _make_item(
        priority=0,
        **_graph_freshness_base_fields(),
        reproduction=_graph_freshness_reproduction(),
        expected=_graph_freshness_expected(),
        actual=_graph_freshness_actuals(graph),
    )


def _graph_freshness_item(session_orient: dict[str, Any]) -> dict[str, Any] | None:
    return _graph_freshness_item_from_graph(_as_dict(session_orient.get("graph")))


def _append_graph_freshness_item(items: list[dict[str, Any]], context: InventoryItemContext) -> None:
    graph_item = _graph_freshness_item_from_graph(context.graph)
    if graph_item:
        graph_item["priority"] = len(items) + 1
        items.append(graph_item)


def _append_input_evidence_item(
    items: list[dict[str, Any]],
    *,
    inputs: InventoryBuildInputs,
) -> list[str]:
    input_error_lines = _inventory_input_error_lines(inputs)
    if input_error_lines:
        items.append(_input_evidence_unavailable_item(priority=len(items) + 1, input_error_lines=input_error_lines))
    return input_error_lines


def _append_hanwoo_t251_item(
    items: list[dict[str, Any]],
    *,
    readiness: dict[str, Any],
    readiness_overall: dict[str, Any],
) -> None:
    items.append(
        _hanwoo_t251_external_blocker_item(
            priority=len(items) + 1,
            readiness_overall=readiness_overall,
            t251_ids=_hanwoo_t251_task_ids(readiness),
        )
    )


def _append_dirty_handoff_boundary_item(
    items: list[dict[str, Any]],
    *,
    selector: dict[str, Any],
    selector_kind: str,
    freshness: dict[str, Any],
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
) -> None:
    items.append(
        _dirty_handoff_boundary_item(
            priority=len(items) + 1,
            selector=selector,
            selector_kind=selector_kind,
            freshness=freshness,
            dirty_count=dirty_count,
            worktree=worktree,
            session_git=session_git,
            signature=signature,
            dirty_handoff_plan=dirty_handoff_plan,
        )
    )


def _append_current_head_publish_boundary_item(
    items: list[dict[str, Any]],
    *,
    selector: dict[str, Any],
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
    readiness: dict[str, Any],
) -> None:
    items.append(
        _current_head_publish_boundary_item(
            priority=len(items) + 1,
            selector=selector,
            dirty_count=dirty_count,
            worktree=worktree,
            session_git=session_git,
            signature=signature,
            readiness=readiness,
        )
    )


def _primary_boundary_kind(*, has_dirty_boundary: bool, has_publish_boundary: bool) -> str:
    if has_dirty_boundary:
        return "dirty_worktree_handoff"
    if has_publish_boundary:
        return "current_head_publish"
    return ""


def _append_primary_dirty_boundary_item(
    items: list[dict[str, Any]],
    *,
    boundary: PrimaryBoundaryState,
    selector: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
    context: InventoryItemContext,
) -> None:
    _append_dirty_handoff_boundary_item(
        items,
        selector=selector,
        selector_kind=boundary.selector_kind,
        freshness=context.freshness,
        dirty_count=boundary.dirty_count,
        worktree=context.worktree,
        session_git=context.session_git,
        signature=context.signature,
        dirty_handoff_plan=dirty_handoff_plan,
    )


def _append_primary_publish_boundary_item(
    items: list[dict[str, Any]],
    *,
    boundary: PrimaryBoundaryState,
    selector: dict[str, Any],
    readiness: dict[str, Any],
    context: InventoryItemContext,
) -> None:
    _append_current_head_publish_boundary_item(
        items,
        selector=selector,
        dirty_count=boundary.dirty_count,
        worktree=context.worktree,
        session_git=context.session_git,
        signature=context.signature,
        readiness=readiness,
    )


def _append_primary_boundary_item(
    items: list[dict[str, Any]],
    *,
    boundary: PrimaryBoundaryState,
    selector: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
    readiness: dict[str, Any],
    context: InventoryItemContext,
) -> None:
    boundary_kind = _primary_boundary_kind(
        has_dirty_boundary=boundary.has_dirty_boundary,
        has_publish_boundary=boundary.has_publish_boundary,
    )
    if boundary_kind == "dirty_worktree_handoff":
        _append_primary_dirty_boundary_item(
            items,
            boundary=boundary,
            selector=selector,
            dirty_handoff_plan=dirty_handoff_plan,
            context=context,
        )
    elif boundary_kind == "current_head_publish":
        _append_primary_publish_boundary_item(
            items,
            boundary=boundary,
            selector=selector,
            readiness=readiness,
            context=context,
        )


def _append_current_head_readiness_item(
    items: list[dict[str, Any]],
    *,
    readiness: dict[str, Any],
    session_git: dict[str, Any],
    has_publish_boundary: bool,
) -> None:
    workflows = _required_workflows(readiness)
    if not _should_append_current_head_readiness_item(
        has_publish_boundary=has_publish_boundary,
        ahead=_int(session_git.get("ahead")),
        workflows=workflows,
    ):
        return
    items.append(
        _current_head_readiness_boundary_item(
            priority=len(items) + 1,
            session_git=session_git,
            workflows=workflows,
        )
    )


def _blind_to_x_dirty_paths(blind: dict[str, Any]) -> list[str]:
    return [str(path) for path in _as_list(blind.get("dirty_paths"))]


def _append_blind_to_x_dirty_item(items: list[dict[str, Any]], readiness: dict[str, Any]) -> list[str]:
    blind = _project(readiness, "blind-to-x")
    blind_dirty = _blind_to_x_dirty_paths(blind)
    if blind_dirty:
        items.append(
            _blind_to_x_dirty_handoff_item(
                priority=len(items) + 1,
                blind=blind,
                blind_dirty=blind_dirty,
            )
        )
    return blind_dirty


def _append_launch_completion_item(
    items: list[dict[str, Any]],
    *,
    completion_audit: dict[str, Any],
    completion_summary: dict[str, Any],
    has_dirty_boundary: bool,
    blind_dirty: list[str],
) -> None:
    items.append(
        _launch_completion_incomplete_item(
            priority=len(items) + 1,
            completion_audit=completion_audit,
            completion_summary=completion_summary,
            has_dirty_boundary=has_dirty_boundary,
            blind_dirty=blind_dirty,
        )
    )


def _inventory_blocked_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if _as_list(item.get("blockers"))]


def _completion_blocker_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item.get("title"),
        "status": item.get("status"),
        "next_action": item.get("next_action"),
        "blockers": _as_list(item.get("blockers")),
    }


def _completion_blockers(blocked_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_completion_blocker_entry(item) for item in blocked_items]


def _reproduction_unclear_count(items: list[dict[str, Any]], reproduction_unclear_items: list[Any]) -> int:
    unclear_count = len(reproduction_unclear_items)
    if unclear_count:
        return unclear_count
    return sum(1 for item in items if "reproduction unclear" in str(item.get("status") or "").lower())


def _completion_gate(
    *,
    items: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
    unclear_count: int,
) -> str:
    if blocked_items:
        return "blocked"
    if unclear_count:
        return "reproduction_unclear"
    if items:
        return "open_items"
    return "clear"


def _inventory_summary(items: list[dict[str, Any]], reproduction_unclear_items: list[Any]) -> dict[str, Any]:
    blocked_items = _inventory_blocked_items(items)
    completion_blockers = _completion_blockers(blocked_items)
    unclear_count = _reproduction_unclear_count(items, reproduction_unclear_items)
    completion_gate = _completion_gate(items=items, blocked_items=blocked_items, unclear_count=unclear_count)

    next_item = blocked_items[0] if blocked_items else (items[0] if items else {})
    next_required_action = next_item.get("next_action") if next_item else "No debug-loop action required."
    return {
        "item_count": len(items),
        "actionable_item_count": sum(1 for item in items if item.get("actionable") is True),
        "blocked_item_count": len(blocked_items),
        "reproduction_unclear_count": unclear_count,
        "highest_priority": items[0].get("title") if items else None,
        "completion_gate": completion_gate,
        "completion_allowed": completion_gate == "clear",
        "next_required_action": next_required_action,
        "completion_blockers": completion_blockers,
    }


def _dirty_handoff_base_fields() -> dict[str, Any]:
    return {
        "title": "Dirty Handoff Boundary Blocks New Product Edits",
        "status": "reproduced, blocked by policy/authorization",
        "severity": "high",
        "frequency": "always",
        "root_cause": _dirty_handoff_root_cause(),
        "next_action": _dirty_handoff_next_action(),
        "actionable": False,
        "blockers": ["Explicit scoped staging/commit authorization is required before product changes."],
    }


def _dirty_handoff_boundary_item(
    *,
    priority: int,
    selector: dict[str, Any],
    selector_kind: str,
    freshness: dict[str, Any],
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
) -> dict[str, Any]:
    return _make_item(
        priority=priority,
        **_dirty_handoff_base_fields(),
        reproduction=_dirty_handoff_reproduction(),
        expected=_dirty_handoff_expected(),
        actual=_dirty_handoff_actuals(
            selector=selector,
            selector_kind=selector_kind,
            freshness=freshness,
            dirty_count=dirty_count,
            worktree=worktree,
            session_git=session_git,
            signature=signature,
            dirty_handoff_plan=dirty_handoff_plan,
        ),
    )


def _current_head_publish_boundary_item(
    *,
    priority: int,
    selector: dict[str, Any],
    dirty_count: int,
    worktree: dict[str, Any],
    session_git: dict[str, Any],
    signature: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    return _make_item(
        priority=priority,
        **_current_head_publish_base_fields(next_action=_current_head_publish_next_action()),
        reproduction=_current_head_publish_reproduction(),
        expected=_current_head_publish_expected(),
        actual=_current_head_publish_actuals(
            selector=selector,
            dirty_count=dirty_count,
            worktree=worktree,
            session_git=session_git,
            signature=signature,
            readiness=readiness,
        ),
    )


def _input_evidence_base_fields() -> dict[str, Any]:
    return {
        "title": "Debug Inventory Input Evidence Is Unavailable",
        "status": "reproduction unclear, helper evidence unavailable",
        "severity": "medium-high",
        "frequency": "until helper recovers",
        "root_cause": (
            "One or more deterministic helper commands failed or produced unusable JSON, "
            "so downstream blocker classification cannot be treated as fully reproduced."
        ),
        "next_action": "Fix or regenerate the failing helper evidence, then rerun debug-loop inventory.",
        "actionable": True,
    }


def _input_evidence_unavailable_item(*, priority: int, input_error_lines: list[str]) -> dict[str, Any]:
    return _make_item(
        priority=priority,
        **_input_evidence_base_fields(),
        reproduction=[
            "Run `python .agents/skills/auto-research/scripts/debug_loop_inventory.py --root . --json`.",
            "Inspect helper `_input_error` fields in the generated JSON.",
        ],
        expected=["Every deterministic helper returns current JSON evidence before the inventory classifies blockers."],
        actual=input_error_lines,
    )


def _current_head_readiness_reproduction() -> list[str]:
    return [
        "Run `python execution/product_readiness_score.py --json`.",
        "Run `python execution/session_orient.py --json`.",
    ]


def _current_head_readiness_expected() -> list[str]:
    return ["Required workflows for current local HEAD are available and passing before launch readiness is claimed."]


def _current_head_readiness_actuals(session_git: dict[str, Any], workflows: list[str]) -> list[str]:
    return [
        f"Branch `main` is ahead of origin by `{_int(session_git.get('ahead'))}` commits.",
        "Required workflow status: " + (", ".join(workflows) if workflows else "missing/unavailable"),
    ]


def _current_head_readiness_next_action() -> str:
    return "Explicit push authorization or user push, then wait for required Actions on the exact current HEAD."


def _should_append_current_head_readiness_item(
    *,
    has_publish_boundary: bool,
    ahead: int,
    workflows: list[str],
) -> bool:
    return not has_publish_boundary and (ahead > 0 or bool(workflows))


def _current_head_readiness_boundary_item(
    *,
    priority: int,
    session_git: dict[str, Any],
    workflows: list[str],
) -> dict[str, Any]:
    return _make_item(
        priority=priority,
        **_current_head_publish_base_fields(next_action=_current_head_readiness_next_action()),
        reproduction=_current_head_readiness_reproduction(),
        expected=_current_head_readiness_expected(),
        actual=_current_head_readiness_actuals(session_git, workflows),
    )


def _hanwoo_t251_actuals(*, readiness_overall: dict[str, Any], t251_ids: list[str]) -> list[str]:
    return [
        "Existing recorded failure signature is Prisma `P2010`, raw `XX000`, "
        "`(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`.",
        "Current readiness reports "
        f"`external_blocker_count={_display(readiness_overall.get('external_blocker_count'))}`, "
        f"user-owned task ids `{', '.join(t251_ids)}`.",
    ]


def _hanwoo_t251_reproduction() -> list[str]:
    return [
        "Historical live check command: `npm.cmd run db:prisma7-test -- --live` from `projects/hanwoo-dashboard`.",
        "Current reproduction is intentionally deferred because no Supabase credential reset/resync has been reported.",
    ]


def _hanwoo_t251_expected() -> list[str]:
    return ["After valid Supabase credentials are reset and synced, live Prisma CRUD E2E should connect and pass."]


def _hanwoo_t251_root_cause() -> str:
    return "Supabase credential/control-plane drift, not a locally reproduced code regression."


def _hanwoo_t251_next_action() -> str:
    return (
        "User resets Supabase database password/control-plane credentials, updates `.env` if changed, "
        "then rerun the live Prisma check once."
    )


def _hanwoo_t251_task_ids(readiness: dict[str, Any]) -> list[str]:
    hanwoo = _project(readiness, "hanwoo-dashboard")
    return _user_task_ids(hanwoo) or ["T-251"]


def _hanwoo_t251_base_fields() -> dict[str, Any]:
    return {
        "title": "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
        "status": "known external blocker, do not retry until reset",
        "severity": "high",
        "frequency": "always until user reset",
        "root_cause": _hanwoo_t251_root_cause(),
        "next_action": _hanwoo_t251_next_action(),
        "actionable": False,
        "blockers": ["Supabase credential reset/resync has not been reported."],
    }


def _hanwoo_t251_external_blocker_item(
    *,
    priority: int,
    readiness_overall: dict[str, Any],
    t251_ids: list[str],
) -> dict[str, Any]:
    return _make_item(
        priority=priority,
        **_hanwoo_t251_base_fields(),
        reproduction=_hanwoo_t251_reproduction(),
        expected=_hanwoo_t251_expected(),
        actual=_hanwoo_t251_actuals(readiness_overall=readiness_overall, t251_ids=t251_ids),
    )


def _blind_to_x_dirty_handoff_actuals(*, blind: dict[str, Any], blind_dirty: list[str]) -> list[str]:
    return [
        "Blind-to-X state is "
        f"`{_display(blind.get('state'))}`, score `{_display(blind.get('score'))}`, "
        f"dirty path count `{len(blind_dirty)}`.",
        "Dirty paths: " + ", ".join(blind_dirty),
    ]


def _blind_to_x_dirty_handoff_reproduction() -> list[str]:
    return [
        "Run `python execution/product_readiness_score.py --json`.",
        "Inspect the `blind-to-x` project entry.",
    ]


def _blind_to_x_dirty_handoff_expected() -> list[str]:
    return ["Launch-complete target product has no dirty project paths and meets expected readiness threshold."]


def _blind_to_x_dirty_handoff_next_action() -> str:
    return "Explicit scoped staging/commit authorization for the `project:blind-to-x` group, or leave as handoff-only."


def _blind_to_x_dirty_handoff_root_cause() -> str:
    return "Completed/validated project changes remain uncommitted or unhanded-off, not a failing runtime gate."


def _blind_to_x_dirty_handoff_base_fields() -> dict[str, Any]:
    return {
        "title": "Blind-to-X Is Ready But Not Launch-Complete Because Dirty Paths Remain",
        "status": "reproduced, handoff/commit boundary",
        "severity": "medium",
        "frequency": "always until dirty paths are handled",
        "root_cause": _blind_to_x_dirty_handoff_root_cause(),
        "next_action": _blind_to_x_dirty_handoff_next_action(),
        "actionable": False,
        "blockers": ["Scoped staging/commit authorization is required."],
    }


def _blind_to_x_dirty_handoff_item(
    *,
    priority: int,
    blind: dict[str, Any],
    blind_dirty: list[str],
) -> dict[str, Any]:
    return _make_item(
        priority=priority,
        **_blind_to_x_dirty_handoff_base_fields(),
        reproduction=_blind_to_x_dirty_handoff_reproduction(),
        expected=_blind_to_x_dirty_handoff_expected(),
        actual=_blind_to_x_dirty_handoff_actuals(blind=blind, blind_dirty=blind_dirty),
    )


def _launch_blocker_labels(*, has_dirty_boundary: bool, blind_dirty: list[str]) -> list[str]:
    blocker_labels = ["publish/current-head Actions", "T-251", "Hanwoo readiness"]
    if has_dirty_boundary:
        blocker_labels.insert(0, "dirty worktree")
    if blind_dirty:
        blocker_labels.append("Blind-to-X handoff")
    return blocker_labels


def _completion_audit_actuals(
    completion_audit: dict[str, Any],
    completion_summary: dict[str, Any],
) -> list[str]:
    return [
        "Completion audit returns "
        f"`status={_display(completion_audit.get('status'))}`, "
        f"`{_display(completion_summary.get('item_count'))}` items, "
        f"`{_display(completion_summary.get('complete_count'))}` complete, "
        f"`{_display(completion_summary.get('issue_count'))}` issues, "
        f"`{_display(completion_summary.get('blocked_count'))}` blocked.",
    ]


def _launch_completion_blocker_phrase(blocker_labels: list[str]) -> str:
    if not blocker_labels:
        return ""
    if len(blocker_labels) == 1:
        return blocker_labels[0]
    if len(blocker_labels) == 2:
        return " and ".join(blocker_labels)
    return ", ".join(blocker_labels[:-1]) + f", and {blocker_labels[-1]}"


def _launch_completion_root_cause(blocker_labels: list[str]) -> str:
    blocker_phrase = _launch_completion_blocker_phrase(blocker_labels)
    if not blocker_phrase:
        return "The audit has no unresolved launch blocker boundaries."
    boundary_word = "boundary" if len(blocker_labels) == 1 else "boundaries"
    return f"The audit correctly reflects unresolved {blocker_phrase} {boundary_word}."


def _launch_completion_reproduction() -> list[str]:
    return [
        "Run `python .agents/skills/auto-research/scripts/launch_objective_audit.py --root . --output .tmp/launch-objective-audit-current.json --json`.",
        "Run `python .agents/skills/auto-research/scripts/completion_audit.py .tmp/launch-objective-audit-current.json --json --allow-incomplete`.",
    ]


def _launch_completion_expected() -> list[str]:
    return ["All explicit launch/debug-loop requirements are complete before marking the goal complete."]


def _launch_completion_next_action() -> str:
    return "Do not call `update_goal`; continue only after scoped authorization or external reset changes live state."


def _launch_completion_base_fields(blocker_labels: list[str]) -> dict[str, Any]:
    return {
        "title": "Launch Completion Audit Remains Incomplete",
        "status": "reproduced, aggregate blocker",
        "severity": "medium",
        "frequency": "always while above blockers remain",
        "root_cause": _launch_completion_root_cause(blocker_labels),
        "next_action": _launch_completion_next_action(),
        "actionable": False,
        "blockers": ["Completion audit is incomplete."],
    }


def _launch_completion_incomplete_item(
    *,
    priority: int,
    completion_audit: dict[str, Any],
    completion_summary: dict[str, Any],
    has_dirty_boundary: bool,
    blind_dirty: list[str],
) -> dict[str, Any]:
    blocker_labels = _launch_blocker_labels(has_dirty_boundary=has_dirty_boundary, blind_dirty=blind_dirty)

    return _make_item(
        priority=priority,
        **_launch_completion_base_fields(blocker_labels),
        reproduction=_launch_completion_reproduction(),
        expected=_launch_completion_expected(),
        actual=_completion_audit_actuals(completion_audit, completion_summary),
    )


def _append_readiness_boundary_items(
    items: list[dict[str, Any]],
    *,
    readiness: dict[str, Any],
    context: InventoryItemContext,
    has_publish_boundary: bool,
) -> None:
    _append_graph_freshness_item(items, context)

    _append_hanwoo_t251_item(items, readiness=readiness, readiness_overall=context.readiness_overall)

    _append_current_head_readiness_item(
        items,
        readiness=readiness,
        session_git=context.session_git,
        has_publish_boundary=has_publish_boundary,
    )


def _primary_boundary_state_from_inputs(
    *,
    selector: dict[str, Any],
    readiness: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
    context: InventoryItemContext,
) -> PrimaryBoundaryState:
    selector_kind = _selector_kind(selector)
    dirty_count, has_dirty_boundary, has_publish_boundary = _inventory_boundary_from_inputs(
        selector_kind=selector_kind,
        readiness=readiness,
        dirty_handoff_plan=dirty_handoff_plan,
        worktree=context.worktree,
    )
    return PrimaryBoundaryState(
        selector_kind=selector_kind,
        dirty_count=dirty_count,
        has_dirty_boundary=has_dirty_boundary,
        has_publish_boundary=has_publish_boundary,
    )


def _append_primary_boundary_from_inputs(
    items: list[dict[str, Any]],
    *,
    selector: dict[str, Any],
    readiness: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
    context: InventoryItemContext,
) -> tuple[bool, bool]:
    boundary = _primary_boundary_state_from_inputs(
        selector=selector,
        readiness=readiness,
        dirty_handoff_plan=dirty_handoff_plan,
        context=context,
    )
    _append_primary_boundary_item(
        items,
        boundary=boundary,
        selector=selector,
        dirty_handoff_plan=dirty_handoff_plan,
        readiness=readiness,
        context=context,
    )
    return boundary.has_dirty_boundary, boundary.has_publish_boundary


def _append_completion_boundary_items(
    items: list[dict[str, Any]],
    *,
    readiness: dict[str, Any],
    completion_audit: dict[str, Any],
    context: InventoryItemContext,
    has_dirty_boundary: bool,
) -> None:
    blind_dirty = _append_blind_to_x_dirty_item(items, readiness)

    _append_launch_completion_from_context(
        items,
        completion_audit=completion_audit,
        context=context,
        has_dirty_boundary=has_dirty_boundary,
        blind_dirty=blind_dirty,
    )


def _append_launch_completion_from_context(
    items: list[dict[str, Any]],
    *,
    completion_audit: dict[str, Any],
    context: InventoryItemContext,
    has_dirty_boundary: bool,
    blind_dirty: list[str],
) -> None:
    _append_launch_completion_item(
        items,
        completion_audit=completion_audit,
        completion_summary=context.completion_summary,
        has_dirty_boundary=has_dirty_boundary,
        blind_dirty=blind_dirty,
    )


def _inventory_item_context(inputs: InventoryBuildInputs) -> InventoryItemContext:
    session_git = _as_dict(inputs.session_orient.get("git"))
    return InventoryItemContext(
        session_git=session_git,
        graph=_as_dict(inputs.session_orient.get("graph")),
        worktree=_as_dict(session_git.get("worktree")),
        readiness_overall=_as_dict(inputs.readiness.get("overall")),
        signature=_as_dict(inputs.dirty_handoff_plan.get("dirty_signature")),
        freshness=_as_dict(inputs.dirty_handoff_plan.get("freshness")),
        completion_summary=_as_dict(inputs.completion_audit.get("summary")),
    )


def _append_boundary_inventory_items(
    items: list[dict[str, Any]],
    *,
    inputs: InventoryBuildInputs,
    context: InventoryItemContext,
) -> tuple[bool, bool]:
    has_dirty_boundary, has_publish_boundary = _append_primary_boundary_from_inputs(
        items,
        selector=inputs.selector,
        readiness=inputs.readiness,
        dirty_handoff_plan=inputs.dirty_handoff_plan,
        context=context,
    )

    _append_readiness_boundary_items(
        items,
        readiness=inputs.readiness,
        context=context,
        has_publish_boundary=has_publish_boundary,
    )

    _append_completion_boundary_items(
        items,
        readiness=inputs.readiness,
        completion_audit=inputs.completion_audit,
        context=context,
        has_dirty_boundary=has_dirty_boundary,
    )

    return has_dirty_boundary, has_publish_boundary


def _append_inventory_evidence_items(
    items: list[dict[str, Any]],
    *,
    inputs: InventoryBuildInputs,
    context: InventoryItemContext,
) -> list[str]:
    input_error_lines = _append_input_evidence_item(
        items,
        inputs=inputs,
    )

    _append_boundary_inventory_items(
        items,
        inputs=inputs,
        context=context,
    )

    return input_error_lines


def _build_inventory_items(
    *,
    session_orient: dict[str, Any],
    selector: dict[str, Any],
    readiness: dict[str, Any],
    completion_audit: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    inputs = InventoryBuildInputs(
        session_orient=session_orient,
        selector=selector,
        readiness=readiness,
        completion_audit=completion_audit,
        dirty_handoff_plan=dirty_handoff_plan,
    )
    items: list[dict[str, Any]] = []
    input_error_lines = _append_inventory_evidence_items(
        items,
        inputs=inputs,
        context=_inventory_item_context(inputs),
    )

    return items, input_error_lines


def _inventory_objective() -> str:
    return (
        "List currently known bugs, anomalies, and blockers for the autonomous reproduce -> isolate -> "
        "root-cause -> fix -> verify loop without guessing or editing product code."
    )


def build_inventory(
    *,
    root: Path,
    session_orient: dict[str, Any],
    selector: dict[str, Any],
    readiness: dict[str, Any],
    completion_audit: dict[str, Any],
    dirty_handoff_plan: dict[str, Any],
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    items, input_error_lines = _build_inventory_items(
        session_orient=session_orient,
        selector=selector,
        readiness=readiness,
        completion_audit=completion_audit,
        dirty_handoff_plan=dirty_handoff_plan,
    )
    summary = _inventory_summary(items, input_error_lines)
    summary["expected_failure_gates"] = _selector_gate_expectations(selector)
    summary["evidence_freshness"] = _session_evidence_freshness(session_orient)

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "root": str(root),
        "objective": _inventory_objective(),
        "items": items,
        "reproduction_unclear_items": input_error_lines,
        "summary": summary,
    }


def _summary_passthrough_fields(existing_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        key: existing_summary[key]
        for key in ("expected_failure_gates", "evidence_freshness")
        if key in existing_summary
    }


def _summary_for_markdown(inventory: dict[str, Any]) -> dict[str, Any]:
    items = [_as_dict(item) for item in _as_list(inventory.get("items"))]
    existing_summary = _as_dict(inventory.get("summary"))
    if "items" not in inventory:
        return dict(existing_summary)

    summary = _inventory_summary(items, _as_list(inventory.get("reproduction_unclear_items")))
    summary.update(_summary_passthrough_fields(existing_summary))
    return summary


def _markdown_summary_lines(summary: dict[str, Any]) -> list[str]:
    return [
        "## Summary",
        "",
        f"- Items: {_display(summary.get('item_count'))}",
        f"- Actionable: {_display(summary.get('actionable_item_count'))}",
        f"- Blocked: {_display(summary.get('blocked_item_count'))}",
        f"- Reproduction unclear: {_display(summary.get('reproduction_unclear_count'))}",
        f"- Completion gate: {_display(summary.get('completion_gate'))}",
        f"- Completion allowed: {_display(summary.get('completion_allowed'))}",
        f"- Next required action: {_display(summary.get('next_required_action'))}",
        "",
    ]


def _append_markdown_summary(lines: list[str], inventory: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_for_markdown(inventory)
    lines.extend(_markdown_summary_lines(summary))
    return summary


def _markdown_blocked_notice_lines(summary: dict[str, Any]) -> list[str]:
    if _int(summary.get("blocked_item_count")) == 0:
        return []
    return [
        "> [!IMPORTANT]",
        "> Debug loop is blocked; do not claim launch completion until blockers are cleared.",
        f"> Highest priority: {_display(summary.get('highest_priority'))}.",
        "",
    ]


def _append_markdown_blocked_notice(lines: list[str], summary: dict[str, Any]) -> None:
    lines.extend(_markdown_blocked_notice_lines(summary))


def _markdown_completion_blocker_line(blocker: dict[str, Any]) -> str:
    return f"  - {_display(blocker.get('title'))}: {_display(blocker.get('next_action'))}"


def _markdown_completion_blocker_section_lines(completion_blockers: list[dict[str, Any]]) -> list[str]:
    if not completion_blockers:
        return []
    return [
        "- Completion blockers:",
        *[_markdown_completion_blocker_line(blocker) for blocker in completion_blockers],
        "",
    ]


def _append_markdown_completion_blockers(lines: list[str], summary: dict[str, Any]) -> None:
    completion_blockers = [_as_dict(blocker) for blocker in _as_list(summary.get("completion_blockers"))]
    lines.extend(_markdown_completion_blocker_section_lines(completion_blockers))


def _markdown_expected_failure_gate_line(gate: dict[str, Any]) -> str:
    expected_codes = ", ".join(str(code) for code in _as_list(gate.get("expected_exit_codes")))
    suffix = f": {_display(gate.get('meaning'))}" if gate.get("meaning") else ""
    return f"  - `{_display(gate.get('gate'))}` expects exit code(s) `{expected_codes or 'unknown'}`{suffix}"


def _markdown_expected_failure_gate_section_lines(expected_failure_gates: list[dict[str, Any]]) -> list[str]:
    if not expected_failure_gates:
        return []
    return [
        "- Expected nonzero gates:",
        *[_markdown_expected_failure_gate_line(gate) for gate in expected_failure_gates],
        "",
    ]


def _append_markdown_expected_failure_gates(lines: list[str], summary: dict[str, Any]) -> None:
    expected_failure_gates = [_as_dict(gate) for gate in _as_list(summary.get("expected_failure_gates"))]
    lines.extend(_markdown_expected_failure_gate_section_lines(expected_failure_gates))


def _markdown_evidence_stale_reason_detail(evidence: dict[str, Any]) -> str | None:
    stale_reason = evidence.get("stale_reason")
    if not stale_reason:
        return None
    return f"reason `{_display(stale_reason)}`"


def _markdown_evidence_freshness_base_details(evidence: dict[str, Any]) -> list[str]:
    return [
        f"available `{_display(evidence.get('available'))}`",
        f"freshness `{_display(evidence.get('freshness'))}`",
        f"stale `{_display(evidence.get('stale'))}`",
        f"built_at_commit `{_display(evidence.get('built_at_commit'))}`",
        f"current_head `{_display(evidence.get('current_head'))}`",
    ]


def _markdown_evidence_freshness_details(evidence: dict[str, Any]) -> list[str]:
    details = _markdown_evidence_freshness_base_details(evidence)
    stale_reason_detail = _markdown_evidence_stale_reason_detail(evidence)
    if stale_reason_detail:
        details.append(stale_reason_detail)
    return details


def _markdown_evidence_freshness_line(evidence: dict[str, Any]) -> str:
    details = _markdown_evidence_freshness_details(evidence)
    return f"  - {_display(evidence.get('source'))}: " + ", ".join(details)


def _markdown_evidence_freshness_section_lines(evidence_freshness: list[dict[str, Any]]) -> list[str]:
    if not evidence_freshness:
        return []
    return [
        "- Evidence freshness:",
        *[_markdown_evidence_freshness_line(evidence) for evidence in evidence_freshness],
        "",
    ]


def _append_markdown_evidence_freshness(lines: list[str], summary: dict[str, Any]) -> None:
    evidence_freshness = [_as_dict(item) for item in _as_list(summary.get("evidence_freshness"))]
    lines.extend(_markdown_evidence_freshness_section_lines(evidence_freshness))


def _markdown_summary_detail_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    _append_markdown_blocked_notice(lines, summary)
    _append_markdown_completion_blockers(lines, summary)
    _append_markdown_expected_failure_gates(lines, summary)
    _append_markdown_evidence_freshness(lines, summary)
    return lines


def _append_markdown_summary_details(lines: list[str], summary: dict[str, Any]) -> None:
    lines.extend(_markdown_summary_detail_lines(summary))


def _markdown_list_lines(label: str, values: list[Any]) -> list[str]:
    return [
        f"- {label}:",
        *[f"  - {_display(value)}" for value in _as_list(values)],
    ]


def _append_markdown_list(lines: list[str], label: str, values: list[Any]) -> None:
    lines.extend(_markdown_list_lines(label, values))


def _markdown_blocker_lines(blockers: list[Any]) -> list[str]:
    if blockers:
        return _markdown_list_lines("Blockers", blockers)
    return ["- Blockers: none"]


def _append_markdown_blockers(lines: list[str], blockers: list[Any]) -> None:
    lines.extend(_markdown_blocker_lines(blockers))


def _markdown_inventory_item_header_lines(item: dict[str, Any]) -> list[str]:
    return [
        f"## Priority {_display(item.get('priority'))} - {_display(item.get('title'))}",
        "",
        f"- Status: {_display(item.get('status'))}",
        f"- Severity x frequency: {_display(item.get('severity_x_frequency'))}",
        f"- Actionable: {_display(item.get('actionable'))}",
    ]


def _markdown_inventory_item_action_sections(item: dict[str, Any]) -> list[tuple[str, list[Any]]]:
    return [
        ("Root cause", [item.get("root_cause")]),
        ("Next action", [item.get("next_action")]),
    ]


def _markdown_inventory_item_action_lines(item: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for title, values in _markdown_inventory_item_action_sections(item):
        lines.extend(_markdown_list_lines(title, values))
    lines.append("")
    return lines


def _markdown_inventory_item_list_sections(item: dict[str, Any]) -> list[tuple[str, list[Any]]]:
    return [
        ("Reproduction", _as_list(item.get("reproduction"))),
        ("Expected", _as_list(item.get("expected"))),
        ("Actual", _as_list(item.get("actual"))),
    ]


def _markdown_inventory_item_list_lines(item: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for title, values in _markdown_inventory_item_list_sections(item):
        lines.extend(_markdown_list_lines(title, values))
    return lines


def _append_markdown_inventory_item_lists(lines: list[str], item: dict[str, Any]) -> None:
    lines.extend(_markdown_inventory_item_list_lines(item))


def _markdown_inventory_item_lines(item: dict[str, Any]) -> list[str]:
    lines = _markdown_inventory_item_header_lines(item)
    lines.extend(_markdown_blocker_lines(_as_list(item.get("blockers"))))
    lines.extend(_markdown_inventory_item_list_lines(item))
    lines.extend(_markdown_inventory_item_action_lines(item))
    return lines


def _append_markdown_inventory_item(lines: list[str], item: dict[str, Any]) -> None:
    lines.extend(_markdown_inventory_item_lines(item))


def _markdown_inventory_items_lines(inventory: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for raw_item in _as_list(inventory.get("items")):
        lines.extend(_markdown_inventory_item_lines(_as_dict(raw_item)))
    return lines


def _append_markdown_inventory_items(lines: list[str], inventory: dict[str, Any]) -> None:
    lines.extend(_markdown_inventory_items_lines(inventory))


def _markdown_reproduction_unclear_section_lines(unclear: list[Any]) -> list[str]:
    lines = ["## Reproduction-Unclear Items", ""]
    if unclear:
        for item in unclear:
            lines.append(f"- {_display(item)}")
    else:
        lines.append(
            "- None currently actionable. Items without direct local reproduction are classified above as "
            "authorization-blocked or external/user-owned instead of being patched speculatively."
        )
    lines.append("")
    return lines


def _markdown_reproduction_unclear_inventory_lines(inventory: dict[str, Any]) -> list[str]:
    return _markdown_reproduction_unclear_section_lines(_as_list(inventory.get("reproduction_unclear_items")))


def _append_markdown_reproduction_unclear_items(lines: list[str], inventory: dict[str, Any]) -> None:
    lines.extend(_markdown_reproduction_unclear_inventory_lines(inventory))


def _markdown_inventory_body_lines(inventory: dict[str, Any]) -> list[str]:
    lines = _markdown_inventory_items_lines(inventory)
    lines.extend(_markdown_reproduction_unclear_inventory_lines(inventory))
    return lines


def _append_markdown_inventory_body(lines: list[str], inventory: dict[str, Any]) -> None:
    lines.extend(_markdown_inventory_body_lines(inventory))


def _markdown_document_header_lines(inventory: dict[str, Any]) -> list[str]:
    return [
        "# Debug Loop Known Bugs / Anomalies",
        "",
        f"Generated: {_display(inventory.get('generated_at'))}",
        "",
        f"Objective: {_display(inventory.get('objective'))}",
        "",
    ]


def _markdown_document_lines(inventory: dict[str, Any]) -> list[str]:
    lines = _markdown_document_header_lines(inventory)
    summary = _append_markdown_summary(lines, inventory)
    _append_markdown_summary_details(lines, summary)
    _append_markdown_inventory_body(lines, inventory)
    return lines


def render_markdown(inventory: dict[str, Any]) -> str:
    lines = _markdown_document_lines(inventory)
    return "\n".join(lines)


def completion_is_blocked(inventory: dict[str, Any]) -> bool:
    summary = _summary_for_markdown(inventory)
    return summary.get("completion_allowed") is not True


def _expected_failure_gate_status_line(gate: dict[str, Any]) -> str:
    expected_codes = ", ".join(str(code) for code in _as_list(gate.get("expected_exit_codes")))
    if not expected_codes:
        return ""
    status = f"expected_exit_codes={expected_codes}"
    meaning = str(gate.get("meaning") or "").strip()
    if meaning:
        status += f"; meaning={meaning}"
    return status


def _expected_failure_gate_status_lines(summary: dict[str, Any]) -> list[str]:
    statuses: list[str] = []
    for raw_gate in _as_list(summary.get("expected_failure_gates")):
        status = _expected_failure_gate_status_line(_as_dict(raw_gate))
        if status:
            statuses.append(status)
    return statuses


def _expected_failure_gate_status(summary: dict[str, Any]) -> str:
    return " | ".join(_expected_failure_gate_status_lines(summary))


def _dirty_handoff_plan_refresh_command() -> list[str]:
    return [
        sys.executable,
        ".agents/skills/auto-research/scripts/dirty_worktree_handoff_plan.py",
        "--root",
        ".",
        "--previous-json",
        str(DEFAULT_DIRTY_HANDOFF_PLAN),
        "--output-json",
        str(DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH),
        "--output-md",
        str(DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH_MD),
        "--json",
    ]


def _apply_dirty_handoff_plan_refresh(
    *,
    refresh_result: dict[str, Any],
    plan_path: Path,
    plan_md_path: Path,
    refresh_path: Path,
    refresh_md_path: Path,
) -> dict[str, Any]:
    if not _has_input_error(refresh_result) and refresh_path.is_file():
        try:
            _replace_refresh_file(refresh_path, plan_path)
            if refresh_md_path.is_file():
                _replace_refresh_file(refresh_md_path, plan_md_path)
            else:
                _discard_regenerated_file(plan_md_path)
        except RefreshPromotionFailure as exc:
            _discard_regenerated_files(refresh_path, refresh_md_path)
            return _refresh_promotion_error(exc)
    else:
        _discard_regenerated_files(refresh_path, refresh_md_path)
    return {}


def _dirty_handoff_plan_refresh_paths(root: Path) -> tuple[Path, Path]:
    return root / DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH, root / DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH_MD


def _dirty_handoff_plan_paths(root: Path) -> tuple[Path, Path]:
    return root / DEFAULT_DIRTY_HANDOFF_PLAN, root / DEFAULT_DIRTY_HANDOFF_PLAN_MD


def _refresh_dirty_handoff_plan_input(root: Path, timeout: int) -> dict[str, Any]:
    dirty_handoff_plan, dirty_handoff_plan_md = _dirty_handoff_plan_paths(root)
    dirty_handoff_plan_refresh, dirty_handoff_plan_refresh_md = _dirty_handoff_plan_refresh_paths(root)
    _discard_regenerated_files(dirty_handoff_plan_refresh, dirty_handoff_plan_refresh_md)
    dirty_plan_refresh_result = _run_json(
        root,
        _dirty_handoff_plan_refresh_command(),
        timeout,
    )
    promotion_error = _apply_dirty_handoff_plan_refresh(
        refresh_result=dirty_plan_refresh_result,
        plan_path=dirty_handoff_plan,
        plan_md_path=dirty_handoff_plan_md,
        refresh_path=dirty_handoff_plan_refresh,
        refresh_md_path=dirty_handoff_plan_refresh_md,
    )
    dirty_handoff_plan_input = _load_json(dirty_handoff_plan)
    if _has_input_error(dirty_plan_refresh_result):
        error = _as_dict(dirty_plan_refresh_result.get("_input_error"))
        dirty_handoff_plan_input = _add_input_error(dirty_handoff_plan_input, error)
    if promotion_error:
        dirty_handoff_plan_input = _add_input_error(dirty_handoff_plan_input, promotion_error)
    return dirty_handoff_plan_input


def _launch_objective_audit_command(output_path: Path = DEFAULT_LAUNCH_AUDIT) -> list[str]:
    return [
        sys.executable,
        ".agents/skills/auto-research/scripts/launch_objective_audit.py",
        "--root",
        ".",
        "--output",
        str(output_path),
        "--json",
    ]


def _completion_audit_command(launch_audit: Path) -> list[str]:
    return [
        sys.executable,
        ".agents/skills/auto-research/scripts/completion_audit.py",
        str(launch_audit),
        "--json",
        "--allow-incomplete",
    ]


def _launch_audit_path(root: Path) -> Path:
    return root / DEFAULT_LAUNCH_AUDIT


def _launch_audit_refresh_path(root: Path) -> Path:
    return root / DEFAULT_LAUNCH_AUDIT_REFRESH


def _launch_objective_audit_timeout(timeout: int) -> int:
    return max(1, timeout) * LAUNCH_AUDIT_TIMEOUT_MULTIPLIER


def _next_experiment_selector_timeout(timeout: int) -> int:
    return max(1, timeout) * SELECTOR_TIMEOUT_MULTIPLIER


def _completion_audit_input_from_launch_audit(
    root: Path,
    launch_audit: Path,
    launch_audit_result: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    if _has_input_error(launch_audit_result):
        return {"_input_error": _as_dict(launch_audit_result.get("_input_error"))}
    if launch_audit.is_file():
        return _run_json(
            root,
            _completion_audit_command(launch_audit),
            timeout,
        )
    return {}


def _collect_completion_audit_input(root: Path, timeout: int) -> dict[str, Any]:
    launch_audit = _launch_audit_path(root)
    launch_audit_refresh = _launch_audit_refresh_path(root)
    _discard_regenerated_file(launch_audit_refresh)
    launch_audit_result = _run_json(
        root,
        _launch_objective_audit_command(DEFAULT_LAUNCH_AUDIT_REFRESH),
        _launch_objective_audit_timeout(timeout),
    )
    if launch_audit_refresh.is_file() and not _has_input_error(launch_audit_result):
        try:
            _replace_refresh_file(launch_audit_refresh, launch_audit)
        except RefreshPromotionFailure as exc:
            _discard_regenerated_file(launch_audit_refresh)
            return {"_input_error": _refresh_promotion_error(exc)}
    else:
        _discard_regenerated_file(launch_audit_refresh)
    return _completion_audit_input_from_launch_audit(root, launch_audit, launch_audit_result, timeout)


def collect_inputs(root: Path, timeout: int) -> dict[str, dict[str, Any]]:
    completion_audit = _collect_completion_audit_input(root, timeout)
    dirty_handoff_plan_input = _refresh_dirty_handoff_plan_input(root, timeout)
    return {
        "session_orient": _run_json(root, _session_orient_command(), timeout),
        "selector": _run_json(
            root,
            _next_experiment_selector_command(),
            _next_experiment_selector_timeout(timeout),
        ),
        "readiness": _run_json(root, _product_readiness_command(), timeout),
        "completion_audit": completion_audit,
        "dirty_handoff_plan": dirty_handoff_plan_input,
    }


def _session_orient_command() -> list[str]:
    return [sys.executable, "execution/session_orient.py", "--json"]


def _next_experiment_selector_command() -> list[str]:
    return [
        sys.executable,
        ".agents/skills/auto-research/scripts/next_experiment_selector.py",
        "--root",
        ".",
        "--dirty-handoff-plan",
        str(DEFAULT_DIRTY_HANDOFF_PLAN),
        "--json",
    ]


def _product_readiness_command() -> list[str]:
    return [sys.executable, "execution/product_readiness_score.py", "--json"]


def _provided_input_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    return {key: getattr(args, key) for key in _PROVIDED_INPUT_KEYS}


def _load_provided_inputs(root: Path, input_paths: dict[str, Path | None]) -> dict[str, dict[str, Any]]:
    return {key: _load_json(_resolve(root, path)) for key, path in input_paths.items() if path is not None}


def _all_input_paths_provided(input_paths: dict[str, Path | None]) -> bool:
    return all(path is not None for path in input_paths.values())


def _apply_provided_input_overrides(
    inputs: dict[str, dict[str, Any]],
    loaded_inputs: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    inputs.update(loaded_inputs)
    return inputs


def _inventory_inputs_from_args(root: Path, args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    provided_inputs = _provided_input_paths(args)
    loaded_inputs = _load_provided_inputs(root, provided_inputs)
    if _all_input_paths_provided(provided_inputs):
        return loaded_inputs

    return _apply_provided_input_overrides(collect_inputs(root, args.timeout), loaded_inputs)


def _inventory_root_from_args(args: argparse.Namespace) -> Path:
    return args.root.resolve()


def _build_inventory_from_args(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    inputs = _inventory_inputs_from_args(root, args)
    return build_inventory(root=root, **inputs)


def _add_workspace_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path("."), help="Workspace root")


def _add_input_artifact_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session-orient", type=Path, help="Existing session orientation JSON")
    parser.add_argument("--selector", type=Path, help="Existing next-experiment selector JSON")
    parser.add_argument("--readiness", type=Path, help="Existing product readiness JSON")
    parser.add_argument("--completion-audit", type=Path, help="Existing completion audit result JSON")
    parser.add_argument("--dirty-handoff-plan", type=Path, help="Existing dirty handoff plan JSON")


def _add_output_artifact_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Markdown inventory output")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="JSON inventory output")


def _add_execution_control_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--timeout", type=int, default=60, help="Per-helper timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print JSON inventory to stdout")
    parser.add_argument(
        "--fail-on-completion-blocked",
        action="store_true",
        help="Return exit code 1 when the inventory summary does not allow completion",
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _add_workspace_root_argument(parser)
    _add_input_artifact_arguments(parser)
    _add_output_artifact_arguments(parser)
    _add_execution_control_arguments(parser)
    return parser


def _inventory_args_from_argv(argv: list[str] | None) -> argparse.Namespace:
    return _build_arg_parser().parse_args(argv)


def _inventory_output_path(root: Path, output_arg: Path, default_output: Path) -> Path:
    return _resolve(root, output_arg) or root / default_output


def _inventory_output_paths(root: Path, output_md_arg: Path, output_json_arg: Path) -> tuple[Path, Path]:
    return (
        _inventory_output_path(root, output_md_arg, DEFAULT_OUTPUT_MD),
        _inventory_output_path(root, output_json_arg, DEFAULT_OUTPUT_JSON),
    )


def _write_inventory_markdown(path: Path, inventory: dict[str, Any]) -> None:
    _atomic_write_text(path, render_markdown(inventory))


def _write_inventory_json(path: Path, inventory: dict[str, Any]) -> None:
    _write_json(path, inventory)


def _write_inventory_outputs(
    root: Path,
    inventory: dict[str, Any],
    output_md_arg: Path,
    output_json_arg: Path,
) -> tuple[Path, Path]:
    output_md, output_json = _inventory_output_paths(root, output_md_arg, output_json_arg)
    prepared = [
        _prepare_text_write(output_md, render_markdown(inventory)),
        _prepare_text_write(output_json, _json_payload_text(inventory)),
    ]
    _commit_prepared_writes(prepared)
    return output_md, output_json


def _inventory_output_status_lines(output_md: Path, output_json: Path) -> list[str]:
    return [
        "status: generated",
        f"markdown: {output_md}",
        f"json: {output_json}",
    ]


def _emit_inventory_status(output_md: Path, output_json: Path) -> None:
    for line in _inventory_output_status_lines(output_md, output_json):
        print(line)


def _emit_inventory_json(inventory: dict[str, Any]) -> None:
    sys.stdout.write(_json_payload_text(inventory))


def _emit_inventory_output(inventory: dict[str, Any], output_md: Path, output_json: Path, as_json: bool) -> None:
    if as_json:
        _emit_inventory_json(inventory)
    else:
        _emit_inventory_status(output_md, output_json)


def _completion_blocked_message_base(summary: dict[str, Any]) -> str:
    return (
        "completion blocked: "
        f"{_display(summary.get('completion_gate'))}; "
        f"next_required_action={_display(summary.get('next_required_action'))}"
    )


def _completion_blocked_expected_gate_suffix(summary: dict[str, Any]) -> str:
    expected_gate_status = _expected_failure_gate_status(summary)
    if not expected_gate_status:
        return ""
    return f"; expected_failure_gates={expected_gate_status}"


def _completion_blocked_message(inventory: dict[str, Any]) -> str:
    summary = _summary_for_markdown(inventory)
    return _completion_blocked_message_base(summary) + _completion_blocked_expected_gate_suffix(summary)


def _completion_blocked_exit_code(inventory: dict[str, Any], fail_on_completion_blocked: bool) -> int:
    if fail_on_completion_blocked and completion_is_blocked(inventory):
        return COMPLETION_BLOCKED_EXIT_CODE
    return 0


def _completion_blocked_stderr_line(inventory: dict[str, Any], exit_code: int) -> str | None:
    if not exit_code:
        return None
    return _completion_blocked_message(inventory)


def _emit_completion_blocked_message(inventory: dict[str, Any], exit_code: int) -> None:
    stderr_line = _completion_blocked_stderr_line(inventory, exit_code)
    if stderr_line is not None:
        print(stderr_line, file=sys.stderr)


def _run_inventory_from_args(args: argparse.Namespace) -> int:
    root = _inventory_root_from_args(args)
    inventory = _build_inventory_from_args(root, args)
    try:
        output_md, output_json = _write_inventory_outputs(root, inventory, args.output_md, args.output_json)
    except OutputWriteFailure as exc:
        inventory["status"] = "write_failed"
        inventory["write_error"] = str(exc)
        inventory["write_error_path"] = exc.path.as_posix()
        if args.json:
            _emit_inventory_json(inventory)
        else:
            print(f"debug loop inventory: write_failed path={exc.path.as_posix()} error={exc}")
        return 4

    _emit_inventory_output(inventory, output_md, output_json, args.json)
    exit_code = _completion_blocked_exit_code(inventory, args.fail_on_completion_blocked)
    _emit_completion_blocked_message(inventory, exit_code)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    return _run_inventory_from_args(_inventory_args_from_argv(argv))


if __name__ == "__main__":
    raise SystemExit(main())
