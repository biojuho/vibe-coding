from __future__ import annotations

import json
import subprocess
from pathlib import Path

from execution.pr_triage_worktree import _decode_output, cleanup_session, prepare_session


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run_git(repo, "init", "-b", "main")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test User")


def _commit_file(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    _run_git(repo, "add", name)
    _run_git(repo, "commit", "-m", message)


def test_prepare_session_creates_manifest_and_clean_conflict_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit_file(repo, "app.txt", "base\n", "base commit")
    _run_git(repo, "checkout", "-b", "feature")
    _commit_file(repo, "app.txt", "feature\n", "feature commit")

    manifest = prepare_session(repo, "feature", base_ref="main", label="pr-42")

    manifest_path = Path(manifest["artifacts"]["manifest_path"])
    conflict_state_path = Path(manifest["artifacts"]["conflict_state_path"])
    worktree_path = Path(manifest["worktree_path"])

    assert manifest["head_ref"] == "feature"
    assert manifest["base_ref"] == "main"
    assert manifest["conflict_check"]["status"] == "clean"
    assert manifest_path.is_file()
    assert conflict_state_path.is_file()
    assert worktree_path.is_dir()

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["head_sha"] == manifest["head_sha"]

    cleanup = cleanup_session(Path(manifest["session_dir"]))
    assert cleanup["removed"] is True
    assert not worktree_path.exists()
    assert not Path(manifest["session_dir"]).exists()


def test_prepare_session_detects_conflicts_and_restores_head(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _commit_file(repo, "conflict.txt", "shared\n", "base commit")
    _run_git(repo, "checkout", "-b", "feature")
    _commit_file(repo, "conflict.txt", "feature change\n", "feature change")
    _run_git(repo, "checkout", "main")
    _commit_file(repo, "conflict.txt", "main change\n", "main change")

    manifest = prepare_session(repo, "feature", base_ref="main", label="pr-conflict")
    worktree_path = Path(manifest["worktree_path"])

    assert manifest["conflict_check"]["status"] == "conflicted"
    assert manifest["conflict_check"]["conflicted_files"] == ["conflict.txt"]
    assert _run_git(worktree_path, "rev-parse", "HEAD").stdout.strip() == manifest["head_sha"]
    assert _run_git(worktree_path, "status", "--short").stdout.strip() == ""

    cleanup_session(Path(manifest["session_dir"]))


def test_decode_output_falls_back_to_windows_ansi_when_utf8_fails() -> None:
    payload = "박주호".encode("cp949")

    assert _decode_output(payload) == "박주호"
