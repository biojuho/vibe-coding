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


def test_index_table_state_detects_sections_and_reset() -> None:
    assert gc._index_table_state("| Directive | Execution Script(s) | Notes |") == (True, False)
    assert gc._index_table_state("| Script | Type | Purpose |") == (False, True)
    assert gc._index_table_state("## SOP → Execution Mapping") == (True, False)
    assert gc._index_table_state("## 매핑 없는 Execution Scripts") == (False, True)
    assert gc._index_table_state("---") == (False, False)
    assert gc._index_table_state("plain text") is None


def test_index_row_cells_ignores_non_data_rows() -> None:
    assert gc._index_row_cells("not a table") is None
    assert gc._index_row_cells("|--------|------|") is None
    assert gc._index_row_cells("| a | b |") == ["a", "b"]


def test_index_script_names_keeps_python_scripts_only() -> None:
    scripts = gc._index_script_names("`one.py`, docs.md; two.py → nested/three.py")

    assert scripts == ["one.py", "two.py", "nested/three.py"]


def test_mapped_script_candidates_include_workspace_and_repo_roots(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = repo_root / "workspace"
    execution_dir = workspace_root / "execution"

    candidates = gc._mapped_script_candidates(
        "tool.py",
        execution_dir=execution_dir,
        root=workspace_root,
        repo_root=repo_root,
    )

    assert candidates == [
        execution_dir / "tool.py",
        workspace_root / "tool.py",
        repo_root / "tool.py",
        repo_root / "execution" / "tool.py",
    ]


def test_mapped_and_unmapped_script_issues_report_missing_files(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    execution_dir = workspace_root / "execution"
    execution_dir.mkdir(parents=True)
    (execution_dir / "present.py").write_text("print('ok')\n", encoding="utf-8")

    mapped_scripts, mapped_issues = gc._mapped_script_issues(
        {"present.md": ["present.py"], "missing.md": ["missing.py"]},
        execution_dir=execution_dir,
        root=workspace_root,
        repo_root=tmp_path,
    )
    unmapped_scripts, unmapped_issues = gc._unmapped_script_issues(
        {"present.py": "utility", "missing_unmapped.py": "utility"},
        execution_dir,
    )

    assert mapped_scripts == {"present.py", "missing.py"}
    assert mapped_issues == ["[SCRIPT MISSING] missing.py (mapped by missing.md)"]
    assert unmapped_scripts == {"present.py", "missing_unmapped.py"}
    assert unmapped_issues == ["[UNMAPPED MISSING] missing_unmapped.py listed as unmapped but not found"]


def test_directive_mapping_detail_status() -> None:
    assert gc._directive_mapping_detail_status(2, 1, 0) == (
        "Checked 2 SOP mappings, 1 unmapped scripts; no mapping drift detected",
        gc.STATUS_OK,
    )
    assert gc._directive_mapping_detail_status(2, 1, 3) == (
        "Checked 2 SOP mappings, 1 unmapped scripts; found 3 issue(s)",
        gc.STATUS_FAIL,
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
