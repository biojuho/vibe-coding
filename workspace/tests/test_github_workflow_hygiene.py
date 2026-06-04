from __future__ import annotations

import configparser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_FILES = [
    REPO_ROOT / ".github" / "workflows" / "full-test-matrix.yml",
    REPO_ROOT / ".github" / "workflows" / "root-quality-gate.yml",
]


def test_nature_skills_gitlink_has_submodule_url() -> None:
    config = configparser.ConfigParser()
    assert config.read(REPO_ROOT / ".gitmodules", encoding="utf-8") == [str(REPO_ROOT / ".gitmodules")]

    section = 'submodule "nature-skills"'
    assert config.has_section(section)
    assert config.get(section, "path") == "nature-skills"
    assert config.get(section, "url") == "https://github.com/Yuan1z0825/nature-skills.git"


def test_ci_checkout_steps_use_current_read_only_checkout() -> None:
    for workflow in WORKFLOW_FILES:
        text = workflow.read_text(encoding="utf-8")
        checkout_count = text.count("uses: actions/checkout@v6")

        assert checkout_count > 0
        assert "uses: actions/checkout@v5" not in text
        assert text.count("persist-credentials: false") == checkout_count
