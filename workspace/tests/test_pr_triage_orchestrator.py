from __future__ import annotations

import json
import sys
from pathlib import Path

from execution.pr_triage_orchestrator import (
    ValidationCommand,
    ValidationProfile,
    resolve_profile_name,
    run_triage,
    run_validation_command,
)


def test_resolve_profile_name_uses_repo_specific_match(tmp_path: Path) -> None:
    repo = tmp_path / "word-chain"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint .","build":"vite build"}}', encoding="utf-8")

    assert resolve_profile_name(repo) == "word-chain"


def test_resolve_profile_name_falls_back_to_generic_node(tmp_path: Path) -> None:
    repo = tmp_path / "custom-ui"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint .","test":"vitest run"}}', encoding="utf-8")

    assert resolve_profile_name(repo) == "node-generic"


def test_run_validation_command_skips_when_required_source_paths_are_missing(tmp_path: Path) -> None:
    source_repo = tmp_path / "word-chain"
    worktree = tmp_path / "session" / "repo"
    logs_dir = tmp_path / "session" / "logs"
    source_repo.mkdir()
    worktree.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    (worktree / "package.json").write_text("{}", encoding="utf-8")

    command = ValidationCommand(
        name="npm-lint",
        args=("npm", "run", "lint"),
        required_worktree_paths=("package.json",),
        required_source_paths=("node_modules",),
        env_mode="node",
    )

    result = run_validation_command(command, source_repo=source_repo, worktree_path=worktree, logs_dir=logs_dir)

    assert result["status"] == "SKIP"
    assert "node_modules" in result["message"]


def test_run_triage_writes_report_and_keeps_session_artifacts(tmp_path: Path, monkeypatch) -> None:
    source_repo = tmp_path / "blind-to-x"
    session_dir = tmp_path / "session"
    worktree = session_dir / "repo"
    source_repo.mkdir()
    worktree.mkdir(parents=True)
    (worktree / "README.md").write_text("ok\n", encoding="utf-8")

    manifest = {
        "repo_path": str(source_repo),
        "session_dir": str(session_dir),
        "worktree_path": str(worktree),
        "artifacts": {
            "manifest_path": str(session_dir / "manifest.json"),
            "conflict_state_path": str(session_dir / "conflict-state.json"),
        },
        "conflict_check": {"status": "clean"},
    }
    Path(manifest["artifacts"]["manifest_path"]).write_text(json.dumps(manifest), encoding="utf-8")
    Path(manifest["artifacts"]["conflict_state_path"]).write_text('{"status":"clean"}', encoding="utf-8")

    monkeypatch.setattr(
        "execution.pr_triage_orchestrator.prepare_session",
        lambda *args, **kwargs: manifest,
    )
    monkeypatch.setattr(
        "execution.pr_triage_orchestrator.cleanup_session",
        lambda *args, **kwargs: {
            "session_dir": str(session_dir),
            "worktree_path": str(worktree),
            "removed": True,
            "session_dir_exists": True,
        },
    )
    monkeypatch.setattr(
        "execution.pr_triage_orchestrator.build_validation_profile",
        lambda repo_root, requested_profile=None: ValidationProfile(
            name="custom",
            description="custom profile",
            commands=(
                ValidationCommand(
                    name="python-ok",
                    args=(sys.executable, "-c", "print('triage ok')"),
                    required_worktree_paths=("README.md",),
                ),
            ),
        ),
    )

    report = run_triage(source_repo, "feature/test")
    report_path = session_dir / "triage-report.json"
    log_files = list((session_dir / "logs").glob("*.log"))

    assert report["validation"]["status"] == "PASS"
    assert report["cleanup"]["removed"] is True
    assert report_path.is_file()
    assert log_files

    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["profile"]["name"] == "custom"
    assert persisted["validation"]["results"][0]["status"] == "PASS"
