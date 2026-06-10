#!/usr/bin/env python3
"""Generate a deterministic scoped handoff plan for a dirty worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_JSON_PATH = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.json")
DEFAULT_MARKDOWN_PATH = Path(".tmp/scoped-dirty-worktree-handoff-plan-current.md")
GITHUB_INVENTORY_GATE = (
    "python .agents/skills/auto-research/scripts/github_project_inventory.py --root . --include-prs --json"
)
SESSION_ORIENT_GATE = "python execution/session_orient.py --json"
PRODUCT_READINESS_GATE = "python execution/product_readiness_score.py --json"
CODE_REVIEW_GATE = "python execution/code_review_gate.py --base HEAD --json"

SOURCE_REFERENCES = [
    {
        "label": "Git status porcelain format",
        "url": "https://git-scm.com/docs/git-status",
        "note": "Use stable porcelain status data for script-facing worktree state.",
    },
    {
        "label": "Git ls-files standard excludes",
        "url": "https://git-scm.com/docs/git-ls-files",
        "note": "Use standard exclude rules for untracked-file evidence.",
    },
]

GROUP_ORDER = [
    "auto-research",
    "workspace-code-review-gate",
    "llm-wiki",
    "workspace-dashboard",
    "project:blind-to-x",
    "project:hanwoo-dashboard",
    "ai-context",
]

GROUP_RULES: dict[str, dict[str, Any]] = {
    "auto-research": {
        "label": "auto-research tooling",
        "commit_shape": "One tooling commit for selector, inventory, release, and gate hardening.",
        "pre_stage_gates": [
            "python -m pytest workspace/tests/test_auto_research_next_experiment_selector.py workspace/tests/test_github_project_inventory.py workspace/tests/test_code_review_gate.py",
            "python execution/code_review_gate.py --base HEAD --json",
        ],
    },
    "workspace-code-review-gate": {
        "label": "workspace code-review gate",
        "commit_shape": "Keep with auto-research tooling unless the diff is independently reviewable.",
        "pre_stage_gates": [
            "python -m pytest workspace/tests/test_code_review_gate.py",
            "python execution/code_review_gate.py --base HEAD --json",
        ],
    },
    "llm-wiki": {
        "label": "LLM Wiki docs and audits",
        "commit_shape": "One docs/audit commit after reviewing untracked manifests and helper files together.",
        "pre_stage_gates": [
            "python -m pytest workspace/tests/test_llm_wiki_audit.py workspace/tests/test_auto_research_llm_wiki_release_summary.py",
            "python execution/llm_wiki_audit.py --json",
            "python execution/llm_wiki_audit.py --write-strict-release-evidence --json",
        ],
    },
    "workspace-dashboard": {
        "label": "workspace Streamlit dashboards",
        "commit_shape": "Prefer page-level commits, not one bulk dashboard commit.",
        "pre_stage_gates": [
            "focused page pytest for the staged page group",
            "fresh browser QA for the staged page group when possible",
        ],
    },
    "project:blind-to-x": {
        "label": "Blind-to-X project",
        "commit_shape": "One publish/readiness repair commit if all dirty paths belong to the same flow.",
        "pre_stage_gates": [
            "focused Blind-to-X process-stage/publish-repair tests",
            "project QC if time allows",
        ],
    },
    "project:hanwoo-dashboard": {
        "label": "Hanwoo package metadata",
        "commit_shape": "Dependency/package-only commit; keep T-251 separate.",
        "pre_stage_gates": [
            "Hanwoo package/version smoke",
            "npm.cmd run lint or project QC",
            "do not rerun live Prisma T-251 until credentials are reset",
        ],
    },
    "ai-context": {
        "label": "AI shared context",
        "commit_shape": "Final relay/context commit after code/documentation groups, or leave handoff-only.",
        "pre_stage_gates": [
            "python execution/handoff_rotator.py",
            "python execution/tasks_done_rotator.py",
            "python execution/session_orient.py --json",
        ],
    },
}


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


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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
        return {
            "available": False,
            "returncode": None,
            "stderr": str(exc),
            "data": {},
        }
    stdout = completed.stdout.strip()
    data: dict[str, Any] = {}
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            data = {"_parse_error": str(exc), "_raw_stdout": stdout[:4000]}
        else:
            data = parsed if isinstance(parsed, dict) else {"_json_root_type": type(parsed).__name__}
    return {
        "available": True,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
        "stdout": stdout,
        "data": data,
    }


def _run_data(root: Path, args: list[str], timeout: int) -> dict[str, Any]:
    return _as_dict(_run_json(root, args, timeout).get("data"))


def _normalize_path(path: Any) -> str:
    return str(path).replace("\\", "/").strip()


def _dirty_groups(github_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    groups = []
    for raw in _as_list(_as_dict(github_inventory.get("git")).get("dirty_path_groups")):
        group = _as_dict(raw)
        key = _display(group.get("key"))
        if key == "unknown":
            continue
        paths = sorted(_normalize_path(path) for path in _as_list(group.get("paths")) if _normalize_path(path))
        groups.append(
            {
                "key": key,
                "owner_hint": _display(group.get("owner_hint")),
                "path_count": _int(group.get("path_count")),
                "paths": paths,
                "sample_truncated": group.get("sample_truncated") is True,
            }
        )
    return sorted(
        groups, key=lambda item: (GROUP_ORDER.index(item["key"]) if item["key"] in GROUP_ORDER else 999, item["key"])
    )


def _dirty_paths(github_inventory: dict[str, Any], groups: list[dict[str, Any]]) -> list[str]:
    git = _as_dict(github_inventory.get("git"))
    paths = [_normalize_path(path) for path in _as_list(git.get("dirty_paths")) if _normalize_path(path)]
    if paths:
        return sorted(set(paths))
    sampled = []
    for group in groups:
        sampled.extend(group["paths"])
    return sorted(set(sampled))


def dirty_signature(github_inventory: dict[str, Any], session_orient: dict[str, Any]) -> dict[str, Any]:
    git = _as_dict(github_inventory.get("git"))
    session_git = _as_dict(session_orient.get("git"))
    worktree = _as_dict(session_git.get("worktree"))
    groups = _dirty_groups(github_inventory)
    payload = {
        "branch": session_git.get("branch") or git.get("branch"),
        "ahead": _int(session_git.get("ahead")),
        "behind": _int(session_git.get("behind")),
        "staged": _int(worktree.get("staged")),
        "dirty_count": _int(git.get("dirty_count")),
        "dirty_paths": _dirty_paths(github_inventory, groups),
        "dirty_path_groups": groups,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return {
        "algorithm": "sha256",
        "value": hashlib.sha256(encoded).hexdigest(),
        "input": payload,
    }


def _previous_plan_freshness(current_signature: dict[str, Any], previous_plan: dict[str, Any]) -> dict[str, Any]:
    previous_signature = _as_dict(previous_plan.get("dirty_signature"))
    previous_value = previous_signature.get("value")
    if not previous_value:
        return {
            "status": "missing_previous_json",
            "current": False,
            "reason": "No previous machine-readable dirty handoff plan was available.",
        }
    current_value = current_signature.get("value")
    if previous_value == current_value:
        return {
            "status": "current",
            "current": True,
            "previous_generated_at": previous_plan.get("generated_at"),
            "reason": "Previous plan dirty signature matches the current dirty group signature.",
        }
    return {
        "status": "stale",
        "current": False,
        "previous_generated_at": previous_plan.get("generated_at"),
        "previous_signature": previous_value,
        "reason": "Previous plan dirty signature differs from the current dirty group signature.",
    }


def _current_plan_freshness(previous_freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "current",
        "current": True,
        "reason": "Generated plan dirty signature represents the current dirty group signature.",
        "previous_status": previous_freshness.get("status"),
        "previous_current": previous_freshness.get("current"),
    }


def _group_plan(group: dict[str, Any], order: int) -> dict[str, Any]:
    key = group["key"]
    rule = GROUP_RULES.get(key, {})
    return {
        "order": order,
        "key": key,
        "label": rule.get("label", key),
        "owner_hint": group.get("owner_hint", "workspace"),
        "path_count": group.get("path_count", 0),
        "paths": group.get("paths", []),
        "sample_truncated": group.get("sample_truncated") is True,
        "commit_shape": rule.get("commit_shape", f"One scoped commit for {key} after direct diff review."),
        "pre_stage_gates": rule.get(
            "pre_stage_gates",
            ["focused tests for touched files", "git diff --check", "python execution/session_orient.py --json"],
        ),
    }


def _build_group_order(github_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    groups = _dirty_groups(github_inventory)
    return [_group_plan(group, index + 1) for index, group in enumerate(groups)]


def _summarize_code_review_gate(code_review_gate: dict[str, Any]) -> dict[str, Any]:
    if not code_review_gate:
        return {"available": False}
    findings = _as_list(code_review_gate.get("findings"))
    test_gaps = _as_list(code_review_gate.get("test_gaps"))
    untracked_files = _as_list(code_review_gate.get("untracked_files"))
    reasons = _as_list(code_review_gate.get("reasons"))
    return {
        "available": True,
        "status": code_review_gate.get("status"),
        "risk_score": code_review_gate.get("risk_score"),
        "finding_count": len(findings),
        "test_gap_count": len(test_gaps),
        "untracked_graph_relevant_file_count": len(untracked_files),
        "reasons": [_display(reason) for reason in reasons],
    }


def _session_dirty_count(session_orient: dict[str, Any]) -> int:
    session_git = _as_dict(session_orient.get("git"))
    worktree = _as_dict(session_git.get("worktree"))
    return _int(worktree.get("staged")) + _int(worktree.get("modified")) + _int(worktree.get("untracked"))


def _state_consistency(inventory_dirty_count: int, session_dirty_count: int) -> dict[str, Any]:
    warnings = []
    if session_dirty_count and not inventory_dirty_count:
        warnings.append("session_orient reports dirty worktree while github inventory reports clean")
    if inventory_dirty_count and not session_dirty_count:
        warnings.append("github inventory reports dirty worktree while session_orient reports clean")
    return {
        "inventory_dirty_count": inventory_dirty_count,
        "session_dirty_count": session_dirty_count,
        "effective_dirty_count": max(inventory_dirty_count, session_dirty_count),
        "warnings": warnings,
    }


def _state_consistency_warning_text(consistency: dict[str, Any]) -> str:
    warnings = ", ".join(_display(warning) for warning in _as_list(consistency.get("warnings")))
    return warnings or "none"


def build_plan(
    *,
    root: Path,
    github_inventory: dict[str, Any],
    session_orient: dict[str, Any],
    readiness: dict[str, Any],
    code_review_gate: dict[str, Any],
    previous_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    signature = dirty_signature(github_inventory, session_orient)
    git = _as_dict(github_inventory.get("git"))
    session_git = _as_dict(session_orient.get("git"))
    worktree = _as_dict(session_git.get("worktree"))
    open_prs = _as_dict(github_inventory.get("open_prs"))
    readiness_overall = _as_dict(readiness.get("overall"))
    inventory_dirty_count = _int(git.get("dirty_count"))
    session_dirty_count = _session_dirty_count(session_orient)
    consistency = _state_consistency(inventory_dirty_count, session_dirty_count)
    dirty_count = _int(consistency.get("effective_dirty_count"))
    group_order = _build_group_order(github_inventory)
    status = "clean" if dirty_count == 0 else "handoff_required"
    previous_freshness = _previous_plan_freshness(signature, previous_plan or {})
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "status": status,
        "dirty_signature": signature,
        "freshness": _current_plan_freshness(previous_freshness),
        "previous_plan_freshness": previous_freshness,
        "decision": {
            "mode": "none" if dirty_count == 0 else "handoff_only",
            "stage_commit_push_authorized": False,
            "summary": (
                "Worktree is clean; no dirty handoff plan is required."
                if dirty_count == 0
                else "Do not stage, commit, push, or revert automatically; use this scoped order as handoff evidence."
            ),
        },
        "inputs": {
            "session_orient": {
                "branch": session_git.get("branch"),
                "ahead": _int(session_git.get("ahead")),
                "behind": _int(session_git.get("behind")),
                "staged": _int(worktree.get("staged")),
                "modified": _int(worktree.get("modified")),
                "untracked": _int(worktree.get("untracked")),
                "open_prs": _int(_as_dict(session_orient.get("pull_requests")).get("open_count")),
            },
            "github_inventory": {
                "dirty_count": inventory_dirty_count,
                "open_prs_available": open_prs.get("available") is True,
                "open_pr_count": _int(open_prs.get("count")),
                "dirty_group_count": len(group_order),
            },
            "state_consistency": consistency,
            "product_readiness": {
                "score": readiness_overall.get("score"),
                "state": readiness_overall.get("state"),
                "local_blocker_count": _int(readiness_overall.get("local_blocker_count")),
                "publish_blocker_count": _int(readiness_overall.get("publish_blocker_count")),
                "external_blocker_count": _int(readiness_overall.get("external_blocker_count")),
            },
            "code_review_gate": _summarize_code_review_gate(code_review_gate),
        },
        "ab_comparison": [
            {
                "option": "A",
                "approach": "Human-readable Markdown handoff only",
                "strengths": "Fast to write and easy to scan.",
                "costs": "No stable dirty signature, so the selector cannot tell whether the plan still matches the worktree.",
                "decision": "reject",
            },
            {
                "option": "B",
                "approach": "Deterministic JSON plus Markdown handoff",
                "strengths": "Machine-readable signature, freshness status, repeatable group order, and human summary.",
                "costs": "Requires a small helper and focused tests.",
                "decision": "adopt",
            },
        ],
        "group_order": group_order,
        "handoff_only_boundaries": [
            "T-251 is user-owned; do not retry live Prisma until Supabase credentials are reset.",
            "No push is authorized.",
            "Current-head GitHub Actions cannot be proven locally while the branch is ahead of origin.",
            "Future UX work before committing should stay in one untouched page/module with immediate browser evidence.",
        ],
        "required_gates": [
            GITHUB_INVENTORY_GATE,
            SESSION_ORIENT_GATE,
            PRODUCT_READINESS_GATE,
            CODE_REVIEW_GATE,
        ],
        "sources": SOURCE_REFERENCES,
    }


def render_markdown(plan: dict[str, Any]) -> str:
    signature = _as_dict(plan.get("dirty_signature"))
    inputs = _as_dict(plan.get("inputs"))
    lines = [
        "# Scoped Dirty Worktree Handoff Plan",
        "",
        f"Generated: {_display(plan.get('generated_at'))}",
        f"Status: {_display(plan.get('status'))}",
        f"Dirty signature: `{_display(signature.get('value'))}`",
        f"Freshness: {_display(_as_dict(plan.get('freshness')).get('status'))}",
        f"Previous plan freshness: {_display(_as_dict(plan.get('previous_plan_freshness')).get('status'))}",
        "",
        "## Decision",
        "",
        _display(_as_dict(plan.get("decision")).get("summary")),
        "",
        "## A/B Decision",
        "",
        "| Option | Approach | Strengths | Costs | Decision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in _as_list(plan.get("ab_comparison")):
        row = _as_dict(item)
        lines.append(
            "| "
            + " | ".join(
                [
                    _display(row.get("option")),
                    _display(row.get("approach")),
                    _display(row.get("strengths")),
                    _display(row.get("costs")),
                    _display(row.get("decision")),
                ]
            )
            + " |"
        )
    session = _as_dict(inputs.get("session_orient"))
    github = _as_dict(inputs.get("github_inventory"))
    readiness = _as_dict(inputs.get("product_readiness"))
    gate = _as_dict(inputs.get("code_review_gate"))
    consistency = _as_dict(inputs.get("state_consistency"))
    lines.extend(
        [
            "",
            "## Inputs",
            "",
            f"- Session: branch `{_display(session.get('branch'))}`, ahead `{_display(session.get('ahead'))}`, staged `{_display(session.get('staged'))}`, modified `{_display(session.get('modified'))}`, untracked `{_display(session.get('untracked'))}`, open PRs `{_display(session.get('open_prs'))}`.",
            f"- GitHub inventory: dirty `{_display(github.get('dirty_count'))}`, open PRs `{_display(github.get('open_pr_count'))}`, dirty groups `{_display(github.get('dirty_group_count'))}`.",
            f"- State consistency: effective dirty `{_display(consistency.get('effective_dirty_count'))}`, warnings `{_state_consistency_warning_text(consistency)}`.",
            f"- Product readiness: score `{_display(readiness.get('score'))}`, state `{_display(readiness.get('state'))}`, local blockers `{_display(readiness.get('local_blocker_count'))}`, publish blockers `{_display(readiness.get('publish_blocker_count'))}`, external blockers `{_display(readiness.get('external_blocker_count'))}`.",
            f"- Code-review gate: status `{_display(gate.get('status'))}`, risk `{_display(gate.get('risk_score'))}`, findings `{_display(gate.get('finding_count'))}`, test gaps `{_display(gate.get('test_gap_count'))}`, untracked graph-relevant files `{_display(gate.get('untracked_graph_relevant_file_count'))}`.",
            "",
            "## Group Order",
            "",
        ]
    )
    for group in _as_list(plan.get("group_order")):
        item = _as_dict(group)
        lines.extend(
            [
                f"{_display(item.get('order'))}. `{_display(item.get('key'))}` - {_display(item.get('label'))}",
                f"   - Owner hint: {_display(item.get('owner_hint'))}",
                f"   - Path count: {_display(item.get('path_count'))}",
                f"   - Commit shape: {_display(item.get('commit_shape'))}",
                "   - Pre-stage gates: " + "; ".join(_display(gate) for gate in _as_list(item.get("pre_stage_gates"))),
            ]
        )
        paths = _as_list(item.get("paths"))
        if paths:
            lines.append("   - Path sample: " + ", ".join(f"`{_display(path)}`" for path in paths[:5]))
        if item.get("sample_truncated") is True:
            lines.append("   - Path sample is truncated; inspect the full JSON before staging.")
    lines.extend(["", "## Handoff-Only Boundaries", ""])
    for boundary in _as_list(plan.get("handoff_only_boundaries")):
        lines.append(f"- {_display(boundary)}")
    lines.extend(["", "## Sources", ""])
    for source in _as_list(plan.get("sources")):
        item = _as_dict(source)
        lines.append(f"- {_display(item.get('label'))}: {_display(item.get('url'))} - {_display(item.get('note'))}")
    return "\n".join(lines).rstrip() + "\n"


def _collect_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = args.root.resolve()
    github_path = _resolve(root, args.github_inventory)
    session_path = _resolve(root, args.session_orient)
    readiness_path = _resolve(root, args.readiness)
    gate_path = _resolve(root, args.code_review_gate)

    github_inventory = _load_json(github_path) if github_path else {}
    if not github_inventory:
        github_inventory = _run_data(
            root,
            [
                sys.executable,
                str(Path(".agents") / "skills" / "auto-research" / "scripts" / "github_project_inventory.py"),
                "--root",
                str(root),
                "--include-prs",
                "--json",
            ],
            args.timeout,
        )
    session_orient = _load_json(session_path) if session_path else {}
    if not session_orient:
        session_orient = _run_data(root, [sys.executable, "execution/session_orient.py", "--json"], args.timeout)
    readiness = _load_json(readiness_path) if readiness_path else {}
    if not readiness:
        readiness = _run_data(root, [sys.executable, "execution/product_readiness_score.py", "--json"], args.timeout)
    code_review_gate = _load_json(gate_path) if gate_path else {}
    if not code_review_gate:
        code_review_gate = _run_data(
            root, [sys.executable, "execution/code_review_gate.py", "--base", "HEAD", "--json"], args.timeout
        )
    return github_inventory, session_orient, readiness, code_review_gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--github-inventory", type=Path, help="Existing github_project_inventory JSON artifact")
    parser.add_argument("--session-orient", type=Path, help="Existing session_orient JSON artifact")
    parser.add_argument("--readiness", type=Path, help="Existing product_readiness_score JSON artifact")
    parser.add_argument("--code-review-gate", type=Path, help="Existing code_review_gate JSON artifact")
    parser.add_argument("--previous-json", type=Path, help="Previous dirty handoff plan JSON for freshness comparison")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON_PATH, help="Path to write plan JSON")
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN_PATH, help="Path to write plan Markdown")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for each live helper command")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output_json = _resolve(root, args.output_json) or root / DEFAULT_JSON_PATH
    output_md = _resolve(root, args.output_md) or root / DEFAULT_MARKDOWN_PATH
    previous_path = _resolve(root, args.previous_json) if args.previous_json else output_json
    previous_plan = _load_json(previous_path)

    github_inventory, session_orient, readiness, code_review_gate = _collect_inputs(args)
    plan = build_plan(
        root=root,
        github_inventory=github_inventory,
        session_orient=session_orient,
        readiness=readiness,
        code_review_gate=code_review_gate,
        previous_plan=previous_plan,
    )
    _write_json(output_json, plan)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(plan), encoding="utf-8")

    if args.json:
        json.dump(plan, sys.stdout, ensure_ascii=True, indent=2)
        print()
    else:
        print(f"dirty handoff plan: {plan['status']}")
        print(f"json: {_rel(root, output_json)}")
        print(f"markdown: {_rel(root, output_md)}")
        print(f"signature: {plan['dirty_signature']['value']}")
        print(f"freshness: {plan['freshness']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
