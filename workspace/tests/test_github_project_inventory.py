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
