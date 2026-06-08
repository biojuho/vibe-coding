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


def _git_info_with_commits(count: int) -> dict[str, object]:
    info = _git_info(ahead=count)
    info["commits"] = [
        {"sha": f"{index:07x}", "subject": f"fix(scope): T-{1300 + index} release item {index}"}
        for index in range(count)
    ]
    return info


def _write_llm_wiki_evidence(root: Path, *, status: str = "pass", head_sha: str = "abc123") -> Path:
    artifact = root / release_authorization_packet.DEFAULT_LLM_WIKI_STRICT_EVIDENCE_PATH
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "evidence_type": "llm_wiki_strict_release_audit",
                "generated_at": "2026-06-08",
                "artifact_path": ".tmp/llm-wiki-strict-audit-current.json",
                "command": "py -3.13 execution/llm_wiki_audit.py --write-strict-release-evidence --json",
                "release_gate": {
                    "status": status,
                    "accepted_manifest_warning_count": 2,
                    "unexpected_manifest_warning_count": 0 if status == "pass" else 1,
                    "strict_manifest_warning_failure": status != "pass",
                },
                "git": {"head_sha": head_sha},
                "report": {"summary": {"source_inventory_count": 64}},
            }
        ),
        encoding="utf-8",
    )
    return artifact


def test_clean_ahead_head_builds_authorization_packet(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path)
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(),
        git_info=_git_info(),
    )

    assert packet["status"] == "ready_for_authorization"
    assert packet["summary"]["head_short"] == "abc123"
    assert packet["summary"]["authorization_required"] is True
    assert packet["git"]["ahead_count"] == 2
    assert packet["git"]["commit_count"] == 2
    assert packet["git"]["commits_ahead_omitted"] == 0
    assert packet["git"]["review_commands"] == [
        "git log --oneline --decorate=no origin/main..HEAD",
        "git diff --stat origin/main..HEAD",
    ]
    assert packet["unproven_workflows"] == ["root-quality-gate", "active-project-matrix"]
    assert packet["authorization"]["suggested_command"] == "git push origin main"
    assert packet["authorization"]["allowed_without_explicit_user_authorization"] is False
    assert packet["summary"]["llm_wiki_strict_evidence_status"] == "pass"
    assert packet["summary"]["llm_wiki_strict_evidence_unexpected_count"] == 0
    assert packet["summary"]["llm_wiki_strict_evidence_path"] == ".tmp/llm-wiki-strict-audit-current.json"
    assert packet["llm_wiki_strict_evidence"]["schema_version"] == 1
    assert packet["llm_wiki_strict_evidence"]["evidence_type"] == "llm_wiki_strict_release_audit"
    assert packet["llm_wiki_strict_evidence"]["audit_status"] == "unknown"
    assert packet["llm_wiki_strict_evidence"]["command"].endswith("--write-strict-release-evidence --json")
    assert packet["llm_wiki_strict_evidence"]["head_matches_current"] is True
    assert packet["llm_wiki_strict_evidence"]["source_inventory_count"] == 64
    assert any("T-251" in blocker for blocker in packet["blockers"])


def test_missing_llm_wiki_strict_evidence_is_packet_blocker(tmp_path: Path) -> None:
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(external=False),
        git_info=_git_info(),
    )

    assert packet["llm_wiki_strict_evidence"]["available"] is False
    assert packet["summary"]["llm_wiki_strict_evidence_status"] == "missing"
    assert (
        "LLM Wiki strict release evidence artifact missing: .tmp/llm-wiki-strict-audit-current.json"
        in packet["blockers"]
    )


def test_llm_wiki_strict_evidence_failures_are_packet_blockers(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path, status="fail")

    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(external=False),
        git_info=_git_info(),
    )

    assert packet["llm_wiki_strict_evidence"]["status"] == "fail"
    assert "LLM Wiki strict release evidence status=fail" in packet["blockers"]


def test_llm_wiki_strict_evidence_head_mismatch_is_packet_blocker(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path, head_sha="def456")

    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(external=False),
        git_info=_git_info(),
    )

    assert packet["llm_wiki_strict_evidence"]["head_matches_current"] is False
    assert "LLM Wiki strict release evidence head does not match current HEAD" in packet["blockers"]


def test_large_ahead_range_defaults_to_readable_commit_preview(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path)
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(ahead_count=40),
        git_info=_git_info_with_commits(40),
    )

    assert packet["git"]["commit_count"] == 40
    assert len(packet["git"]["commits_ahead"]) == release_authorization_packet.DEFAULT_COMMIT_PREVIEW_LIMIT
    assert packet["git"]["commits_ahead_omitted"] == 15
    assert packet["summary"]["commit_preview_count"] == 25
    assert packet["summary"]["commit_omitted_count"] == 15
    assert packet["git"]["review_commands"][0] == "git log --oneline --decorate=no origin/main..HEAD"


def test_commit_preview_limit_can_be_lowered_for_compact_packets(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path)
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(ahead_count=4),
        git_info=_git_info_with_commits(4),
        max_commits=1,
    )

    assert [commit["sha"] for commit in packet["git"]["commits_ahead"]] == ["0000000"]
    assert packet["git"]["commits_ahead_limit"] == 1
    assert packet["git"]["commits_ahead_omitted"] == 3


def test_dirty_worktree_blocks_push_command(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path)
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
    _write_llm_wiki_evidence(tmp_path)
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
    assert stdout["summary"]["commit_preview_count"] <= release_authorization_packet.DEFAULT_COMMIT_PREVIEW_LIMIT
    assert persisted["git"]["head_sha"]
    assert output.read_text(encoding="utf-8").isascii()
