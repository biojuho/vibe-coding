"""Build product-readiness scores for the workspace operations dashboard."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
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
PROJECT_QC_ARTIFACT = Path(".tmp") / "project_qc_runner_latest.json"
LEGACY_QAQC_ARTIFACTS = (
    Path("projects") / "knowledge-dashboard" / "data" / "qaqc_result.json",
    Path("projects") / "knowledge-dashboard" / "public" / "qaqc_result.json",
)
PROJECT_QC_SOURCE = "project_qc_runner"
REQUIRED_GITHUB_WORKFLOWS = ("root-quality-gate", "active-project-matrix")


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
        env_checks=("blind_to_x_launch_env",),
    ),
    "shorts-maker-v2": ProjectProfile(
        name="shorts-maker-v2",
        path="projects/shorts-maker-v2",
        required_files=("README.md", "ARCHITECTURE.md", "CLAUDE.md", "FEATURE.md", "pyproject.toml"),
        env_checks=("shorts_provider_keys",),
    ),
    "hanwoo-dashboard": ProjectProfile(
        name="hanwoo-dashboard",
        path="projects/hanwoo-dashboard",
        required_files=("README.md", "API_SPEC.md", "package.json", ".env.example"),
        env_checks=("supabase_password",),
    ),
    "knowledge-dashboard": ProjectProfile(
        name="knowledge-dashboard",
        path="projects/knowledge-dashboard",
        required_files=("README.md", "package.json", "src/app/page.tsx"),
        env_checks=("dashboard_runtime_auth",),
    ),
}


BLIND_TO_X_NOTION_KEYS = ("NOTION_API_KEY", "NOTION_DATABASE_ID")
BLIND_TO_X_PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "ZHIPUAI_API_KEY",
    "OPENAI_API_KEY",
)
SHORTS_PROVIDER_KEYS = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "ZHIPUAI_API_KEY",
    "MIMO_API_KEY",
)
KNOWLEDGE_DASHBOARD_ENV_FILES = (".env.local", ".env")


def _round_score(value: float) -> int:
    return int(round(max(0, min(100, value))))


def _is_active_task(task: dict[str, str]) -> bool:
    section = task.get("section", "").upper()
    return section.startswith("TODO") or section.startswith("IN_PROGRESS")


def _is_user_owned_task(task: dict[str, str]) -> bool:
    return task.get("owner", "").strip().lower() == "user"


def _check_ids(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _observed_project_qc_checks(result: dict[str, Any]) -> list[str]:
    observed = _check_ids(result.get("observed_checks"))
    if observed:
        return observed

    checks = result.get("checks")
    if isinstance(checks, list):
        return _check_ids([item.get("check") for item in checks if isinstance(item, dict)])

    return _check_ids(result.get("expected_checks"))


@lru_cache(maxsize=1)
def _current_project_qc_expected_checks() -> dict[str, tuple[str, ...]]:
    runner_path = Path(__file__).with_name("project_qc_runner.py")
    spec = importlib.util.spec_from_file_location("_product_readiness_project_qc_runner", runner_path)
    if spec is None or spec.loader is None:
        return {}

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return {}

    projects = getattr(module, "PROJECTS", None)
    if not isinstance(projects, dict):
        return {}

    expected: dict[str, tuple[str, ...]] = {}
    for name, project in projects.items():
        checks = getattr(project, "checks", ())
        expected[str(name)] = tuple(sorted(str(check.id) for check in checks if getattr(check, "id", None)))
    return expected


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _read_default_qc_data(repo_root: Path) -> dict[str, Any]:
    for relative in (PROJECT_QC_ARTIFACT, *LEGACY_QAQC_ARTIFACTS):
        data = _read_json(repo_root / relative)
        if data:
            return data
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


def _run_json_command(repo_root: Path, command: list[str], timeout: int = 15) -> Any:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except Exception:
        return None

    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout or "null")
    except json.JSONDecodeError:
        return None


def _run_text_command(repo_root: Path, command: list[str], timeout: int = 10) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except Exception:
        return ""

    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _unavailable_github_release_status(head_sha: str | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "head_sha": head_sha or None,
        "open_pr_count": None,
        "open_prs": [],
        "required_workflows": [],
        "checks": [
            {
                "name": "GitHub release gate",
                "ok": False,
                "severity": "watch",
                "message": "GitHub PR/Actions status is unavailable; verify open PRs and required workflows before launch.",
            }
        ],
        "blockers": [],
    }


def _github_release_status(repo_root: Path) -> dict[str, Any]:
    if not (repo_root / ".git").exists():
        return _unavailable_github_release_status()

    head_sha = _run_text_command(repo_root, ["git", "rev-parse", "HEAD"])
    open_prs = _run_json_command(
        repo_root,
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,url,headRefName"],
    )
    runs = _run_json_command(
        repo_root,
        [
            "gh",
            "run",
            "list",
            "--branch",
            "main",
            "--limit",
            "30",
            "--json",
            "databaseId,headSha,workflowName,status,conclusion,createdAt,url",
        ],
        timeout=20,
    )

    checks: list[dict[str, Any]] = []
    available = isinstance(open_prs, list) and isinstance(runs, list) and bool(head_sha)
    if not available:
        return _unavailable_github_release_status(head_sha)

    open_pr_items = [
        {
            "number": item.get("number"),
            "title": item.get("title"),
            "url": item.get("url"),
            "headRefName": item.get("headRefName"),
        }
        for item in open_prs
        if isinstance(item, dict)
    ]
    open_pr_count = len(open_pr_items)
    checks.append(
        {
            "name": "Open GitHub pull requests",
            "ok": open_pr_count == 0,
            "severity": "blocker" if open_pr_count else "ok",
            "message": (
                f"{open_pr_count} open GitHub pull request(s) must be triaged before launch."
                if open_pr_count
                else "No open GitHub pull requests."
            ),
        }
    )

    required_workflows: list[dict[str, Any]] = []
    for workflow in REQUIRED_GITHUB_WORKFLOWS:
        matching_run = next(
            (
                run
                for run in runs
                if isinstance(run, dict) and run.get("workflowName") == workflow and run.get("headSha") == head_sha
            ),
            None,
        )
        if matching_run is None:
            required_workflows.append(
                {
                    "name": workflow,
                    "status": "missing",
                    "conclusion": None,
                    "databaseId": None,
                    "url": None,
                }
            )
            continue
        required_workflows.append(
            {
                "name": workflow,
                "status": matching_run.get("status"),
                "conclusion": matching_run.get("conclusion"),
                "databaseId": matching_run.get("databaseId"),
                "url": matching_run.get("url"),
            }
        )

    failing_workflows = [
        item for item in required_workflows if item["status"] != "completed" or item["conclusion"] != "success"
    ]
    checks.append(
        {
            "name": "Required GitHub Actions",
            "ok": not failing_workflows,
            "severity": "blocker" if failing_workflows else "ok",
            "message": (
                "Required GitHub Actions are not green for current HEAD: "
                + ", ".join(item["name"] for item in failing_workflows)
                + "."
                if failing_workflows
                else "Required GitHub Actions are green for current HEAD."
            ),
        }
    )

    blockers = [check for check in checks if check["severity"] == "blocker"]
    return {
        "available": True,
        "head_sha": head_sha,
        "open_pr_count": open_pr_count,
        "open_prs": open_pr_items[:10],
        "required_workflows": required_workflows,
        "checks": checks,
        "blockers": blockers,
    }


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


def _dirty_workspace_paths(status_text: str) -> list[str]:
    dirty_paths: list[str] = []
    for raw_line in status_text.splitlines():
        if len(raw_line) < 4:
            continue
        dirty_paths.append(raw_line[3:].replace("\\", "/"))
    return dirty_paths


def _worktree_release_status(dirty_paths: list[str]) -> dict[str, Any]:
    if not dirty_paths:
        checks = [
            {
                "name": "Workspace worktree",
                "ok": True,
                "severity": "ok",
                "message": "Workspace worktree is clean.",
            }
        ]
    else:
        checks = [
            {
                "name": "Workspace worktree",
                "ok": False,
                "severity": "blocker",
                "message": f"{len(dirty_paths)} uncommitted workspace path(s) must be committed, ignored, or handed off.",
            }
        ]
    blockers = [check for check in checks if check["severity"] == "blocker"]
    return {
        "dirty_count": len(dirty_paths),
        "dirty_paths": dirty_paths[:20],
        "checks": checks,
        "blockers": blockers,
    }


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
        return {
            "available": False,
            "status": "UNKNOWN",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "missing_checks": [],
            **freshness,
        }

    result = projects.get(project_name)
    if not isinstance(result, dict):
        return {
            "available": False,
            "status": "UNKNOWN",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "missing_checks": [],
            **freshness,
        }

    status = str(result.get("status") or "UNKNOWN").upper()
    missing_checks = [str(check) for check in result.get("missing_checks") or []]
    is_project_qc = qaqc_data.get("source") == PROJECT_QC_SOURCE
    if is_project_qc:
        current_expected_checks = _current_project_qc_expected_checks().get(project_name, ())
        if current_expected_checks:
            observed_checks = set(_observed_project_qc_checks(result))
            drift_missing_checks = sorted(set(current_expected_checks) - observed_checks)
            missing_checks = sorted(set(missing_checks) | set(drift_missing_checks))

    if is_project_qc and (result.get("coverage") != "complete" or missing_checks):
        return {
            "available": False,
            "status": "PARTIAL",
            "passed": int(result.get("passed") or 0),
            "failed": int(result.get("failed") or 0) + int(result.get("errors") or 0),
            "skipped": int(result.get("skipped") or 0),
            "missing_checks": missing_checks,
            **freshness,
        }
    return {
        "available": True,
        "status": status,
        "passed": int(result.get("passed") or 0),
        "failed": int(result.get("failed") or 0) + int(result.get("errors") or 0),
        "skipped": int(result.get("skipped") or 0),
        "missing_checks": missing_checks,
        **freshness,
    }


def _required_file_status(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
    statuses = []
    project_root = repo_root / profile.path
    for relative in profile.required_files:
        statuses.append({"path": f"{profile.path}/{relative}", "present": (project_root / relative).exists()})
    return statuses


def _read_env_assignments(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    assignments: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        normalized_value = value.strip()
        if (
            len(normalized_value) >= 2
            and normalized_value[0] == normalized_value[-1]
            and normalized_value[0] in {'"', "'"}
        ):
            normalized_value = normalized_value[1:-1].strip()
        assignments[key.strip()] = normalized_value
    return assignments


def _read_first_project_env(project_root: Path, names: tuple[str, ...]) -> tuple[Path | None, dict[str, str]]:
    for name in names:
        env_path = project_root / name
        if env_path.exists():
            return env_path, _read_env_assignments(env_path)
    return None, {}


def _looks_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True
    return any(
        marker in normalized
        for marker in (
            "your_",
            "placeholder",
            "changeme",
            "change_me",
            "change-me",
            "replace-me",
            "sk-...",
            "aiza...",
            "<",
            ">",
            "__",
        )
    )


def _usable_keys(assignments: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if key in assignments and not _looks_placeholder(assignments[key])]


def _missing_or_placeholder_keys(assignments: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    return [key for key in keys if key not in assignments or _looks_placeholder(assignments[key])]


def _env_status(repo_root: Path, profile: ProjectProfile) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if "blind_to_x_launch_env" in profile.env_checks:
        env_path = repo_root / profile.path / ".env"
        assignments = _read_env_assignments(env_path)

        missing_notion_keys = _missing_or_placeholder_keys(assignments, BLIND_TO_X_NOTION_KEYS)
        if not env_path.exists():
            notion_message = (
                "projects/blind-to-x/.env is missing; configure NOTION_API_KEY and NOTION_DATABASE_ID before launch."
            )
        elif missing_notion_keys:
            notion_message = (
                "Missing usable blind-to-x Notion env key(s) in projects/blind-to-x/.env: "
                + ", ".join(missing_notion_keys)
                + "."
            )
        else:
            notion_message = "Notion review queue keys are configured."
        checks.append(
            {
                "name": "Notion review queue keys",
                "ok": not missing_notion_keys,
                "severity": "blocker" if missing_notion_keys else "ok",
                "message": notion_message,
            }
        )

        present_provider_keys = _usable_keys(assignments, BLIND_TO_X_PROVIDER_KEYS)
        if not env_path.exists():
            provider_message = "projects/blind-to-x/.env is missing; add at least one LLM provider API key."
        elif not present_provider_keys:
            provider_message = "No usable blind-to-x LLM provider API key is configured in projects/blind-to-x/.env."
        else:
            provider_message = f"{len(present_provider_keys)} blind-to-x LLM provider key(s) are configured."
        checks.append(
            {
                "name": "blind-to-x LLM provider keys",
                "ok": bool(present_provider_keys),
                "severity": "blocker" if not present_provider_keys else "ok",
                "message": provider_message,
            }
        )

    if "supabase_password" in profile.env_checks:
        env_path = repo_root / profile.path / ".env"
        assignments = _read_env_assignments(env_path)
        database_line = "DATABASE_URL" in assignments
        database_url = assignments.get("DATABASE_URL", "")
        placeholder = _looks_placeholder(database_url)
        configured = bool(database_url) and not placeholder
        if not env_path.exists():
            message = "projects/hanwoo-dashboard/.env is missing; configure Supabase DATABASE_URL before live checks."
        elif not database_line:
            message = "Supabase DATABASE_URL is missing from projects/hanwoo-dashboard/.env."
        elif not database_url:
            message = "Supabase DATABASE_URL is empty in projects/hanwoo-dashboard/.env."
        elif placeholder:
            message = "Supabase DATABASE_URL still contains a placeholder."
        else:
            message = "DATABASE_URL is present; run the live Prisma check to verify current Supabase credentials."
        checks.append(
            {
                "name": "Supabase DATABASE_URL",
                "ok": configured,
                "severity": "blocker" if not configured else "ok",
                "message": message,
            }
        )
    if "shorts_provider_keys" in profile.env_checks:
        env_path = repo_root / profile.path / ".env"
        assignments = _read_env_assignments(env_path)
        present_keys = _usable_keys(assignments, SHORTS_PROVIDER_KEYS)
        if not env_path.exists():
            message = "projects/shorts-maker-v2/.env is missing; add at least one generation provider API key."
        elif not present_keys:
            message = "No usable Shorts generation provider API key is configured in projects/shorts-maker-v2/.env."
        else:
            message = f"{len(present_keys)} Shorts generation provider key(s) are configured."
        checks.append(
            {
                "name": "Shorts generation provider keys",
                "ok": bool(present_keys),
                "severity": "blocker" if not present_keys else "ok",
                "message": message,
            }
        )
    if "dashboard_runtime_auth" in profile.env_checks:
        project_root = repo_root / profile.path
        env_path, assignments = _read_first_project_env(project_root, KNOWLEDGE_DASHBOARD_ENV_FILES)
        dashboard_key = assignments.get("DASHBOARD_API_KEY", "")
        dashboard_key_configured = bool(dashboard_key) and not _looks_placeholder(dashboard_key)
        if env_path is None:
            dashboard_message = (
                "projects/knowledge-dashboard/.env.local or .env is missing; configure DASHBOARD_API_KEY before launch."
            )
        elif "DASHBOARD_API_KEY" not in assignments:
            dashboard_message = f"DASHBOARD_API_KEY is missing from {env_path.relative_to(repo_root).as_posix()}."
        elif not dashboard_key:
            dashboard_message = f"DASHBOARD_API_KEY is empty in {env_path.relative_to(repo_root).as_posix()}."
        elif _looks_placeholder(dashboard_key):
            dashboard_message = "DASHBOARD_API_KEY still contains a placeholder."
        else:
            dashboard_message = "DASHBOARD_API_KEY is configured for authenticated dashboard routes."
        checks.append(
            {
                "name": "Dashboard API key",
                "ok": dashboard_key_configured,
                "severity": "blocker" if not dashboard_key_configured else "ok",
                "message": dashboard_message,
            }
        )

        session_secret = assignments.get("DASHBOARD_SESSION_SECRET", "")
        dedicated_secret_configured = bool(session_secret) and not _looks_placeholder(session_secret)
        session_message = (
            "Dedicated DASHBOARD_SESSION_SECRET is configured."
            if dedicated_secret_configured
            else "DASHBOARD_SESSION_SECRET is optional; DASHBOARD_API_KEY fallback will sign sessions."
        )
        checks.append(
            {
                "name": "Dashboard session signing secret",
                "ok": True,
                "severity": "ok" if dedicated_secret_configured else "watch",
                "message": session_message,
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

    active_blockers = [task for task in project_tasks if _is_active_task(task)]
    user_task_blockers = [task for task in active_blockers if _is_user_owned_task(task)]
    agent_task_blockers = [task for task in active_blockers if not _is_user_owned_task(task)]
    blocker_score = 25 if not active_blockers else max(0, 25 - 14 * len(active_blockers))
    docs_score = 15 * (sum(1 for item in docs if item["present"]) / max(1, len(docs)))
    worktree_score = 10 if not dirty_paths else max(2, 10 - len(dirty_paths) * 2)
    env_score = env["score"]
    score = _round_score(qc_score + blocker_score + docs_score + worktree_score + env_score)

    env_blockers = [check for check in env.get("checks", []) if check.get("severity") == "blocker"]
    env_blocked = bool(env_blockers)
    if env_blocked or user_task_blockers:
        state = "blocked"
    elif qc.get("stale"):
        state = "needs-review"
    elif score >= 85:
        state = "ready"
    elif score >= 70:
        state = "needs-review"
    else:
        state = "at-risk"

    recommendations: list[str] = []
    if env_blocked:
        env_message = next(
            (
                str(check.get("message"))
                for check in env.get("checks", [])
                if check.get("severity") == "blocker" and check.get("message")
            ),
            "Configure the required project environment variables and rerun live checks.",
        )
        recommendations.append(env_message)
    if active_blockers:
        recommendations.append(f"Resolve {len(active_blockers)} open task blocker(s).")
    if qc.get("stale"):
        age = qc.get("age_days")
        suffix = f" ({age} days old)" if isinstance(age, int) else ""
        recommendations.append(f"Refresh project QC; latest recorded run is stale{suffix}.")
    elif qc_score < 35:
        recommendations.append("Refresh project QC so the score reflects the latest test/lint/build/smoke state.")
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
        "blocker_breakdown": {
            "task_count": len(active_blockers),
            "user_task_count": len(user_task_blockers),
            "agent_task_count": len(agent_task_blockers),
            "environment_count": len(env_blockers),
        },
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
    github_status: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    now = now or datetime.now(timezone.utc)
    generated_at = now.astimezone().isoformat()
    qaqc_data = _read_json(qaqc_path) if qaqc_path is not None else _read_default_qc_data(repo_root)
    tasks = _tasks_by_project(repo_root)
    status_text = git_status_text if git_status_text is not None else _run_git_status(repo_root)
    dirty = _dirty_paths_by_project(status_text)
    worktree_release = _worktree_release_status(_dirty_workspace_paths(status_text))
    github_release = github_status if github_status is not None else _github_release_status(repo_root)

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
    worktree_blockers = list(worktree_release.get("blockers") or [])
    github_blockers = list(github_release.get("blockers") or [])
    workspace_gate_blockers = worktree_blockers + github_blockers
    if blocked_projects or workspace_gate_blockers:
        overall_state = "blocked"
    elif overall_score >= 85:
        overall_state = "ready"
    elif overall_score >= 70:
        overall_state = "needs-review"
    else:
        overall_state = "at-risk"

    workspace_blockers = [task for task in tasks.get("workspace", []) if _is_active_task(task)]
    workspace_user_task_blockers = [task for task in workspace_blockers if _is_user_owned_task(task)]
    workspace_agent_task_blockers = [task for task in workspace_blockers if not _is_user_owned_task(task)]
    project_user_task_count = sum(project["blocker_breakdown"]["user_task_count"] for project in projects)
    project_agent_task_count = sum(project["blocker_breakdown"]["agent_task_count"] for project in projects)
    project_environment_blocker_count = sum(project["blocker_breakdown"]["environment_count"] for project in projects)
    user_blocker_count = project_user_task_count + len(workspace_user_task_blockers)
    agent_task_count = project_agent_task_count + len(workspace_agent_task_blockers)
    workspace_gate_blocker_count = len(workspace_gate_blockers)
    local_blocker_count = project_environment_blocker_count + workspace_gate_blocker_count
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
                "state": "blocked" if _is_user_owned_task(task) else "needs-review",
                "score": overall_score,
                "action": action.strip("` "),
            }
        )
    for blocker in workspace_gate_blockers[:2]:
        next_actions.append(
            {
                "project": "workspace",
                "state": "blocked",
                "score": overall_score,
                "action": str(blocker.get("message") or "Resolve GitHub release gate blocker."),
            }
        )

    return {
        "generated_at": generated_at,
        "overall": {
            "score": overall_score,
            "state": overall_state,
            "project_count": len(projects),
            "blocked_count": len(blocked_projects),
            "workspace_blocker_count": len(workspace_blockers) + len(workspace_gate_blockers),
            "external_blocker_count": user_blocker_count,
            "local_blocker_count": local_blocker_count,
            "agent_task_count": agent_task_count,
            "environment_blocker_count": project_environment_blocker_count,
            "blocker_breakdown": {
                "external": user_blocker_count,
                "local": local_blocker_count,
                "user_owned_tasks": user_blocker_count,
                "agent_owned_tasks": agent_task_count,
                "environment": project_environment_blocker_count,
                "workspace_gate": workspace_gate_blocker_count,
            },
        },
        "projects": projects,
        "workspace_blockers": workspace_blockers,
        "workspace_gates": {
            "worktree": worktree_release,
            "github_release": github_release,
        },
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
