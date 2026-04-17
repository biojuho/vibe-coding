from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "execution" / "github_branch_protection.py"
SPEC = importlib.util.spec_from_file_location("github_branch_protection", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def run_main(args: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = MODULE.main(args)
    return code, json.loads(stdout.getvalue())


def test_parse_repo_slug_supports_https_and_ssh_formats() -> None:
    assert MODULE.parse_repo_slug("https://github.com/biojuho/vibe-coding.git") == "biojuho/vibe-coding"
    assert MODULE.parse_repo_slug("git@github.com:biojuho/vibe-coding.git") == "biojuho/vibe-coding"


def test_build_branch_protection_payload_uses_workspace_defaults() -> None:
    payload = MODULE.build_branch_protection_payload(MODULE.DEFAULT_REQUIRED_CHECKS)

    assert payload["required_status_checks"] == {
        "strict": True,
        "contexts": ["root-quality-gate", "test-summary"],
    }
    assert payload["enforce_admins"] is True
    assert payload["required_pull_request_reviews"]["required_approving_review_count"] == 1
    assert payload["required_linear_history"] is True
    assert payload["required_conversation_resolution"] is True


def test_infer_repo_slug_reads_git_remote(monkeypatch) -> None:
    monkeypatch.setattr(
        MODULE,
        "run_command",
        lambda command, input_text=None: subprocess.CompletedProcess(
            command,
            0,
            stdout="https://github.com/biojuho/vibe-coding.git\n",
            stderr="",
        ),
    )

    assert MODULE.infer_repo_slug() == "biojuho/vibe-coding"


def test_check_live_reports_private_repo_plan_blocker(monkeypatch) -> None:
    monkeypatch.setattr(
        MODULE,
        "get_repo_metadata",
        lambda repo: {
            "repo_full_name": repo,
            "repo_visibility": "PRIVATE",
            "is_private": True,
            "default_branch": "main",
        },
    )

    def fake_gh_api_json(endpoint, method="GET", payload=None):
        raise MODULE.GhApiError(
            endpoint=endpoint,
            status=403,
            message=MODULE.UPGRADE_REQUIRED_MESSAGE,
            stdout='{"message":"Upgrade to GitHub Pro or make this repository public to enable this feature.","status":"403"}',
            stderr="",
        )

    monkeypatch.setattr(MODULE, "gh_api_json", fake_gh_api_json)

    code, output = run_main(["--repo", "biojuho/vibe-coding", "--check-live"])

    assert code == 2
    assert output["status"] == "blocked"
    assert output["repo_visibility"] == "PRIVATE"
    assert output["next_step"] == MODULE.BLOCKED_NEXT_STEP


def test_apply_reports_successful_live_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        MODULE,
        "get_repo_metadata",
        lambda repo: {
            "repo_full_name": repo,
            "repo_visibility": "PRIVATE",
            "is_private": True,
            "default_branch": "main",
        },
    )

    def fake_gh_api_json(endpoint, method="GET", payload=None):
        assert method == "PUT"
        assert payload["required_status_checks"]["contexts"] == [
            "root-quality-gate",
            "test-summary",
        ]
        return {
            "required_status_checks": {
                "strict": True,
                "contexts": ["root-quality-gate", "test-summary"],
            },
            "enforce_admins": {"enabled": True},
            "required_linear_history": {"enabled": True},
            "required_conversation_resolution": {"enabled": True},
            "allow_force_pushes": {"enabled": False},
            "allow_deletions": {"enabled": False},
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
            },
        }

    monkeypatch.setattr(MODULE, "gh_api_json", fake_gh_api_json)

    code, output = run_main(["--repo", "biojuho/vibe-coding", "--apply"])

    assert code == 0
    assert output["status"] == "applied"
    assert output["live"]["required_checks"] == ["root-quality-gate", "test-summary"]
    assert output["live"]["enforce_admins"] is True
