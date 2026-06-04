from __future__ import annotations

import importlib.util
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
