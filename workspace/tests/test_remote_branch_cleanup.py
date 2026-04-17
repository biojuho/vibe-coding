from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "execution" / "remote_branch_cleanup.py"
SPEC = importlib.util.spec_from_file_location("remote_branch_cleanup", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def run_main(args: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = MODULE.main(args)
    return code, json.loads(stdout.getvalue())


def test_build_cleanup_plan_marks_remote_only_and_open_pr_branches(monkeypatch, tmp_path: Path) -> None:
    local_repo = tmp_path / "rewrite"
    local_repo.mkdir()

    monkeypatch.setattr(
        MODULE,
        "get_repo_metadata",
        lambda repo: {
            "repo_full_name": repo,
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(MODULE, "list_local_branches", lambda repo_dir: ["codex/dashboard-refresh", "main"])
    monkeypatch.setattr(
        MODULE,
        "list_remote_branches",
        lambda repo_dir, remote: [
            "codex/dashboard-refresh",
            "dependabot/pip/requests-2.32.5",
            "fix/notion-review-status",
            "main",
        ],
    )

    def fake_open_prs(repo: str, branch: str) -> list[dict[str, object]]:
        if branch == "fix/notion-review-status":
            return [
                {
                    "number": 123,
                    "title": "Keep me for review",
                    "url": "https://github.com/biojuho/vibe-coding/pull/123",
                    "head_ref": branch,
                }
            ]
        return []

    monkeypatch.setattr(MODULE, "list_open_pull_requests_for_branch", fake_open_prs)

    code, output = run_main(
        [
            "--repo",
            "biojuho/vibe-coding",
            "--local-repo",
            str(local_repo),
        ]
    )

    assert code == 0
    assert output["status"] == "ok"
    assert output["remote_only_count"] == 2
    assert output["safe_to_delete_count"] == 1
    assert output["blocked_count"] == 1

    rows = {row["name"]: row for row in output["remote_only_branches"]}
    assert rows["dependabot/pip/requests-2.32.5"]["safe_to_delete"] is True
    assert str(local_repo.resolve()) in rows["dependabot/pip/requests-2.32.5"]["delete_command"]
    assert rows["fix/notion-review-status"]["safe_to_delete"] is False
    assert rows["fix/notion-review-status"]["open_pull_requests"][0]["number"] == 123


def test_write_delete_script_includes_only_safe_commands(monkeypatch, tmp_path: Path) -> None:
    local_repo = tmp_path / "rewrite"
    local_repo.mkdir()
    script_path = tmp_path / "delete_remote_only_branches.ps1"

    monkeypatch.setattr(
        MODULE,
        "get_repo_metadata",
        lambda repo: {
            "repo_full_name": repo,
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(MODULE, "list_local_branches", lambda repo_dir: ["main"])
    monkeypatch.setattr(
        MODULE,
        "list_remote_branches",
        lambda repo_dir, remote: [
            "dependabot/npm_and_yarn/foo",
            "main",
            "release/keep-me",
        ],
    )

    def fake_open_prs(repo: str, branch: str) -> list[dict[str, object]]:
        if branch == "release/keep-me":
            return [{"number": 9, "title": "blocked", "url": "https://example.com/pr/9", "head_ref": branch}]
        return []

    monkeypatch.setattr(MODULE, "list_open_pull_requests_for_branch", fake_open_prs)

    code, output = run_main(
        [
            "--repo",
            "biojuho/vibe-coding",
            "--local-repo",
            str(local_repo),
            "--write-delete-script",
            str(script_path),
        ]
    )

    assert code == 0
    assert Path(output["delete_script_path"]).exists()

    contents = script_path.read_text(encoding="utf-8")
    assert 'push origin --delete "dependabot/npm_and_yarn/foo"' in contents
    assert 'push origin --delete "release/keep-me"' not in contents


def test_protected_branch_names_are_blocked_even_without_open_prs(monkeypatch, tmp_path: Path) -> None:
    local_repo = tmp_path / "rewrite"
    local_repo.mkdir()

    monkeypatch.setattr(
        MODULE,
        "get_repo_metadata",
        lambda repo: {
            "repo_full_name": repo,
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(MODULE, "list_local_branches", lambda repo_dir: ["main"])
    monkeypatch.setattr(MODULE, "list_remote_branches", lambda repo_dir, remote: ["develop", "main"])
    monkeypatch.setattr(MODULE, "list_open_pull_requests_for_branch", lambda repo, branch: [])

    code, output = run_main(
        [
            "--repo",
            "biojuho/vibe-coding",
            "--local-repo",
            str(local_repo),
            "--protect-branch",
            "develop",
        ]
    )

    assert code == 0
    row = output["remote_only_branches"][0]
    assert row["name"] == "develop"
    assert row["is_protected_name"] is True
    assert row["safe_to_delete"] is False
