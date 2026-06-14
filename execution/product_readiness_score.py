"""Build product-readiness scores for the workspace operations dashboard."""

from __future__ import annotations

import argparse
import copy
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
PROJECT_QC_PARTIAL_ARTIFACT = Path(".tmp") / "project_qc_runner_partial_latest.json"
LEGACY_QAQC_ARTIFACTS = (
    Path("projects") / "knowledge-dashboard" / "data" / "qaqc_result.json",
    Path("projects") / "knowledge-dashboard" / "public" / "qaqc_result.json",
)
PROJECT_QC_SOURCE = "project_qc_runner"
PROJECT_QC_PROJECT_SOURCES_KEY = "_project_qc_sources"
REQUIRED_GITHUB_WORKFLOWS = ("root-quality-gate", "active-project-matrix")
PROJECT_QC_ARTIFACT_CONTRACT_MISMATCH = "artifact_schema_version"
PROJECT_QC_ARTIFACT_HEAD_STALE = "artifact_head"
PROJECT_QC_GLOBAL_STALE_PATHS = ("execution/project_qc_runner.py",)


class _WriteFailure(Exception):
    def __init__(self, path: Path, cause: OSError) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.path = path
        self.cause = cause


def _write_report_json(path: Path, report: dict[str, Any]) -> None:
    tmp = path.with_name(f"{path.name}.refresh-tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError as exc:
        try:
            if tmp.is_file() or tmp.is_symlink():
                tmp.unlink()
        except OSError:
            pass
        raise _WriteFailure(path, exc) from exc


def _write_failed_report(report: dict[str, Any], exc: _WriteFailure) -> dict[str, Any]:
    failed = dict(report)
    failed["status"] = "write_failed"
    failed["write_error"] = str(exc)
    failed["write_error_path"] = exc.path.as_posix()
    return failed


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


def _task_ids(tasks: list[dict[str, str]]) -> str:
    ids = [task.get("id", "").strip() for task in tasks if task.get("id", "").strip()]
    return ", ".join(ids) if ids else "unlisted task(s)"


def _task_blocker_recommendation(
    *,
    active_blockers: list[dict[str, str]],
    user_task_blockers: list[dict[str, str]],
    agent_task_blockers: list[dict[str, str]],
) -> str | None:
    if not active_blockers:
        return None
    if user_task_blockers and not agent_task_blockers:
        return (
            f"Wait for {len(user_task_blockers)} user-owned task blocker(s) before rerunning local launch checks: "
            f"{_task_ids(user_task_blockers)}."
        )
    if agent_task_blockers and user_task_blockers:
        return (
            f"Resolve {len(agent_task_blockers)} agent-owned task blocker(s), then wait for "
            f"{len(user_task_blockers)} user-owned task blocker(s): {_task_ids(user_task_blockers)}."
        )
    return f"Resolve {len(active_blockers)} open task blocker(s)."


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
def _current_project_qc_contract() -> dict[str, Any]:
    runner_path = Path(__file__).with_name("project_qc_runner.py")
    spec = importlib.util.spec_from_file_location("_product_readiness_project_qc_runner", runner_path)
    if spec is None or spec.loader is None:
        return {"expected_checks": {}, "schema_version": None}

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        return {"expected_checks": {}, "schema_version": None}

    projects = getattr(module, "PROJECTS", None)
    if not isinstance(projects, dict):
        return {"expected_checks": {}, "schema_version": None}

    expected: dict[str, tuple[str, ...]] = {}
    for name, project in projects.items():
        checks = getattr(project, "checks", ())
        expected[str(name)] = tuple(sorted(str(check.id) for check in checks if getattr(check, "id", None)))

    schema_version = getattr(module, "READINESS_ARTIFACT_SCHEMA_VERSION", None)
    return {"expected_checks": expected, "schema_version": schema_version}


def _current_project_qc_expected_checks() -> dict[str, tuple[str, ...]]:
    expected = _current_project_qc_contract().get("expected_checks")
    return expected if isinstance(expected, dict) else {}


def _current_project_qc_artifact_schema_version() -> Any:
    return _current_project_qc_contract().get("schema_version")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _project_qc_artifact_for_project(qaqc_data: dict[str, Any], project_name: str) -> dict[str, Any]:
    sources = qaqc_data.get(PROJECT_QC_PROJECT_SOURCES_KEY)
    if isinstance(sources, dict):
        source = sources.get(project_name)
        if isinstance(source, dict):
            return source
    return qaqc_data


def _project_qc_result_is_complete(result: Any) -> bool:
    return isinstance(result, dict) and result.get("coverage") == "complete"


def _project_qc_source_copy(artifact: dict[str, Any]) -> dict[str, Any]:
    source = copy.deepcopy(artifact)
    source.pop(PROJECT_QC_PROJECT_SOURCES_KEY, None)
    return source


def _artifact_timestamp_is_at_least(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_timestamp = _parse_timestamp(candidate.get("timestamp"))
    current_timestamp = _parse_timestamp(current.get("timestamp"))
    if current_timestamp is None:
        return candidate_timestamp is not None
    if candidate_timestamp is None:
        return False
    return candidate_timestamp >= current_timestamp


def _merge_project_qc_artifacts(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Merge newer complete per-project QC into the canonical workspace artifact."""
    if not candidate or candidate.get("source") != PROJECT_QC_SOURCE:
        return base
    candidate_projects = candidate.get("projects")
    if not isinstance(candidate_projects, dict):
        return base

    if not base:
        return copy.deepcopy(candidate)

    base_projects = base.get("projects")
    if not isinstance(base_projects, dict):
        return base

    merged = copy.deepcopy(base)
    merged_projects = merged.setdefault("projects", {})
    if not isinstance(merged_projects, dict):
        return base

    sources: dict[str, Any] = {
        name: _project_qc_source_copy(base)
        for name, result in base_projects.items()
        if isinstance(name, str) and isinstance(result, dict)
    }
    existing_sources = base.get(PROJECT_QC_PROJECT_SOURCES_KEY)
    if isinstance(existing_sources, dict):
        for name, source in existing_sources.items():
            if isinstance(name, str) and isinstance(source, dict):
                sources[name] = _project_qc_source_copy(source)

    for project_name, candidate_result in candidate_projects.items():
        if not isinstance(project_name, str) or not isinstance(candidate_result, dict):
            continue
        candidate_source = _project_qc_artifact_for_project(candidate, project_name)
        current_source = sources.get(project_name, base)
        current_result = merged_projects.get(project_name)
        if not isinstance(current_result, dict) or (
            _project_qc_result_is_complete(candidate_result)
            and _artifact_timestamp_is_at_least(candidate_source, current_source)
        ):
            merged_projects[project_name] = copy.deepcopy(candidate_result)
            sources[project_name] = _project_qc_source_copy(candidate_source)

    if sources:
        merged[PROJECT_QC_PROJECT_SOURCES_KEY] = sources
    return merged


def _read_default_qc_data(repo_root: Path) -> dict[str, Any]:
    project_qc_data = _read_json(repo_root / PROJECT_QC_ARTIFACT)
    partial_project_qc_data = _read_json(repo_root / PROJECT_QC_PARTIAL_ARTIFACT)
    merged_project_qc_data = _merge_project_qc_artifacts(project_qc_data, partial_project_qc_data)
    if merged_project_qc_data:
        return merged_project_qc_data

    for relative in LEGACY_QAQC_ARTIFACTS:
        data = _read_json(repo_root / relative)
        if data:
            return data
    return {}


def _run_command(
    repo_root: Path,
    command: list[str],
    *,
    default: Any = "",
    timeout: int = 10,
    parse_json: bool = False,
) -> Any:
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
        return default

    if completed.returncode != 0:
        return default
    stdout = completed.stdout
    if parse_json:
        try:
            return json.loads(stdout or "null")
        except json.JSONDecodeError:
            return None
    return stdout.strip()


def _normalize_git_path(path: str) -> str:
    return path.replace("\\", "/").strip().strip('"')


def _project_qc_artifact_head(qaqc_data: dict[str, Any]) -> str | None:
    git = qaqc_data.get("git")
    if not isinstance(git, dict):
        return None
    head = git.get("head_sha")
    return str(head).strip() if isinstance(head, str) and head.strip() else None


def _changed_paths_between(repo_root: Path, base_sha: str, head_sha: str) -> dict[str, Any]:
    if base_sha == head_sha:
        return {"available": True, "paths": []}
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except Exception as exc:
        return {"available": False, "paths": [], "error": str(exc)}
    if completed.returncode != 0:
        return {"available": False, "paths": [], "error": completed.stderr.strip()}
    return {
        "available": True,
        "paths": [_normalize_git_path(line) for line in completed.stdout.splitlines() if line.strip()],
    }


def _project_qc_head_freshness(
    *,
    repo_root: Path,
    qaqc_data: dict[str, Any],
    current_head_sha: str | None,
) -> dict[str, Any]:
    if qaqc_data.get("source") != PROJECT_QC_SOURCE:
        return {}

    artifact_head = _project_qc_artifact_head(qaqc_data)
    current_head = current_head_sha or _run_command(repo_root, ["git", "rev-parse", "HEAD"])
    result: dict[str, Any] = {
        "artifact_head_sha": artifact_head,
        "current_head_sha": current_head or None,
        "head_stale": False,
        "changed_paths_available": False,
        "changed_paths_since_qc": [],
    }
    if not artifact_head or not current_head:
        return result

    changed = _changed_paths_between(repo_root, artifact_head, current_head)
    result["changed_paths_available"] = bool(changed.get("available"))
    result["changed_paths_since_qc"] = list(changed.get("paths") or [])
    if changed.get("error"):
        result["changed_paths_error"] = str(changed.get("error"))
    return result


def _relevant_project_qc_changes(project_name: str, head_freshness: dict[str, Any]) -> list[str]:
    paths = [_normalize_git_path(str(path)) for path in head_freshness.get("changed_paths_since_qc") or []]
    profile = PROJECTS.get(project_name)
    project_prefix = f"{profile.path}/" if profile else ""
    relevant: list[str] = []
    for path in paths:
        if project_prefix and (path == project_prefix.rstrip("/") or path.startswith(project_prefix)):
            relevant.append(path)
        elif path in PROJECT_QC_GLOBAL_STALE_PATHS:
            relevant.append(path)
    return relevant


def _unavailable_github_release_status(head_sha: str | None = None) -> dict[str, Any]:
    return {
        "available": False,
        "head_sha": head_sha or None,
        "branch_status": "",
        "ahead_count": 0,
        "publish_required": False,
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


def _git_ahead_count(branch_status: str) -> int:
    match = re.search(r"\bahead\s+(\d+)", branch_status)
    if not match:
        return 0
    return int(match.group(1))


def _github_release_status(repo_root: Path) -> dict[str, Any]:
    if not (repo_root / ".git").exists():
        return _unavailable_github_release_status()

    head_sha = _run_command(repo_root, ["git", "rev-parse", "HEAD"])
    branch_status = _run_command(repo_root, ["git", "status", "--short", "--branch"])
    ahead_count = _git_ahead_count(branch_status)
    open_prs = _run_command(
        repo_root,
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,url,headRefName"],
        parse_json=True,
        default=None,
    )
    runs = _run_command(
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
        parse_json=True,
        default=None,
    )

    checks: list[dict[str, Any]] = []
    available = isinstance(open_prs, list) and isinstance(runs, list) and bool(head_sha)
    if not available:
        status = _unavailable_github_release_status(head_sha)
        status["branch_status"] = branch_status
        status["ahead_count"] = ahead_count
        status["publish_required"] = ahead_count > 0
        return status

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
    publish_required = (
        bool(failing_workflows) and ahead_count > 0 and all(item["status"] == "missing" for item in failing_workflows)
    )
    if publish_required and failing_workflows:
        workflow_message = (
            "Required GitHub Actions are unavailable for current local HEAD because main is ahead of origin by "
            f"{ahead_count} commit(s): "
            + ", ".join(item["name"] for item in failing_workflows)
            + ". Push only with explicit authorization, then wait for Actions."
        )
    else:
        workflow_message = (
            "Required GitHub Actions are not green for current HEAD: "
            + ", ".join(item["name"] for item in failing_workflows)
            + "."
            if failing_workflows
            else "Required GitHub Actions are green for current HEAD."
        )
    checks.append(
        {
            "name": "Required GitHub Actions",
            "ok": not failing_workflows,
            "severity": "blocker" if failing_workflows else "ok",
            "message": workflow_message,
            "blocker_type": "publish" if publish_required else "local",
            "ahead_count": ahead_count,
            "requires_publish": publish_required,
        }
    )

    blockers = [check for check in checks if check["severity"] == "blocker"]
    return {
        "available": True,
        "head_sha": head_sha,
        "branch_status": branch_status,
        "ahead_count": ahead_count,
        "publish_required": publish_required,
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


def _project_qc_freshness(
    qaqc_data: dict[str, Any],
    project_name: str,
    now: datetime,
    head_freshness: dict[str, Any] | None,
) -> dict[str, Any]:
    time_freshness = _qc_freshness(qaqc_data, now)
    head_freshness = head_freshness or {}
    relevant_changes = _relevant_project_qc_changes(project_name, head_freshness)
    head_stale = bool(relevant_changes)
    stale_reasons = []
    if time_freshness.get("stale"):
        stale_reasons.append("age")
    if head_stale:
        stale_reasons.append(PROJECT_QC_ARTIFACT_HEAD_STALE)

    freshness = {
        **time_freshness,
        "stale": bool(time_freshness.get("stale")) or head_stale,
        "stale_reasons": stale_reasons,
    }
    if not head_freshness:
        return freshness

    freshness.update(
        {
            "artifact_head_sha": head_freshness.get("artifact_head_sha"),
            "current_head_sha": head_freshness.get("current_head_sha"),
            "head_stale": head_stale,
            "changed_paths_available": head_freshness.get("changed_paths_available", False),
            "relevant_changes_since_qc": relevant_changes[:20],
        }
    )
    if head_freshness.get("changed_paths_error"):
        freshness["changed_paths_error"] = head_freshness.get("changed_paths_error")
    return freshness


def _project_qc_empty_status(freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": False,
        "status": "UNKNOWN",
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "missing_checks": [],
        "contract_mismatches": [],
        **freshness,
    }


def _project_qc_contract_state(
    qaqc_data: dict[str, Any],
    project_name: str,
    result: dict[str, Any],
    missing_checks: list[str],
) -> tuple[list[str], list[str]]:
    contract_mismatches: list[str] = []
    if qaqc_data.get("source") != PROJECT_QC_SOURCE:
        return missing_checks, contract_mismatches

    current_schema_version = _current_project_qc_artifact_schema_version()
    if current_schema_version is not None and qaqc_data.get("schema_version") != current_schema_version:
        contract_mismatches.append(PROJECT_QC_ARTIFACT_CONTRACT_MISMATCH)

    current_expected_checks = _current_project_qc_expected_checks().get(project_name, ())
    if current_expected_checks:
        observed_checks = set(_observed_project_qc_checks(result))
        drift_missing_checks = sorted(set(current_expected_checks) - observed_checks)
        missing_checks = sorted(set(missing_checks) | set(drift_missing_checks))
    return missing_checks, contract_mismatches


def _project_qc_counts(result: dict[str, Any]) -> dict[str, int]:
    return {
        "passed": int(result.get("passed") or 0),
        "failed": int(result.get("failed") or 0) + int(result.get("errors") or 0),
        "skipped": int(result.get("skipped") or 0),
    }


def _project_qc_status(
    qaqc_data: dict[str, Any],
    project_name: str,
    now: datetime,
    *,
    head_freshness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_data = _project_qc_artifact_for_project(qaqc_data, project_name)
    freshness = _project_qc_freshness(source_data, project_name, now, head_freshness)
    projects = qaqc_data.get("projects")
    if not isinstance(projects, dict):
        return _project_qc_empty_status(freshness)

    result = projects.get(project_name)
    if not isinstance(result, dict):
        return _project_qc_empty_status(freshness)

    status = str(result.get("status") or "UNKNOWN").upper()
    missing_checks = [str(check) for check in result.get("missing_checks") or []]
    is_project_qc = source_data.get("source") == PROJECT_QC_SOURCE
    missing_checks, contract_mismatches = _project_qc_contract_state(
        source_data,
        project_name,
        result,
        missing_checks,
    )
    counts = _project_qc_counts(result)

    if is_project_qc and (result.get("coverage") != "complete" or missing_checks or contract_mismatches):
        return {
            "available": False,
            "status": "PARTIAL",
            **counts,
            "missing_checks": missing_checks,
            "contract_mismatches": contract_mismatches,
            **freshness,
        }
    return {
        "available": True,
        "status": status,
        **counts,
        "missing_checks": missing_checks,
        "contract_mismatches": contract_mismatches,
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


def _env_check(name: str, ok: bool, message: str, *, severity: str | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "severity": severity or ("ok" if ok else "blocker"),
        "message": message,
    }


def _blind_to_x_launch_env_checks(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
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

    present_provider_keys = _usable_keys(assignments, BLIND_TO_X_PROVIDER_KEYS)
    if not env_path.exists():
        provider_message = "projects/blind-to-x/.env is missing; add at least one LLM provider API key."
    elif not present_provider_keys:
        provider_message = "No usable blind-to-x LLM provider API key is configured in projects/blind-to-x/.env."
    else:
        provider_message = f"{len(present_provider_keys)} blind-to-x LLM provider key(s) are configured."

    return [
        _env_check("Notion review queue keys", not missing_notion_keys, notion_message),
        _env_check("blind-to-x LLM provider keys", bool(present_provider_keys), provider_message),
    ]


def _supabase_password_env_checks(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
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
    return [_env_check("Supabase DATABASE_URL", configured, message)]


def _supabase_database_url_check(repo_root: Path, profile: ProjectProfile) -> dict[str, Any]:
    return _supabase_password_env_checks(repo_root, profile)[0]


def _shorts_provider_env_checks(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
    env_path = repo_root / profile.path / ".env"
    assignments = _read_env_assignments(env_path)
    present_keys = _usable_keys(assignments, SHORTS_PROVIDER_KEYS)
    if not env_path.exists():
        message = "projects/shorts-maker-v2/.env is missing; add at least one generation provider API key."
    elif not present_keys:
        message = "No usable Shorts generation provider API key is configured in projects/shorts-maker-v2/.env."
    else:
        message = f"{len(present_keys)} Shorts generation provider key(s) are configured."
    return [_env_check("Shorts generation provider keys", bool(present_keys), message)]


def _shorts_provider_key_check(repo_root: Path, profile: ProjectProfile) -> dict[str, Any]:
    return _shorts_provider_env_checks(repo_root, profile)[0]


def _dashboard_runtime_auth_env_checks(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
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

    session_secret = assignments.get("DASHBOARD_SESSION_SECRET", "")
    dedicated_secret_configured = bool(session_secret) and not _looks_placeholder(session_secret)
    session_message = (
        "Dedicated DASHBOARD_SESSION_SECRET is configured."
        if dedicated_secret_configured
        else "DASHBOARD_SESSION_SECRET is optional; DASHBOARD_API_KEY fallback will sign sessions."
    )

    return [
        _env_check("Dashboard API key", dashboard_key_configured, dashboard_message),
        _env_check(
            "Dashboard session signing secret",
            True,
            session_message,
            severity="ok" if dedicated_secret_configured else "watch",
        ),
    ]


def _dashboard_runtime_auth_checks(repo_root: Path, profile: ProjectProfile) -> list[dict[str, Any]]:
    return _dashboard_runtime_auth_env_checks(repo_root, profile)


def _env_status_result(checks: list[dict[str, Any]]) -> dict[str, Any]:
    if not checks:
        return {"available": False, "score": 10, "checks": []}

    blocker_count = sum(1 for check in checks if check["severity"] == "blocker")
    score = 0 if blocker_count else 15
    return {"available": True, "score": score, "checks": checks}


def _env_status(repo_root: Path, profile: ProjectProfile) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if "blind_to_x_launch_env" in profile.env_checks:
        checks.extend(_blind_to_x_launch_env_checks(repo_root, profile))
    if "supabase_password" in profile.env_checks:
        checks.extend(_supabase_password_env_checks(repo_root, profile))
    if "shorts_provider_keys" in profile.env_checks:
        checks.extend(_shorts_provider_env_checks(repo_root, profile))
    if "dashboard_runtime_auth" in profile.env_checks:
        checks.extend(_dashboard_runtime_auth_env_checks(repo_root, profile))
    return _env_status_result(checks)


def _project_qc_score(qc: dict[str, Any]) -> int:
    qc_score = 12
    if qc["available"] and qc["status"] == "PASS" and qc["failed"] == 0:
        qc_score = 35
    elif qc["available"] and qc["failed"] == 0:
        qc_score = 25
    elif qc["available"]:
        qc_score = 0
    if qc.get("stale"):
        qc_score = min(qc_score, 20)
    return qc_score


def _project_task_blockers(
    project_tasks: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    active_blockers = [task for task in project_tasks if _is_active_task(task)]
    user_task_blockers = [task for task in active_blockers if _is_user_owned_task(task)]
    agent_task_blockers = [task for task in active_blockers if not _is_user_owned_task(task)]
    return active_blockers, user_task_blockers, agent_task_blockers


def _project_blocker_score(active_blockers: list[dict[str, str]]) -> int:
    return 25 if not active_blockers else max(0, 25 - 14 * len(active_blockers))


def _project_docs_score(docs: list[dict[str, Any]]) -> float:
    return 15 * (sum(1 for item in docs if item["present"]) / max(1, len(docs)))


def _project_worktree_score(dirty_paths: list[str]) -> int:
    return 10 if not dirty_paths else max(2, 10 - len(dirty_paths) * 2)


def _project_score_value(
    *,
    qc_score: int,
    active_blockers: list[dict[str, str]],
    docs: list[dict[str, Any]],
    dirty_paths: list[str],
    env: dict[str, Any],
) -> int:
    return _round_score(
        qc_score
        + _project_blocker_score(active_blockers)
        + _project_docs_score(docs)
        + _project_worktree_score(dirty_paths)
        + env["score"]
    )


def _project_state(
    *,
    env_blocked: bool,
    user_task_blockers: list[dict[str, str]],
    qc: dict[str, Any],
    score: int,
) -> str:
    if env_blocked or user_task_blockers:
        return "blocked"
    if qc.get("stale"):
        return "needs-review"
    if score >= 85:
        return "ready"
    if score >= 70:
        return "needs-review"
    return "at-risk"


def _env_blocker_recommendation(env_blockers: list[dict[str, Any]]) -> str | None:
    if not env_blockers:
        return None
    return next(
        (str(check.get("message")) for check in env_blockers if check.get("message")),
        "Configure the required project environment variables and rerun live checks.",
    )


def _qc_recommendation(qc: dict[str, Any], qc_score: int) -> str | None:
    if qc.get("stale"):
        if qc.get("head_stale"):
            return "Refresh project QC; latest recorded run predates current project changes."
        age = qc.get("age_days")
        suffix = f" ({age} days old)" if isinstance(age, int) else ""
        return f"Refresh project QC; latest recorded run is stale{suffix}."
    if qc_score < 35:
        return "Refresh project QC so the score reflects the latest test/lint/build/smoke state."
    return None


def _project_recommendations(
    *,
    env_blockers: list[dict[str, Any]],
    active_blockers: list[dict[str, str]],
    user_task_blockers: list[dict[str, str]],
    agent_task_blockers: list[dict[str, str]],
    qc: dict[str, Any],
    qc_score: int,
    docs: list[dict[str, Any]],
    dirty_paths: list[str],
) -> list[str]:
    recommendations = [
        recommendation
        for recommendation in (
            _env_blocker_recommendation(env_blockers),
            _task_blocker_recommendation(
                active_blockers=active_blockers,
                user_task_blockers=user_task_blockers,
                agent_task_blockers=agent_task_blockers,
            ),
            _qc_recommendation(qc, qc_score),
        )
        if recommendation
    ]
    if any(not item["present"] for item in docs):
        recommendations.append("Add or repair the missing product documentation files.")
    if dirty_paths:
        recommendations.append("Commit or hand off the current project worktree changes.")
    if not recommendations:
        recommendations.append("Keep the current release path warm with scheduled QC and smoke checks.")
    return recommendations[:3]


def _project_env_blockers(env: dict[str, Any]) -> list[dict[str, Any]]:
    return [check for check in env.get("checks", []) if check.get("severity") == "blocker"]


def _project_blocker_breakdown(
    *,
    active_blockers: list[dict[str, str]],
    user_task_blockers: list[dict[str, str]],
    agent_task_blockers: list[dict[str, str]],
    env_blockers: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "task_count": len(active_blockers),
        "user_task_count": len(user_task_blockers),
        "agent_task_count": len(agent_task_blockers),
        "environment_count": len(env_blockers),
    }


def _project_result(
    *,
    profile: ProjectProfile,
    score: int,
    qc: dict[str, Any],
    active_blockers: list[dict[str, str]],
    user_task_blockers: list[dict[str, str]],
    agent_task_blockers: list[dict[str, str]],
    env_blockers: list[dict[str, Any]],
    dirty_paths: list[str],
    docs: list[dict[str, Any]],
    env: dict[str, Any],
    recommendations: list[str],
) -> dict[str, Any]:
    return {
        "name": profile.name,
        "path": profile.path,
        "score": score,
        "state": _project_state(
            env_blocked=bool(env_blockers),
            user_task_blockers=user_task_blockers,
            qc=qc,
            score=score,
        ),
        "qc": qc,
        "tasks": active_blockers,
        "blocker_breakdown": _project_blocker_breakdown(
            active_blockers=active_blockers,
            user_task_blockers=user_task_blockers,
            agent_task_blockers=agent_task_blockers,
            env_blockers=env_blockers,
        ),
        "dirty_paths": dirty_paths,
        "docs": docs,
        "env": env,
        "recommendations": recommendations,
    }


def _score_project(
    *,
    repo_root: Path,
    profile: ProjectProfile,
    qaqc_data: dict[str, Any],
    project_tasks: list[dict[str, str]],
    dirty_paths: list[str],
    now: datetime,
    qc_head_freshness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qc = _project_qc_status(qaqc_data, profile.name, now, head_freshness=qc_head_freshness)
    docs = _required_file_status(repo_root, profile)
    env = _env_status(repo_root, profile)

    qc_score = _project_qc_score(qc)
    active_blockers, user_task_blockers, agent_task_blockers = _project_task_blockers(project_tasks)
    score = _project_score_value(
        qc_score=qc_score,
        active_blockers=active_blockers,
        docs=docs,
        dirty_paths=dirty_paths,
        env=env,
    )
    env_blockers = _project_env_blockers(env)
    recommendations = _project_recommendations(
        env_blockers=env_blockers,
        active_blockers=active_blockers,
        user_task_blockers=user_task_blockers,
        agent_task_blockers=agent_task_blockers,
        qc=qc,
        qc_score=qc_score,
        docs=docs,
        dirty_paths=dirty_paths,
    )

    return _project_result(
        profile=profile,
        score=score,
        qc=qc,
        active_blockers=active_blockers,
        user_task_blockers=user_task_blockers,
        agent_task_blockers=agent_task_blockers,
        env_blockers=env_blockers,
        dirty_paths=dirty_paths,
        docs=docs,
        env=env,
        recommendations=recommendations,
    )


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
    status_text = (
        git_status_text if git_status_text is not None else _run_command(repo_root, ["git", "status", "--porcelain"])
    )
    dirty = _dirty_paths_by_project(status_text)
    worktree_release = _worktree_release_status(_dirty_workspace_paths(status_text))
    github_release = github_status if github_status is not None else _github_release_status(repo_root)
    current_head_sha = github_release.get("head_sha") if isinstance(github_release.get("head_sha"), str) else None
    qc_head_freshness_by_project = {
        name: _project_qc_head_freshness(
            repo_root=repo_root,
            qaqc_data=_project_qc_artifact_for_project(qaqc_data, name),
            current_head_sha=current_head_sha,
        )
        for name in ACTIVE_PROJECTS
    }

    projects = [
        _score_project(
            repo_root=repo_root,
            profile=PROJECTS[name],
            qaqc_data=qaqc_data,
            project_tasks=tasks.get(name, []),
            dirty_paths=dirty.get(name, []),
            now=now,
            qc_head_freshness=qc_head_freshness_by_project.get(name),
        )
        for name in ACTIVE_PROJECTS
    ]

    overall_score = _round_score(sum(project["score"] for project in projects) / len(projects))
    blocked_projects = [project for project in projects if project["state"] == "blocked"]
    worktree_blockers = list(worktree_release.get("blockers") or [])
    github_blockers = list(github_release.get("blockers") or [])
    workspace_gate_blockers = worktree_blockers + github_blockers
    publish_gate_blockers = [blocker for blocker in github_blockers if blocker.get("blocker_type") == "publish"]
    local_gate_blockers = worktree_blockers + [
        blocker for blocker in github_blockers if blocker.get("blocker_type") != "publish"
    ]
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
    publish_blocker_count = len(publish_gate_blockers)
    local_blocker_count = project_environment_blocker_count + len(local_gate_blockers)
    next_actions = []
    for blocker in publish_gate_blockers[:2]:
        next_actions.append(
            {
                "project": "workspace",
                "state": "blocked",
                "score": overall_score,
                "action": str(blocker.get("message") or "Resolve GitHub release publish blocker."),
            }
        )
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
    for blocker in local_gate_blockers[:2]:
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
            "publish_blocker_count": publish_blocker_count,
            "agent_task_count": agent_task_count,
            "environment_blocker_count": project_environment_blocker_count,
            "blocker_breakdown": {
                "external": user_blocker_count,
                "local": local_blocker_count,
                "publish": publish_blocker_count,
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


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    report = build_report(args.repo_root)
    try:
        _write_report_json(args.output, report)
    except _WriteFailure as exc:
        failed = _write_failed_report(report, exc)
        if args.json:
            print(json.dumps(failed, ensure_ascii=False, indent=2))
        else:
            print(f"Product readiness write_failed: {exc.path} ({exc})")
        return 4
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Product readiness written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
