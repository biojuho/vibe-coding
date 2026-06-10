"""Unit tests for the auto-research debug-loop inventory helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


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


def _session_with_stale_graph() -> dict[str, object]:
    session = json.loads(json.dumps(_session()))
    session["graph"] = {
        "available": True,
        "freshness": "stale",
        "stale": True,
        "built_at_commit": "old-head",
        "current_head": "new-head",
        "stale_reason": "built_at_commit old-head != current_head new-head",
    }
    return session


def _session_with_fresh_graph() -> dict[str, object]:
    session = json.loads(json.dumps(_session()))
    session["graph"] = {
        "available": True,
        "freshness": "current",
        "stale": False,
        "built_at_commit": "current-head",
        "current_head": "current-head",
    }
    return session


def _selector() -> dict[str, object]:
    return {
        "status": "blocked",
        "selected": {
            "kind": "dirty_worktree_handoff_current",
            "gate_expectations": [
                {
                    "gate": (
                        "python .agents/skills/auto-research/scripts/debug_loop_inventory.py "
                        "--fail-on-completion-blocked"
                    ),
                    "expected_exit_codes": [1],
                    "meaning": "Completion remains blocked; not a source failure.",
                }
            ],
        },
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


def _stale_accepted_handoff_plan() -> dict[str, object]:
    plan = json.loads(json.dumps(_handoff_plan()))
    plan["freshness"] = {
        "status": "stale",
        "current": False,
        "reason": "previous dirty signature differs from refreshed inventory",
    }
    plan["dirty_signature"]["value"] = "accepted-current-signature"
    return plan


def _clean_publish_session() -> dict[str, object]:
    return {
        "git": {
            "branch": "main",
            "ahead": 856,
            "behind": 0,
            "worktree": {"staged": 0, "modified": 0, "untracked": 0},
        }
    }


def _publish_selector() -> dict[str, object]:
    return {
        "status": "blocked_publish_only",
        "selected": {"kind": "current_head_release_checks_unproven"},
        "summary": {"adoptable_candidate_count": 0, "selected_kind": "current_head_release_checks_unproven"},
    }


def _clean_publish_readiness() -> dict[str, object]:
    readiness = json.loads(json.dumps(_readiness()))
    readiness["overall"]["score"] = 96
    readiness["overall"]["external_blocker_count"] = 1
    readiness["workspace_gates"]["worktree"]["dirty_count"] = 0
    readiness["projects"][1]["score"] = 100
    readiness["projects"][1]["dirty_paths"] = []
    return readiness


def _clean_handoff_plan() -> dict[str, object]:
    return {
        "status": "clean",
        "freshness": {"status": "current", "current": True},
        "dirty_signature": {
            "value": "clean-signature",
            "input": {"dirty_count": 0, "dirty_paths": []},
        },
        "group_order": [],
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
    assert inventory["summary"]["completion_gate"] == "blocked"
    assert inventory["summary"]["completion_allowed"] is False
    assert (
        inventory["summary"]["next_required_action"]
        == "Wait for explicit scoped staging/commit authorization, or keep handoff-only evidence current."
    )
    expected_gate = inventory["summary"]["expected_failure_gates"][0]
    assert expected_gate["expected_exit_codes"] == [1]
    assert "not a source failure" in expected_gate["meaning"]
    blocker_titles = [blocker["title"] for blocker in inventory["summary"]["completion_blockers"]]
    assert blocker_titles == [
        "Dirty Handoff Boundary Blocks New Product Edits",
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
        "Current-HEAD GitHub Actions Cannot Be Proven Locally",
        "Blind-to-X Is Ready But Not Launch-Complete Because Dirty Paths Remain",
        "Launch Completion Audit Remains Incomplete",
    ]
    assert inventory["items"][0]["title"] == "Dirty Handoff Boundary Blocks New Product Edits"
    assert "`71`" in "\n".join(inventory["items"][0]["actual"])
    assert "fresh-signature" in markdown
    assert "## Summary" in markdown
    assert "- Items: 5" in markdown
    assert "- Actionable: 0" in markdown
    assert "- Blocked: 5" in markdown
    assert "- Reproduction unclear: 0" in markdown
    assert "- Completion gate: blocked" in markdown
    assert "- Completion allowed: false" in markdown
    assert "- Next required action: Wait for explicit scoped staging/commit authorization" in markdown
    assert "- Completion blockers:" in markdown
    assert (
        "Dirty Handoff Boundary Blocks New Product Edits: "
        "Wait for explicit scoped staging/commit authorization, or keep handoff-only evidence current."
    ) in markdown
    assert "- Expected nonzero gates:" in markdown
    assert "expects exit code(s) `1`" in markdown
    assert "not a source failure" in markdown
    assert "Launch Completion Audit Remains Incomplete: Do not call `update_goal`" in markdown
    assert "> [!IMPORTANT]" in markdown
    assert "> Debug loop is blocked; do not claim launch completion until blockers are cleared." in markdown
    assert "> Highest priority: Dirty Handoff Boundary Blocks New Product Edits." in markdown
    assert "- Actionable: false" in markdown
    assert "- Blockers:" in markdown
    assert "Explicit scoped staging/commit authorization is required before product changes." in markdown
    assert "Current handoff plan freshness is `current`" in markdown
    assert "previous-signature freshness is `current`" not in markdown
    assert "dirty count `70`" not in markdown
    assert "T-251" in markdown
    assert "15` items" in markdown


def test_build_inventory_surfaces_session_graph_freshness(tmp_path: Path) -> None:
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session_with_stale_graph(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)

    evidence = inventory["summary"]["evidence_freshness"][0]
    assert evidence["source"] == "code_review_graph"
    assert evidence["freshness"] == "stale"
    assert evidence["stale"] is True
    assert evidence["built_at_commit"] == "old-head"
    assert evidence["current_head"] == "new-head"
    assert "old-head != current_head new-head" in evidence["stale_reason"]
    assert inventory["summary"]["completion_gate"] == "blocked"
    assert inventory["summary"]["blocked_item_count"] == 5
    assert inventory["summary"]["actionable_item_count"] == 1
    assert inventory["summary"]["item_count"] == 6
    assert inventory["items"][1]["title"] == "Code Review Graph Evidence Is Stale"
    assert inventory["items"][1]["actionable"] is True
    assert inventory["items"][1]["blockers"] == []
    assert "code_review_graph update" in inventory["items"][1]["next_action"]
    assert "- Evidence freshness:" in markdown
    assert "code_review_graph" in markdown
    assert "freshness `stale`" in markdown
    assert "built_at_commit `old-head`" in markdown
    assert "current_head `new-head`" in markdown
    assert "old-head != current_head new-head" in markdown
    assert "## Priority 2 - Code Review Graph Evidence Is Stale" in markdown
    assert "- Actionable: true" in markdown
    assert "- Blockers: none" in markdown
    assert "Stale reason: `built_at_commit old-head != current_head new-head`" in markdown


def test_build_inventory_does_not_report_current_session_graph_as_anomaly(tmp_path: Path) -> None:
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session_with_fresh_graph(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)

    titles = [item["title"] for item in inventory["items"]]
    assert "Code Review Graph Evidence Is Stale" not in titles
    assert inventory["summary"]["item_count"] == 5
    assert inventory["summary"]["actionable_item_count"] == 0
    assert "- Evidence freshness:" in markdown
    assert "freshness `current`" in markdown
    assert "Code Review Graph Evidence Is Stale" not in markdown


def test_build_inventory_disambiguates_stale_freshness_when_selector_accepts_current_dirty_plan(
    tmp_path: Path,
) -> None:
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_stale_accepted_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)

    assert "previous-signature freshness is `stale`" in markdown
    assert "accepted by selector as matching the current dirty inventory" in markdown
    assert "Current handoff plan is `stale`" not in markdown


def test_build_inventory_reports_publish_boundary_when_worktree_is_clean(tmp_path: Path) -> None:
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_clean_publish_session(),
        selector=_publish_selector(),
        readiness=_clean_publish_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_clean_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)
    titles = [item["title"] for item in inventory["items"]]
    blockers = "\n".join(blocker for item in inventory["items"] for blocker in item["blockers"])

    assert titles[0] == "Current-HEAD GitHub Actions Cannot Be Proven Locally"
    assert "Dirty Handoff Boundary Blocks New Product Edits" not in titles
    assert "Blind-to-X Is Ready But Not Launch-Complete Because Dirty Paths Remain" not in titles
    assert "Explicit scoped staging/commit authorization" not in blockers
    assert "branch ahead `856`" in markdown
    assert "current_head_release_checks_unproven" in markdown


def test_build_inventory_ignores_stale_dirty_plan_count_when_selector_reports_publish_only(
    tmp_path: Path,
) -> None:
    stale_plan = _stale_accepted_handoff_plan()
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_clean_publish_session(),
        selector=_publish_selector(),
        readiness=_clean_publish_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=stale_plan,
    )
    markdown = debug_loop_inventory.render_markdown(inventory)
    titles = [item["title"] for item in inventory["items"]]

    assert titles[0] == "Current-HEAD GitHub Actions Cannot Be Proven Locally"
    assert "Dirty Handoff Boundary Blocks New Product Edits" not in titles
    assert "Current inventory reports dirty count `0`" in markdown
    assert "dirty count `71`" not in markdown


def test_build_inventory_reports_publish_boundary_when_workflows_are_missing(
    tmp_path: Path,
) -> None:
    readiness = json.loads(json.dumps(_readiness()))
    readiness["workspace_gates"]["github_release"]["required_workflows"] = []

    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session(),
        selector=_selector(),
        readiness=readiness,
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)
    titles = [item["title"] for item in inventory["items"]]

    assert "Current-HEAD GitHub Actions Cannot Be Proven Locally" in titles
    assert "Required workflow status: missing/unavailable" in markdown
    assert "Branch `main` is ahead of origin by `833` commits." in markdown


def test_build_inventory_surfaces_helper_input_errors_as_reproduction_unclear(tmp_path: Path) -> None:
    selector = {"_input_error": {"reason": "invalid helper JSON", "returncode": 1, "detail": "bad json"}}
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session(),
        selector=selector,
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    markdown = debug_loop_inventory.render_markdown(inventory)

    assert inventory["items"][0]["title"] == "Debug Inventory Input Evidence Is Unavailable"
    assert inventory["items"][0]["actionable"] is True
    assert inventory["summary"]["reproduction_unclear_count"] == 1
    assert inventory["summary"]["completion_gate"] == "blocked"
    assert inventory["summary"]["completion_allowed"] is False
    assert inventory["summary"]["completion_blockers"][0]["title"] == "Dirty Handoff Boundary Blocks New Product Edits"
    assert inventory["reproduction_unclear_items"] == ["selector: invalid helper JSON; returncode=1; detail=bad json"]
    assert "- Items: 6" in markdown
    assert "- Actionable: 1" in markdown
    assert "- Reproduction unclear: 1" in markdown
    assert "- Completion gate: blocked" in markdown
    assert "- Completion allowed: false" in markdown
    assert "- Completion blockers:" in markdown
    assert "- Actionable: true" in markdown
    assert "- Blockers: none" in markdown
    assert "selector: invalid helper JSON; returncode=1; detail=bad json" in markdown


def test_render_markdown_derives_summary_when_summary_is_missing(tmp_path: Path) -> None:
    inventory = debug_loop_inventory.build_inventory(
        root=tmp_path,
        session_orient=_session(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    inventory.pop("summary")

    markdown = debug_loop_inventory.render_markdown(inventory)

    assert "- Items: 5" in markdown
    assert "- Actionable: 0" in markdown
    assert "- Blocked: 5" in markdown
    assert "- Reproduction unclear: 0" in markdown
    assert "- Completion gate: blocked" in markdown
    assert "- Completion allowed: false" in markdown
    assert "- Next required action: Wait for explicit scoped staging/commit authorization" in markdown
    assert "- Completion blockers:" in markdown
    assert "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker" in markdown
    assert "- Items: unknown" not in markdown
    assert "- Blocked: unknown" not in markdown
    assert "> Highest priority: Dirty Handoff Boundary Blocks New Product Edits." in markdown
    assert "- Expected nonzero gates:" not in markdown

    empty_inventory = {
        "items": [],
        "summary": {
            "expected_failure_gates": [
                {
                    "gate": "debug_inventory_expected_fail",
                    "expected_exit_codes": [1],
                    "meaning": "known nonzero completion-blocked gate",
                }
            ]
        },
    }
    empty_markdown = debug_loop_inventory.render_markdown(empty_inventory)
    assert "- Items: 0" in empty_markdown
    assert "- Actionable: 0" in empty_markdown
    assert "- Blocked: 0" in empty_markdown
    assert "- Reproduction unclear: 0" in empty_markdown
    assert "- Completion gate: clear" in empty_markdown
    assert "- Completion allowed: true" in empty_markdown
    assert "- Next required action: No debug-loop action required." in empty_markdown
    assert "- Items: unknown" not in empty_markdown
    assert "- Next required action: unknown" not in empty_markdown
    assert "- Expected nonzero gates:" in empty_markdown


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
    output_payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert output_payload["summary"]["blocked_item_count"] == 5
    assert output_payload["summary"]["expected_failure_gates"][0]["expected_exit_codes"] == [1]
    assert "- Expected nonzero gates:" in output_md.read_text(encoding="utf-8")


def test_cli_with_full_input_artifacts_does_not_collect_live_inputs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    inputs = {
        "session.json": _session(),
        "selector.json": _selector(),
        "readiness.json": _readiness(),
        "completion.json": _completion(),
        "handoff.json": _handoff_plan(),
    }
    for name, payload in inputs.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    existing_launch_audit = tmp_path / ".tmp" / "launch-objective-audit-current.json"
    existing_launch_audit.parent.mkdir(parents=True, exist_ok=True)
    existing_launch_audit.write_text(json.dumps({"sentinel": True}), encoding="utf-8")
    output_md = tmp_path / ".tmp" / "debug-loop-known-bugs-current.md"
    output_json = tmp_path / ".tmp" / "debug-loop-known-bugs-current.json"

    def fail_collect_inputs(root: Path, timeout: int) -> dict[str, dict[str, object]]:
        raise AssertionError("full artifact mode must not regenerate live inputs")

    monkeypatch.setattr(debug_loop_inventory, "collect_inputs", fail_collect_inputs)

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
        ]
    )

    assert code == 0
    assert json.loads(existing_launch_audit.read_text(encoding="utf-8")) == {"sentinel": True}
    assert json.loads(output_json.read_text(encoding="utf-8"))["summary"]["blocked_item_count"] == 5


def test_inventory_inputs_from_args_loads_complete_artifacts_without_collect(
    monkeypatch,
    tmp_path: Path,
) -> None:
    payloads = {
        "session_orient": {"git": {"branch": "main"}},
        "selector": {"status": "blocked"},
        "readiness": {"overall": {"state": "blocked"}},
        "completion_audit": {"status": "incomplete"},
        "dirty_handoff_plan": {"status": "handoff_required"},
    }
    paths = {key: Path(f"{key}.json") for key in debug_loop_inventory._PROVIDED_INPUT_KEYS}
    for key, path in paths.items():
        (tmp_path / path).write_text(json.dumps(payloads[key]), encoding="utf-8")

    def fail_collect_inputs(root: Path, timeout: int) -> dict[str, dict[str, object]]:
        raise AssertionError("complete artifact input mode must not collect live inputs")

    monkeypatch.setattr(debug_loop_inventory, "collect_inputs", fail_collect_inputs)
    args = SimpleNamespace(timeout=5, **paths)

    assert debug_loop_inventory._inventory_inputs_from_args(tmp_path, args) == payloads


def test_inventory_inputs_from_args_collects_then_overrides_partial_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    selector_path = Path("selector.json")
    (tmp_path / selector_path).write_text(json.dumps({"status": "provided"}), encoding="utf-8")
    collected = {
        "session_orient": {"git": {"branch": "main"}},
        "selector": {"status": "collected"},
        "readiness": {"overall": {"state": "blocked"}},
        "completion_audit": {"status": "incomplete"},
        "dirty_handoff_plan": {"status": "handoff_required"},
    }
    calls: list[tuple[Path, int]] = []

    def fake_collect_inputs(root: Path, timeout: int) -> dict[str, dict[str, object]]:
        calls.append((root, timeout))
        return json.loads(json.dumps(collected))

    monkeypatch.setattr(debug_loop_inventory, "collect_inputs", fake_collect_inputs)
    args = SimpleNamespace(
        timeout=7,
        session_orient=None,
        selector=selector_path,
        readiness=None,
        completion_audit=None,
        dirty_handoff_plan=None,
    )

    inputs = debug_loop_inventory._inventory_inputs_from_args(tmp_path, args)

    assert calls == [(tmp_path, 7)]
    assert inputs["session_orient"] == collected["session_orient"]
    assert inputs["selector"] == {"status": "provided"}
    assert inputs["dirty_handoff_plan"] == collected["dirty_handoff_plan"]


def test_build_inventory_from_args_forwards_root_and_loaded_inputs(monkeypatch, tmp_path: Path) -> None:
    args = SimpleNamespace(timeout=9)
    inputs = {
        "session_orient": {"git": {"branch": "main"}},
        "selector": {"status": "blocked"},
        "readiness": {"overall": {"state": "blocked"}},
        "completion_audit": {"status": "incomplete"},
        "dirty_handoff_plan": {"status": "handoff_required"},
    }
    calls: list[tuple[Path, dict[str, object]]] = []

    def fake_inventory_inputs_from_args(root: Path, received_args: SimpleNamespace) -> dict[str, dict[str, object]]:
        assert root == tmp_path
        assert received_args is args
        return inputs

    def fake_build_inventory(root: Path, **received_inputs: dict[str, object]) -> dict[str, object]:
        calls.append((root, received_inputs))
        return {"summary": {"completion_allowed": False}}

    monkeypatch.setattr(debug_loop_inventory, "_inventory_inputs_from_args", fake_inventory_inputs_from_args)
    monkeypatch.setattr(debug_loop_inventory, "build_inventory", fake_build_inventory)

    inventory = debug_loop_inventory._build_inventory_from_args(tmp_path, args)

    assert inventory == {"summary": {"completion_allowed": False}}
    assert calls == [(tmp_path, inputs)]


def test_cli_fail_on_completion_blocked_returns_one_after_writing_outputs(
    capsys,
    tmp_path: Path,
) -> None:
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
            "--fail-on-completion-blocked",
        ]
    )
    captured = capsys.readouterr()

    assert code == debug_loop_inventory.COMPLETION_BLOCKED_EXIT_CODE
    assert output_md.exists()
    assert output_json.exists()
    assert json.loads(captured.out)["summary"]["completion_allowed"] is False
    assert "completion blocked: blocked" in captured.err
    assert "next_required_action=Wait for explicit scoped staging/commit authorization" in captured.err
    assert "expected_failure_gates=expected_exit_codes=1" in captured.err
    assert "not a source failure" in captured.err


def test_cli_fail_on_completion_blocked_allows_clear_inventory(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    output_md = tmp_path / ".tmp" / "debug-loop-known-bugs-current.md"
    output_json = tmp_path / ".tmp" / "debug-loop-known-bugs-current.json"
    clear_inventory = {
        "schema_version": 1,
        "generated_at": "2026-06-09T00:00:00+00:00",
        "root": str(tmp_path),
        "objective": "test clear inventory",
        "items": [],
        "reproduction_unclear_items": [],
        "summary": {
            "item_count": 0,
            "actionable_item_count": 0,
            "blocked_item_count": 0,
            "reproduction_unclear_count": 0,
            "highest_priority": None,
            "completion_gate": "clear",
            "completion_allowed": True,
            "next_required_action": None,
            "completion_blockers": [],
        },
    }

    monkeypatch.setattr(debug_loop_inventory, "collect_inputs", lambda root, timeout: {})
    monkeypatch.setattr(debug_loop_inventory, "build_inventory", lambda root, **inputs: clear_inventory)

    code = debug_loop_inventory.main(
        [
            "--root",
            str(tmp_path),
            "--output-md",
            str(output_md),
            "--output-json",
            str(output_json),
            "--fail-on-completion-blocked",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    assert "completion blocked" not in captured.err
    assert "status: generated" in captured.out
    assert json.loads(output_json.read_text(encoding="utf-8"))["summary"]["completion_allowed"] is True


def test_collect_inputs_pins_selector_to_dirty_handoff_plan(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        calls.append(args)
        if any("launch_objective_audit.py" in part for part in args):
            launch_audit = tmp_path / ".tmp" / "launch-objective-audit-current.json"
            launch_audit.parent.mkdir(parents=True, exist_ok=True)
            launch_audit.write_text(json.dumps({}), encoding="utf-8")
        if any("dirty_worktree_handoff_plan.py" in part for part in args):
            dirty_plan = tmp_path / Path(args[args.index("--output-json") + 1])
            dirty_plan.parent.mkdir(parents=True, exist_ok=True)
            dirty_plan.write_text(json.dumps({"status": "handoff_required"}), encoding="utf-8")
            dirty_plan_md = tmp_path / Path(args[args.index("--output-md") + 1])
            dirty_plan_md.write_text("handoff", encoding="utf-8")
        return {}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)
    monkeypatch.setattr(debug_loop_inventory, "_load_json", lambda path: {})

    debug_loop_inventory.collect_inputs(tmp_path, timeout=30)

    selector_call = next(call for call in calls if any("next_experiment_selector.py" in part for part in call))
    launch_call_index = next(
        index for index, call in enumerate(calls) if any("launch_objective_audit.py" in part for part in call)
    )
    dirty_plan_call_index = next(
        index for index, call in enumerate(calls) if any("dirty_worktree_handoff_plan.py" in part for part in call)
    )
    selector_call_index = next(
        index for index, call in enumerate(calls) if any("next_experiment_selector.py" in part for part in call)
    )
    completion_call_index = next(
        index for index, call in enumerate(calls) if any("completion_audit.py" in part for part in call)
    )
    assert "--dirty-handoff-plan" in selector_call
    plan_index = selector_call.index("--dirty-handoff-plan") + 1
    assert Path(selector_call[plan_index]).as_posix() == ".tmp/scoped-dirty-worktree-handoff-plan-current.json"
    dirty_plan_call = calls[dirty_plan_call_index]
    previous_index = dirty_plan_call.index("--previous-json") + 1
    output_index = dirty_plan_call.index("--output-json") + 1
    assert Path(dirty_plan_call[previous_index]).as_posix() == ".tmp/scoped-dirty-worktree-handoff-plan-current.json"
    assert Path(dirty_plan_call[output_index]).as_posix() == ".tmp/scoped-dirty-worktree-handoff-plan-refresh.json"
    assert dirty_plan_call_index < selector_call_index
    assert launch_call_index < completion_call_index


def test_collect_inputs_expands_selector_timeout(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[list[str], int]] = []

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        assert root == tmp_path
        calls.append((args, timeout))
        return {}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)
    monkeypatch.setattr(debug_loop_inventory, "_load_json", lambda path: {})

    debug_loop_inventory.collect_inputs(tmp_path, timeout=30)

    selector_call = next(call for call in calls if any("next_experiment_selector.py" in part for part in call[0]))
    session_call = next(call for call in calls if any("session_orient.py" in part for part in call[0]))
    readiness_call = next(call for call in calls if any("product_readiness_score.py" in part for part in call[0]))
    assert debug_loop_inventory._next_experiment_selector_timeout(30) == 60
    assert debug_loop_inventory._next_experiment_selector_timeout(0) == 2
    assert selector_call[1] == 60
    assert session_call[1] == 30
    assert readiness_call[1] == 30


def test_collect_completion_audit_uses_expanded_launch_audit_timeout(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[list[str], int]] = []

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        assert root == tmp_path
        calls.append((args, timeout))
        if any("launch_objective_audit.py" in part for part in args):
            launch_audit = tmp_path / ".tmp" / "launch-objective-audit-current.json"
            launch_audit.parent.mkdir(parents=True, exist_ok=True)
            launch_audit.write_text(json.dumps({"objective": "launch"}), encoding="utf-8")
        return {"status": "incomplete"}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)

    result = debug_loop_inventory._collect_completion_audit_input(tmp_path, timeout=30)

    assert result == {"status": "incomplete"}
    assert debug_loop_inventory._launch_objective_audit_timeout(30) == 90
    assert debug_loop_inventory._launch_objective_audit_timeout(0) == 3
    launch_call = next(call for call in calls if any("launch_objective_audit.py" in part for part in call[0]))
    completion_call = next(call for call in calls if any("completion_audit.py" in part for part in call[0]))
    assert launch_call[1] == 90
    assert completion_call[1] == 30


def test_collect_inputs_replaces_dirty_plan_from_successful_refresh(monkeypatch, tmp_path: Path) -> None:
    current_plan = tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-current.json"
    current_plan_md = tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-current.md"
    current_plan.parent.mkdir(parents=True, exist_ok=True)
    current_plan.write_text(json.dumps({"status": "stale"}), encoding="utf-8")
    current_plan_md.write_text("stale", encoding="utf-8")

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        if any("launch_objective_audit.py" in part for part in args):
            launch_audit = tmp_path / ".tmp" / "launch-objective-audit-current.json"
            launch_audit.write_text(json.dumps({}), encoding="utf-8")
        if any("dirty_worktree_handoff_plan.py" in part for part in args):
            refresh_plan = tmp_path / Path(args[args.index("--output-json") + 1])
            refresh_plan_md = tmp_path / Path(args[args.index("--output-md") + 1])
            refresh_plan.write_text(json.dumps({"status": "handoff_required"}), encoding="utf-8")
            refresh_plan_md.write_text("fresh", encoding="utf-8")
        return {}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)

    inputs = debug_loop_inventory.collect_inputs(tmp_path, timeout=30)

    assert json.loads(current_plan.read_text(encoding="utf-8")) == {"status": "handoff_required"}
    assert current_plan_md.read_text(encoding="utf-8") == "fresh"
    assert not (tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.json").exists()
    assert inputs["dirty_handoff_plan"] == {"status": "handoff_required"}


def test_collect_inputs_preserves_current_dirty_plan_when_refresh_fails(monkeypatch, tmp_path: Path) -> None:
    stale_launch_audit = tmp_path / ".tmp" / "launch-objective-audit-current.json"
    current_dirty_plan = tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-current.json"
    current_dirty_plan_md = tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-current.md"
    refresh_dirty_plan = tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.json"
    refresh_dirty_plan_md = tmp_path / ".tmp" / "scoped-dirty-worktree-handoff-plan-refresh.md"
    stale_launch_audit.parent.mkdir(parents=True, exist_ok=True)
    stale_launch_audit.write_text(json.dumps({"stale": True}), encoding="utf-8")
    current_dirty_plan.write_text(json.dumps({"status": "stale"}), encoding="utf-8")
    current_dirty_plan_md.write_text("stale", encoding="utf-8")
    refresh_dirty_plan.write_text(json.dumps({"status": "old-refresh"}), encoding="utf-8")
    refresh_dirty_plan_md.write_text("old refresh", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        calls.append(args)
        if any("launch_objective_audit.py" in part or "dirty_worktree_handoff_plan.py" in part for part in args):
            return {"_input_error": {"reason": "helper failed"}}
        return {}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)

    inputs = debug_loop_inventory.collect_inputs(tmp_path, timeout=30)

    assert not stale_launch_audit.exists()
    assert json.loads(current_dirty_plan.read_text(encoding="utf-8")) == {"status": "stale"}
    assert current_dirty_plan_md.read_text(encoding="utf-8") == "stale"
    assert not refresh_dirty_plan.exists()
    assert not refresh_dirty_plan_md.exists()
    assert inputs["completion_audit"] == {"_input_error": {"reason": "helper failed"}}
    assert inputs["dirty_handoff_plan"] == {
        "status": "stale",
        "_input_error": {"reason": "helper failed"},
    }
    assert not any(any("completion_audit.py" in part for part in call) for call in calls)


def test_completion_audit_input_from_launch_audit_runs_or_preserves_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    launch_audit = tmp_path / ".tmp" / "launch-objective-audit-current.json"
    assert debug_loop_inventory._launch_audit_path(tmp_path) == launch_audit
    launch_audit.parent.mkdir(parents=True, exist_ok=True)
    launch_audit.write_text(json.dumps({"objective": "launch"}), encoding="utf-8")
    calls: list[tuple[Path, list[str], int]] = []

    def fake_run_json(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        calls.append((root, args, timeout))
        return {"status": "incomplete"}

    monkeypatch.setattr(debug_loop_inventory, "_run_json", fake_run_json)

    assert debug_loop_inventory._completion_audit_input_from_launch_audit(
        tmp_path,
        launch_audit,
        {"status": "pass"},
        9,
    ) == {"status": "incomplete"}
    assert calls == [
        (
            tmp_path,
            debug_loop_inventory._completion_audit_command(launch_audit),
            9,
        )
    ]

    launch_audit.unlink()
    assert debug_loop_inventory._completion_audit_input_from_launch_audit(
        tmp_path,
        launch_audit,
        {"_input_error": {"reason": "launch helper failed"}},
        9,
    ) == {"_input_error": {"reason": "launch helper failed"}}
    assert (
        debug_loop_inventory._completion_audit_input_from_launch_audit(
            tmp_path,
            launch_audit,
            {"status": "pass"},
            9,
        )
        == {}
    )


def test_run_json_reports_success_parse_and_nonzero_contract(tmp_path: Path) -> None:
    success = debug_loop_inventory._run_json(
        tmp_path,
        [sys.executable, "-c", "import json; print(json.dumps({'ok': True}))"],
        timeout=10,
    )
    assert success == {"ok": True}

    invalid = debug_loop_inventory._run_json(
        tmp_path,
        [sys.executable, "-c", "print('not json')"],
        timeout=10,
    )
    assert invalid["_input_error"]["reason"] == "invalid helper JSON"
    assert invalid["_input_error"]["returncode"] == 0

    nonzero = debug_loop_inventory._run_json(
        tmp_path,
        [
            sys.executable,
            "-c",
            "import json, sys; print(json.dumps({'ok': False})); print('failed', file=sys.stderr); sys.exit(7)",
        ],
        timeout=10,
    )
    assert nonzero["ok"] is False
    assert nonzero["_input_error"] == {
        "reason": "helper returned non-zero",
        "returncode": 7,
        "detail": "failed",
    }


def test_low_level_summary_helpers_preserve_blocker_contract(tmp_path: Path) -> None:
    helper_error = {
        "_input_error": {
            "reason": "helper failed",
            "returncode": 2,
            "detail": "bad json",
        }
    }
    assert debug_loop_inventory._has_input_error(helper_error) is True
    assert (
        debug_loop_inventory._input_error_line("selector", helper_error)
        == "selector: helper failed; returncode=2; detail=bad json"
    )

    selected = debug_loop_inventory._selector_status_line(_selector())
    expectations = debug_loop_inventory._selector_gate_expectations(_selector())
    assert "dirty_worktree_handoff_current" in selected
    assert expectations == [
        {
            "gate": (
                "python .agents/skills/auto-research/scripts/debug_loop_inventory.py --fail-on-completion-blocked"
            ),
            "expected_exit_codes": [1],
            "meaning": "Completion remains blocked; not a source failure.",
        }
    ]

    freshness = debug_loop_inventory._session_evidence_freshness(_session_with_fresh_graph())
    assert freshness == [
        {
            "source": "code_review_graph",
            "available": True,
            "freshness": "current",
            "stale": False,
            "built_at_commit": "current-head",
            "current_head": "current-head",
            "stale_reason": None,
        }
    ]
    assert debug_loop_inventory._graph_freshness_item(_session_with_fresh_graph()) is None
    context_inputs = debug_loop_inventory.InventoryBuildInputs(
        session_orient=_session_with_fresh_graph(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    context = debug_loop_inventory._inventory_item_context(context_inputs)
    assert context.graph == _session_with_fresh_graph()["graph"]

    assert debug_loop_inventory._graph_freshness_is_degraded(_session_with_fresh_graph()["graph"]) is False
    assert debug_loop_inventory._graph_freshness_is_degraded(_session_with_stale_graph()["graph"]) is True
    assert debug_loop_inventory._graph_freshness_reproduction() == [
        "Run `python execution/session_orient.py --json`.",
        "Inspect `graph.available`, `graph.freshness`, `graph.stale`, `graph.built_at_commit`, and `graph.current_head`.",
    ]
    assert debug_loop_inventory._graph_freshness_expected() == [
        "Graph evidence used before code review is fresh for the current HEAD or explicitly marked stale."
    ]
    assert debug_loop_inventory._graph_freshness_base_fields() == {
        "title": "Code Review Graph Evidence Is Stale",
        "status": "reproduced, evidence freshness degraded",
        "severity": "medium",
        "frequency": "until graph is updated for current HEAD",
        "root_cause": (
            "The graph index is older than the live repository HEAD, so graph-first exploration remains useful "
            "but should be treated as evidence with degraded freshness until the graph is updated."
        ),
        "next_action": (
            "Run `py -3.13 -m code_review_graph update`, or `py -3.13 -m code_review_graph build` if "
            "incremental update cannot reconcile the index, then rerun session orientation and debug inventory."
        ),
        "actionable": True,
    }
    assert debug_loop_inventory._graph_freshness_item(_session_with_stale_graph())["title"] == (
        "Code Review Graph Evidence Is Stale"
    )
    assert (
        debug_loop_inventory._graph_freshness_item_from_graph(_session_with_stale_graph()["graph"])["title"]
        == "Code Review Graph Evidence Is Stale"
    )
    assert debug_loop_inventory._markdown_summary_lines(
        {
            "item_count": 5,
            "actionable_item_count": 1,
            "blocked_item_count": 2,
            "reproduction_unclear_count": 0,
            "completion_gate": "blocked",
            "completion_allowed": False,
            "next_required_action": "Keep handoff evidence current.",
        }
    ) == [
        "## Summary",
        "",
        "- Items: 5",
        "- Actionable: 1",
        "- Blocked: 2",
        "- Reproduction unclear: 0",
        "- Completion gate: blocked",
        "- Completion allowed: false",
        "- Next required action: Keep handoff evidence current.",
        "",
    ]
    assert debug_loop_inventory._markdown_blocked_notice_lines(
        {"blocked_item_count": 2, "highest_priority": "Dirty handoff"}
    ) == [
        "> [!IMPORTANT]",
        "> Debug loop is blocked; do not claim launch completion until blockers are cleared.",
        "> Highest priority: Dirty handoff.",
        "",
    ]
    assert debug_loop_inventory._markdown_blocked_notice_lines({"blocked_item_count": 0}) == []
    assert (
        debug_loop_inventory._markdown_completion_blocker_line(
            {"title": "Blocked Item", "next_action": "Wait for scoped authorization."}
        )
        == "  - Blocked Item: Wait for scoped authorization."
    )
    assert debug_loop_inventory._markdown_completion_blocker_section_lines(
        [{"title": "Blocked Item", "next_action": "Wait for scoped authorization."}]
    ) == [
        "- Completion blockers:",
        "  - Blocked Item: Wait for scoped authorization.",
        "",
    ]
    assert debug_loop_inventory._markdown_completion_blocker_section_lines([]) == []
    assert debug_loop_inventory._markdown_expected_failure_gate_line(
        {
            "gate": "python debug_loop_inventory.py --fail-on-completion-blocked",
            "expected_exit_codes": [1],
            "meaning": "Completion remains blocked; not a source failure.",
        }
    ) == (
        "  - `python debug_loop_inventory.py --fail-on-completion-blocked` expects exit code(s) `1`: "
        "Completion remains blocked; not a source failure."
    )
    assert debug_loop_inventory._markdown_expected_failure_gate_section_lines(
        [
            {
                "gate": "python debug_loop_inventory.py --fail-on-completion-blocked",
                "expected_exit_codes": [1],
                "meaning": "Completion remains blocked; not a source failure.",
            }
        ]
    ) == [
        "- Expected nonzero gates:",
        (
            "  - `python debug_loop_inventory.py --fail-on-completion-blocked` expects exit code(s) `1`: "
            "Completion remains blocked; not a source failure."
        ),
        "",
    ]
    assert debug_loop_inventory._markdown_expected_failure_gate_section_lines([]) == []
    assert debug_loop_inventory._markdown_evidence_freshness_details(
        {
            "available": True,
            "freshness": "stale",
            "stale": True,
            "built_at_commit": "old-head",
            "current_head": "new-head",
            "stale_reason": "built_at_commit old-head != current_head new-head",
        }
    ) == [
        "available `true`",
        "freshness `stale`",
        "stale `true`",
        "built_at_commit `old-head`",
        "current_head `new-head`",
        "reason `built_at_commit old-head != current_head new-head`",
    ]
    assert (
        debug_loop_inventory._markdown_evidence_stale_reason_detail(
            {"stale_reason": "built_at_commit old-head != current_head new-head"}
        )
        == "reason `built_at_commit old-head != current_head new-head`"
    )
    assert debug_loop_inventory._markdown_evidence_stale_reason_detail({}) is None
    assert debug_loop_inventory._markdown_evidence_freshness_base_details(
        {
            "available": True,
            "freshness": "current",
            "stale": False,
            "built_at_commit": "current-head",
            "current_head": "current-head",
        }
    ) == [
        "available `true`",
        "freshness `current`",
        "stale `false`",
        "built_at_commit `current-head`",
        "current_head `current-head`",
    ]
    assert debug_loop_inventory._markdown_evidence_freshness_line(
        {
            "source": "code_review_graph",
            "available": True,
            "freshness": "current",
            "stale": False,
            "built_at_commit": "current-head",
            "current_head": "current-head",
        }
    ) == (
        "  - code_review_graph: available `true`, freshness `current`, stale `false`, "
        "built_at_commit `current-head`, current_head `current-head`"
    )
    assert debug_loop_inventory._markdown_evidence_freshness_section_lines(
        [
            {
                "source": "code_review_graph",
                "available": True,
                "freshness": "current",
                "stale": False,
                "built_at_commit": "current-head",
                "current_head": "current-head",
            }
        ]
    ) == [
        "- Evidence freshness:",
        (
            "  - code_review_graph: available `true`, freshness `current`, stale `false`, "
            "built_at_commit `current-head`, current_head `current-head`"
        ),
        "",
    ]
    assert debug_loop_inventory._markdown_evidence_freshness_section_lines([]) == []
    summary_detail_lines = debug_loop_inventory._markdown_summary_detail_lines(
        {
            "blocked_item_count": 1,
            "highest_priority": "Dirty handoff",
            "completion_blockers": [{"title": "Blocked Item", "next_action": "Wait for scoped authorization."}],
            "expected_failure_gates": [
                {
                    "gate": "python debug_loop_inventory.py --fail-on-completion-blocked",
                    "expected_exit_codes": [1],
                    "meaning": "Completion remains blocked; not a source failure.",
                }
            ],
            "evidence_freshness": [
                {
                    "source": "code_review_graph",
                    "available": True,
                    "freshness": "current",
                    "stale": False,
                    "built_at_commit": "current-head",
                    "current_head": "current-head",
                }
            ],
        }
    )
    assert summary_detail_lines == [
        "> [!IMPORTANT]",
        "> Debug loop is blocked; do not claim launch completion until blockers are cleared.",
        "> Highest priority: Dirty handoff.",
        "",
        "- Completion blockers:",
        "  - Blocked Item: Wait for scoped authorization.",
        "",
        "- Expected nonzero gates:",
        (
            "  - `python debug_loop_inventory.py --fail-on-completion-blocked` expects exit code(s) `1`: "
            "Completion remains blocked; not a source failure."
        ),
        "",
        "- Evidence freshness:",
        (
            "  - code_review_graph: available `true`, freshness `current`, stale `false`, "
            "built_at_commit `current-head`, current_head `current-head`"
        ),
        "",
    ]
    assert debug_loop_inventory._markdown_inventory_item_header_lines(
        {
            "priority": 3,
            "title": "Blocked Item",
            "status": "reproduced",
            "severity_x_frequency": "high x always",
            "actionable": False,
        }
    ) == [
        "## Priority 3 - Blocked Item",
        "",
        "- Status: reproduced",
        "- Severity x frequency: high x always",
        "- Actionable: false",
    ]
    assert debug_loop_inventory._markdown_inventory_item_action_lines(
        {"root_cause": "dirty handoff", "next_action": "wait"}
    ) == ["- Root cause:", "  - dirty handoff", "- Next action:", "  - wait", ""]
    assert debug_loop_inventory._markdown_inventory_item_action_sections(
        {"root_cause": "dirty handoff", "next_action": "wait"}
    ) == [
        ("Root cause", ["dirty handoff"]),
        ("Next action", ["wait"]),
    ]
    assert debug_loop_inventory._markdown_inventory_item_list_sections(
        {"reproduction": ["run helper"], "expected": ["candidate"], "actual": ["blocked"]}
    ) == [
        ("Reproduction", ["run helper"]),
        ("Expected", ["candidate"]),
        ("Actual", ["blocked"]),
    ]
    assert debug_loop_inventory._markdown_inventory_item_list_lines(
        {"reproduction": ["run helper"], "expected": ["candidate"], "actual": ["blocked"]}
    ) == [
        "- Reproduction:",
        "  - run helper",
        "- Expected:",
        "  - candidate",
        "- Actual:",
        "  - blocked",
    ]
    assert debug_loop_inventory._markdown_list_lines("Reproduction", ["run helper"]) == [
        "- Reproduction:",
        "  - run helper",
    ]
    assert debug_loop_inventory._markdown_list_lines("Actual", []) == ["- Actual:"]
    assert debug_loop_inventory._markdown_blocker_lines(["authorization required"]) == [
        "- Blockers:",
        "  - authorization required",
    ]
    assert debug_loop_inventory._markdown_blocker_lines([]) == ["- Blockers: none"]
    inventory_item_lines: list[str] = []
    debug_loop_inventory._append_markdown_inventory_item_lists(
        inventory_item_lines,
        {"reproduction": ["run helper"], "expected": ["candidate"], "actual": ["blocked"]},
    )
    assert inventory_item_lines == [
        "- Reproduction:",
        "  - run helper",
        "- Expected:",
        "  - candidate",
        "- Actual:",
        "  - blocked",
    ]
    expected_inventory_item_lines = [
        "## Priority 2 - Loop Blocked",
        "",
        "- Status: unknown",
        "- Severity x frequency: unknown",
        "- Actionable: unknown",
        "- Blockers: none",
        "- Reproduction:",
        "  - run helper",
        "- Expected:",
        "- Actual:",
        "- Root cause:",
        "  - unknown",
        "- Next action:",
        "  - unknown",
        "",
    ]
    assert (
        debug_loop_inventory._markdown_inventory_item_lines(
            {"priority": 2, "title": "Loop Blocked", "reproduction": ["run helper"]}
        )
        == expected_inventory_item_lines
    )

    assert (
        debug_loop_inventory._markdown_inventory_items_lines(
            {"items": [{"priority": 2, "title": "Loop Blocked", "reproduction": ["run helper"]}]}
        )
        == expected_inventory_item_lines
    )
    markdown_lines = []
    debug_loop_inventory._append_markdown_inventory_items(
        markdown_lines,
        {"items": [{"priority": 2, "title": "Loop Blocked", "reproduction": ["run helper"]}]},
    )
    assert markdown_lines == expected_inventory_item_lines

    expected_reproduction_unclear_lines = [
        "## Reproduction-Unclear Items",
        "",
        "- selector helper failed",
        "",
    ]
    inventory_body = {
        "items": [{"priority": 2, "title": "Loop Blocked", "reproduction": ["run helper"]}],
        "reproduction_unclear_items": ["selector helper failed"],
    }
    assert (
        debug_loop_inventory._markdown_reproduction_unclear_inventory_lines(inventory_body)
        == expected_reproduction_unclear_lines
    )
    assert (
        debug_loop_inventory._markdown_inventory_body_lines(inventory_body)
        == expected_inventory_item_lines + expected_reproduction_unclear_lines
    )
    markdown_lines = []
    debug_loop_inventory._append_markdown_inventory_body(markdown_lines, inventory_body)
    assert markdown_lines == expected_inventory_item_lines + expected_reproduction_unclear_lines
    assert debug_loop_inventory._inventory_boundary_from_inputs(
        selector_kind="dirty_worktree_handoff_current",
        readiness=_readiness(),
        dirty_handoff_plan=_handoff_plan(),
        worktree={"staged": 0, "modified": 0, "untracked": 0},
    ) == (71, True, False)
    assert debug_loop_inventory._inventory_boundary_from_inputs(
        selector_kind="current_head_release_checks_unproven",
        readiness=_clean_publish_readiness(),
        dirty_handoff_plan=_handoff_plan(),
        worktree={"staged": 0, "modified": 0, "untracked": 0},
    ) == (0, False, True)

    boundary_inputs = debug_loop_inventory.InventoryBuildInputs(
        session_orient=_session(),
        selector=_selector(),
        readiness=_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_handoff_plan(),
    )
    boundary_context = debug_loop_inventory._inventory_item_context(boundary_inputs)
    assert debug_loop_inventory._primary_boundary_state_from_inputs(
        selector=_selector(),
        readiness=_readiness(),
        dirty_handoff_plan=_handoff_plan(),
        context=boundary_context,
    ) == debug_loop_inventory.PrimaryBoundaryState(
        selector_kind="dirty_worktree_handoff_current",
        dirty_count=71,
        has_dirty_boundary=True,
        has_publish_boundary=False,
    )
    boundary_items: list[dict[str, object]] = []
    assert debug_loop_inventory._append_boundary_inventory_items(
        boundary_items,
        inputs=boundary_inputs,
        context=boundary_context,
    ) == (True, False)
    assert [item["title"] for item in boundary_items] == [
        "Dirty Handoff Boundary Blocks New Product Edits",
        "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
        "Current-HEAD GitHub Actions Cannot Be Proven Locally",
        "Blind-to-X Is Ready But Not Launch-Complete Because Dirty Paths Remain",
        "Launch Completion Audit Remains Incomplete",
    ]
    evidence_items: list[dict[str, object]] = []
    assert (
        debug_loop_inventory._append_inventory_evidence_items(
            evidence_items,
            inputs=boundary_inputs,
            context=boundary_context,
        )
        == []
    )
    assert [item["title"] for item in evidence_items] == [item["title"] for item in boundary_items]
    completion_items: list[dict[str, object]] = []
    debug_loop_inventory._append_launch_completion_from_context(
        completion_items,
        completion_audit=_completion(),
        context=boundary_context,
        has_dirty_boundary=True,
        blind_dirty=["dirty.py"],
    )
    assert completion_items[0]["priority"] == 1
    assert completion_items[0]["title"] == "Launch Completion Audit Remains Incomplete"
    assert "dirty worktree" in completion_items[0]["root_cause"]
    assert "Blind-to-X handoff" in completion_items[0]["root_cause"]
    assert (
        debug_loop_inventory._primary_boundary_kind(has_dirty_boundary=True, has_publish_boundary=True)
        == "dirty_worktree_handoff"
    )
    assert (
        debug_loop_inventory._primary_boundary_kind(has_dirty_boundary=False, has_publish_boundary=True)
        == "current_head_publish"
    )
    assert debug_loop_inventory._primary_boundary_kind(has_dirty_boundary=False, has_publish_boundary=False) == ""

    primary_dirty_items: list[dict[str, object]] = []
    debug_loop_inventory._append_primary_dirty_boundary_item(
        primary_dirty_items,
        boundary=debug_loop_inventory.PrimaryBoundaryState(
            selector_kind="dirty_worktree_handoff_current",
            dirty_count=71,
            has_dirty_boundary=True,
            has_publish_boundary=False,
        ),
        selector=_selector(),
        dirty_handoff_plan=_handoff_plan(),
        context=boundary_context,
    )
    assert primary_dirty_items[0]["priority"] == 1
    assert primary_dirty_items[0]["title"] == "Dirty Handoff Boundary Blocks New Product Edits"

    publish_inputs = debug_loop_inventory.InventoryBuildInputs(
        session_orient=_clean_publish_session(),
        selector=_publish_selector(),
        readiness=_clean_publish_readiness(),
        completion_audit=_completion(),
        dirty_handoff_plan=_clean_handoff_plan(),
    )
    publish_context = debug_loop_inventory._inventory_item_context(publish_inputs)
    primary_publish_items: list[dict[str, object]] = []
    debug_loop_inventory._append_primary_publish_boundary_item(
        primary_publish_items,
        boundary=debug_loop_inventory.PrimaryBoundaryState(
            selector_kind="current_head_release_checks_unproven",
            dirty_count=0,
            has_dirty_boundary=False,
            has_publish_boundary=True,
        ),
        selector=_publish_selector(),
        readiness=_clean_publish_readiness(),
        context=publish_context,
    )
    assert primary_publish_items[0]["priority"] == 1
    assert primary_publish_items[0]["title"] == "Current-HEAD GitHub Actions Cannot Be Proven Locally"

    assert debug_loop_inventory._launch_blocker_labels(has_dirty_boundary=True, blind_dirty=["dirty.py"]) == [
        "dirty worktree",
        "publish/current-head Actions",
        "T-251",
        "Hanwoo readiness",
        "Blind-to-X handoff",
    ]
    assert debug_loop_inventory._blind_to_x_dirty_paths({"dirty_paths": ["projects/blind-to-x/a.py", 123]}) == [
        "projects/blind-to-x/a.py",
        "123",
    ]
    assert debug_loop_inventory._blind_to_x_dirty_paths({"dirty_paths": "not-a-list"}) == []
    assert debug_loop_inventory._blind_to_x_dirty_handoff_base_fields() == {
        "title": "Blind-to-X Is Ready But Not Launch-Complete Because Dirty Paths Remain",
        "status": "reproduced, handoff/commit boundary",
        "severity": "medium",
        "frequency": "always until dirty paths are handled",
        "root_cause": "Completed/validated project changes remain uncommitted or unhanded-off, not a failing runtime gate.",
        "next_action": (
            "Explicit scoped staging/commit authorization for the `project:blind-to-x` group, or leave as handoff-only."
        ),
        "actionable": False,
        "blockers": ["Scoped staging/commit authorization is required."],
    }
    assert debug_loop_inventory._completion_audit_actuals(_completion(), _completion()["summary"]) == [
        "Completion audit returns `status=incomplete`, `15` items, `8` complete, `11` issues, `7` blocked."
    ]
    assert debug_loop_inventory._launch_completion_blocker_phrase([]) == ""
    assert debug_loop_inventory._launch_completion_blocker_phrase(["T-251"]) == "T-251"
    assert (
        debug_loop_inventory._launch_completion_blocker_phrase(["dirty worktree", "T-251"])
        == "dirty worktree and T-251"
    )
    assert debug_loop_inventory._launch_completion_root_cause([]) == (
        "The audit has no unresolved launch blocker boundaries."
    )
    assert debug_loop_inventory._launch_completion_root_cause(["T-251"]) == (
        "The audit correctly reflects unresolved T-251 boundary."
    )
    assert debug_loop_inventory._launch_completion_root_cause(["dirty worktree", "T-251"]) == (
        "The audit correctly reflects unresolved dirty worktree and T-251 boundaries."
    )
    assert debug_loop_inventory._inventory_objective() == (
        "List currently known bugs, anomalies, and blockers for the autonomous reproduce -> isolate -> "
        "root-cause -> fix -> verify loop without guessing or editing product code."
    )
    assert debug_loop_inventory._launch_completion_base_fields(
        ["dirty worktree", "publish/current-head Actions", "T-251"]
    ) == {
        "title": "Launch Completion Audit Remains Incomplete",
        "status": "reproduced, aggregate blocker",
        "severity": "medium",
        "frequency": "always while above blockers remain",
        "root_cause": (
            "The audit correctly reflects unresolved dirty worktree, publish/current-head Actions, and T-251 "
            "boundaries."
        ),
        "next_action": (
            "Do not call `update_goal`; continue only after scoped authorization or external reset changes live state."
        ),
        "actionable": False,
        "blockers": ["Completion audit is incomplete."],
    }
    assert debug_loop_inventory._dirty_handoff_base_fields() == {
        "title": "Dirty Handoff Boundary Blocks New Product Edits",
        "status": "reproduced, blocked by policy/authorization",
        "severity": "high",
        "frequency": "always",
        "root_cause": (
            "Existing dirty work spans multiple project slices, and a machine-readable handoff plan already matches "
            "the current inventory; starting unrelated product edits would mix scopes without explicit staging/commit "
            "authorization."
        ),
        "next_action": "Wait for explicit scoped staging/commit authorization, or keep handoff-only evidence current.",
        "actionable": False,
        "blockers": ["Explicit scoped staging/commit authorization is required before product changes."],
    }
    assert debug_loop_inventory._hanwoo_t251_base_fields() == {
        "title": "Hanwoo T-251 Live Prisma CRUD Remains User-Owned External Blocker",
        "status": "known external blocker, do not retry until reset",
        "severity": "high",
        "frequency": "always until user reset",
        "root_cause": "Supabase credential/control-plane drift, not a locally reproduced code regression.",
        "next_action": (
            "User resets Supabase database password/control-plane credentials, updates `.env` if changed, "
            "then rerun the live Prisma check once."
        ),
        "actionable": False,
        "blockers": ["Supabase credential reset/resync has not been reported."],
    }
    readiness_with_multiple_hanwoo_tasks = json.loads(json.dumps(_readiness()))
    readiness_with_multiple_hanwoo_tasks["projects"][0]["tasks"] = [
        {"id": "T-777", "owner": "User"},
        {"id": "T-agent", "owner": "Codex"},
        {"id": "T-251", "owner": "User"},
    ]
    assert debug_loop_inventory._hanwoo_t251_task_ids(readiness_with_multiple_hanwoo_tasks) == ["T-251", "T-777"]

    readiness_without_hanwoo_tasks = json.loads(json.dumps(_readiness()))
    readiness_without_hanwoo_tasks["projects"][0]["tasks"] = []
    assert debug_loop_inventory._hanwoo_t251_task_ids(readiness_without_hanwoo_tasks) == ["T-251"]

    assert debug_loop_inventory._current_head_readiness_reproduction() == [
        "Run `python execution/product_readiness_score.py --json`.",
        "Run `python execution/session_orient.py --json`.",
    ]
    assert debug_loop_inventory._current_head_readiness_expected() == [
        "Required workflows for current local HEAD are available and passing before launch readiness is claimed."
    ]
    assert debug_loop_inventory._current_head_readiness_actuals(
        {"ahead": 833},
        ["root-quality-gate=missing:none", "active-project-matrix=missing:none"],
    ) == [
        "Branch `main` is ahead of origin by `833` commits.",
        "Required workflow status: root-quality-gate=missing:none, active-project-matrix=missing:none",
    ]
    assert debug_loop_inventory._current_head_readiness_next_action() == (
        "Explicit push authorization or user push, then wait for required Actions on the exact current HEAD."
    )
    assert (
        debug_loop_inventory._should_append_current_head_readiness_item(
            has_publish_boundary=True,
            ahead=833,
            workflows=["root-quality-gate=missing:none"],
        )
        is False
    )
    assert (
        debug_loop_inventory._should_append_current_head_readiness_item(
            has_publish_boundary=False,
            ahead=0,
            workflows=[],
        )
        is False
    )
    assert (
        debug_loop_inventory._should_append_current_head_readiness_item(
            has_publish_boundary=False,
            ahead=1,
            workflows=[],
        )
        is True
    )
    assert (
        debug_loop_inventory._should_append_current_head_readiness_item(
            has_publish_boundary=False,
            ahead=0,
            workflows=["root-quality-gate=missing:none"],
        )
        is True
    )

    handoff_line = debug_loop_inventory._handoff_plan_status_line(
        freshness=_handoff_plan()["freshness"],
        selector_kind="dirty_worktree_handoff_current",
        dirty_count=71,
        worktree={"staged": 0},
        session_git={"ahead": 833},
        signature={"value": "fresh-signature"},
    )
    assert "fresh-signature" in handoff_line
    assert "dirty count `71`" in handoff_line
    assert (
        debug_loop_inventory._handoff_plan_status_details(
            dirty_count=71,
            worktree={"staged": 2},
            session_git={"ahead": 833},
            signature={"value": "fresh-signature"},
        )
        == "dirty count `71`, staged `2`, branch ahead `833`, signature `fresh-signature`."
    )
    assert debug_loop_inventory._handoff_plan_status_line(
        freshness={"status": "current"},
        selector_kind="current_head_release_checks_unproven",
        dirty_count=0,
        worktree={"staged": 0},
        session_git={"ahead": 885},
        signature={"value": "clean-signature"},
    ) == (
        "Current handoff plan freshness is `current` with dirty count `0`, staged `0`, "
        "branch ahead `885`, signature `clean-signature`."
    )

    publish_fields = debug_loop_inventory._current_head_publish_base_fields(next_action="publish")
    assert publish_fields == {
        "title": "Current-HEAD GitHub Actions Cannot Be Proven Locally",
        "status": "reproduced, publish authorization required",
        "severity": "medium-high",
        "frequency": "always while ahead/unpushed",
        "root_cause": "Current local HEAD is not published, so GitHub Actions cannot run against it.",
        "next_action": "publish",
        "actionable": False,
        "blockers": ["No push authorization is present."],
    }
    assert debug_loop_inventory._input_evidence_base_fields() == {
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

    publish_item = debug_loop_inventory._current_head_publish_boundary_item(
        priority=1,
        selector=_publish_selector(),
        dirty_count=0,
        worktree=_clean_publish_session()["git"]["worktree"],
        session_git=_clean_publish_session()["git"],
        signature=_clean_handoff_plan()["dirty_signature"],
        readiness=_clean_publish_readiness(),
    )
    readiness_item = debug_loop_inventory._current_head_readiness_boundary_item(
        priority=2,
        session_git=_clean_publish_session()["git"],
        workflows=["root-quality-gate=completed:success"],
    )
    shared_publish_keys = ("title", "status", "severity", "frequency", "root_cause", "actionable", "blockers")
    assert {key: publish_item[key] for key in shared_publish_keys} == {
        key: readiness_item[key] for key in shared_publish_keys
    }
    assert "release authorization packet" in publish_item["next_action"]
    assert "Explicit push authorization" in readiness_item["next_action"]

    item = debug_loop_inventory._make_item(
        priority=1,
        title="Blocked Item",
        status="reproduced, blocked",
        severity="high",
        frequency="always",
        reproduction=["run helper"],
        expected=["candidate"],
        actual=["blocked"],
        root_cause="dirty handoff",
        next_action="wait",
        actionable=False,
        blockers=["authorization required"],
    )
    assert debug_loop_inventory._severity_x_frequency("high", "always") == "high x always"
    assert debug_loop_inventory._item_blockers(None) == []
    assert debug_loop_inventory._item_blockers(["authorization required"]) == ["authorization required"]
    assert debug_loop_inventory._inventory_item_header_fields(
        priority=1,
        title="Blocked Item",
        status="reproduced, blocked",
        severity="high",
        frequency="always",
    ) == {
        "priority": 1,
        "title": "Blocked Item",
        "status": "reproduced, blocked",
        "severity": "high",
        "frequency": "always",
        "severity_x_frequency": "high x always",
    }
    assert debug_loop_inventory._inventory_item_observation_fields(
        reproduction=["run helper"],
        expected=["candidate"],
        actual=["blocked"],
    ) == {
        "reproduction": ["run helper"],
        "expected": ["candidate"],
        "actual": ["blocked"],
    }
    assert debug_loop_inventory._inventory_item_resolution_fields(
        root_cause="dirty handoff",
        next_action="wait",
        actionable=False,
        blockers=None,
    ) == {
        "root_cause": "dirty handoff",
        "next_action": "wait",
        "actionable": False,
        "blockers": [],
    }
    assert item["severity_x_frequency"] == "high x always"
    summary = debug_loop_inventory._inventory_summary([item], [])
    assert summary["completion_gate"] == "blocked"
    assert summary["completion_allowed"] is False
    assert summary["completion_blockers"][0]["title"] == "Blocked Item"
    assert debug_loop_inventory._inventory_blocked_items([item]) == [item]
    assert debug_loop_inventory._completion_blocker_entry(item) == {
        "title": "Blocked Item",
        "status": "reproduced, blocked",
        "next_action": "wait",
        "blockers": ["authorization required"],
    }
    assert debug_loop_inventory._completion_blockers([item])[0]["blockers"] == ["authorization required"]
    assert debug_loop_inventory._reproduction_unclear_count([item], ["input error"]) == 1
    assert (
        debug_loop_inventory._reproduction_unclear_count(
            [{"status": "reproduction unclear, helper unavailable"}],
            [],
        )
        == 1
    )
    assert debug_loop_inventory._completion_gate(items=[item], blocked_items=[item], unclear_count=0) == "blocked"
    assert (
        debug_loop_inventory._completion_gate(items=[item], blocked_items=[], unclear_count=1) == "reproduction_unclear"
    )
    assert debug_loop_inventory._completion_gate(items=[item], blocked_items=[], unclear_count=0) == "open_items"
    assert debug_loop_inventory._completion_gate(items=[], blocked_items=[], unclear_count=0) == "clear"

    markdown_lines: list[str] = []
    debug_loop_inventory._append_markdown_list(markdown_lines, "Actual", ["blocked"])
    assert markdown_lines == ["- Actual:", "  - blocked"]

    markdown_lines = []
    debug_loop_inventory._append_markdown_blockers(markdown_lines, ["authorization required"])
    assert markdown_lines == ["- Blockers:", "  - authorization required"]

    markdown_lines = []
    debug_loop_inventory._append_markdown_blockers(markdown_lines, [])
    assert markdown_lines == ["- Blockers: none"]

    markdown_lines = []
    debug_loop_inventory._append_markdown_reproduction_unclear_items(markdown_lines, {})
    assert markdown_lines == [
        "## Reproduction-Unclear Items",
        "",
        (
            "- None currently actionable. Items without direct local reproduction are classified above as "
            "authorization-blocked or external/user-owned instead of being patched speculatively."
        ),
        "",
    ]
    assert debug_loop_inventory._markdown_reproduction_unclear_section_lines([]) == markdown_lines
    assert debug_loop_inventory._markdown_reproduction_unclear_inventory_lines({}) == markdown_lines

    markdown_lines = []
    debug_loop_inventory._append_markdown_reproduction_unclear_items(
        markdown_lines,
        {"reproduction_unclear_items": ["selector helper failed"]},
    )
    assert markdown_lines == [
        "## Reproduction-Unclear Items",
        "",
        "- selector helper failed",
        "",
    ]
    assert debug_loop_inventory._markdown_reproduction_unclear_section_lines(["selector helper failed"]) == (
        markdown_lines
    )
    assert (
        debug_loop_inventory._markdown_reproduction_unclear_inventory_lines(
            {"reproduction_unclear_items": ["selector helper failed"]}
        )
        == markdown_lines
    )
    assert debug_loop_inventory._markdown_document_header_lines(
        {"generated_at": "2026-06-10T00:00:00+00:00", "objective": "Keep launch evidence current."}
    ) == [
        "# Debug Loop Known Bugs / Anomalies",
        "",
        "Generated: 2026-06-10T00:00:00+00:00",
        "",
        "Objective: Keep launch evidence current.",
        "",
    ]
    assert debug_loop_inventory._markdown_document_header_lines({}) == [
        "# Debug Loop Known Bugs / Anomalies",
        "",
        "Generated: unknown",
        "",
        "Objective: unknown",
        "",
    ]
    document_inventory = {
        "generated_at": "2026-06-10T00:00:00+00:00",
        "objective": "Confirm document helper",
        "items": [{"priority": 2, "title": "Loop Blocked", "reproduction": ["run helper"]}],
        "reproduction_unclear_items": ["selector helper failed"],
    }
    document_lines = debug_loop_inventory._markdown_document_lines(document_inventory)
    assert "\n".join(document_lines) == debug_loop_inventory.render_markdown(document_inventory)

    inventory = {"items": [item], "summary": {"expected_failure_gates": expectations}}
    markdown_summary = debug_loop_inventory._summary_for_markdown(inventory)
    assert markdown_summary["item_count"] == 1
    assert markdown_summary["expected_failure_gates"] == expectations
    assert "expected_exit_codes=1" in debug_loop_inventory._expected_failure_gate_status(markdown_summary)
    assert debug_loop_inventory._expected_failure_gate_status_line(expectations[0]) == (
        "expected_exit_codes=1; meaning=Completion remains blocked; not a source failure."
    )
    assert debug_loop_inventory._expected_failure_gate_status_line({"meaning": "missing code"}) == ""
    assert debug_loop_inventory._expected_failure_gate_status_lines(
        {
            "expected_failure_gates": [
                expectations[0],
                {"meaning": "missing code"},
                {"expected_exit_codes": [2], "meaning": ""},
            ]
        }
    ) == [
        "expected_exit_codes=1; meaning=Completion remains blocked; not a source failure.",
        "expected_exit_codes=2",
    ]
    assert debug_loop_inventory._completion_blocked_message_base(markdown_summary) == (
        "completion blocked: blocked; next_required_action=wait"
    )
    expected_gate_suffix = (
        "; expected_failure_gates=expected_exit_codes=1; meaning=Completion remains blocked; not a source failure."
    )
    assert debug_loop_inventory._completion_blocked_expected_gate_suffix(markdown_summary) == expected_gate_suffix
    assert debug_loop_inventory._completion_blocked_expected_gate_suffix({}) == ""
    assert debug_loop_inventory._completion_blocked_message(
        {"items": [], "summary": {"expected_failure_gates": expectations}}
    ) == (
        "completion blocked: clear; next_required_action=No debug-loop action required.; "
        "expected_failure_gates=expected_exit_codes=1; meaning=Completion remains blocked; not a source failure."
    )
    empty_markdown_summary = debug_loop_inventory._summary_for_markdown(
        {"items": [], "summary": {"expected_failure_gates": expectations}}
    )
    assert empty_markdown_summary["item_count"] == 0
    assert empty_markdown_summary["completion_gate"] == "clear"
    assert empty_markdown_summary["completion_allowed"] is True
    assert empty_markdown_summary["next_required_action"] == "No debug-loop action required."
    assert empty_markdown_summary["expected_failure_gates"] == expectations
    assert debug_loop_inventory._completion_blocked_exit_code(inventory, True) == (
        debug_loop_inventory.COMPLETION_BLOCKED_EXIT_CODE
    )
    assert debug_loop_inventory._completion_blocked_exit_code(inventory, False) == 0
    assert (
        debug_loop_inventory._completion_blocked_exit_code(
            {"summary": {"completion_allowed": True}},
            True,
        )
        == 0
    )

    file_path = tmp_path / "regenerated.json"
    file_path.write_text("stale", encoding="utf-8")
    debug_loop_inventory._discard_regenerated_file(file_path)
    assert not file_path.exists()
    first_regenerated_path = tmp_path / "regenerated-one.json"
    second_regenerated_path = tmp_path / "regenerated-two.md"
    missing_regenerated_path = tmp_path / "missing-regenerated.json"
    first_regenerated_path.write_text("stale one", encoding="utf-8")
    second_regenerated_path.write_text("stale two", encoding="utf-8")
    debug_loop_inventory._discard_regenerated_files(
        first_regenerated_path,
        missing_regenerated_path,
        second_regenerated_path,
    )
    assert not first_regenerated_path.exists()
    assert not missing_regenerated_path.exists()
    assert not second_regenerated_path.exists()
    assert debug_loop_inventory._dirty_handoff_plan_refresh_paths(tmp_path) == (
        tmp_path / debug_loop_inventory.DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH,
        tmp_path / debug_loop_inventory.DEFAULT_DIRTY_HANDOFF_PLAN_REFRESH_MD,
    )
    assert debug_loop_inventory._dirty_handoff_plan_paths(tmp_path) == (
        tmp_path / debug_loop_inventory.DEFAULT_DIRTY_HANDOFF_PLAN,
        tmp_path / debug_loop_inventory.DEFAULT_DIRTY_HANDOFF_PLAN_MD,
    )


def test_direct_input_and_completion_helpers_preserve_cli_contract(tmp_path: Path) -> None:
    session_path = Path("session.json")
    selector_path = Path("selector.json")
    readiness_path = Path("readiness.json")
    completion_path = Path("completion.json")
    dirty_plan_path = Path("dirty-plan.json")
    args = SimpleNamespace(
        session_orient=session_path,
        selector=selector_path,
        readiness=None,
        completion_audit=None,
        dirty_handoff_plan=dirty_plan_path,
    )

    provided_paths = debug_loop_inventory._provided_input_paths(args)
    assert debug_loop_inventory._PROVIDED_INPUT_KEYS == (
        "session_orient",
        "selector",
        "readiness",
        "completion_audit",
        "dirty_handoff_plan",
    )
    assert debug_loop_inventory._session_orient_command() == [
        sys.executable,
        "execution/session_orient.py",
        "--json",
    ]
    assert debug_loop_inventory._next_experiment_selector_command() == [
        sys.executable,
        ".agents/skills/auto-research/scripts/next_experiment_selector.py",
        "--root",
        ".",
        "--dirty-handoff-plan",
        str(debug_loop_inventory.DEFAULT_DIRTY_HANDOFF_PLAN),
        "--json",
    ]
    assert debug_loop_inventory._product_readiness_command() == [
        sys.executable,
        "execution/product_readiness_score.py",
        "--json",
    ]
    assert provided_paths == {
        "session_orient": session_path,
        "selector": selector_path,
        "readiness": None,
        "completion_audit": None,
        "dirty_handoff_plan": dirty_plan_path,
    }
    parsed_args = debug_loop_inventory._inventory_args_from_argv(
        [
            "--session-orient",
            str(session_path),
            "--selector",
            str(selector_path),
            "--readiness",
            str(readiness_path),
            "--completion-audit",
            str(completion_path),
            "--dirty-handoff-plan",
            str(dirty_plan_path),
        ]
    )
    assert debug_loop_inventory._provided_input_paths(parsed_args) == {
        "session_orient": session_path,
        "selector": selector_path,
        "readiness": readiness_path,
        "completion_audit": completion_path,
        "dirty_handoff_plan": dirty_plan_path,
    }
    assert debug_loop_inventory._all_input_paths_provided(debug_loop_inventory._provided_input_paths(parsed_args))
    assert not debug_loop_inventory._all_input_paths_provided(provided_paths)
    assert parsed_args.output_md == debug_loop_inventory.DEFAULT_OUTPUT_MD
    assert parsed_args.output_json == debug_loop_inventory.DEFAULT_OUTPUT_JSON
    assert parsed_args.timeout == 60
    assert parsed_args.json is False
    assert parsed_args.fail_on_completion_blocked is False
    assert parsed_args.root == Path(".")
    assert debug_loop_inventory._inventory_args_from_argv([]).root == Path(".")

    custom_root = Path("workspace-root")
    root_args = debug_loop_inventory._inventory_args_from_argv(["--root", str(custom_root)])
    assert root_args.root == custom_root
    absolute_root_args = SimpleNamespace(root=tmp_path / "workspace-root")
    assert debug_loop_inventory._inventory_root_from_args(absolute_root_args) == absolute_root_args.root.resolve()

    custom_output_md = Path("custom-debug.md")
    custom_output_json = Path("custom-debug.json")
    output_args = debug_loop_inventory._build_arg_parser().parse_args(
        [
            "--output-md",
            str(custom_output_md),
            "--output-json",
            str(custom_output_json),
        ]
    )
    assert output_args.output_md == custom_output_md
    assert output_args.output_json == custom_output_json

    control_args = debug_loop_inventory._build_arg_parser().parse_args(
        [
            "--timeout",
            "5",
            "--json",
            "--fail-on-completion-blocked",
        ]
    )
    assert control_args.timeout == 5
    assert control_args.json is True
    assert control_args.fail_on_completion_blocked is True

    (tmp_path / session_path).write_text(json.dumps({"git": {"branch": "main"}}), encoding="utf-8")
    absolute_selector = tmp_path / selector_path
    absolute_selector.write_text(json.dumps({"status": "blocked"}), encoding="utf-8")
    loaded_inputs = debug_loop_inventory._load_provided_inputs(
        tmp_path,
        {
            "session_orient": session_path,
            "selector": absolute_selector,
            "readiness": None,
        },
    )
    assert loaded_inputs == {
        "session_orient": {"git": {"branch": "main"}},
        "selector": {"status": "blocked"},
    }
    collected_inputs = {
        "session_orient": {"git": {"branch": "main"}},
        "selector": {"status": "collected"},
    }
    applied_inputs = debug_loop_inventory._apply_provided_input_overrides(
        collected_inputs,
        {"selector": {"status": "provided"}},
    )
    assert applied_inputs is collected_inputs
    assert collected_inputs == {
        "session_orient": {"git": {"branch": "main"}},
        "selector": {"status": "provided"},
    }

    merged_error = debug_loop_inventory._add_input_error({"status": "stale"}, {"reason": "helper failed"})
    assert merged_error == {"status": "stale", "_input_error": {"reason": "helper failed"}}
    error_inputs = debug_loop_inventory.InventoryBuildInputs(
        session_orient=debug_loop_inventory._input_error_payload(
            "empty helper output",
            returncode=2,
            detail="no stdout",
        ),
        selector={},
        readiness={},
        completion_audit={},
        dirty_handoff_plan={},
    )
    assert debug_loop_inventory._inventory_input_error_lines(error_inputs) == [
        "session_orient: empty helper output; returncode=2; detail=no stdout"
    ]
    ordered_error_inputs = debug_loop_inventory.InventoryBuildInputs(
        session_orient=debug_loop_inventory._input_error_payload("session failed"),
        selector=debug_loop_inventory._input_error_payload("selector failed"),
        readiness={},
        completion_audit=debug_loop_inventory._input_error_payload("audit failed"),
        dirty_handoff_plan=debug_loop_inventory._input_error_payload("handoff failed"),
    )
    assert debug_loop_inventory._inventory_input_error_lines(ordered_error_inputs) == [
        "session_orient: session failed",
        "selector: selector failed",
        "completion_audit: audit failed",
        "dirty_handoff_plan: handoff failed",
    ]
    input_items: list[dict[str, object]] = []
    assert debug_loop_inventory._append_input_evidence_item(input_items, inputs=error_inputs) == [
        "session_orient: empty helper output; returncode=2; detail=no stdout"
    ]
    assert input_items[0]["title"] == "Debug Inventory Input Evidence Is Unavailable"
    assert debug_loop_inventory._selector_kind(_selector()) == "dirty_worktree_handoff_current"
    assert debug_loop_inventory._selector_kind({"summary": {"selected_kind": "fallback_kind"}}) == "fallback_kind"
    assert debug_loop_inventory.completion_is_blocked({"summary": {"completion_allowed": True}}) is False
    assert debug_loop_inventory.completion_is_blocked({"summary": {"completion_allowed": False}}) is True


def test_task_workflow_and_dirty_group_helpers_normalize_contracts() -> None:
    assert debug_loop_inventory._user_task_ids(
        {
            "tasks": [
                {"id": "T-252", "owner": "user"},
                {"id": "T-251", "owner": "User"},
                {"id": "T-251", "owner": "USER"},
                {"id": "T-999", "owner": "Codex"},
                {"id": "", "owner": "user"},
                "malformed",
            ]
        }
    ) == ["T-251", "T-252"]

    assert debug_loop_inventory._required_workflows(
        {
            "workspace_gates": {
                "github_release": {
                    "required_workflows": [
                        {"name": "root-quality-gate", "status": "missing", "conclusion": None},
                        {"name": "active-project-matrix", "status": "", "conclusion": "success"},
                        {"name": "", "status": "completed", "conclusion": "success"},
                        "malformed",
                    ]
                }
            }
        }
    ) == ["root-quality-gate=missing:none", "active-project-matrix=unknown:success"]

    assert (
        debug_loop_inventory._dirty_group_summary(
            {
                "group_order": [
                    {"key": "auto-research", "path_count": "7"},
                    {"key": "project:blind-to-x", "path_count": None},
                    {"key": "", "path_count": 5},
                    "malformed",
                ]
            }
        )
        == "auto-research=7, project:blind-to-x=0"
    )
    assert debug_loop_inventory._dirty_group_summary({"group_order": []}) == "unknown"


def test_basic_value_helpers_normalize_malformed_evidence() -> None:
    original_dict = {"state": "blocked"}
    original_list = ["root-quality-gate"]

    assert debug_loop_inventory._as_dict(original_dict) is original_dict
    assert debug_loop_inventory._as_dict(["not", "a", "dict"]) == {}
    assert debug_loop_inventory._as_list(original_list) is original_list
    assert debug_loop_inventory._as_list({"not": "a list"}) == []

    assert debug_loop_inventory._int("7") == 7
    assert debug_loop_inventory._int(None) == 0
    assert debug_loop_inventory._int("") == 0
    assert debug_loop_inventory._int("not-a-number") == 0

    assert debug_loop_inventory._display(True) == "true"
    assert debug_loop_inventory._display(False) == "false"
    assert debug_loop_inventory._display(None) == "unknown"
    assert debug_loop_inventory._display("") == "unknown"
    assert debug_loop_inventory._display(" blocked\nby dirty tree ") == "blocked by dirty tree"


def test_path_and_project_helpers_resolve_safe_contracts(tmp_path: Path) -> None:
    absolute = tmp_path / "absolute.json"
    relative = Path(".tmp/current.json")

    assert debug_loop_inventory._resolve(tmp_path, None) is None
    assert debug_loop_inventory._resolve(tmp_path, absolute) == absolute
    assert debug_loop_inventory._resolve(tmp_path, relative) == tmp_path / relative

    matched = {"name": "hanwoo-dashboard", "state": "blocked"}
    readiness = {
        "projects": [
            "malformed",
            {"name": "blind-to-x", "state": "ready"},
            matched,
            {"name": "", "state": "ignored"},
        ]
    }

    assert debug_loop_inventory._project(readiness, "hanwoo-dashboard") is matched
    assert debug_loop_inventory._project(readiness, "missing-project") == {}
    assert debug_loop_inventory._project({"projects": "malformed"}, "hanwoo-dashboard") == {}


def test_inventory_output_path_preserves_relative_and_absolute_outputs(tmp_path: Path) -> None:
    relative_output = Path("nested/output.md")
    assert (
        debug_loop_inventory._inventory_output_path(
            tmp_path,
            relative_output,
            debug_loop_inventory.DEFAULT_OUTPUT_MD,
        )
        == tmp_path / relative_output
    )

    absolute_output = tmp_path / "absolute" / "output.json"
    assert (
        debug_loop_inventory._inventory_output_path(
            tmp_path,
            absolute_output,
            debug_loop_inventory.DEFAULT_OUTPUT_JSON,
        )
        == absolute_output
    )


def test_inventory_output_paths_resolves_markdown_and_json_outputs(tmp_path: Path) -> None:
    output_md, output_json = debug_loop_inventory._inventory_output_paths(
        tmp_path,
        Path("nested/output.md"),
        Path("nested/output.json"),
    )

    assert output_md == tmp_path / "nested" / "output.md"
    assert output_json == tmp_path / "nested" / "output.json"


def test_write_inventory_markdown_creates_parent_and_writes_rendered_content(tmp_path: Path) -> None:
    output_md = tmp_path / "nested" / "debug-loop.md"
    inventory = {
        "objective": "Confirm Markdown writer",
        "items": [],
        "summary": {"completion_allowed": True},
    }

    debug_loop_inventory._write_inventory_markdown(output_md, inventory)

    assert output_md.read_text(encoding="utf-8") == debug_loop_inventory.render_markdown(inventory)
    assert "# Debug Loop Known Bugs / Anomalies" in output_md.read_text(encoding="utf-8")


def test_write_inventory_json_creates_parent_and_writes_ascii_payload(tmp_path: Path) -> None:
    output_json = tmp_path / "nested" / "debug-loop.json"
    inventory = {"message": "한글", "items": [1]}

    debug_loop_inventory._write_inventory_json(output_json, inventory)

    payload = output_json.read_text(encoding="utf-8")
    assert json.loads(payload) == inventory
    assert "\\ud55c\\uae00" in payload
    assert payload.endswith("\n")


def test_json_payload_text_uses_shared_ascii_pretty_contract() -> None:
    inventory = {"message": "한글", "items": [1]}

    payload = debug_loop_inventory._json_payload_text(inventory)

    assert payload == json.dumps(inventory, ensure_ascii=True, indent=2) + "\n"
    assert "\\ud55c\\uae00" in payload


def test_inventory_output_status_lines_name_written_artifacts(tmp_path: Path) -> None:
    output_md = tmp_path / ".tmp" / "debug-loop-known-bugs-current.md"
    output_json = tmp_path / ".tmp" / "debug-loop-known-bugs-current.json"

    assert debug_loop_inventory._inventory_output_status_lines(output_md, output_json) == [
        "status: generated",
        f"markdown: {output_md}",
        f"json: {output_json}",
    ]


def test_emit_inventory_status_prints_written_artifact_paths(capsys, tmp_path: Path) -> None:
    output_md = tmp_path / ".tmp" / "debug-loop-known-bugs-current.md"
    output_json = tmp_path / ".tmp" / "debug-loop-known-bugs-current.json"

    debug_loop_inventory._emit_inventory_status(output_md, output_json)
    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out.splitlines() == [
        "status: generated",
        f"markdown: {output_md}",
        f"json: {output_json}",
    ]


def test_emit_inventory_json_prints_ascii_pretty_payload(capsys) -> None:
    inventory = {"message": "한글", "items": [1]}

    debug_loop_inventory._emit_inventory_json(inventory)
    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert captured.out.startswith("{\n  ")
    assert "\\ud55c\\uae00" in captured.out
    assert json.loads(captured.out) == inventory


def test_emit_completion_blocked_message_only_writes_when_exit_code_is_nonzero(capsys) -> None:
    inventory = {
        "items": [
            {
                "title": "Dirty handoff",
                "status": "reproduced, blocked",
                "next_action": "wait",
                "blockers": ["authorization required"],
            }
        ]
    }

    assert debug_loop_inventory._completion_blocked_stderr_line(inventory, 0) is None
    assert (
        debug_loop_inventory._completion_blocked_stderr_line(
            inventory,
            debug_loop_inventory.COMPLETION_BLOCKED_EXIT_CODE,
        )
        == "completion blocked: blocked; next_required_action=wait"
    )

    debug_loop_inventory._emit_completion_blocked_message(inventory, 0)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    debug_loop_inventory._emit_completion_blocked_message(
        inventory,
        debug_loop_inventory.COMPLETION_BLOCKED_EXIT_CODE,
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "completion blocked: blocked; next_required_action=wait\n"


def test_run_inventory_from_args_writes_outputs_and_returns_exit_code(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    root_arg = tmp_path / "workspace-root"
    output_md_arg = Path("debug-loop.md")
    output_json_arg = Path("debug-loop.json")
    args = SimpleNamespace(
        root=root_arg,
        output_md=output_md_arg,
        output_json=output_json_arg,
        json=False,
        fail_on_completion_blocked=False,
    )
    inventory = {
        "objective": "Confirm run-from-args orchestration",
        "items": [],
        "summary": {"completion_allowed": True},
    }
    observed: dict[str, object] = {}

    def fake_build_inventory_from_args(root: Path, received_args: SimpleNamespace) -> dict[str, object]:
        observed["root"] = root
        observed["args"] = received_args
        return inventory

    monkeypatch.setattr(debug_loop_inventory, "_build_inventory_from_args", fake_build_inventory_from_args)

    exit_code = debug_loop_inventory._run_inventory_from_args(args)

    output_md = root_arg.resolve() / output_md_arg
    output_json = root_arg.resolve() / output_json_arg
    captured = capsys.readouterr()
    assert exit_code == 0
    assert observed == {"root": root_arg.resolve(), "args": args}
    assert captured.err == ""
    assert captured.out.splitlines() == [
        "status: generated",
        f"markdown: {output_md}",
        f"json: {output_json}",
    ]
    assert output_md.read_text(encoding="utf-8") == debug_loop_inventory.render_markdown(inventory)
    assert json.loads(output_json.read_text(encoding="utf-8")) == inventory
