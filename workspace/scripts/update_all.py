from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from path_contract import REPO_ROOT


SCAN_EXCLUDES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".tmp",
    ".agent",
    ".agents",
    ".claude",
    ".codex",
    "dist",
    "build",
    ".next",
}


@dataclass
class RepoUpdateResult:
    path: Path
    branch: str
    dirty: bool
    status: str
    detail: str = ""


def run_git(repo: Path, *args: str, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def list_git_repos(root: Path) -> list[Path]:
    repos: list[Path] = []
    if (root / ".git").is_dir():
        repos.append(root)

    for git_dir in root.rglob(".git"):
        if not git_dir.is_dir():
            continue
        parent_name = git_dir.parent.name
        if parent_name in SCAN_EXCLUDES:
            continue
        repos.append(git_dir.parent)

    deduped = sorted({p.resolve() for p in repos})
    return deduped


def get_branch(repo: Path) -> str:
    result = run_git(repo, "symbolic-ref", "--short", "HEAD")
    if result.returncode != 0:
        fallback = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        if fallback.returncode != 0:
            return "unknown"
        return fallback.stdout.strip() or "unknown"
    return result.stdout.strip() or "unknown"


def is_dirty(repo: Path) -> bool:
    result = run_git(repo, "status", "--porcelain")
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def has_upstream(repo: Path) -> bool:
    result = run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return result.returncode == 0 and bool(result.stdout.strip())


def update_repo(repo: Path, strategy: str, skip_dirty: bool) -> RepoUpdateResult:
    branch = get_branch(repo)
    dirty = is_dirty(repo)

    if skip_dirty and dirty:
        return RepoUpdateResult(
            path=repo,
            branch=branch,
            dirty=dirty,
            status="skipped_dirty",
            detail="Working tree has local changes.",
        )

    fetch_result = run_git(repo, "fetch", "--all", "--prune")
    if fetch_result.returncode != 0:
        return RepoUpdateResult(
            path=repo,
            branch=branch,
            dirty=dirty,
            status="fetch_failed",
            detail=(fetch_result.stderr or fetch_result.stdout).strip(),
        )

    if not has_upstream(repo):
        return RepoUpdateResult(
            path=repo,
            branch=branch,
            dirty=dirty,
            status="no_upstream",
            detail="No upstream tracking branch.",
        )

    if strategy == "rebase":
        pull_args = ["pull", "--rebase", "--autostash"]
    else:
        pull_args = ["pull", "--ff-only"]

    pull_result = run_git(repo, *pull_args, timeout=180)
    if pull_result.returncode != 0:
        return RepoUpdateResult(
            path=repo,
            branch=branch,
            dirty=dirty,
            status="pull_failed",
            detail=(pull_result.stderr or pull_result.stdout).strip(),
        )

    detail = (pull_result.stdout or "").strip()
    if "Already up to date." in detail or "Already up-to-date." in detail:
        status = "up_to_date"
    else:
        status = "updated"

    return RepoUpdateResult(path=repo, branch=branch, dirty=dirty, status=status, detail=detail)


def print_repo_list(repos: Iterable[Path]) -> None:
    print("Detected repositories:")
    for repo in repos:
        branch = get_branch(repo)
        dirty = "dirty" if is_dirty(repo) else "clean"
        print(f"- {repo} [{branch}] ({dirty})")


def summarize(results: list[RepoUpdateResult]) -> int:
    counters: dict[str, int] = {}
    for res in results:
        counters[res.status] = counters.get(res.status, 0) + 1

    print("\nSummary:")
    for key in sorted(counters):
        print(f"- {key}: {counters[key]}")

    failed = counters.get("fetch_failed", 0) + counters.get("pull_failed", 0)
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upgrade all nested git repositories by pulling latest changes safely.",
    )
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="Root directory to scan (default: repository root).",
    )
    parser.add_argument(
        "--strategy",
        choices=["ff-only", "rebase"],
        default="ff-only",
        help="Pull strategy (default: ff-only).",
    )
    parser.add_argument(
        "--include-dirty",
        action="store_true",
        help="Include repositories with local changes.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Number of repositories to update in parallel (default: 4).",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list detected repositories, do not update.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Error: root path does not exist: {root}", file=sys.stderr)
        return 1

    repos = list_git_repos(root)
    print(f"Scanning: {root}")
    print(f"Found {len(repos)} repositories.")

    if not repos:
        return 0

    print_repo_list(repos)
    if args.list_only:
        return 0

    skip_dirty = not args.include_dirty
    print(f"\nStarting updates (strategy={args.strategy}, skip_dirty={skip_dirty}, jobs={max(args.jobs, 1)})")

    results: list[RepoUpdateResult] = []
    with ThreadPoolExecutor(max_workers=max(args.jobs, 1)) as executor:
        future_map = {executor.submit(update_repo, repo, args.strategy, skip_dirty): repo for repo in repos}
        for future in as_completed(future_map):
            repo = future_map[future]
            try:
                res = future.result()
            except Exception as exc:  # pragma: no cover - defensive path
                res = RepoUpdateResult(
                    path=repo,
                    branch="unknown",
                    dirty=False,
                    status="exception",
                    detail=str(exc),
                )

            results.append(res)
            detail = f" | {res.detail}" if res.detail else ""
            print(f"[{res.status}] {res.path} ({res.branch}){detail}")

    return summarize(results)


if __name__ == "__main__":
    raise SystemExit(main())
