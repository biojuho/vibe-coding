"""Unit tests for the auto-research completion audit helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


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
