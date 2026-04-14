"""
Deterministic helper for GitHub branch protection on the current repository.

This script exists for workspace task T-199. The current repository is private,
and GitHub Free blocks branch protection for private repositories. The helper
keeps the desired protection payload reproducible today, reports the current
blocker cleanly, and can apply the rule later with a single command once the
account is upgraded to GitHub Pro or the repository is made public.

Examples:
    python execution/github_branch_protection.py
    python execution/github_branch_protection.py --check-live
    python execution/github_branch_protection.py --apply
    python execution/github_branch_protection.py --required-check test-summary
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


DEFAULT_REQUIRED_CHECKS = [
    "root-quality-gate",
    "test-summary",
]
UPGRADE_REQUIRED_MESSAGE = "Upgrade to GitHub Pro or make this repository public to enable this feature."
BLOCKED_NEXT_STEP = "Upgrade the owner account to GitHub Pro or make the repository public, then rerun with --apply."
ACCEPT_HEADER = "Accept: application/vnd.github+json"


@dataclass
class GhApiError(RuntimeError):
    endpoint: str
    status: int | None
    message: str
    stdout: str
    stderr: str

    def __str__(self) -> str:
        if self.status is None:
            return self.message
        return f"{self.message} (HTTP {self.status})"

    @classmethod
    def from_process(
        cls,
        endpoint: str,
        result: subprocess.CompletedProcess[str],
    ) -> "GhApiError":
        body: dict[str, Any] = {}
        stdout = result.stdout.strip()
        if stdout:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                body = parsed

        status = body.get("status")
        if isinstance(status, str) and status.isdigit():
            status = int(status)
        if not isinstance(status, int):
            status = None

        message = body.get("message")
        if not isinstance(message, str) or not message.strip():
            message = result.stderr.strip() or stdout or "gh api request failed."

        return cls(
            endpoint=endpoint,
            status=status,
            message=message,
            stdout=result.stdout,
            stderr=result.stderr,
        )


def normalize_required_checks(checks: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for check in checks:
        stripped = check.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            normalized.append(stripped)
    return normalized


def build_branch_protection_payload(
    required_checks: list[str],
    *,
    review_count: int = 1,
) -> dict[str, Any]:
    checks = normalize_required_checks(required_checks)
    if not checks:
        raise ValueError("At least one required status check is required.")
    if review_count < 1:
        raise ValueError("Review count must be at least 1.")

    return {
        "required_status_checks": {
            "strict": True,
            "contexts": checks,
        },
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": review_count,
            "require_last_push_approval": False,
        },
        "restrictions": None,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": True,
        "lock_branch": False,
        "allow_fork_syncing": False,
    }


def parse_repo_slug(remote_url: str) -> str:
    url = remote_url.strip()
    if not url:
        raise ValueError("Remote URL is empty.")

    if url.startswith("git@github.com:"):
        slug = url.split(":", 1)[1]
    elif url.startswith("ssh://git@github.com/"):
        slug = url.split("github.com/", 1)[1]
    else:
        parsed = urlparse(url)
        if parsed.hostname != "github.com":
            raise ValueError(f"Unsupported git remote host: {parsed.hostname or url}")
        slug = parsed.path.lstrip("/")

    if slug.endswith(".git"):
        slug = slug[:-4]
    if slug.count("/") != 1:
        raise ValueError(f"Could not parse owner/repo from remote URL: {remote_url}")
    return slug


def run_command(
    command: list[str],
    *,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        input=input_text,
    )


def infer_repo_slug(remote: str = "origin") -> str:
    result = run_command(["git", "remote", "get-url", remote])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"Unable to read git remote '{remote}': {stderr}")
    return parse_repo_slug(result.stdout.strip())


def gh_api_json(
    endpoint: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    command = ["gh", "api", "-H", ACCEPT_HEADER, "-X", method, endpoint]
    input_text = None
    if payload is not None:
        command.extend(["--input", "-"])
        input_text = json.dumps(payload)

    result = run_command(command, input_text=input_text)
    if result.returncode != 0:
        raise GhApiError.from_process(endpoint, result)

    stdout = result.stdout.strip()
    if not stdout:
        return {}

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected non-JSON response from gh api for {endpoint}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected response type from gh api for {endpoint}")
    return parsed


def get_repo_metadata(repo: str) -> dict[str, Any]:
    data = gh_api_json(f"repos/{repo}")
    return {
        "repo_full_name": data["full_name"],
        "repo_visibility": str(data.get("visibility", "UNKNOWN")).upper(),
        "is_private": bool(data.get("private", False)),
        "default_branch": data.get("default_branch"),
    }


def is_plan_blocked(error: GhApiError) -> bool:
    return error.status == 403 and UPGRADE_REQUIRED_MESSAGE in error.message


def enabled_value(raw: Any) -> Any:
    if isinstance(raw, dict) and "enabled" in raw:
        return raw["enabled"]
    return raw


def summarize_live_protection(data: dict[str, Any]) -> dict[str, Any]:
    required_status_checks = data.get("required_status_checks") or {}
    contexts = required_status_checks.get("contexts") or []
    checks = required_status_checks.get("checks") or []

    normalized_checks = list(contexts)
    for item in checks:
        if isinstance(item, dict):
            context = item.get("context")
            if isinstance(context, str) and context not in normalized_checks:
                normalized_checks.append(context)

    review_rules = data.get("required_pull_request_reviews") or {}
    return {
        "required_checks": normalized_checks,
        "strict_checks": required_status_checks.get("strict"),
        "enforce_admins": enabled_value(data.get("enforce_admins")),
        "required_linear_history": enabled_value(data.get("required_linear_history")),
        "required_conversation_resolution": enabled_value(data.get("required_conversation_resolution")),
        "allow_force_pushes": enabled_value(data.get("allow_force_pushes")),
        "allow_deletions": enabled_value(data.get("allow_deletions")),
        "required_approving_review_count": review_rules.get("required_approving_review_count"),
        "dismiss_stale_reviews": review_rules.get("dismiss_stale_reviews"),
    }


def protection_endpoint(repo: str, branch: str) -> str:
    return f"repos/{repo}/branches/{branch}/protection"


def build_result(
    *,
    status: str,
    repo: str,
    branch: str,
    required_checks: list[str],
    payload: dict[str, Any],
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    result = {
        "status": status,
        "repo": repo,
        "branch": branch,
        "required_checks": list(required_checks),
        "payload": payload,
        "message": message,
    }
    result.update(extra)
    return result


def run_flow(
    *,
    repo: str,
    branch: str,
    required_checks: list[str],
    review_count: int,
    check_live: bool,
    apply: bool,
) -> tuple[int, dict[str, Any]]:
    payload = build_branch_protection_payload(required_checks, review_count=review_count)

    if not check_live and not apply:
        return 0, build_result(
            status="dry-run",
            repo=repo,
            branch=branch,
            required_checks=required_checks,
            payload=payload,
            message="Payload generated locally. Re-run with --check-live or --apply when ready.",
        )

    metadata = get_repo_metadata(repo)
    endpoint = protection_endpoint(repo, branch)

    try:
        if apply:
            live = gh_api_json(endpoint, method="PUT", payload=payload)
            return 0, build_result(
                status="applied",
                repo=repo,
                branch=branch,
                required_checks=required_checks,
                payload=payload,
                message="Branch protection applied successfully.",
                live=summarize_live_protection(live),
                **metadata,
            )

        live = gh_api_json(endpoint)
        return 0, build_result(
            status="configured",
            repo=repo,
            branch=branch,
            required_checks=required_checks,
            payload=payload,
            message="Live branch protection fetched successfully.",
            live=summarize_live_protection(live),
            **metadata,
        )
    except GhApiError as error:
        if is_plan_blocked(error):
            return 2, build_result(
                status="blocked",
                repo=repo,
                branch=branch,
                required_checks=required_checks,
                payload=payload,
                message=error.message,
                next_step=BLOCKED_NEXT_STEP,
                **metadata,
            )
        if not apply and error.status == 404 and "Branch not protected" in error.message:
            return 0, build_result(
                status="unprotected",
                repo=repo,
                branch=branch,
                required_checks=required_checks,
                payload=payload,
                message="Branch protection is not enabled on this branch yet.",
                **metadata,
            )
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview, check, or apply GitHub branch protection for the current repository."
    )
    parser.add_argument(
        "--repo",
        help="Repository slug in owner/repo format. Defaults to the current git remote.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote to inspect when --repo is omitted (default: origin).",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to protect (default: main).",
    )
    parser.add_argument(
        "--required-check",
        action="append",
        default=[],
        help="Repeat to override required status checks.",
    )
    parser.add_argument(
        "--review-count",
        type=int,
        default=1,
        help="Required approving review count (default: 1).",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check-live",
        action="store_true",
        help="Fetch the live branch-protection state from GitHub.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the desired branch-protection payload through the GitHub API.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        repo = args.repo or infer_repo_slug(args.remote)
        required_checks = normalize_required_checks(args.required_check or DEFAULT_REQUIRED_CHECKS)
        exit_code, result = run_flow(
            repo=repo,
            branch=args.branch,
            required_checks=required_checks,
            review_count=args.review_count,
            check_live=args.check_live,
            apply=args.apply,
        )
    except Exception as exc:  # pragma: no cover - exercised through CLI surface
        error_payload = {
            "status": "error",
            "message": str(exc),
        }
        print(json.dumps(error_payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
