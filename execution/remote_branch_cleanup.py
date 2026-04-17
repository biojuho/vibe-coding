"""
Deterministic helper for remote-only branch cleanup before a public repository flip.

The main use case is comparing a sanitized rewrite sandbox (for example,
`.tmp/public-history-rewrite`) with the live GitHub remote. Any branch that
still exists on the remote but not in the sanitized local clone must either be
deleted or handled in a broader rewrite plan before making the repository
public.

Examples:
    python execution/remote_branch_cleanup.py --local-repo .tmp/public-history-rewrite
    python execution/remote_branch_cleanup.py --local-repo .tmp/public-history-rewrite --write-delete-script .tmp/public-history-rewrite/delete_remote_only_branches.ps1
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from urllib.parse import quote, urlparse


ACCEPT_HEADER = "Accept: application/vnd.github+json"


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd) if cwd is not None else None,
    )


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


def infer_repo_slug(remote: str, *, cwd: Path) -> str:
    result = run_command(["git", "remote", "get-url", remote], cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"Unable to read git remote '{remote}': {stderr}")
    return parse_repo_slug(result.stdout.strip())


def gh_api_json(endpoint: str) -> dict[str, object]:
    result = run_command(["gh", "api", "-H", ACCEPT_HEADER, endpoint])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "gh api request failed."
        raise RuntimeError(f"{endpoint}: {stderr}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected non-JSON response from gh api for {endpoint}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected response type from gh api for {endpoint}")
    return parsed


def gh_api_list(endpoint: str) -> list[dict[str, object]]:
    result = run_command(["gh", "api", "-H", ACCEPT_HEADER, endpoint])
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "gh api request failed."
        raise RuntimeError(f"{endpoint}: {stderr}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Unexpected non-JSON response from gh api for {endpoint}") from exc
    if not isinstance(parsed, list):
        raise RuntimeError(f"Unexpected response type from gh api for {endpoint}")
    rows: list[dict[str, object]] = []
    for item in parsed:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def get_repo_metadata(repo: str) -> dict[str, object]:
    data = gh_api_json(f"repos/{repo}")
    default_branch = data.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch.strip():
        raise RuntimeError(f"Repository {repo} did not return a default branch.")
    return {
        "repo_full_name": data.get("full_name", repo),
        "default_branch": default_branch,
    }


def list_local_branches(repo_dir: Path) -> list[str]:
    result = run_command(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"],
        cwd=repo_dir,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"Unable to list local branches in {repo_dir}: {stderr}")
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def list_remote_branches(repo_dir: Path, remote: str) -> list[str]:
    result = run_command(["git", "ls-remote", "--heads", remote], cwd=repo_dir)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"Unable to list remote branches from {remote}: {stderr}")

    branches: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            branches.add(ref[len(prefix) :])
    return sorted(branches)


def list_open_pull_requests_for_branch(repo: str, branch: str) -> list[dict[str, object]]:
    owner = repo.split("/", 1)[0]
    head = quote(f"{owner}:{branch}", safe=":")
    pulls = gh_api_list(f"repos/{repo}/pulls?state=open&head={head}")
    rows: list[dict[str, object]] = []
    for pull in pulls:
        number = pull.get("number")
        title = pull.get("title")
        url = pull.get("html_url")
        head_ref = pull.get("head", {})
        if isinstance(head_ref, dict):
            head_name = head_ref.get("ref")
        else:
            head_name = None
        rows.append(
            {
                "number": number,
                "title": title,
                "url": url,
                "head_ref": head_name,
            }
        )
    return rows


def build_delete_command(local_repo: Path, remote: str, branch: str) -> str:
    resolved = str(local_repo.resolve())
    return f'git -C "{resolved}" push {remote} --delete "{branch}"'


def build_cleanup_plan(
    *,
    repo: str,
    local_repo: Path,
    remote: str,
    protected_branches: set[str],
) -> dict[str, object]:
    metadata = get_repo_metadata(repo)
    default_branch = str(metadata["default_branch"])
    local_branches = list_local_branches(local_repo)
    remote_branches = list_remote_branches(local_repo, remote)

    remote_only = [branch for branch in remote_branches if branch not in set(local_branches)]
    branch_rows: list[dict[str, object]] = []
    safe_count = 0
    blocked_count = 0

    for branch in remote_only:
        open_prs = list_open_pull_requests_for_branch(repo, branch)
        is_protected = branch == default_branch or branch in protected_branches
        safe_to_delete = not is_protected and not open_prs
        if safe_to_delete:
            safe_count += 1
        else:
            blocked_count += 1

        branch_rows.append(
            {
                "name": branch,
                "open_pull_requests": open_prs,
                "is_default_branch": branch == default_branch,
                "is_protected_name": branch in protected_branches,
                "safe_to_delete": safe_to_delete,
                "delete_command": build_delete_command(local_repo, remote, branch) if safe_to_delete else None,
            }
        )

    return {
        "status": "ok",
        "repo": repo,
        "default_branch": default_branch,
        "remote": remote,
        "local_repo": str(local_repo.resolve()),
        "local_branch_count": len(local_branches),
        "remote_branch_count": len(remote_branches),
        "remote_only_count": len(remote_only),
        "safe_to_delete_count": safe_count,
        "blocked_count": blocked_count,
        "remote_only_branches": branch_rows,
        "next_steps": [
            "Rotate or revoke leaked credentials before deleting remote branches or making the repository public.",
            "Review any branches blocked by open pull requests or protected-name rules.",
            "Run the generated delete commands from the sanitized rewrite clone, then push the rewritten branches from that same clone.",
            "After the repository becomes public, apply branch protection with execution/github_branch_protection.py.",
        ],
    }


def write_delete_script(path: Path, plan: dict[str, object]) -> Path:
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"# Generated by execution/remote_branch_cleanup.py for {plan['repo']}",
        f"# Local sanitized clone: {plan['local_repo']}",
        "# Review blocked branches in the JSON plan before running this script.",
        "",
    ]

    safe_rows = [
        row
        for row in plan["remote_only_branches"]
        if isinstance(row, dict) and row.get("safe_to_delete") and row.get("delete_command")
    ]
    for row in safe_rows:
        lines.append(str(row["delete_command"]))

    if not safe_rows:
        lines.append("# No safe-to-delete remote-only branches were found.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory remote-only GitHub branches relative to a sanitized local clone.",
    )
    parser.add_argument("--repo", help="GitHub owner/repo slug. Defaults to the specified local repo's origin remote.")
    parser.add_argument(
        "--local-repo",
        default=".",
        help="Local repo path to compare against the live remote. Use the sanitized rewrite clone here.",
    )
    parser.add_argument("--remote", default="origin", help="Git remote name to inspect. Default: origin")
    parser.add_argument(
        "--protect-branch",
        action="append",
        default=[],
        help="Additional branch names that should never be marked safe_to_delete.",
    )
    parser.add_argument(
        "--write-delete-script",
        help="Optional path for a generated PowerShell script containing only safe delete commands.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    local_repo = Path(args.local_repo).resolve()
    repo = args.repo or infer_repo_slug(args.remote, cwd=local_repo)
    protected_branches = {branch.strip() for branch in args.protect_branch if branch.strip()}

    try:
        plan = build_cleanup_plan(
            repo=repo,
            local_repo=local_repo,
            remote=args.remote,
            protected_branches=protected_branches,
        )
        if args.write_delete_script:
            script_path = write_delete_script(Path(args.write_delete_script), plan)
            plan["delete_script_path"] = str(script_path)
    except Exception as exc:  # pragma: no cover - JSON wrapper path
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
