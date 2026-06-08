#!/usr/bin/env python3
"""Generate the debug-loop 0-step bug/anomaly inventory from live evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_MD = Path(".tmp/debug-loop-known-bugs-current.md")
DEFAULT_OUTPUT_JSON = Path(".tmp/debug-loop-known-bugs-current.json")
DEFAULT_LAUNCH_AUDIT = Path(".tmp/launch-objective-audit-current.json")
DEFAULT_DIRTY_HANDOFF_PLAN = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.json")


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
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


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
        return {"_input_error": {"reason": "helper unavailable", "detail": str(exc)}}

    stdout = completed.stdout.strip()
    if not stdout:
        return {
            "_input_error": {
                "reason": "empty helper output",
                "returncode": completed.returncode,
                "detail": completed.stderr.strip(),
            }
        }
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return {
            "_input_error": {
                "reason": "invalid helper JSON",
                "returncode": completed.returncode,
                "detail": str(exc),
            }
        }
    if completed.returncode != 0:
        parsed = parsed if isinstance(parsed, dict) else {}
        parsed["_input_error"] = {
            "reason": "helper returned non-zero",
            "returncode": completed.returncode,
            "detail": completed.stderr.strip(),
        }
    return parsed if isinstance(parsed, dict) else {}


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
        "priority": priority,
        "title": title,
        "status": status,
        "severity": severity,
        "frequency": frequency,
        "severity_x_frequency": f"{severity} x {frequency}",
        "reproduction": reproduction,
        "expected": expected,
        "actual": actual,
        "root_cause": root_cause,
        "next_action": next_action,
        "actionable": actionable,
        "blockers": blockers or [],
    }


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
    session_git = _as_dict(session_orient.get("git"))
    worktree = _as_dict(session_git.get("worktree"))
    readiness_overall = _as_dict(readiness.get("overall"))
    selected = _as_dict(selector.get("selected"))
    summary = _as_dict(selector.get("summary"))
    signature = _as_dict(dirty_handoff_plan.get("dirty_signature"))
    signature_input = _as_dict(signature.get("input"))
    freshness = _as_dict(dirty_handoff_plan.get("freshness"))
    completion_summary = _as_dict(completion_audit.get("summary"))

    dirty_count = _int(
        signature_input.get("dirty_count") or _as_dict(readiness.get("workspace_gates")).get("dirty_count")
    )
    if dirty_count == 0:
        dirty_count = _int(_as_dict(_as_dict(readiness.get("workspace_gates")).get("worktree")).get("dirty_count"))
    if dirty_count == 0:
        dirty_count = _int(worktree.get("modified")) + _int(worktree.get("untracked"))

    items: list[dict[str, Any]] = [
        _make_item(
            priority=1,
            title="Dirty Handoff Boundary Blocks New Product Edits",
            status="reproduced, blocked by policy/authorization",
            severity="high",
            frequency="always",
            reproduction=[
                "Run `python .agents/skills/auto-research/scripts/next_experiment_selector.py --root . --json`.",
                "Run `python execution/session_orient.py --json`.",
            ],
            expected=["If a safe local bug candidate exists, selector returns an adoptable experiment."],
            actual=[
                "Selector returns "
                f"`status={_display(selector.get('status'))}`, "
                f"`selected_kind={_display(selected.get('kind') or summary.get('selected_kind'))}`, "
                f"`adoptable_candidate_count={_display(summary.get('adoptable_candidate_count'))}`.",
                "Current handoff plan is "
                f"`{_display(freshness.get('status'))}` with dirty count `{dirty_count}`, "
                f"staged `{_int(worktree.get('staged'))}`, branch ahead `{_int(session_git.get('ahead'))}`, "
                f"signature `{_display(signature.get('value'))}`.",
                f"Dirty groups: {_dirty_group_summary(dirty_handoff_plan)}.",
            ],
            root_cause=(
                "Existing dirty work spans multiple project slices, and a machine-readable handoff plan "
                "already matches the current inventory; starting unrelated product edits would mix scopes "
                "without explicit staging/commit authorization."
            ),
            next_action="Wait for explicit scoped staging/commit authorization, or keep handoff-only evidence current.",
            actionable=False,
            blockers=["Explicit scoped staging/commit authorization is required before product changes."],
        )
    ]

    hanwoo = _project(readiness, "hanwoo-dashboard")
    t251_ids = _user_task_ids(hanwoo) or ["T-251"]
    items.append(
        _make_item(
            priority=2,
            title="Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
            status="known external blocker, do not retry until reset",
            severity="high",
            frequency="always until user reset",
            reproduction=[
                "Historical live check command: `npm.cmd run db:prisma7-test -- --live` from `projects/hanwoo-dashboard`.",
                "Current reproduction is intentionally deferred because no Supabase credential reset/resync has been reported.",
            ],
            expected=[
                "After valid Supabase credentials are reset and synced, live Prisma CRUD E2E should connect and pass."
            ],
            actual=[
                "Existing recorded failure signature is Prisma `P2010`, raw `XX000`, "
                "`(ENOTFOUND) tenant/user postgres.fuemeqmigptwfzqvrpjf not found`.",
                "Current readiness reports "
                f"`external_blocker_count={_display(readiness_overall.get('external_blocker_count'))}`, "
                f"user-owned task ids `{', '.join(t251_ids)}`.",
            ],
            root_cause="Supabase credential/control-plane drift, not a locally reproduced code regression.",
            next_action=(
                "User resets Supabase database password/control-plane credentials, updates `.env` if changed, "
                "then rerun the live Prisma check once."
            ),
            actionable=False,
            blockers=["Supabase credential reset/resync has not been reported."],
        )
    )

    workflows = _required_workflows(readiness)
    items.append(
        _make_item(
            priority=3,
            title="Current-HEAD GitHub Actions Cannot Be Proven Locally",
            status="reproduced, publish authorization required",
            severity="medium-high",
            frequency="always while ahead/unpushed",
            reproduction=[
                "Run `python execution/product_readiness_score.py --json`.",
                "Run `python execution/session_orient.py --json`.",
            ],
            expected=[
                "Required workflows for current local HEAD are available and passing before launch readiness is claimed."
            ],
            actual=[
                f"Branch `main` is ahead of origin by `{_int(session_git.get('ahead'))}` commits.",
                "Required workflow status: " + (", ".join(workflows) if workflows else "missing/unavailable"),
            ],
            root_cause="Current local HEAD is not published, so GitHub Actions cannot run against it.",
            next_action="Explicit push authorization or user push, then wait for required Actions on the exact current HEAD.",
            actionable=False,
            blockers=["No push authorization is present."],
        )
    )

    blind = _project(readiness, "blind-to-x")
    blind_dirty = [str(path) for path in _as_list(blind.get("dirty_paths"))]
    items.append(
        _make_item(
            priority=4,
            title="Blind-to-X Is Ready But Not Launch-Complete Because Dirty Paths Remain",
            status="reproduced, handoff/commit boundary",
            severity="medium",
            frequency="always until dirty paths are handled",
            reproduction=[
                "Run `python execution/product_readiness_score.py --json`.",
                "Inspect the `blind-to-x` project entry.",
            ],
            expected=[
                "Launch-complete target product has no dirty project paths and meets expected readiness threshold."
            ],
            actual=[
                "Blind-to-X state is "
                f"`{_display(blind.get('state'))}`, score `{_display(blind.get('score'))}`, "
                f"dirty path count `{len(blind_dirty)}`.",
                "Dirty paths: " + (", ".join(blind_dirty) if blind_dirty else "none"),
            ],
            root_cause="Completed/validated project changes remain uncommitted or unhanded-off, not a failing runtime gate.",
            next_action="Explicit scoped staging/commit authorization for the `project:blind-to-x` group, or leave as handoff-only.",
            actionable=False,
            blockers=["Scoped staging/commit authorization is required."],
        )
    )

    items.append(
        _make_item(
            priority=5,
            title="Launch Completion Audit Remains Incomplete",
            status="reproduced, aggregate blocker",
            severity="medium",
            frequency="always while above blockers remain",
            reproduction=[
                "Run `python .agents/skills/auto-research/scripts/launch_objective_audit.py --root . --output .tmp/launch-objective-audit-current.json --json`.",
                "Run `python .agents/skills/auto-research/scripts/completion_audit.py .tmp/launch-objective-audit-current.json --json --allow-incomplete`.",
            ],
            expected=["All explicit launch/debug-loop requirements are complete before marking the goal complete."],
            actual=[
                "Completion audit returns "
                f"`status={_display(completion_audit.get('status'))}`, "
                f"`{_display(completion_summary.get('item_count'))}` items, "
                f"`{_display(completion_summary.get('complete_count'))}` complete, "
                f"`{_display(completion_summary.get('issue_count'))}` issues, "
                f"`{_display(completion_summary.get('blocked_count'))}` blocked.",
            ],
            root_cause=(
                "The audit correctly reflects unresolved dirty worktree, publish, selector, T-251, "
                "Hanwoo, and Blind-to-X handoff boundaries."
            ),
            next_action="Do not call `update_goal`; continue only after scoped authorization or external reset changes live state.",
            actionable=False,
            blockers=["Completion audit is incomplete."],
        )
    )

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "root": str(root),
        "objective": (
            "List currently known bugs, anomalies, and blockers for the autonomous reproduce -> isolate -> "
            "root-cause -> fix -> verify loop without guessing or editing product code."
        ),
        "items": items,
        "reproduction_unclear_items": [],
        "summary": {
            "item_count": len(items),
            "actionable_item_count": sum(1 for item in items if item["actionable"]),
            "blocked_item_count": sum(1 for item in items if item["blockers"]),
            "highest_priority": items[0]["title"] if items else None,
        },
    }


def render_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# Debug Loop Known Bugs / Anomalies",
        "",
        f"Generated: {_display(inventory.get('generated_at'))}",
        "",
        f"Objective: {_display(inventory.get('objective'))}",
        "",
    ]
    for raw_item in _as_list(inventory.get("items")):
        item = _as_dict(raw_item)
        lines.extend(
            [
                f"## Priority {_display(item.get('priority'))} - {_display(item.get('title'))}",
                "",
                f"- Status: {_display(item.get('status'))}",
                f"- Severity x frequency: {_display(item.get('severity_x_frequency'))}",
                "- Reproduction:",
            ]
        )
        for step in _as_list(item.get("reproduction")):
            lines.append(f"  - {_display(step)}")
        lines.append("- Expected:")
        for expected in _as_list(item.get("expected")):
            lines.append(f"  - {_display(expected)}")
        lines.append("- Actual:")
        for actual in _as_list(item.get("actual")):
            lines.append(f"  - {_display(actual)}")
        lines.extend(
            [
                "- Root cause:",
                f"  - {_display(item.get('root_cause'))}",
                "- Next action:",
                f"  - {_display(item.get('next_action'))}",
                "",
            ]
        )

    unclear = _as_list(inventory.get("reproduction_unclear_items"))
    lines.extend(["## Reproduction-Unclear Items", ""])
    if unclear:
        for item in unclear:
            lines.append(f"- {_display(item)}")
    else:
        lines.append(
            "- None currently actionable. Items without direct local reproduction are classified above as "
            "authorization-blocked or external/user-owned instead of being patched speculatively."
        )
    lines.append("")
    return "\n".join(lines)


def collect_inputs(root: Path, timeout: int) -> dict[str, dict[str, Any]]:
    launch_audit = root / DEFAULT_LAUNCH_AUDIT
    return {
        "session_orient": _run_json(root, [sys.executable, "execution/session_orient.py", "--json"], timeout),
        "selector": _run_json(
            root,
            [
                sys.executable,
                ".agents/skills/auto-research/scripts/next_experiment_selector.py",
                "--root",
                ".",
                "--dirty-handoff-plan",
                str(DEFAULT_DIRTY_HANDOFF_PLAN),
                "--json",
            ],
            timeout,
        ),
        "readiness": _run_json(root, [sys.executable, "execution/product_readiness_score.py", "--json"], timeout),
        "completion_audit": _run_json(
            root,
            [
                sys.executable,
                ".agents/skills/auto-research/scripts/completion_audit.py",
                str(launch_audit),
                "--json",
                "--allow-incomplete",
            ],
            timeout,
        )
        if launch_audit.exists()
        else {},
        "dirty_handoff_plan": _load_json(root / DEFAULT_DIRTY_HANDOFF_PLAN),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Workspace root")
    parser.add_argument("--session-orient", type=Path, help="Existing session orientation JSON")
    parser.add_argument("--selector", type=Path, help="Existing next-experiment selector JSON")
    parser.add_argument("--readiness", type=Path, help="Existing product readiness JSON")
    parser.add_argument("--completion-audit", type=Path, help="Existing completion audit result JSON")
    parser.add_argument("--dirty-handoff-plan", type=Path, help="Existing dirty handoff plan JSON")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD, help="Markdown inventory output")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON, help="JSON inventory output")
    parser.add_argument("--timeout", type=int, default=60, help="Per-helper timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print JSON inventory to stdout")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    inputs = collect_inputs(root, args.timeout)
    if args.session_orient:
        inputs["session_orient"] = _load_json(_resolve(root, args.session_orient))
    if args.selector:
        inputs["selector"] = _load_json(_resolve(root, args.selector))
    if args.readiness:
        inputs["readiness"] = _load_json(_resolve(root, args.readiness))
    if args.completion_audit:
        inputs["completion_audit"] = _load_json(_resolve(root, args.completion_audit))
    if args.dirty_handoff_plan:
        inputs["dirty_handoff_plan"] = _load_json(_resolve(root, args.dirty_handoff_plan))

    inventory = build_inventory(root=root, **inputs)
    output_md = _resolve(root, args.output_md) or root / DEFAULT_OUTPUT_MD
    output_json = _resolve(root, args.output_json) or root / DEFAULT_OUTPUT_JSON
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(inventory), encoding="utf-8")
    _write_json(output_json, inventory)

    if args.json:
        json.dump(inventory, sys.stdout, ensure_ascii=True, indent=2)
        print()
    else:
        print("status: generated")
        print(f"markdown: {output_md}")
        print(f"json: {output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
