"""Unit tests for the auto-research completion audit helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "completion_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("completion_audit", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["completion_audit"] = module
    spec.loader.exec_module(module)
    return module


completion_audit = _load_module()


def test_audit_item_normalizes_blockers_and_issue_codes():
    item, issues, passed, blocked = completion_audit._audit_item(
        2,
        {
            "requirement": " Run live Supabase CRUD ",
            "artifacts": ["projects/hanwoo-dashboard/.env"],
            "evidence": ["P2010 / XX000 tenant-user mismatch reproduced"],
            "verified": True,
            "coverage": "complete",
            "blockers": ["Supabase password must be reset by user"],
        },
    )

    assert item == {
        "index": 2,
        "requirement": "Run live Supabase CRUD",
        "artifacts": ["projects/hanwoo-dashboard/.env"],
        "evidence": ["P2010 / XX000 tenant-user mismatch reproduced"],
        "verified": True,
        "coverage": "complete",
        "blockers": ["Supabase password must be reset by user"],
        "passed": False,
        "issues": ["blocked"],
    }
    assert [issue["code"] for issue in issues] == ["blocked"]
    assert issues[0]["requirement"] == "Run live Supabase CRUD"
    assert passed is False
    assert blocked is True


def test_audit_item_reports_invalid_non_object_without_normalized_item():
    item, issues, passed, blocked = completion_audit._audit_item(3, "not an item")

    assert item is None
    assert issues == [
        {
            "index": 3,
            "code": "invalid_item",
            "message": "Checklist item must be an object.",
        }
    ]
    assert passed is False
    assert blocked is False


def test_complete_manifest_passes():
    result = completion_audit.audit_manifest(
        {
            "objective": "Launch product",
            "items": [
                {
                    "requirement": "Inventory GitHub projects",
                    "artifacts": ["projects/hanwoo-dashboard", ".github/workflows/root-quality-gate.yml"],
                    "evidence": ["github_project_inventory.py returned open_prs.count=0"],
                    "verified": True,
                    "coverage": "complete",
                }
            ],
        }
    )

    assert result["status"] == "complete"
    assert result["summary"]["complete_count"] == 1
    assert result["issues"] == []


def test_missing_evidence_and_verification_are_incomplete():
    result = completion_audit.audit_manifest(
        {
            "objective": "Launch product",
            "items": [
                {
                    "requirement": "Click through the app",
                    "artifacts": [],
                    "evidence": [],
                    "verified": False,
                    "coverage": "partial",
                }
            ],
        }
    )

    codes = {issue["code"] for issue in result["issues"]}
    assert result["status"] == "incomplete"
    assert "missing_artifacts" in codes
    assert "missing_evidence" in codes
    assert "not_verified" in codes
    assert "incomplete_coverage" in codes


def test_blocked_items_prevent_completion():
    blocker = "Supabase password must be reset by user"
    result = completion_audit.audit_manifest(
        {
            "objective": "Launch product",
            "items": [
                {
                    "requirement": "Run live Supabase CRUD",
                    "artifacts": ["projects/hanwoo-dashboard/.env"],
                    "evidence": ["P2010 / XX000 tenant-user mismatch reproduced"],
                    "verified": True,
                    "coverage": "complete",
                    "blockers": [blocker],
                }
            ],
        }
    )

    assert result["status"] == "incomplete"
    assert result["summary"]["blocked_count"] == 1
    issue = next(issue for issue in result["issues"] if issue["code"] == "blocked")
    assert blocker in issue["message"]
    assert issue["blockers"] == [blocker]
    assert issue["requirement"] == "Run live Supabase CRUD"


def test_load_json_accepts_powershell_utf16_redirect(tmp_path: Path):
    manifest_path = tmp_path / "completion-audit.json"
    manifest_path.write_text(
        json.dumps(
            {
                "objective": "Launch product",
                "items": [
                    {
                        "requirement": "Run completion audit",
                        "artifacts": [".tmp/completion-audit.json"],
                        "evidence": ["completion_audit.py returned complete"],
                        "verified": True,
                        "coverage": "complete",
                    }
                ],
            }
        ),
        encoding="utf-16",
    )

    result = completion_audit.audit_manifest(completion_audit._load_json(manifest_path))

    assert result["status"] == "complete"


def test_load_json_reports_unreadable_manifest_without_traceback(tmp_path: Path):
    manifest_path = tmp_path / "completion-audit.json"
    manifest_path.mkdir()

    with pytest.raises(SystemExit, match="manifest unreadable"):
        completion_audit._load_json(manifest_path)


def test_main_output_writes_utf8_json_without_bom(tmp_path: Path, capsys):
    manifest_path = tmp_path / "completion-audit.json"
    output_path = tmp_path / ".tmp" / "completion-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "objective": "Launch product",
                "items": [
                    {
                        "requirement": "Run completion audit",
                        "artifacts": [".tmp/completion-audit.json"],
                        "evidence": ["completion_audit.py returned complete"],
                        "verified": True,
                        "coverage": "complete",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = completion_audit.main(
        [
            str(manifest_path),
            "--json",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    raw = output_path.read_bytes()
    assert exit_code == 0
    assert raw.startswith(b"{\n")
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert json.loads(raw.decode("utf-8"))["status"] == "complete"
    assert json.loads(captured.out)["status"] == "complete"


def test_main_reports_output_write_failure_without_overwriting(tmp_path: Path, capsys):
    manifest_path = tmp_path / "completion-audit.json"
    output_path = tmp_path / ".tmp" / "completion-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "objective": "Launch product",
                "items": [
                    {
                        "requirement": "Run completion audit",
                        "artifacts": [".tmp/completion-audit.json"],
                        "evidence": ["completion_audit.py returned complete"],
                        "verified": True,
                        "coverage": "complete",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path.parent.mkdir()
    output_path.write_text('{"status":"existing"}\n', encoding="utf-8")
    output_path.with_name(f"{output_path.name}.refresh-tmp").mkdir()

    exit_code = completion_audit.main(
        [
            str(manifest_path),
            "--json",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 4
    assert output_path.read_text(encoding="utf-8") == '{"status":"existing"}\n'
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_path.as_posix()
    assert stdout["write_error"]


def test_main_reports_output_parent_write_failure_without_traceback(tmp_path: Path, capsys):
    manifest_path = tmp_path / "completion-audit.json"
    blocked_parent = tmp_path / ".tmp" / "blocked-parent"
    output_path = blocked_parent / "completion-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "objective": "Launch product",
                "items": [
                    {
                        "requirement": "Run completion audit",
                        "artifacts": [".tmp/completion-audit.json"],
                        "evidence": ["completion_audit.py returned complete"],
                        "verified": True,
                        "coverage": "complete",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    blocked_parent.parent.mkdir()
    blocked_parent.write_text("blocking file\n", encoding="utf-8")

    exit_code = completion_audit.main(
        [
            str(manifest_path),
            "--json",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "blocking file\n"
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_path.as_posix()
    assert "FileExistsError" in stdout["write_error"]


def test_template_output_writes_utf8_json_without_bom(tmp_path: Path, capsys):
    output_path = tmp_path / ".tmp" / "completion-template.json"

    exit_code = completion_audit.main(
        [
            "--template",
            "--objective",
            "Launch product",
            "--template-output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    raw = output_path.read_bytes()
    assert exit_code == 0
    assert raw.startswith(b"{\n")
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert json.loads(raw.decode("utf-8"))["objective"] == "Launch product"
    assert json.loads(captured.out)["objective"] == "Launch product"


def test_template_output_write_failure_preserves_existing_template(tmp_path: Path, capsys):
    output_path = tmp_path / ".tmp" / "completion-template.json"
    output_path.parent.mkdir()
    output_path.write_text('{"objective":"existing"}\n', encoding="utf-8")
    output_path.with_name(f"{output_path.name}.refresh-tmp").mkdir()

    exit_code = completion_audit.main(
        [
            "--template",
            "--objective",
            "Launch product",
            "--template-output",
            str(output_path),
        ]
    )

    assert exit_code == 4
    assert output_path.read_text(encoding="utf-8") == '{"objective":"existing"}\n'
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_path.as_posix()
    assert stdout["write_error"]


def test_template_output_parent_write_failure_without_traceback(tmp_path: Path, capsys):
    blocked_parent = tmp_path / ".tmp" / "blocked-parent"
    output_path = blocked_parent / "completion-template.json"
    blocked_parent.parent.mkdir()
    blocked_parent.write_text("blocking file\n", encoding="utf-8")

    exit_code = completion_audit.main(
        [
            "--template",
            "--objective",
            "Launch product",
            "--template-output",
            str(output_path),
        ]
    )

    assert exit_code == 4
    assert blocked_parent.read_text(encoding="utf-8") == "blocking file\n"
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["status"] == "write_failed"
    assert stdout["write_error_path"] == output_path.as_posix()
    assert "FileExistsError" in stdout["write_error"]
