"""Unit tests for `execution/skill_lint.py`."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "execution" / "skill_lint.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("skill_lint", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["skill_lint"] = module
    spec.loader.exec_module(module)
    return module


skill_lint = _load_module()


def _write_skill(root: Path, name: str, text: str) -> Path:
    target = root / ".agents" / "skills" / name / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def test_healthy_skill_passes(tmp_path: Path):
    _write_skill(
        tmp_path,
        "healthy",
        "---\n"
        "name: healthy\n"
        "description: Use when validating a complete and documented local workflow.\n"
        "---\n\n"
        "# Healthy\n\n"
        "Use when the agent needs this workflow.\n",
    )

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["skill_count"] == 1
    assert report["summary"]["healthy_count"] == 1
    assert report["issues"] == []


def test_missing_frontmatter_is_error(tmp_path: Path):
    _write_skill(tmp_path, "broken", "# Broken\n\nNo metadata here.\n")

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))

    assert report["summary"]["status"] == "fail"
    assert any(issue["code"] == "missing_frontmatter" for issue in report["issues"])
    assert any(issue["code"] == "missing_name" for issue in report["issues"])
    assert any(issue["code"] == "missing_description" for issue in report["issues"])


def test_duplicate_names_and_broken_references_warn(tmp_path: Path):
    body = (
        "---\n"
        "name: duplicate\n"
        "description: Use when validating duplicate skill metadata and local references.\n"
        "---\n\n"
        "See `scripts/missing.py` for details.\n"
    )
    _write_skill(tmp_path, "one", body)
    _write_skill(tmp_path, "two", body)

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))
    codes = {issue["code"] for issue in report["issues"]}

    assert report["summary"]["status"] == "warn"
    assert "duplicate_name" in codes
    assert "broken_reference" in codes
