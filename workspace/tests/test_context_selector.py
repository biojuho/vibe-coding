from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.context_selector import ContextSelector
from execution.repo_map import RepoMapBuilder


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_repo_map_ranks_relevant_workspace_files(tmp_path: Path) -> None:
    _write(
        tmp_path / "workspace" / "execution" / "graph_engine.py",
        '"""Graph orchestration."""\n\nclass VibeCodingGraph:\n    pass\n',
    )
    _write(
        tmp_path / "workspace" / "execution" / "workers.py",
        '"""Worker helpers."""\n\ndef helper() -> None:\n    pass\n',
    )
    builder = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",))

    result = builder.build("Improve graph engine context selection", max_files=5)

    assert result
    assert result[0].relative_path == "workspace/execution/graph_engine.py"
    assert any(reason.startswith("path:graph") or reason.startswith("summary:graph") for reason in result[0].reasons)


def test_context_selector_stays_within_budget(tmp_path: Path) -> None:
    _write(
        tmp_path / "workspace" / "execution" / "context_selector.py",
        '"""Selects repository context for graph tasks."""\n\nclass ContextSelector:\n    pass\n',
    )
    _write(
        tmp_path / "workspace" / "execution" / "repo_map.py",
        '"""Builds compact repository maps."""\n\nclass RepoMapBuilder:\n    pass\n',
    )
    selector = ContextSelector(
        repo_map=RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",)),
        budget_chars=260,
        max_files=2,
    )

    selected = selector.select("Add context selector and repo map", include_roots=("workspace",))

    assert selected.files
    assert len(selected.text) <= 380
    assert all(path.startswith("workspace/") for path in selected.files)


def test_context_selector_surfaces_relevant_changed_files(tmp_path: Path) -> None:
    _write(
        tmp_path / "workspace" / "execution" / "graph_engine.py",
        '"""Graph orchestration."""\n\nclass VibeCodingGraph:\n    pass\n',
    )
    _write(
        tmp_path / "workspace" / "execution" / "context_selector.py",
        '"""Context selection helpers."""\n\nclass ContextSelector:\n    pass\n',
    )
    repo_map = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",))
    repo_map.collect_changed_files = lambda: {"workspace/execution/context_selector.py"}  # type: ignore[method-assign]
    selector = ContextSelector(repo_map=repo_map, budget_chars=1200, max_files=3)

    selected = selector.select("Update context selector for graph tasks", include_roots=("workspace",))

    assert "workspace/execution/context_selector.py" in selected.files
    assert "Relevant working tree changes" in selected.text
