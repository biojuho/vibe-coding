from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.context_selector import ContextSelector, ContextProfile  # noqa: E402
from execution.repo_map import RepoMapBuilder, RepoMapEntry  # noqa: E402


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


def test_repo_map_persistent_cache_survives_new_builder(tmp_path: Path) -> None:
    target = tmp_path / "workspace" / "execution" / "graph_engine.py"
    _write(
        target,
        '"""Graph orchestration."""\n\nclass VibeCodingGraph:\n    pass\n',
    )
    cache_db_path = tmp_path / ".tmp" / "repo_map_cache.db"

    builder = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",), cache_db_path=cache_db_path)
    seeded = builder.build("graph engine orchestration", max_files=5)

    assert seeded
    assert builder.cache_stats()["disk_writes"] >= 1

    second_builder = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",), cache_db_path=cache_db_path)
    with patch.object(RepoMapBuilder, "_analyze_python_text", side_effect=AssertionError("cache should satisfy read")):
        cached = second_builder.build("graph engine orchestration", max_files=5)

    assert cached
    assert second_builder.cache_stats()["disk_hits"] >= 1


def test_repo_map_persistent_cache_invalidates_on_file_change(tmp_path: Path) -> None:
    target = tmp_path / "workspace" / "execution" / "graph_engine.py"
    _write(
        target,
        '"""Graph orchestration."""\n\nclass OldGraph:\n    pass\n',
    )
    cache_db_path = tmp_path / ".tmp" / "repo_map_cache.db"

    builder = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",), cache_db_path=cache_db_path)
    builder.build("graph orchestration", max_files=5)

    time.sleep(0.01)
    _write(
        target,
        '"""Graph orchestration updated."""\n\nclass NewGraph:\n    pass\n',
    )
    os.utime(target, None)

    second_builder = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",), cache_db_path=cache_db_path)
    with patch.object(RepoMapBuilder, "_analyze_python_text", wraps=RepoMapBuilder._analyze_python_text) as parser:
        refreshed = second_builder.build("updated graph orchestration", max_files=5)

    assert refreshed
    assert "NewGraph" in refreshed[0].symbols
    assert parser.call_count >= 1
    assert second_builder.cache_stats()["disk_hits"] == 0
    assert second_builder.cache_stats()["disk_writes"] >= 1


def test_context_profile_overrides(tmp_path: Path) -> None:
    _write(tmp_path / "workspace" / "foo.py", "def bar(): pass")
    cb = ContextProfile.CODER.default_budget
    assert cb == 4000
    db = ContextProfile.DEFAULT.default_budget
    assert db == 2800

    selector = ContextSelector(repo_map=RepoMapBuilder(repo_root=tmp_path))
    selected = selector.select("query", include_roots=("workspace",), profile=ContextProfile.CODER)
    assert selected is not None


def test_context_selector_adaptive_pruning(tmp_path: Path) -> None:
    # Build a file with lots of summary, symbols, imports
    content = '"""A very long summary ' + "x " * 50 + '"""\n'
    for i in range(20):
        content += f"import mod_{i}\n"
    for i in range(20):
        content += f"def func_{i}(): pass\n"

    _write(tmp_path / "workspace" / "mega.py", content)

    selector = ContextSelector(repo_map=RepoMapBuilder(repo_root=tmp_path))

    # Try with a small budget that forces pruning but leaves just enough for basic info
    selected_pruned = selector.select("mega", budget_chars=180, include_roots=("workspace",))
    assert selected_pruned.files == ["workspace/mega.py"]
    text = selected_pruned.text
    # Symbols or imports should be pruned
    assert "Imports:" not in text or "Symbols:" not in text
    assert not selected_pruned.truncated


def test_context_selector_truncates(tmp_path: Path) -> None:
    _write(tmp_path / "workspace" / "aaa.py", "pass")
    _write(tmp_path / "workspace" / "bbb.py", "pass")
    selector = ContextSelector(repo_map=RepoMapBuilder(repo_root=tmp_path))

    # Budget small enough that one file fits but two do not
    selected = selector.select("aaa bbb", budget_chars=130, include_roots=("workspace",))
    assert selected.truncated
    assert len(selected.files) == 1


def test_infer_roots(tmp_path: Path) -> None:
    p_dir = tmp_path / "projects" / "testme"
    p_dir.mkdir(parents=True)

    selector = ContextSelector(repo_map=RepoMapBuilder(repo_root=tmp_path))
    roots = selector._infer_roots("mcp handling in testme", "")
    assert "infrastructure" in roots
    assert "projects" in roots
    assert "workspace" not in roots

    roots_2 = selector._infer_roots("graph_engine and projects/some", "")
    assert "workspace" in roots_2
    assert "projects" in roots_2

    roots_3 = selector._infer_roots("random stuff", "")
    assert roots_3 == ("workspace",)


def test_repo_map_scoring_profiles(tmp_path: Path) -> None:
    builder = RepoMapBuilder(repo_root=tmp_path)
    entry = RepoMapEntry(
        relative_path="workspace/tests/test_x.py",
        absolute_path=tmp_path,
        language="python",
        line_count=10,
        module_summary="",
        imports=["typing"],
    )

    score, reasons = builder._score_entry(entry, {"test", "typing"}, set(), profile_name="tester")
    assert score >= 3.0
    assert any("import" in r for r in reasons)

    entry2 = RepoMapEntry(
        relative_path="workspace/y.py", absolute_path=tmp_path, language="python", line_count=1, module_summary=""
    )
    score_rev, reasons_rev = builder._score_entry(entry2, {"something"}, {"workspace/y.py"}, profile_name="reviewer")
    assert score_rev >= 5.0

    score_def, _ = builder._score_entry(entry2, {"something"}, {"workspace/y.py"}, profile_name="")
    assert score_def > 0


def test_repo_map_non_python_and_file_root(tmp_path: Path) -> None:
    target = tmp_path / "workspace" / "file.md"
    _write(target, "# Title\nexport class Item {}\nimport { xyz } from 'mod';")

    # Test setting include_roots to exactly a file
    builder = RepoMapBuilder(repo_root=tmp_path, include_roots=["workspace/file.md"])
    entries = builder.build("item xyz")

    assert len(entries) == 1
    assert "Item" in entries[0].symbols
    assert "mod" in entries[0].imports


def test_repo_map_fallback_changed(tmp_path: Path) -> None:
    _write(tmp_path / "workspace" / "extra.py", "pass")
    builder = RepoMapBuilder(repo_root=tmp_path, include_roots=("workspace",))

    # query unmatched but changed_files forces it
    entries = builder.build("unmatched_query", changed_files=["workspace/extra.py"])
    assert len(entries) == 1
    assert entries[0].relative_path == "workspace/extra.py"
    assert "working tree change" in entries[0].reasons


def test_limits_hit(tmp_path: Path) -> None:
    for i in range(5):
        _write(tmp_path / "workspace" / f"foo{i}.py", "pass")
    selector = ContextSelector(repo_map=RepoMapBuilder(repo_root=tmp_path))
    # Test limit directly
    selected = selector.select("foo1 foo2 foo3", max_files=2, include_roots=("workspace",))
    assert len(selected.files) == 2
    assert selected.truncated
