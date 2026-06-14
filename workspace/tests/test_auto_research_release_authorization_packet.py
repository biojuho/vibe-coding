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


def _current_head_actions(
    *,
    available: bool = True,
    run_count: int | None = 0,
    required_success_count: int = 0,
    missing: list[str] | None = None,
) -> dict[str, object]:
    required = list(release_authorization_packet.DEFAULT_REQUIRED_WORKFLOWS)
    resolved_missing = missing if missing is not None else required[required_success_count:]
    successful = [name for name in required if name not in resolved_missing]
    successful_rows = [
        {
            "workflowName": name,
            "status": "completed",
            "conclusion": "success",
            "headSha": "abc123",
        }
        for name in successful
    ]
    resolved_run_count = len(successful_rows) if run_count is None else run_count
    return {
        "available": available,
        "head_sha": "abc123",
        "command": "gh run list --commit abc123 --limit 20 --json databaseId,name,workflowName,status,conclusion,headSha,createdAt,url",
        "returncode": 0 if available else None,
        "reason": "" if available else "not a git worktree",
        "limit": 20,
        "run_count": resolved_run_count,
        "required_workflow_names": required,
        "required_run_count": len(successful_rows),
        "required_success_count": required_success_count,
        "successful_required_workflows": successful_rows,
        "missing_required_workflows": resolved_missing,
        "runs_preview": successful_rows,
    }


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
        current_head_actions=_current_head_actions(),
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
    assert packet["current_head_actions"]["available"] is True
    assert packet["summary"]["current_head_actions_available"] is True
    assert packet["summary"]["current_head_run_count"] == 0
    assert packet["summary"]["current_head_required_success_count"] == 0
    assert any("T-251" in blocker for blocker in packet["blockers"])


def test_current_head_actions_success_evidence_is_recorded(tmp_path: Path) -> None:
    _write_llm_wiki_evidence(tmp_path)
    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(external=False),
        git_info=_git_info(),
        current_head_actions=_current_head_actions(
            run_count=None,
            required_success_count=2,
            missing=[],
        ),
    )

    assert packet["current_head_actions"]["run_count"] == 2
    assert packet["current_head_actions"]["missing_required_workflows"] == []
    assert packet["summary"]["current_head_run_count"] == 2
    assert packet["summary"]["current_head_required_success_count"] == 2


def test_collect_current_head_actions_matches_required_workflows(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".git").mkdir()

    def fake_run(root: Path, args: list[str], timeout: int) -> dict[str, object]:
        assert root == tmp_path
        assert args[:5] == ["gh", "run", "list", "--commit", "abc123"]
        assert timeout == 7
        return {
            "ok": True,
            "returncode": 0,
            "stdout": json.dumps(
                [
                    {
                        "databaseId": 11,
                        "name": "Root Gate",
                        "workflowName": "root-quality-gate",
                        "status": "completed",
                        "conclusion": "success",
                        "headSha": "abc123",
                    },
                    {
                        "databaseId": 12,
                        "name": "Matrix",
                        "workflowName": "active-project-matrix",
                        "status": "completed",
                        "conclusion": "failure",
                        "headSha": "abc123",
                    },
                ]
            ),
            "stderr": "",
        }

    monkeypatch.setattr(release_authorization_packet, "_run", fake_run)

    actions = release_authorization_packet._collect_current_head_actions(tmp_path, "abc123", timeout=7)

    assert actions["available"] is True
    assert actions["run_count"] == 2
    assert actions["required_run_count"] == 2
    assert actions["required_success_count"] == 1
    assert actions["missing_required_workflows"] == ["active-project-matrix"]


def test_required_workflow_rows_filter_required_workflows_only() -> None:
    rows = [
        {"workflowName": "root-quality-gate", "status": "completed"},
        {"workflowName": "unrelated-workflow", "status": "completed"},
        {"name": "active-project-matrix", "status": "queued"},
        {"workflowName": "  ", "status": "completed"},
    ]

    required = release_authorization_packet._required_workflow_rows(
        rows,
        ["root-quality-gate", "active-project-matrix"],
    )

    assert required == [rows[0], rows[2]]


def test_successful_required_workflow_rows_filter_successful_required_only() -> None:
    rows = [
        {"workflowName": "root-quality-gate", "status": "completed", "conclusion": "success"},
        {"workflowName": "active-project-matrix", "status": "completed", "conclusion": "failure"},
        {"workflowName": "unrelated-workflow", "status": "completed", "conclusion": "success"},
        {"name": "root-quality-gate", "status": "in_progress", "conclusion": None},
        {"name": "active-project-matrix", "status": "completed", "conclusion": "success"},
    ]

    successful = release_authorization_packet._successful_required_workflow_rows(
        rows,
        ["root-quality-gate", "active-project-matrix"],
    )

    assert successful == [rows[0], rows[4]]


def test_workflow_run_rows_normalize_github_rows_only() -> None:
    rows = release_authorization_packet._workflow_run_rows(
        [
            {
                "databaseId": 7,
                "name": "Root Gate",
                "workflowName": "root-quality-gate",
                "status": "completed",
                "conclusion": "success",
                "headSha": "abc123",
                "createdAt": "2026-06-10T00:00:00Z",
                "url": "https://github.com/example/actions/runs/7",
                "extra": "ignored",
            },
            ["not", "a", "dict"],
            "also ignored",
        ]
    )

    assert rows == [
        {
            "databaseId": 7,
            "name": "Root Gate",
            "workflowName": "root-quality-gate",
            "status": "completed",
            "conclusion": "success",
            "headSha": "abc123",
            "createdAt": "2026-06-10T00:00:00Z",
            "url": "https://github.com/example/actions/runs/7",
        }
    ]


def test_current_head_actions_helpers_preserve_github_lookup_contract() -> None:
    command = release_authorization_packet._actions_lookup_command("abc123", limit=-4)
    assert command == [
        "gh",
        "run",
        "list",
        "--commit",
        "abc123",
        "--limit",
        "0",
        "--json",
        "databaseId,name,workflowName,status,conclusion,headSha,createdAt,url",
    ]

    unavailable = release_authorization_packet._current_head_actions_unavailable(
        head_sha="abc123",
        reason="gh unavailable",
        command=command,
        returncode=127,
        stderr="not found",
        limit=-4,
    )
    assert unavailable["available"] is False
    assert unavailable["command"] == " ".join(command)
    assert unavailable["returncode"] == 127
    assert unavailable["stderr"] == "not found"
    assert unavailable["limit"] == 0
    assert unavailable["missing_required_workflows"] == list(release_authorization_packet.DEFAULT_REQUIRED_WORKFLOWS)

    assert release_authorization_packet._workflow_name({"workflowName": "root-quality-gate"}) == "root-quality-gate"
    assert release_authorization_packet._workflow_name({"name": "Fallback Gate"}) == "Fallback Gate"
    assert release_authorization_packet._workflow_name({"workflowName": "  "}) == ""


def test_packet_status_blocker_and_summary_helpers_preserve_contract() -> None:
    fallback_workflows = release_authorization_packet._packet_workflows({"workspace_gates": {"github_release": {}}})
    assert [workflow["name"] for workflow in fallback_workflows] == list(
        release_authorization_packet.DEFAULT_REQUIRED_WORKFLOWS
    )
    assert release_authorization_packet._packet_ahead_count(_readiness(ahead_count=0), "## main [ahead 3]") == 3
    assert (
        release_authorization_packet._packet_status(
            git_available=False,
            dirty_paths=[],
            ahead_count=1,
            unproven=["root-quality-gate"],
        )
        == "git_unavailable"
    )
    assert (
        release_authorization_packet._packet_status(
            git_available=True,
            dirty_paths=[".ai/HANDOFF.md"],
            ahead_count=1,
            unproven=["root-quality-gate"],
        )
        == "blocked_dirty_worktree"
    )
    assert (
        release_authorization_packet._packet_status(
            git_available=True,
            dirty_paths=[],
            ahead_count=0,
            unproven=[],
        )
        == "not_required"
    )
    assert (
        release_authorization_packet._packet_status(
            git_available=True,
            dirty_paths=[],
            ahead_count=1,
            unproven=["root-quality-gate"],
        )
        == "ready_for_authorization"
    )
    assert (
        release_authorization_packet._packet_status(
            git_available=True,
            dirty_paths=[],
            ahead_count=1,
            unproven=[],
        )
        == "already_verified"
    )

    blockers = release_authorization_packet._packet_blockers(
        dirty_paths=[".ai/HANDOFF.md"],
        ahead_count=1,
        unproven=["root-quality-gate"],
        external_task_ids=["T-251"],
        llm_wiki_evidence={"available": False, "path": ".tmp/llm-wiki.json"},
    )
    assert blockers == [
        "dirty worktree paths: 1",
        "current-head Actions unavailable until push authorization/user push",
        "external/user-owned blocker(s): T-251",
        "LLM Wiki strict release evidence artifact missing: .tmp/llm-wiki.json",
    ]
    git_info = _git_info_with_commits(3)
    assert release_authorization_packet._packet_push_command(git_info, ahead_count=3, dirty_paths=[]) == (
        "git push origin main"
    )
    assert release_authorization_packet._packet_push_command(git_info, ahead_count=3, dirty_paths=["dirty.py"]) is None
    git_section = release_authorization_packet._packet_git_section(
        git_info=git_info,
        branch_status="## main...origin/main [ahead 3]",
        ahead_count=3,
        dirty_paths=[],
        commits_preview=git_info["commits"][:1],
        commits_omitted=2,
        commit_count=3,
        max_commits=1,
    )
    assert git_section["commits_ahead_limit"] == 1
    assert git_section["commits_ahead_omitted"] == 2
    assert git_section["commit_count"] == 3
    authorization = release_authorization_packet._packet_authorization(
        git_info=git_info,
        ahead_count=3,
        dirty_paths=[],
        unproven=[],
        workflows=fallback_workflows,
    )
    assert authorization["push_required"] is True
    assert authorization["allowed_without_explicit_user_authorization"] is False
    assert authorization["suggested_command"] == "git push origin main"
    assert authorization["post_push_gates"] == list(release_authorization_packet.DEFAULT_REQUIRED_WORKFLOWS)

    summary = release_authorization_packet._packet_summary(
        git_info={"branch": "main", "head_sha": "abcdef123456"},
        ahead_count=1,
        dirty_paths=[],
        unproven=["root-quality-gate"],
        external_task_ids=["T-251"],
        commit_count=3,
        commits_preview=[{"sha": "1"}, {"sha": "2"}],
        commits_omitted=1,
        llm_wiki_evidence={
            "status": "pass",
            "head_matches_current": True,
            "unexpected_manifest_warning_count": 0,
            "path": ".tmp/llm-wiki.json",
        },
        current_head_actions={"available": True, "run_count": 2, "required_success_count": 1},
    )
    assert summary["head_short"] == "abcdef12"
    assert summary["authorization_required"] is True
    assert summary["commit_preview_count"] == 2
    assert summary["current_head_run_count"] == 2
    assert summary["current_head_required_success_count"] == 1


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


def test_invalid_encoding_llm_wiki_strict_evidence_is_packet_blocker(tmp_path: Path) -> None:
    artifact = tmp_path / release_authorization_packet.DEFAULT_LLM_WIKI_STRICT_EVIDENCE_PATH
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"\xff\xfe\x00")

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


def test_load_json_returns_empty_for_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "readiness.json"
    path.write_bytes(b"\xff\xfe\x00")

    assert release_authorization_packet._load_json(path) == {}


def test_load_json_accepts_powershell_utf16_json(tmp_path: Path) -> None:
    path = tmp_path / "readiness.json"
    payload = _readiness(ahead_count=7, external=False)
    path.write_text(json.dumps(payload), encoding="utf-16")

    loaded = release_authorization_packet._load_json(path)

    assert loaded["workspace_gates"]["github_release"]["ahead_count"] == 7
    assert loaded["projects"][0]["tasks"] == []


def test_utf16_llm_wiki_strict_evidence_is_not_reported_missing(tmp_path: Path) -> None:
    artifact = tmp_path / release_authorization_packet.DEFAULT_LLM_WIKI_STRICT_EVIDENCE_PATH
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "evidence_type": "llm_wiki_strict_release_audit",
                "release_gate": {
                    "status": "pass",
                    "accepted_manifest_warning_count": 1,
                    "unexpected_manifest_warning_count": 0,
                    "strict_manifest_warning_failure": False,
                },
                "git": {"head_sha": "abc123"},
                "report": {"summary": {"status": "pass", "source_inventory_count": 12}},
            }
        ),
        encoding="utf-16",
    )

    packet = release_authorization_packet.build_packet(
        tmp_path,
        readiness=_readiness(external=False),
        git_info=_git_info(),
    )

    assert packet["llm_wiki_strict_evidence"]["available"] is True
    assert packet["llm_wiki_strict_evidence"]["status"] == "pass"
    assert packet["llm_wiki_strict_evidence"]["audit_status"] == "pass"
    assert packet["llm_wiki_strict_evidence"]["source_inventory_count"] == 12
    assert packet["summary"]["llm_wiki_strict_evidence_status"] == "pass"
    assert not any("LLM Wiki strict release evidence artifact missing" in blocker for blocker in packet["blockers"])


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
    assert packet["git"]["commits_ahead_omitted"] == 5
    assert packet["summary"]["commit_preview_count"] == 35
    assert packet["summary"]["commit_omitted_count"] == 5
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


def test_cli_writes_ascii_json_with_fixture_readiness(tmp_path: Path, capsys, monkeypatch) -> None:
    root = REPO_ROOT
    readiness = tmp_path / "readiness.json"
    output = tmp_path / "packet.json"
    readiness.write_text(json.dumps(_readiness()), encoding="utf-8")
    monkeypatch.setattr(
        release_authorization_packet,
        "_collect_current_head_actions",
        lambda *_args, **_kwargs: _current_head_actions(),
    )

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


def test_cli_output_write_failure_preserves_existing_packet(tmp_path: Path, capsys, monkeypatch) -> None:
    root = REPO_ROOT
    readiness = tmp_path / "readiness.json"
    output = tmp_path / "packet.json"
    temp_output = output.with_name(f"{output.name}.refresh-tmp")
    readiness.write_text(json.dumps(_readiness()), encoding="utf-8")
    output.write_text('{"status":"previous"}\n', encoding="utf-8")
    temp_output.mkdir()
    monkeypatch.setattr(
        release_authorization_packet,
        "_collect_current_head_actions",
        lambda *_args, **_kwargs: _current_head_actions(),
    )

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

    assert code == 4
    assert stdout["status"] == "write_failed"
    assert stdout["write_error"]
    assert stdout["write_error_path"] == output.as_posix()
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "previous"}


def test_cli_output_parent_write_failure_reports_structured_json(tmp_path: Path, capsys, monkeypatch) -> None:
    root = REPO_ROOT
    readiness = tmp_path / "readiness.json"
    blocked_parent = tmp_path / "blocked-parent"
    output = blocked_parent / "packet.json"
    readiness.write_text(json.dumps(_readiness()), encoding="utf-8")
    blocked_parent.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        release_authorization_packet,
        "_collect_current_head_actions",
        lambda *_args, **_kwargs: _current_head_actions(),
    )

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

    assert code == 4
    assert stdout["status"] == "write_failed"
    assert stdout["write_error"]
    assert stdout["write_error_path"] == output.as_posix()
    assert blocked_parent.read_text(encoding="utf-8") == "not a directory"
