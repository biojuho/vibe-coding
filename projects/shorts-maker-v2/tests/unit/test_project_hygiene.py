from __future__ import annotations

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _workflow_paths(text: str) -> list[str]:
    return re.findall(r"archive/tests_legacy_v1/[A-Za-z0-9_./-]+\.py", text)


def test_archived_shortsfactory_workflow_uses_existing_paths_and_pyproject_dependencies():
    workflow = PROJECT_ROOT / ".github" / "workflows" / "visual-regression.yml"
    text = workflow.read_text(encoding="utf-8")

    assert yaml.safe_load(text)
    assert "requirements.txt" not in text
    assert "workflow_dispatch:" in text
    assert "tests/unit/test_visual_regression.py" not in text
    assert "tests/unit/test_engines_v2.py" not in text
    assert "tests/unit/test_interfaces.py" not in text
    assert 'pip install -e ".[dev]"' in text

    paths = _workflow_paths(text)
    assert paths
    assert all((PROJECT_ROOT / path).exists() for path in paths)


def test_runbook_uses_pyproject_install_command():
    runbook = PROJECT_ROOT / "docs" / "runbook.md"
    text = runbook.read_text(encoding="utf-8")

    assert "requirements.txt" not in text
    assert 'python -m pip install -e ".[dev]"' in text


def test_local_verification_docs_include_project_venv_python():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    package_readme = (PROJECT_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert r".\.venv\Scripts\python.exe -m pytest" in readme
    assert r".\.venv\Scripts\python.exe -m ruff check ." in readme
    assert (
        r".\.venv\Scripts\python.exe -m pytest --no-cov tests/unit tests/integration -q --tb=short --maxfail=1"
        in package_readme
    )
