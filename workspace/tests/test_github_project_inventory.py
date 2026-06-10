from __future__ import annotations

import importlib.util
import json
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / ".agents"
    / "skills"
    / "auto-research"
    / "scripts"
    / "github_project_inventory.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("github_project_inventory_for_test", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


inventory = _load_module()


def test_inventory_recommends_root_readme_for_project_with_only_docs_readme(tmp_path: Path) -> None:
    root = tmp_path
    (root / ".git").mkdir()
    projects_dir = root / "projects"
    project = projects_dir / "shorts-maker-v2"
    docs = project / "docs"
    docs.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname='shorts-maker-v2'\n", encoding="utf-8")
    (docs / "README.md").write_text("# Detailed docs\n", encoding="utf-8")

    summary = inventory.build_inventory(root, include_prs=False)

    assert summary["projects"][0]["path"] == "projects/shorts-maker-v2"
    assert summary["projects"][0]["has_readme"] is False
    assert any(
        "projects/shorts-maker-v2" in recommendation and "root README.md" in recommendation
        for recommendation in summary["recommendations"]
    )


def test_inventory_accepts_project_root_readme(tmp_path: Path) -> None:
    root = tmp_path
    (root / ".git").mkdir()
    projects_dir = root / "projects"
    project = projects_dir / "shorts-maker-v2"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname='shorts-maker-v2'\n", encoding="utf-8")
    (project / "README.md").write_text("# Shorts Maker V2\n", encoding="utf-8")

    summary = inventory.build_inventory(root, include_prs=False)

    assert summary["projects"][0]["has_readme"] is True
    assert not any("root README.md" in recommendation for recommendation in summary["recommendations"])


def test_inventory_detects_node_colocated_tests_and_test_script(tmp_path: Path) -> None:
    root = tmp_path
    projects_dir = root / "projects"
    project = projects_dir / "hanwoo-dashboard"
    tests = project / "src" / "lib"
    tests.mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"scripts": {"test": 'node --test "src/**/*.test.mjs"'}}),
        encoding="utf-8",
    )
    (project / "CLAUDE.md").write_text("# Hanwoo\n", encoding="utf-8")
    (tests / "weather.test.mjs").write_text("test('ok', () => {})\n", encoding="utf-8")

    summary = inventory.build_inventory(root, include_prs=False)

    project_summary = summary["projects"][0]
    assert project_summary["path"] == "projects/hanwoo-dashboard"
    assert project_summary["has_tests"] is True
    assert project_summary["has_package_test_script"] is True
    assert project_summary["test_file_count"] == 1
    assert project_summary["test_files"] == ["projects/hanwoo-dashboard/src/lib/weather.test.mjs"]


def test_inventory_ignores_default_npm_no_test_placeholder(tmp_path: Path) -> None:
    root = tmp_path
    projects_dir = root / "projects"
    project = projects_dir / "empty-node-app"
    project.mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}),
        encoding="utf-8",
    )

    summary = inventory.build_inventory(root, include_prs=False)

    project_summary = summary["projects"][0]
    assert project_summary["has_tests"] is False
    assert project_summary["has_package_test_script"] is False
    assert project_summary["test_file_count"] == 0


def test_inventory_detects_colocated_python_tests_without_test_dir(tmp_path: Path) -> None:
    root = tmp_path
    projects_dir = root / "projects"
    project = projects_dir / "python-pipeline"
    package = project / "pipeline"
    package.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname = 'python-pipeline'\n", encoding="utf-8")
    (package / "test_notes.txt").write_text("not a test module\n", encoding="utf-8")
    (package / "test_writer.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (package / "writer_test.py").write_text("def test_other():\n    assert True\n", encoding="utf-8")

    summary = inventory.build_inventory(root, include_prs=False)

    project_summary = summary["projects"][0]
    assert project_summary["has_tests"] is True
    assert project_summary["test_file_count"] == 2
    assert project_summary["test_files"] == [
        "projects/python-pipeline/pipeline/test_writer.py",
        "projects/python-pipeline/pipeline/writer_test.py",
    ]


def test_inventory_ignores_bare_exit_one_test_script(tmp_path: Path) -> None:
    root = tmp_path
    project = root / "projects" / "placeholder-node-app"
    project.mkdir(parents=True)
    (project / "package.json").write_text(json.dumps({"scripts": {"test": "exit 1"}}), encoding="utf-8")

    summary = inventory.build_inventory(root, include_prs=False)

    assert summary["projects"][0]["has_tests"] is False
    assert summary["projects"][0]["has_package_test_script"] is False


def test_inventory_does_not_duplicate_project_test_files_in_root_summary(tmp_path: Path) -> None:
    root = tmp_path
    (root / "package.json").write_text(json.dumps({"scripts": {"test": "pytest"}}), encoding="utf-8")
    project = root / "projects" / "word-chain"
    source = project / "src"
    source.mkdir(parents=True)
    (project / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run"}}), encoding="utf-8")
    (source / "gameLogic.test.js").write_text("test('ok', () => {})\n", encoding="utf-8")

    summary = inventory.build_inventory(root, include_prs=False)

    root_summary = next(project for project in summary["projects"] if project["path"] == ".")
    child_summary = next(project for project in summary["projects"] if project["path"] == "projects/word-chain")
    assert root_summary["test_file_count"] == 0
    assert root_summary["test_files"] == []
    assert child_summary["test_file_count"] == 1
    assert child_summary["test_files"] == ["projects/word-chain/src/gameLogic.test.js"]


def test_test_scan_helpers_preserve_root_projects_and_hidden_file_rules(tmp_path: Path) -> None:
    root = tmp_path
    projects = root / "projects"
    hidden_file = root / ".hidden_test.py"
    test_file = root / "test_visible.py"
    projects.mkdir()
    hidden_file.write_text("def test_hidden():\n    assert True\n", encoding="utf-8")
    test_file.write_text("def test_visible():\n    assert True\n", encoding="utf-8")

    assert inventory._should_skip_test_scan_candidate(root, root, root, projects) is True
    assert inventory._should_skip_test_scan_candidate(root, root, root, hidden_file) is True
    assert inventory._should_skip_test_scan_candidate(root, root, root, test_file) is False
    assert inventory._test_file_sample(test_file, root) == "test_visible.py"
    assert inventory._test_file_sample(hidden_file, root) == ".hidden_test.py"


def test_inventory_cli_accepts_json_flag_and_emits_parseable_json(tmp_path: Path, capsys) -> None:
    root = tmp_path
    project = root / "projects" / "knowledge-dashboard"
    project.mkdir(parents=True)
    (project / "package.json").write_text(json.dumps({"scripts": {"test": "node --test"}}), encoding="utf-8")
    (project / "README.md").write_text("# Knowledge Dashboard\n", encoding="utf-8")

    result = inventory.main(["--root", str(root), "--json"])

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert result == 0
    assert payload["root"] == str(root.resolve())
    assert payload["projects"][0]["path"] == "projects/knowledge-dashboard"
    assert payload["projects"][0]["has_package_test_script"] is True


def test_inventory_cli_output_file_writes_ascii_json_and_preserves_stdout(tmp_path: Path, capsys) -> None:
    root = tmp_path / "박주호"
    project = root / "projects" / "knowledge-dashboard"
    project.mkdir(parents=True)
    (project / "package.json").write_text(json.dumps({"scripts": {"test": "node --test"}}), encoding="utf-8")
    (project / "README.md").write_text("# Knowledge Dashboard\n", encoding="utf-8")
    output = root / ".tmp" / "github-inventory.json"

    result = inventory.main(["--root", str(root), "--output", str(output)])

    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert stdout_payload == file_payload
    assert file_payload["root"] == str(root.resolve())
    assert output.read_text(encoding="utf-8").isascii()


def test_git_summary_keeps_status_dirty_lines_when_diff_is_clean(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], cwd: Path, timeout: int = 20) -> dict[str, object]:
        calls.append(args)
        command = tuple(args)
        if command == ("git", "branch", "--show-current"):
            return {"available": True, "returncode": 0, "stdout": "main", "stderr": ""}
        if command == ("git", "status", "--porcelain=v1", "-b"):
            return {
                "available": True,
                "returncode": 0,
                "stdout": "## main...origin/main\nM  .ai/HANDOFF.md\n M .ai/TASKS.md",
                "stderr": "",
            }
        if command in {
            ("git", "update-index", "-q", "--refresh"),
            ("git", "diff", "--quiet"),
            ("git", "diff", "--cached", "--quiet"),
            ("git", "remote", "-v"),
        }:
            return {"available": True, "returncode": 0, "stdout": "", "stderr": ""}
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(inventory, "_run", fake_run)

    summary = inventory._git_summary(tmp_path)

    assert calls[0] == ["git", "update-index", "-q", "--refresh"]
    assert summary["status_dirty_count"] == 2
    assert summary["dirty_count"] == 2
    assert summary["dirty_paths"] == [".ai/HANDOFF.md", ".ai/TASKS.md"]
    assert summary["dirty_confirmation"] == "status_dirty_diff_clean"


def test_confirmed_dirty_count_keeps_status_dirty_when_diff_is_clean() -> None:
    clean_diff = {"available": True, "returncode": 0}

    count, paths, confirmation = inventory._confirmed_dirty_count(
        [" M .ai/TASKS.md", "M  .ai/HANDOFF.md"],
        worktree_diff=clean_diff,
        cached_diff=clean_diff,
    )

    assert count == 2
    assert paths == [".ai/TASKS.md", ".ai/HANDOFF.md"]
    assert confirmation == "status_dirty_diff_clean"


def test_git_summary_keeps_tracked_status_when_worktree_diff_is_dirty(tmp_path: Path, monkeypatch) -> None:
    def fake_run(args: list[str], cwd: Path, timeout: int = 20) -> dict[str, object]:
        command = tuple(args)
        if command == ("git", "branch", "--show-current"):
            return {"available": True, "returncode": 0, "stdout": "main", "stderr": ""}
        if command == ("git", "status", "--porcelain=v1", "-b"):
            return {
                "available": True,
                "returncode": 0,
                "stdout": "## main...origin/main\n M .ai/TASKS.md",
                "stderr": "",
            }
        if command == ("git", "diff", "--quiet"):
            return {"available": True, "returncode": 1, "stdout": "", "stderr": ""}
        if command in {
            ("git", "update-index", "-q", "--refresh"),
            ("git", "diff", "--cached", "--quiet"),
            ("git", "remote", "-v"),
        }:
            return {"available": True, "returncode": 0, "stdout": "", "stderr": ""}
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(inventory, "_run", fake_run)

    summary = inventory._git_summary(tmp_path)

    assert summary["status_dirty_count"] == 1
    assert summary["dirty_count"] == 1
    assert summary["dirty_paths"] == [".ai/TASKS.md"]
    assert summary["dirty_confirmation"] == "diff_dirty"


def test_git_summary_keeps_untracked_status_even_when_tracked_diff_is_clean(tmp_path: Path, monkeypatch) -> None:
    def fake_run(args: list[str], cwd: Path, timeout: int = 20) -> dict[str, object]:
        command = tuple(args)
        if command == ("git", "branch", "--show-current"):
            return {"available": True, "returncode": 0, "stdout": "main", "stderr": ""}
        if command == ("git", "status", "--porcelain=v1", "-b"):
            return {
                "available": True,
                "returncode": 0,
                "stdout": "## main...origin/main\n?? .tmp/new-evidence.json",
                "stderr": "",
            }
        if command in {
            ("git", "update-index", "-q", "--refresh"),
            ("git", "diff", "--quiet"),
            ("git", "diff", "--cached", "--quiet"),
            ("git", "remote", "-v"),
        }:
            return {"available": True, "returncode": 0, "stdout": "", "stderr": ""}
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(inventory, "_run", fake_run)

    summary = inventory._git_summary(tmp_path)

    assert summary["status_dirty_count"] == 1
    assert summary["dirty_count"] == 1
    assert summary["dirty_paths"] == [".tmp/new-evidence.json"]
    assert summary["dirty_confirmation"] == "untracked"


def test_dirty_path_groups_bucket_common_handoff_surfaces() -> None:
    assert inventory._dirty_path_group_key(".ai/HANDOFF.md") == "ai-context"
    assert (
        inventory._dirty_path_group_key(".agents/skills/auto-research/scripts/next_experiment_selector.py")
        == "auto-research"
    )
    assert inventory._dirty_path_group_key("workspace/tests/test_github_project_inventory.py") == "auto-research"
    assert inventory._dirty_path_group_key("docs/wiki/llm/README.md") == "llm-wiki"
    assert inventory._dirty_path_group_key("execution/code_review_gate.py") == "workspace-code-review-gate"
    assert inventory._dirty_path_group_key("workspace/execution/pages/finance_tracker.py") == "workspace-dashboard"
    assert inventory._dirty_path_group_key("projects/blind-to-x/pipeline/publish_repair.py") == "project:blind-to-x"

    groups = inventory._dirty_path_groups(
        [
            ".ai/HANDOFF.md",
            ".agents/skills/auto-research/scripts/next_experiment_selector.py",
            "workspace/tests/test_auto_research_next_experiment_selector.py",
            "workspace/tests/test_dirty_worktree_handoff_plan.py",
            "workspace/tests/test_github_project_inventory.py",
            "docs/wiki/llm/README.md",
            "execution/llm_wiki_audit.py",
            "execution/code_review_gate.py",
            "workspace/tests/test_code_review_gate.py",
            "workspace/execution/pages/finance_tracker.py",
            "projects/blind-to-x/pipeline/publish_repair.py",
            "projects/hanwoo-dashboard/package.json",
        ]
    )
    by_key = {group["key"]: group for group in groups}

    assert by_key["ai-context"]["path_count"] == 1
    assert by_key["auto-research"]["owner_hint"] == "Codex/current-auto-research"
    assert by_key["auto-research"]["paths"] == [
        ".agents/skills/auto-research/scripts/next_experiment_selector.py",
        "workspace/tests/test_auto_research_next_experiment_selector.py",
        "workspace/tests/test_dirty_worktree_handoff_plan.py",
        "workspace/tests/test_github_project_inventory.py",
    ]
    assert by_key["llm-wiki"]["path_count"] == 2
    assert by_key["workspace-code-review-gate"]["paths"] == [
        "execution/code_review_gate.py",
        "workspace/tests/test_code_review_gate.py",
    ]
    assert by_key["workspace-dashboard"]["paths"] == ["workspace/execution/pages/finance_tracker.py"]
    assert by_key["project:blind-to-x"]["owner_hint"] == "blind-to-x"
    assert by_key["project:hanwoo-dashboard"]["owner_hint"] == "hanwoo-dashboard"


def test_auto_research_test_path_predicate_names_tooling_tests() -> None:
    assert inventory._is_auto_research_test_path("workspace/tests/test_auto_research_next_experiment_selector.py")
    assert inventory._is_auto_research_test_path("workspace/tests/test_dirty_worktree_handoff_plan.py")
    assert inventory._is_auto_research_test_path("workspace/tests/test_github_project_inventory.py")
    assert not inventory._is_auto_research_test_path("workspace/tests/test_code_review_gate.py")
    assert not inventory._is_auto_research_test_path("workspace/tests/test_finance_tracker.py")


def test_dirty_path_group_helpers_preserve_priority_boundaries() -> None:
    assert (
        inventory._dirty_path_prefixed_group(
            "workspace/tests/test_auto_research_llm_wiki_release.py",
            inventory.DIRTY_PATH_PRIMARY_PREFIX_GROUPS,
        )
        == "llm-wiki"
    )
    assert inventory._dirty_path_group_key("workspace/tests/test_auto_research_llm_wiki_release.py") == "llm-wiki"
    assert inventory._dirty_path_group_key("workspace/tests/test_auto_research_next_experiment_selector.py") == (
        "auto-research"
    )
    assert inventory._dirty_project_group_key("projects/blind-to-x/pipeline/runner.py") == "project:blind-to-x"
    assert inventory._dirty_project_group_key("projects//unknown.py") == "projects"


def test_git_summary_includes_dirty_path_groups(tmp_path: Path, monkeypatch) -> None:
    def fake_run(args: list[str], cwd: Path, timeout: int = 20) -> dict[str, object]:
        command = tuple(args)
        if command == ("git", "branch", "--show-current"):
            return {"available": True, "returncode": 0, "stdout": "main", "stderr": ""}
        if command == ("git", "status", "--porcelain=v1", "-b"):
            return {
                "available": True,
                "returncode": 0,
                "stdout": (
                    "## main...origin/main\n"
                    " M execution/code_review_gate.py\n"
                    "?? docs/wiki/llm/README.md\n"
                    "?? projects/blind-to-x/pipeline/publish_repair.py"
                ),
                "stderr": "",
            }
        if command in {
            ("git", "update-index", "-q", "--refresh"),
            ("git", "diff", "--quiet"),
            ("git", "diff", "--cached", "--quiet"),
            ("git", "remote", "-v"),
        }:
            return {"available": True, "returncode": 0, "stdout": "", "stderr": ""}
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(inventory, "_run", fake_run)

    summary = inventory._git_summary(tmp_path)
    by_key = {group["key"]: group for group in summary["dirty_path_groups"]}

    assert summary["dirty_confirmation"] == "untracked"
    assert by_key["workspace-code-review-gate"]["paths"] == ["execution/code_review_gate.py"]
    assert by_key["llm-wiki"]["paths"] == ["docs/wiki/llm/README.md"]
    assert by_key["project:blind-to-x"]["paths"] == ["projects/blind-to-x/pipeline/publish_repair.py"]
