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


def _project_info(path: Path, root: Path) -> dict[str, Any]:
    workflows = sorted((path / ".github" / "workflows").glob("*.y*ml")) if (path / ".github").exists() else []
    markers = [name for name in PROJECT_MARKERS if (path / name).exists()]
    tests_dirs = [name for name in ("test", "tests", "__tests__") if (path / name).exists()]
    return {
        "path": _relative(path, root),
        "markers": markers,
        "has_src": (path / "src").exists(),
        "has_tests": bool(tests_dirs),
        "test_dirs": tests_dirs,
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


def _git_summary(root: Path) -> dict[str, Any]:
    branch = _run(["git", "branch", "--show-current"], root)
    status = _run(["git", "status", "--porcelain=v1", "-b"], root)
    remote = _run(["git", "remote", "-v"], root)
    dirty_count = 0
    if status.get("available") and status.get("stdout"):
        dirty_count = sum(1 for line in status["stdout"].splitlines() if not line.startswith("##"))
    return {
        "branch": branch.get("stdout") if branch.get("returncode") == 0 else None,
        "dirty_count": dirty_count,
        "status": status,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to inspect")
    parser.add_argument("--include-prs", action="store_true", help="Include open PRs via gh CLI")
    args = parser.parse_args(argv)

    inventory = build_inventory(args.root, args.include_prs)
    json.dump(inventory, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
