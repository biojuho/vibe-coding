"""Build product-readiness scores for the workspace operations dashboard."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ACTIVE_PROJECTS = (
    "blind-to-x",
    "shorts-maker-v2",
    "hanwoo-dashboard",
    "knowledge-dashboard",
)
QC_FRESH_DAYS = 7


@dataclass(frozen=True)
class ProjectProfile:
    name: str
    path: str
    required_files: tuple[str, ...]
    env_checks: tuple[str, ...] = ()


PROJECTS = {
    "blind-to-x": ProjectProfile(
        name="blind-to-x",
        path="projects/blind-to-x",
        required_files=("README.md", "config.example.yaml", "docs/ops-runbook.md"),
    ),
    "shorts-maker-v2": ProjectProfile(
        name="shorts-maker-v2",
        path="projects/shorts-maker-v2",
        required_files=("ARCHITECTURE.md", "CLAUDE.md", "FEATURE.md", "pyproject.toml"),
    ),
    "hanwoo-dashboard": ProjectProfile(
        name="hanwoo-dashboard",
        path="projects/hanwoo-dashboard",
        required_files=("README.md", "API_SPEC.md", "package.json"),
        env_checks=("supabase_password",),
    ),
    "knowledge-dashboard": ProjectProfile(
        name="knowledge-dashboard",
        path="projects/knowledge-dashboard",
        required_files=("README.md", "package.json", "src/app/page.tsx"),
        env_checks=("dashboard_api_key",),
    ),
}


def _round_score(value: float) -> int:
    return int(round(max(0, min(100, value))))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _run_git_status(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception:
        return ""

    if completed.returncode != 0:
        return ""
    return completed.stdout


def _dirty_paths_by_project(status_text: str) -> dict[str, list[str]]:
    dirty: dict[str, list[str]] = {name: [] for name in ACTIVE_PROJECTS}
    for raw_line in status_text.splitlines():
        if len(raw_line) < 4:
            continue
        path = raw_line[3:].replace("\\", "/")
        for name, profile in PROJECTS.items():
            prefix = f"{profile.path}/"
            if path == profile.path or path.startswith(prefix):
                dirty[name].append(path)
                break
    return dirty


def _parse_task_rows(tasks_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_section = ""
    for line in tasks_text.splitlines():
        if line.startswith("## "):
            current_section = line.strip("# ").strip()
            continue
        if not line.startswith("| T-"):
            continue

        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        rows.append(
            {
                "id": cells[0],
                "task": cells[1],
                "owner": cells[2] if len(cells) > 2 else "",
                "section": current_section,
            }
        )
    return rows


def _tasks_by_project(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    tasks_path = repo_root / ".ai" / "TASKS.md"
    try:
        rows = _parse_task_rows(tasks_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {name: [] for name in ACTIVE_PROJECTS}

    by_project: dict[str, list[dict[str, str]]] = {name: [] for name in ACTIVE_PROJECTS}
    by_project["workspace"] = []
    for row in rows:
        task = row["task"]
        matched = False
        for name in ACTIVE_PROJECTS:
            if f"[{name}]" in task:
                by_project[name].append(row)
                matched = True
        if "[workspace]" in task or not matched:
            by_project["workspace"].append(row)
    return by_project


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _qc_freshness(qaqc_data: dict[str, Any], now: datetime) -> dict[str, Any]:
    checked_at = _parse_timestamp(qaqc_data.get("timestamp"))
    if checked_at is None:
        return {"checked_at": None, "age_days": None, "stale": False}

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age = now.astimezone(timezone.utc) - checked_at.astimezone(timezone.utc)
    age_days = max(0, age.days)
    return {
        "checked_at": checked_at.isoformat(),
        "age_days": age_days,
        "stale": age_days > QC_FRESH_DAYS,
    }


def _project_qc_status(qaqc_data: dict[str, Any], project_name: str, now: datetime) -> dict[str, Any]:
    freshness = _qc_freshness(qaqc_data, now)
    projects = qaqc_data.get("projects")
    if not isinstance(projects, dict):
        return {"available": False, "status": "UNKNOWN", "passed": 0, "failed": 0, "skipped": 0, **freshness}

    result = projects.get(project_name)
    if not isinstance(result, dict):
        return {"available": False, "status": "UNKNOWN", "passed": 0, "failed": 0, "skipped": 0, **freshness}

    status = str(result.get("status") or "UNKNOWN").upper()
    return {
        "available": True,
        "status": status,
        "passed": int(result.get("passed") or 0),
        "failed": int(result.get("failed") or 0) + int(result.get("errors") or 0),
        "skipped": int(result.get("skipped") or 0),
        **freshness,
    }


def _required_file_status(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
    statuses = []
    project_root = repo_root / profile.path
    for relative in profile.required_files:
        statuses.append({"path": f"{profile.path}/{relative}", "present": (project_root / relative).exists()})
    return statuses


def _env_status(repo_root: Path, profile: ProjectProfile) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if "supabase_password" in profile.env_checks:
        env_path = repo_root / profile.path / ".env"
        content = env_path.read_text(encoding="utf-8", errors="replace") if env_path.exists() else ""
        placeholder = "YOUR_PASSWORD" in content
        configured = "DATABASE_URL=" in content and not placeholder
        checks.append(
            {
                "name": "Supabase DATABASE_URL",
                "ok": configured,
                "severity": "blocker" if not configured else "ok",
                "message": "DATABASE_URL still contains YOUR_PASSWORD."
                if placeholder
                else "DATABASE_URL is configured.",
            }
        )
    if "dashboard_api_key" in profile.env_checks:
        checks.append(
            {
                "name": "Dashboard API key",
                "ok": True,
                "severity": "watch",
                "message": "Runtime key is checked by the dashboard auth route.",
            }
        )

    if not checks:
        return {"available": False, "score": 10, "checks": []}

    blocker_count = sum(1 for check in checks if check["severity"] == "blocker")
    score = 0 if blocker_count else 15
    return {"available": True, "score": score, "checks": checks}


def _score_project(
    *,
    repo_root: Path,
    profile: ProjectProfile,
    qaqc_data: dict[str, Any],
    project_tasks: list[dict[str, str]],
    dirty_paths: list[str],
    now: datetime,
) -> dict[str, Any]:
    qc = _project_qc_status(qaqc_data, profile.name, now)
    docs = _required_file_status(repo_root, profile)
    env = _env_status(repo_root, profile)

    qc_score = 12
    if qc["available"] and qc["status"] == "PASS" and qc["failed"] == 0:
        qc_score = 35
    elif qc["available"] and qc["failed"] == 0:
        qc_score = 25
    elif qc["available"]:
        qc_score = 0
    if qc.get("stale"):
        qc_score = min(qc_score, 20)

    active_blockers = [
        task
        for task in project_tasks
        if task["section"].upper().startswith("TODO") or task["section"].upper().startswith("IN_PROGRESS")
    ]
    blocker_score = 25 if not active_blockers else max(0, 25 - 14 * len(active_blockers))
    docs_score = 15 * (sum(1 for item in docs if item["present"]) / max(1, len(docs)))
    worktree_score = 10 if not dirty_paths else max(2, 10 - len(dirty_paths) * 2)
    env_score = env["score"]
    score = _round_score(qc_score + blocker_score + docs_score + worktree_score + env_score)

    env_blocked = any(check.get("severity") == "blocker" for check in env.get("checks", []))
    if env_blocked or any(task["owner"].lower() == "user" for task in active_blockers):
        state = "blocked"
    elif score >= 85:
        state = "ready"
    elif score >= 70:
        state = "needs-review"
    else:
        state = "at-risk"

    recommendations: list[str] = []
    if env_blocked:
        recommendations.append("Replace the Supabase password placeholder and run the live Prisma check.")
    if active_blockers:
        recommendations.append(f"Resolve {len(active_blockers)} open task blocker(s).")
    if qc.get("stale"):
        age = qc.get("age_days")
        suffix = f" ({age} days old)" if isinstance(age, int) else ""
        recommendations.append(f"Refresh project QC; latest recorded run is stale{suffix}.")
    elif qc_score < 35:
        recommendations.append("Refresh project QC so the score reflects the latest test/lint/build state.")
    if any(not item["present"] for item in docs):
        recommendations.append("Add or repair the missing product documentation files.")
    if dirty_paths:
        recommendations.append("Commit or hand off the current project worktree changes.")
    if not recommendations:
        recommendations.append("Keep the current release path warm with scheduled QC and smoke checks.")

    return {
        "name": profile.name,
        "path": profile.path,
        "score": score,
        "state": state,
        "qc": qc,
        "tasks": active_blockers,
        "dirty_paths": dirty_paths,
        "docs": docs,
        "env": env,
        "recommendations": recommendations[:3],
    }


def build_report(
    repo_root: Path,
    *,
    qaqc_path: Path | None = None,
    git_status_text: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    # qaqc_runner.py writes the canonical (git-tracked) artifact to public/; data/ is a gitignored orphan.
    qaqc_path = qaqc_path or repo_root / "projects" / "knowledge-dashboard" / "public" / "qaqc_result.json"
    now = now or datetime.now(timezone.utc)
    generated_at = now.astimezone().isoformat()
    qaqc_data = _read_json(qaqc_path)
    tasks = _tasks_by_project(repo_root)
    dirty = _dirty_paths_by_project(git_status_text if git_status_text is not None else _run_git_status(repo_root))

    projects = [
        _score_project(
            repo_root=repo_root,
            profile=PROJECTS[name],
            qaqc_data=qaqc_data,
            project_tasks=tasks.get(name, []),
            dirty_paths=dirty.get(name, []),
            now=now,
        )
        for name in ACTIVE_PROJECTS
    ]

    overall_score = _round_score(sum(project["score"] for project in projects) / len(projects))
    blocked_projects = [project for project in projects if project["state"] == "blocked"]
    if blocked_projects:
        overall_state = "blocked"
    elif overall_score >= 85:
        overall_state = "ready"
    elif overall_score >= 70:
        overall_state = "needs-review"
    else:
        overall_state = "at-risk"

    workspace_blockers = [
        task
        for task in tasks.get("workspace", [])
        if task["section"].upper().startswith("TODO") or task["section"].upper().startswith("IN_PROGRESS")
    ]
    next_actions = []
    for project in sorted(projects, key=lambda item: item["score"]):
        next_actions.append(
            {
                "project": project["name"],
                "state": project["state"],
                "score": project["score"],
                "action": project["recommendations"][0],
            }
        )
    for task in workspace_blockers[:2]:
        title_match = re.search(r"\[workspace\]\s*(.+)", task["task"])
        action = title_match.group(1) if title_match else task["task"]
        next_actions.append(
            {
                "project": "workspace",
                "state": "blocked" if task["owner"].lower() == "user" else "needs-review",
                "score": overall_score,
                "action": action.strip("` "),
            }
        )

    return {
        "generated_at": generated_at,
        "overall": {
            "score": overall_score,
            "state": overall_state,
            "project_count": len(projects),
            "blocked_count": len(blocked_projects),
            "workspace_blocker_count": len(workspace_blockers),
        },
        "projects": projects,
        "workspace_blockers": workspace_blockers,
        "next_actions": next_actions[:6],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "projects"
        / "knowledge-dashboard"
        / "data"
        / "product_readiness.json",
    )
    parser.add_argument("--json", action="store_true", help="Print the report JSON to stdout.")
    args = parser.parse_args()

    report = build_report(args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Product readiness written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
