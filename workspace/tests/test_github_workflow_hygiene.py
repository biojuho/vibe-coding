from __future__ import annotations

import configparser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_WORKFLOW_FILES = {
    "active-project-matrix": REPO_ROOT / ".github" / "workflows" / "full-test-matrix.yml",
    "root-quality-gate": REPO_ROOT / ".github" / "workflows" / "root-quality-gate.yml",
}


def test_nature_skills_gitlink_has_submodule_url() -> None:
    config = configparser.ConfigParser()
    assert config.read(REPO_ROOT / ".gitmodules", encoding="utf-8") == [str(REPO_ROOT / ".gitmodules")]

    section = 'submodule "nature-skills"'
    assert config.has_section(section)
    assert config.get(section, "path") == "nature-skills"
    assert config.get(section, "url") == "https://github.com/Yuan1z0825/nature-skills.git"


def test_ci_checkout_steps_use_current_read_only_checkout() -> None:
    for workflow in REQUIRED_WORKFLOW_FILES.values():
        text = workflow.read_text(encoding="utf-8")
        checkout_count = text.count("uses: actions/checkout@v6")

        assert checkout_count > 0
        assert "uses: actions/checkout@v5" not in text
        assert text.count("persist-credentials: false") == checkout_count


def test_required_release_workflows_are_defined_with_expected_names() -> None:
    for expected_name, workflow in REQUIRED_WORKFLOW_FILES.items():
        assert workflow.exists()
        text = workflow.read_text(encoding="utf-8")

        assert f"name: {expected_name}" in text.splitlines()[:5]
        assert "\n  push:" in text
        assert "\n  pull_request:" in text
