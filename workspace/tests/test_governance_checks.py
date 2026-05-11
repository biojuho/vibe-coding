from __future__ import annotations

from pathlib import Path

import execution.governance_checks as gc


def _index_text(rows: list[str]) -> str:
    return "\n".join(
        [
            "## SOP to Execution Mapping",
            "",
            "| Directive | Execution Script(s) | Notes |",
            "|-----------|---------------------|------|",
            *rows,
            "",
            "---",
            "",
            "## Unmapped Execution Scripts",
            "",
            "| Script | Type | Purpose |",
            "|--------|------|------|",
        ]
    )


def test_audit_directive_mapping_detects_orphan_script(tmp_path: Path) -> None:
    directives_dir = tmp_path / "directives"
    execution_dir = tmp_path / "execution"
    directives_dir.mkdir()
    execution_dir.mkdir()

    (directives_dir / "INDEX.md").write_text(
        _index_text(["| local_inference.md | local_inference.py | test |"]),
        encoding="utf-8",
    )
    (directives_dir / "local_inference.md").write_text("# local inference", encoding="utf-8")
    (execution_dir / "local_inference.py").write_text("print('ok')\n", encoding="utf-8")
    (execution_dir / "orphan.py").write_text("print('orphan')\n", encoding="utf-8")

    result = gc.audit_directive_mapping(
        index_path=directives_dir / "INDEX.md",
        directives_dir=directives_dir,
        execution_dir=execution_dir,
        root=tmp_path,
    )

    assert result["status"] == gc.STATUS_FAIL
    assert any("orphan.py" in issue for issue in result["issues"])


def test_audit_directive_mapping_passes_when_index_is_complete(tmp_path: Path) -> None:
    directives_dir = tmp_path / "directives"
    execution_dir = tmp_path / "execution"
    directives_dir.mkdir()
    execution_dir.mkdir()

    index_text = _index_text(["| local_inference.md | local_inference.py | test |"])
    index_text += "\n| helper.py | utility | helper |"
    (directives_dir / "INDEX.md").write_text(index_text, encoding="utf-8")
    (directives_dir / "local_inference.md").write_text("# local inference", encoding="utf-8")
    (execution_dir / "local_inference.py").write_text("print('ok')\n", encoding="utf-8")
    (execution_dir / "helper.py").write_text("print('helper')\n", encoding="utf-8")

    result = gc.audit_directive_mapping(
        index_path=directives_dir / "INDEX.md",
        directives_dir=directives_dir,
        execution_dir=execution_dir,
        root=tmp_path,
    )

    assert result["status"] == gc.STATUS_OK
    assert result["issues"] == []


def test_audit_directive_mapping_accepts_repo_root_execution_scripts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = repo_root / "workspace"
    directives_dir = workspace_root / "directives"
    workspace_execution_dir = workspace_root / "execution"
    root_execution_dir = repo_root / "execution"
    directives_dir.mkdir(parents=True)
    workspace_execution_dir.mkdir()
    root_execution_dir.mkdir()

    (directives_dir / "INDEX.md").write_text(
        _index_text(["| root_tooling.md | root_tool.py | root execution script |"]),
        encoding="utf-8",
    )
    (directives_dir / "root_tooling.md").write_text("# root tooling", encoding="utf-8")
    (root_execution_dir / "root_tool.py").write_text("print('ok')\n", encoding="utf-8")

    result = gc.audit_directive_mapping(
        index_path=directives_dir / "INDEX.md",
        directives_dir=directives_dir,
        execution_dir=workspace_execution_dir,
        root=workspace_root,
    )

    assert result["status"] == gc.STATUS_OK
    assert result["issues"] == []


def test_audit_directive_mapping_accepts_repo_root_targets(tmp_path: Path) -> None:
    repo_root = tmp_path
    workspace_root = repo_root / "workspace"
    directives_dir = workspace_root / "directives"
    execution_dir = workspace_root / "execution"
    root_execution_dir = repo_root / "execution"
    project_dir = repo_root / "projects" / "blind-to-x" / "pipeline"
    directives_dir.mkdir(parents=True)
    execution_dir.mkdir()
    root_execution_dir.mkdir()
    project_dir.mkdir(parents=True)

    (directives_dir / "INDEX.md").write_text(
        _index_text(["| eval.md | execution/run_eval.py, projects/blind-to-x/pipeline/draft_providers.py | test |"]),
        encoding="utf-8",
    )
    (directives_dir / "eval.md").write_text("# eval", encoding="utf-8")
    (root_execution_dir / "run_eval.py").write_text("print('ok')\n", encoding="utf-8")
    (project_dir / "draft_providers.py").write_text("print('ok')\n", encoding="utf-8")

    result = gc.audit_directive_mapping(
        index_path=directives_dir / "INDEX.md",
        directives_dir=directives_dir,
        execution_dir=execution_dir,
        root=workspace_root,
    )

    assert result["status"] == gc.STATUS_OK
    assert result["issues"] == []


def test_audit_relay_claim_consistency_fails_on_stale_claim(tmp_path: Path) -> None:
    ai_dir = tmp_path / ".ai"
    execution_dir = tmp_path / "execution"
    ai_dir.mkdir()
    execution_dir.mkdir()

    handoff_path = ai_dir / "HANDOFF.md"
    handoff_path.write_text(
        "- `workspace/execution/code_evaluator.py` integrated into `graph_engine.py`\n",
        encoding="utf-8",
    )
    (execution_dir / "graph_engine.py").write_text("def run_graph():\n    return 'ok'\n", encoding="utf-8")

    result = gc.audit_relay_claim_consistency(
        handoff_path=handoff_path,
        claim_specs=(
            {
                "name": "code_evaluator_graph_engine_integration",
                "claim_pattern": gc.RELAY_CLAIM_SPECS[0]["claim_pattern"],
                "proof_path": execution_dir / "graph_engine.py",
                "proof_patterns": gc.RELAY_CLAIM_SPECS[0]["proof_patterns"],
                "failure_detail": gc.RELAY_CLAIM_SPECS[0]["failure_detail"],
            },
        ),
    )

    assert result["status"] == gc.STATUS_FAIL
    assert any("CodeEvaluator" in issue for issue in result["issues"])


def test_audit_relay_claim_consistency_passes_when_claim_matches_code(tmp_path: Path) -> None:
    ai_dir = tmp_path / ".ai"
    execution_dir = tmp_path / "execution"
    ai_dir.mkdir()
    execution_dir.mkdir()

    handoff_path = ai_dir / "HANDOFF.md"
    handoff_path.write_text(
        "- `workspace/execution/code_evaluator.py` integrated into `graph_engine.py`\n",
        encoding="utf-8",
    )
    (execution_dir / "graph_engine.py").write_text(
        "from execution.code_evaluator import CodeEvaluator\nevaluator = CodeEvaluator(llm_client=None)\n",
        encoding="utf-8",
    )

    result = gc.audit_relay_claim_consistency(
        handoff_path=handoff_path,
        claim_specs=(
            {
                "name": "code_evaluator_graph_engine_integration",
                "claim_pattern": gc.RELAY_CLAIM_SPECS[0]["claim_pattern"],
                "proof_path": execution_dir / "graph_engine.py",
                "proof_patterns": gc.RELAY_CLAIM_SPECS[0]["proof_patterns"],
                "failure_detail": gc.RELAY_CLAIM_SPECS[0]["failure_detail"],
            },
        ),
    )

    assert result["status"] == gc.STATUS_OK
    assert result["checked_claims"] == ["code_evaluator_graph_engine_integration"]


def test_audit_task_backlog_alignment_fails_without_task_link(tmp_path: Path) -> None:
    tasks_path = tmp_path / "TASKS.md"
    tracked_path = tmp_path / "plan.md"

    tasks_path.write_text(
        "\n".join(
            [
                "## TODO",
                "",
                "| ID | Task | Owner | Priority | Created |",
                "|----|------|-------|----------|---------|",
                "| T-100 | Example task | Codex | High | 2026-03-31 |",
            ]
        ),
        encoding="utf-8",
    )
    tracked_path.write_text("- [ ] open follow-up without task ref\n", encoding="utf-8")

    result = gc.audit_task_backlog_alignment(
        tasks_path=tasks_path,
        tracked_files=(tracked_path,),
    )

    assert result["status"] == gc.STATUS_FAIL
    assert "missing [TASK: T-XXX]" in result["detail"]


def test_audit_task_backlog_alignment_passes_with_active_task_refs(tmp_path: Path) -> None:
    tasks_path = tmp_path / "TASKS.md"
    tracked_path = tmp_path / "plan.md"

    tasks_path.write_text(
        "\n".join(
            [
                "## TODO",
                "",
                "| ID | Task | Owner | Priority | Created |",
                "|----|------|-------|----------|---------|",
                "| T-100 | Example task | Codex | High | 2026-03-31 |",
                "",
                "## IN_PROGRESS",
                "",
                "| ID | Task | Owner | Started | Notes |",
                "|----|------|-------|---------|-------|",
            ]
        ),
        encoding="utf-8",
    )
    tracked_path.write_text("- [ ] linked follow-up [TASK: T-100]\n", encoding="utf-8")

    result = gc.audit_task_backlog_alignment(
        tasks_path=tasks_path,
        tracked_files=(tracked_path,),
    )

    assert result["status"] == gc.STATUS_OK
    assert "T-100" in result["detail"]
