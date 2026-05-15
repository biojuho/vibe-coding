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


def test_reference_resolution_checks_common_skill_subdirectories(tmp_path: Path):
    skill_path = _write_skill(
        tmp_path,
        "tooling",
        "---\n"
        "name: tooling\n"
        "description: Use when validating bundled skill reference resolution.\n"
        "---\n\n"
        "Run `helper.py`, inspect `examples.md`, and call `skills/tooling/scripts/helper.py`.\n",
    )
    (skill_path.parent / "scripts").mkdir()
    (skill_path.parent / "scripts" / "helper.py").write_text("print('ok')\n", encoding="utf-8")
    (skill_path.parent / "references").mkdir()
    (skill_path.parent / "references" / "examples.md").write_text("# Examples\n", encoding="utf-8")

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))

    assert report["summary"]["status"] == "pass"
    assert report["issues"] == []


def test_bare_inline_filenames_are_not_treated_as_required_bundled_files(tmp_path: Path):
    _write_skill(
        tmp_path,
        "artifact-skill",
        "---\n"
        "name: artifact-skill\n"
        "description: Use when validating generated artifact mentions in skill prose.\n"
        "---\n\n"
        "The workflow may create `draft.json`, `outline.md`, or `robots.txt` in the user's project.\n",
    )

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))

    assert report["summary"]["status"] == "pass"
    assert report["issues"] == []


def test_references_inside_fenced_code_are_examples_not_required_files(tmp_path: Path):
    _write_skill(
        tmp_path,
        "example-links",
        "---\n"
        "name: example-links\n"
        "description: Use when validating example links inside fenced code blocks.\n"
        "---\n\n"
        "```markdown\n"
        "See [FORMS.md](FORMS.md) and `scripts/generated.py` in generated output.\n"
        "```\n",
    )

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))

    assert report["summary"]["status"] == "pass"
    assert report["issues"] == []


def test_trigger_guidance_accepts_common_heading_variants(tmp_path: Path):
    _write_skill(
        tmp_path,
        "triggered",
        "---\n"
        "name: triggered\n"
        "description: Validates trigger guidance that uses common headings.\n"
        "---\n\n"
        "## When to Use This Skill\n\n"
        "Apply it when the user asks for this workflow.\n",
    )

    report = skill_lint.build_report(tmp_path, now=datetime(2026, 5, 13, tzinfo=timezone.utc))

    assert report["summary"]["status"] == "pass"
    assert report["issues"] == []
