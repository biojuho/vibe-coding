#!/usr/bin/env python3
"""Inventory local projects and GitHub automation surfaces."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_MARKERS = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "CLAUDE.md",
)
TEST_FILE_SUFFIXES = (
    "_test.py",
    ".test.js",
    ".test.jsx",
    ".test.mjs",
    ".test.py",
    ".test.mts",
    ".test.ts",
    ".test.tsx",
    ".spec.js",
    ".spec.jsx",
    ".spec.mjs",
    ".spec.mts",
    ".spec.ts",
    ".spec.tsx",
)
TEST_FILE_PREFIXES = ("test_",)
TEST_SCAN_EXCLUDES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".tmp",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "output",
    "venv",
}
MAX_TEST_FILE_SAMPLES = 20


def _run(args: list[str], cwd: Path, timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc), "stdout": "", "stderr": ""}
    return {
        "available": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _has_any(path: Path, names: tuple[str, ...]) -> bool:
    return any((path / name).exists() for name in names)


def _read_package_scripts(path: Path) -> dict[str, str]:
    package_path = path / "package.json"
    try:
        data = json.loads(package_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items() if isinstance(value, str)}


def _has_usable_package_test_script(path: Path) -> bool:
    script = _read_package_scripts(path).get("test", "").strip().lower()
    if not script:
        return False
    if "no test specified" in script:
        return False
    if script in {"exit 1", "false"} or script.startswith("exit 1 "):
        return False
    return True


def _is_test_file_name(name: str) -> bool:
    is_python_prefix_test = name.endswith(".py") and any(name.startswith(prefix) for prefix in TEST_FILE_PREFIXES)
    return is_python_prefix_test or any(name.endswith(suffix) for suffix in TEST_FILE_SUFFIXES)


def _test_file_summary(path: Path, root: Path) -> tuple[int, list[str]]:
    count = 0
    samples: list[str] = []
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
            continue
        for candidate in children:
            if current == path and path == root and candidate.name == "projects":
                continue
            if candidate.name in TEST_SCAN_EXCLUDES:
                continue
            if candidate.is_dir():
                stack.append(candidate)
                continue
            if not candidate.is_file():
                continue
            name = candidate.name
            if name.startswith("."):
                continue
            if _is_test_file_name(name):
                count += 1
                if len(samples) < MAX_TEST_FILE_SAMPLES:
                    samples.append(_relative(candidate, root))
    return count, sorted(samples)


def _project_info(path: Path, root: Path) -> dict[str, Any]:
    workflows = sorted((path / ".github" / "workflows").glob("*.y*ml")) if (path / ".github").exists() else []
    markers = [name for name in PROJECT_MARKERS if (path / name).exists()]
    tests_dirs = [name for name in ("test", "tests", "__tests__") if (path / name).exists()]
    test_file_count, test_files = _test_file_summary(path, root)
    has_package_test_script = _has_usable_package_test_script(path)
    return {
        "path": _relative(path, root),
        "markers": markers,
        "has_src": (path / "src").exists(),
        "has_tests": bool(tests_dirs or test_file_count or has_package_test_script),
        "test_dirs": tests_dirs,
        "test_file_count": test_file_count,
        "test_files": test_files,
        "has_package_test_script": has_package_test_script,
        "has_readme": any((path / name).exists() for name in ("README.md", "readme.md")),
        "has_env_example": (path / ".env.example").exists(),
        "has_dockerfile": (path / "Dockerfile").exists(),
        "workflows": [_relative(workflow, root) for workflow in workflows],
        "dependabot": _relative(path / ".github" / "dependabot.yml", root)
        if (path / ".github" / "dependabot.yml").exists()
        else None,
    }


def _discover_projects(root: Path) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    projects_dir = root / "projects"
    if projects_dir.exists():
        candidates.extend(path for path in projects_dir.iterdir() if path.is_dir())
    if _has_any(root, PROJECT_MARKERS):
        candidates.append(root)

    unique = sorted({path.resolve() for path in candidates})
    return [_project_info(path, root) for path in unique if _has_any(path, PROJECT_MARKERS)]


def _status_dirty_lines(status_stdout: str) -> list[str]:
    return [line for line in status_stdout.splitlines() if line and not line.startswith("##")]


def _status_path(line: str) -> str:
    return line[3:].strip() if len(line) > 3 else line.strip()


def _diff_is_clean(result: dict[str, Any]) -> bool:
    return result.get("available") is True and result.get("returncode") == 0


def _diff_is_dirty(result: dict[str, Any]) -> bool:
    return result.get("available") is True and result.get("returncode") == 1


def _confirmed_dirty_count(
    status_dirty_lines: list[str],
    *,
    worktree_diff: dict[str, Any],
    cached_diff: dict[str, Any],
) -> tuple[int, list[str], str]:
    if not status_dirty_lines:
        return 0, [], "status_clean"

    dirty_paths = [_status_path(line) for line in status_dirty_lines]
    if any(line.startswith("??") for line in status_dirty_lines):
        return len(status_dirty_lines), dirty_paths, "untracked"

    if _diff_is_dirty(worktree_diff) or _diff_is_dirty(cached_diff):
        return len(status_dirty_lines), dirty_paths, "diff_dirty"

    if _diff_is_clean(worktree_diff) and _diff_is_clean(cached_diff):
        return 0, [], "diff_clean_status_stale"

    return len(status_dirty_lines), dirty_paths, "status_unconfirmed"


def _git_summary(root: Path) -> dict[str, Any]:
    index_refresh = _run(["git", "update-index", "-q", "--refresh"], root)
    branch = _run(["git", "branch", "--show-current"], root)
    status = _run(["git", "status", "--porcelain=v1", "-b"], root)
    worktree_diff = _run(["git", "diff", "--quiet"], root)
    cached_diff = _run(["git", "diff", "--cached", "--quiet"], root)
    remote = _run(["git", "remote", "-v"], root)
    status_dirty_lines = _status_dirty_lines(str(status.get("stdout") or "")) if status.get("available") else []
    dirty_count, dirty_paths, dirty_confirmation = _confirmed_dirty_count(
        status_dirty_lines,
        worktree_diff=worktree_diff,
        cached_diff=cached_diff,
    )
    return {
        "branch": branch.get("stdout") if branch.get("returncode") == 0 else None,
        "dirty_count": dirty_count,
        "dirty_paths": dirty_paths,
        "status_dirty_count": len(status_dirty_lines),
        "dirty_confirmation": dirty_confirmation,
        "index_refresh": index_refresh,
        "status": status,
        "worktree_diff": worktree_diff,
        "cached_diff": cached_diff,
        "remote": remote,
    }


def _workflow_files(root: Path) -> list[str]:
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.exists():
        return []
    return [_relative(path, root) for path in sorted(workflow_dir.glob("*.y*ml"))]


def _dependabot_files(root: Path) -> list[str]:
    files = []
    for path in (root / ".github").glob("dependabot.y*ml") if (root / ".github").exists() else []:
        files.append(_relative(path, root))
    for path in (root / "projects").glob("*/.github/dependabot.y*ml") if (root / "projects").exists() else []:
        files.append(_relative(path, root))
    return sorted(files)


def _open_prs(root: Path, include_prs: bool) -> dict[str, Any]:
    if not include_prs:
        return {"requested": False}
    if shutil.which("gh") is None:
        return {"requested": True, "available": False, "error": "gh CLI not found"}
    fields = "number,title,headRefName,baseRefName,mergeStateStatus,isDraft,author,updatedAt,url"
    result = _run(["gh", "pr", "list", "--limit", "100", "--json", fields], root, timeout=45)
    if result.get("returncode") != 0:
        return {"requested": True, "available": False, "error": result.get("stderr") or result.get("stdout")}
    try:
        prs = json.loads(result.get("stdout") or "[]")
    except json.JSONDecodeError as exc:
        return {"requested": True, "available": False, "error": f"failed to parse gh output: {exc}"}
    return {"requested": True, "available": True, "count": len(prs), "items": prs}


def _recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if summary["git"]["dirty_count"]:
        recommendations.append("Worktree is dirty; stage and commit only files owned by the current experiment.")
    missing_readme = [project["path"] for project in summary["projects"] if not project.get("has_readme")]
    if missing_readme:
        recommendations.append(
            "Add a root README.md for project(s) missing a GitHub-visible entrypoint: " + ", ".join(missing_readme)
        )
    if not summary["workflows"]:
        recommendations.append(
            "No root GitHub Actions workflows found; verify each active project has a deterministic QC path."
        )
    if not summary["dependabot_files"]:
        recommendations.append(
            "No Dependabot config found; consider dependency automation after project-specific gates are clear."
        )
    prs = summary.get("open_prs", {})
    if prs.get("available") and prs.get("count", 0):
        blocked = [pr for pr in prs["items"] if pr.get("mergeStateStatus") == "BLOCKED"]
        if blocked:
            recommendations.append(
                f"{len(blocked)} open PR(s) are BLOCKED; inspect required checks before merge automation."
            )
        dependabot = [pr for pr in prs["items"] if "dependabot" in pr.get("headRefName", "").lower()]
        if dependabot:
            recommendations.append(
                f"{len(dependabot)} Dependabot PR(s) found; triage patch/minor updates before major upgrades."
            )
    return recommendations


def build_inventory(root: Path, include_prs: bool) -> dict[str, Any]:
    root = root.resolve()
    summary: dict[str, Any] = {
        "root": str(root),
        "git": _git_summary(root),
        "projects": _discover_projects(root),
        "workflows": _workflow_files(root),
        "dependabot_files": _dependabot_files(root),
        "open_prs": _open_prs(root, include_prs),
    }
    summary["recommendations"] = _recommendations(summary)
    return summary


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to inspect")
    parser.add_argument("--include-prs", action="store_true", help="Include open PRs via gh CLI")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output. This is the default and is kept for automation consistency.",
    )
    parser.add_argument("--output", type=Path, help="Optional path to write the inventory JSON")
    args = parser.parse_args(argv)

    inventory = build_inventory(args.root, args.include_prs)
    if args.output:
        _write_json(args.output, inventory)
    json.dump(inventory, sys.stdout, ensure_ascii=True, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
