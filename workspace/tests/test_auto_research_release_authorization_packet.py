"""Unit tests for the auto-research release authorization packet helper."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "auto-research" / "scripts" / "release_authorization_packet.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_authorization_packet", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["release_authorization_packet"] = module
    spec.loader.exec_module(module)
    return module


release_authorization_packet = _load_module()


def _readiness(*, ahead_count: int = 2, external: bool = True) -> dict[str, object]:
    return {
        "workspace_gates": {
            "github_release": {
                "ahead_count": ahead_count,
                "required_workflows": [
                    {"name": "root-quality-gate", "status": "missing", "conclusion": None},
                    {"name": "active-project-matrix", "status": "missing", "conclusion": None},
                ],
            }
        },
        "projects": [
            {
                "name": "hanwoo-dashboard",
                "tasks": [{"id": "T-251", "owner": "User", "task": "Supabase reset"}] if external else [],
            }
        ],
    }


def _git_info(*, dirty: bool = False, ahead: int = 2) -> dict[str, object]:
    return {
        "available": True,
        "branch_status": f"## main...origin/main [ahead {ahead}]" if ahead else "## main...origin/main",
        "branch": "main",
        "upstream": "origin/main",
        "head_sha": "abc123",
        "dirty_paths": ["workspace/tests/example.py"] if dirty else [],
        "commits": [
            {"sha": "abc123", "subject": "fix(readiness): T-1312 packet"},
            {"sha": "def456", "subject": "[ai-context] relay"},
        ],
    }


def test_clean_ahead_head_builds_authorization_packet(tmp_path: Path) -> None:
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(),
        git_info=_git_info(),
    )

    assert packet["status"] == "ready_for_authorization"
    assert packet["git"]["ahead_count"] == 2
    assert packet["git"]["commit_count"] == 2
    assert packet["unproven_workflows"] == ["root-quality-gate", "active-project-matrix"]
    assert packet["authorization"]["suggested_command"] == "git push origin main"
    assert packet["authorization"]["allowed_without_explicit_user_authorization"] is False
    assert any("T-251" in blocker for blocker in packet["blockers"])


def test_dirty_worktree_blocks_push_command(tmp_path: Path) -> None:
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(),
        git_info=_git_info(dirty=True),
    )

    assert packet["status"] == "blocked_dirty_worktree"
    assert packet["authorization"]["suggested_command"] is None
    assert packet["git"]["dirty_count"] == 1
    assert packet["blockers"][0] == "dirty worktree paths: 1"


def test_synced_head_does_not_require_authorization(tmp_path: Path) -> None:
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(ahead_count=0, external=False),
        git_info=_git_info(ahead=0),
    )

    assert packet["status"] == "not_required"
    assert packet["authorization"]["push_required"] is False
    assert packet["authorization"]["suggested_command"] is None


def test_cli_writes_ascii_json_with_fixture_readiness(tmp_path: Path, capsys) -> None:
    root = REPO_ROOT
    readiness = tmp_path / "readiness.json"
    output = tmp_path / "packet.json"
    readiness.write_text(json.dumps(_readiness()), encoding="utf-8")

    code = release_authorization_packet.main(
        [
            "--root",
            str(root),
            "--readiness",
            str(readiness),
            "--output",
            str(output),
            "--json",
        ]
    )
    stdout = json.loads(capsys.readouterr().out)
    persisted = json.loads(output.read_text(encoding="utf-8"))

    assert code == 0
    assert stdout["authorization"]["allowed_without_explicit_user_authorization"] is False
    assert persisted["git"]["head_sha"]
    assert output.read_text(encoding="utf-8").isascii()
