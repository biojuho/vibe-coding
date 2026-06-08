"""Unit tests for the auto-research debug-loop inventory helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "debug_loop_inventory.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("debug_loop_inventory", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["debug_loop_inventory"] = module
    spec.loader.exec_module(module)
    return module


debug_loop_inventory = _load_module()


def _session() -> dict[str, object]:
    return {
        "git": {
            "branch": "main",
            "ahead": 833,
            "behind": 0,
            "worktree": {"staged": 0, "modified": 45, "untracked": 26},
        }
    }


def _selector() -> dict[str, object]:
    return {
        "status": "blocked",
        "selected": {"kind": "dirty_worktree_handoff_current"},
        "summary": {"adoptable_candidate_count": 0, "selected_kind": "dirty_worktree_handoff_current"},
    }


def _readiness() -> dict[str, object]:
    return {
        "overall": {
            "score": 94,
            "state": "blocked",
            "external_blocker_count": 1,
        },
        "workspace_gates": {
            "worktree": {"dirty_count": 71},
            "github_release": {
                "required_workflows": [
                    {"name": "root-quality-gate", "status": "missing", "conclusion": None},
                    {"name": "active-project-matrix", "status": "missing", "conclusion": None},
                ]
            },
        },
        "projects": [
            {
                "name": "hanwoo-dashboard",
                "score": 82,
                "state": "blocked",
                "tasks": [{"id": "T-251", "owner": "User"}],
                "dirty_paths": ["projects/hanwoo-dashboard/package.json"],
            },
            {
                "name": "blind-to-x",
                "score": 92,
                "state": "ready",
                "dirty_paths": [
                    "projects/blind-to-x/pipeline/process_stages/generate_review_stage.py",
                    "projects/blind-to-x/pipeline/publish_repair.py",
                ],
            },
        ],
    }


def _completion() -> dict[str, object]:
    return {
        "status": "incomplete",
        "summary": {"item_count": 15, "complete_count": 8, "issue_count": 11, "blocked_count": 7},
    }


def _handoff_plan() -> dict[str, object]:
    return {
        "status": "handoff_required",
        "freshness": {"status": "current", "current": True},
        "dirty_signature": {
            "value": "fresh-signature",
            "input": {"dirty_count": 71, "dirty_paths": [".ai/HANDOFF.md"]},
        },
        "group_order": [
            {"key": "auto-research", "path_count": 7},
            {"key": "project:blind-to-x", "path_count": 2},
        ],
    }


def test_build_inventory_uses_current_dirty_handoff_values(tmp_path: Path) -> None:
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)

    assert inventory["summary"]["item_count"] == 5
    assert inventory["summary"]["actionable_item_count"] == 0
    assert inventory["items"][0]["title"] == "Dirty Handoff Boundary Blocks New Product Edits"
    assert "`71`" in "\n".join(inventory["items"][0]["actual"])
    assert "fresh-signature" in markdown
    assert "dirty count `70`" not in markdown
    assert "T-251" in markdown
    assert "15` items" in markdown


def test_cli_writes_markdown_and_json_from_artifacts(tmp_path: Path) -> None:
    inputs = {
        "session.json": _session(),
        "selector.json": _selector(),
        "readiness.json": _readiness(),
        "completion.json": _completion(),
        "handoff.json": _handoff_plan(),
    }
    for name, payload in inputs.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    output_md = tmp_path / ".tmp" / "debug-loop-known-bugs-current.md"
    output_json = tmp_path / ".tmp" / "debug-loop-known-bugs-current.json"

    code = debug_loop_inventory.main(
        [
            "--root",
            str(tmp_path),
            "--session-orient",
            str(tmp_path / "session.json"),
            "--selector",
            str(tmp_path / "selector.json"),
            "--readiness",
            str(tmp_path / "readiness.json"),
            "--completion-audit",
            str(tmp_path / "completion.json"),
            "--dirty-handoff-plan",
            str(tmp_path / "handoff.json"),
            "--output-md",
            str(output_md),
            "--output-json",
            str(output_json),
            "--json",
        ]
    )

    assert code == 0
    assert output_md.exists()
    assert output_json.exists()
    assert "Debug Loop Known Bugs" in output_md.read_text(encoding="utf-8")
    assert json.loads(output_json.read_text(encoding="utf-8"))["summary"]["blocked_item_count"] == 5


def test_collect_inputs_pins_selector_to_dirty_handoff_plan(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        calls.append(args)
        return {}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)
    monkeypatch.setattr(debug_loop_inventory, "_load_json", lambda path: {})

    debug_loop_inventory.collect_inputs(tmp_path, timeout=30)

    selector_call = next(call for call in calls if any("next_experiment_selector.py" in part for part in call))
    assert "--dirty-handoff-plan" in selector_call
    plan_index = selector_call.index("--dirty-handoff-plan") + 1
    assert Path(selector_call[plan_index]).as_posix() == ".tmp/scoped-dirty-worktree-handoff-plan-current.json"
