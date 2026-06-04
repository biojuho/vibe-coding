"""Run the known local QC commands for active projects.

The workspace keeps project-specific verification commands in each
project's CLAUDE.md. This script makes those commands deterministic and
repeatable from one entry point without changing the commands themselves.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_TAIL_CHARS = 4000
PROJECT_QC_RUN_ID = f"{os.getpid()}-{time.time_ns()}"
DEFAULT_ARTIFACT_PATH = REPO_ROOT / ".tmp" / "project_qc_runner_latest.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


@dataclass(frozen=True)
class CheckCommand:
    id: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class ProjectChecks:
    path: str
    status: str
    checks: tuple[CheckCommand, ...]


@dataclass(frozen=True)
class PlanItem:
    project: str
    cwd: Path
    check: CheckCommand


PROJECTS: dict[str, ProjectChecks] = {
    "blind-to-x": ProjectChecks(
        path="projects/blind-to-x",
        status="active",
        checks=(
            CheckCommand(
                id="test",
                description="unit pytest with coverage addopts disabled and repo-local basetemp",
                command=(
                    "python",
                    "-m",
                    "pytest",
                    "tests/unit",
                    "-q",
                    "--tb=short",
                    "--maxfail=1",
                    "-o",
                    "addopts=",
                    "--basetemp",
                    str(REPO_ROOT / ".tmp" / "project-qc-temp" / "blind-to-x" / f"basetemp-{PROJECT_QC_RUN_ID}"),
                ),
            ),
            CheckCommand(
                id="lint",
                description="ruff lint",
                command=("python", "-m", "ruff", "check", "."),
            ),
        ),
    ),
    "shorts-maker-v2": ProjectChecks(
        path="projects/shorts-maker-v2",
        status="active",
        checks=(
            CheckCommand(
                id="test",
                description="unit and integration pytest with coverage addopts disabled and repo-local basetemp",
                command=(
                    "python",
                    "-m",
                    "pytest",
                    "tests/unit",
                    "tests/integration",
                    "-q",
                    "--tb=short",
                    "--maxfail=1",
                    "-o",
                    "addopts=",
                    "--basetemp",
                    str(REPO_ROOT / ".tmp" / "project-qc-temp" / "shorts-maker-v2" / f"basetemp-{PROJECT_QC_RUN_ID}"),
                ),
            ),
            CheckCommand(
                id="lint",
                description="ruff lint",
                command=("python", "-m", "ruff", "check", "."),
            ),
        ),
    ),
    "hanwoo-dashboard": ProjectChecks(
        path="projects/hanwoo-dashboard",
        status="active",
        checks=(
            CheckCommand(id="test", description="Node test suite", command=("npm", "test")),
            CheckCommand(id="lint", description="ESLint", command=("npm", "run", "lint")),
            CheckCommand(id="build", description="Next production build", command=("npm", "run", "build")),
        ),
    ),
    "knowledge-dashboard": ProjectChecks(
        path="projects/knowledge-dashboard",
        status="maintenance",
        checks=(
            CheckCommand(id="test", description="Node test suite", command=("npm", "test")),
            CheckCommand(id="lint", description="ESLint", command=("npm", "run", "lint")),
            CheckCommand(id="build", description="Next production build", command=("npm", "run", "build")),
        ),
    ),
}


def normalize_project_names(values: Iterable[str] | None) -> list[str]:
    requested = [value for value in values or [] if value]
    if not requested or "all" in requested:
        return list(PROJECTS)

    unknown = sorted(set(requested) - set(PROJECTS))
    if unknown:
        raise ValueError(f"Unknown project(s): {', '.join(unknown)}")

    names: list[str] = []
    for name in requested:
        if name not in names:
            names.append(name)
    return names


def build_plan(project_names: Iterable[str], check_ids: Iterable[str] | None = None) -> list[PlanItem]:
    requested_checks = set(check_ids or [])
    plan: list[PlanItem] = []
    for project_name in project_names:
        project = PROJECTS[project_name]
        cwd = REPO_ROOT / project.path
        for check in project.checks:
            if requested_checks and check.id not in requested_checks:
                continue
            plan.append(PlanItem(project=project_name, cwd=cwd, check=check))
    return plan


def command_to_string(command: tuple[str, ...]) -> str:
    return " ".join(command)


def project_python_candidates(cwd: Path) -> tuple[Path, ...]:
    windows_candidates = (
        cwd / ".venv" / "Scripts" / "python.exe",
        cwd / "venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
    )
    posix_candidates = (
        cwd / ".venv" / "bin" / "python",
        cwd / "venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "bin" / "python",
    )
    if sys.platform == "win32":
        return (*windows_candidates, *posix_candidates)
    return (*posix_candidates, *windows_candidates)


def python_has_module(python_path: str, module_name: str) -> bool:
    try:
        completed = subprocess.run(
            (
                python_path,
                "-c",
                (f"import importlib.util, sys; sys.exit(0 if importlib.util.find_spec({module_name!r}) else 1)"),
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def resolve_project_python(cwd: Path | None, required_module: str | None = None) -> str | None:
    if cwd is None:
        return None
    seen: set[Path] = set()
    for candidate in project_python_candidates(cwd):
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file() and (sys.platform == "win32" or os.access(candidate, os.X_OK)):
            if required_module and not python_has_module(str(candidate), required_module):
                continue
            return str(candidate)
    return None


def resolve_command(command: tuple[str, ...], cwd: Path | None = None) -> tuple[str, ...]:
    executable = command[0]
    if executable == "python":
        required_module = command[2] if command[1:2] == ("-m",) and len(command) > 2 else None
        return (resolve_project_python(cwd, required_module) or sys.executable, *command[1:])
    if Path(executable).suffix or "/" in executable or "\\" in executable:
        return command

    resolved = shutil.which(executable)
    if resolved:
        return (resolved, *command[1:])

    if sys.platform == "win32":
        for suffix in (".cmd", ".bat", ".exe"):
            resolved = shutil.which(executable + suffix)
            if resolved:
                return (resolved, *command[1:])

    return command


def _is_pytest_command(command: tuple[str, ...]) -> bool:
    return len(command) >= 3 and command[1:3] == ("-m", "pytest")


def build_subprocess_env(item: PlanItem) -> dict[str, str]:
    env = os.environ.copy()
    if _is_pytest_command(item.check.command):
        temp_dir = REPO_ROOT / ".tmp" / "project-qc-temp" / item.project
        temp_dir.mkdir(parents=True, exist_ok=True)
        env["TMP"] = str(temp_dir)
        env["TEMP"] = str(temp_dir)
        env.setdefault("PYTHONUTF8", "1")
    return env


def tail_text(text: str | None, limit: int = OUTPUT_TAIL_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def serialize_plan(plan: list[PlanItem]) -> list[dict[str, str]]:
    return [
        {
            "project": item.project,
            "check": item.check.id,
            "description": item.check.description,
            "cwd": str(item.cwd),
            "command": command_to_string(item.check.command),
        }
        for item in plan
    ]


def run_item(item: PlanItem, timeout_seconds: int) -> dict[str, object]:
    started = time.monotonic()
    resolved_command = resolve_command(item.check.command, item.cwd)
    try:
        completed = subprocess.run(
            resolved_command,
            cwd=item.cwd,
            env=build_subprocess_env(item),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        duration = time.monotonic() - started
        status = "passed" if completed.returncode == 0 else "failed"
        return {
            "project": item.project,
            "check": item.check.id,
            "status": status,
            "returncode": completed.returncode,
            "duration_seconds": round(duration, 2),
            "command": command_to_string(item.check.command),
            "resolved_command": command_to_string(resolved_command),
            "stdout_tail": tail_text(completed.stdout),
            "stderr_tail": tail_text(completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        return {
            "project": item.project,
            "check": item.check.id,
            "status": "timed_out",
            "returncode": None,
            "duration_seconds": round(duration, 2),
            "command": command_to_string(item.check.command),
            "resolved_command": command_to_string(resolved_command),
            "stdout_tail": tail_text(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr_tail": tail_text(exc.stderr if isinstance(exc.stderr, str) else ""),
        }
    except OSError as exc:
        duration = time.monotonic() - started
        return {
            "project": item.project,
            "check": item.check.id,
            "status": "failed",
            "returncode": None,
            "duration_seconds": round(duration, 2),
            "command": command_to_string(item.check.command),
            "resolved_command": command_to_string(resolved_command),
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def run_plan(plan: list[PlanItem], timeout_seconds: int, stop_on_failure: bool) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for item in plan:
        result = run_item(item, timeout_seconds)
        results.append(result)
        if stop_on_failure and result["status"] != "passed":
            break
    return results


def exit_code_for_results(results: list[dict[str, object]]) -> int:
    return 0 if all(result["status"] == "passed" for result in results) else 1


def _parse_word_count(output: str, word: str) -> int:
    return sum(int(match.group(1)) for match in re.finditer(rf"(\d+)\s+{re.escape(word)}", output))


def _parse_node_test_count(output: str, word: str) -> int:
    return sum(int(match.group(1)) for match in re.finditer(rf"(?m)^[#\s]*{re.escape(word)}\s+(\d+)\s*$", output))


def _result_output(result: dict[str, object]) -> str:
    return f"{result.get('stdout_tail') or ''}\n{result.get('stderr_tail') or ''}"


def _check_counts(result: dict[str, object]) -> dict[str, int]:
    output = _result_output(result)
    passed = _parse_word_count(output, "passed") + _parse_node_test_count(output, "pass")
    failed = _parse_word_count(output, "failed") + _parse_node_test_count(output, "fail")
    skipped = _parse_word_count(output, "skipped") + _parse_node_test_count(output, "skipped")
    errors = _parse_word_count(output, "error")
    if result.get("status") != "passed" and failed == 0 and errors == 0:
        errors = 1
    return {"passed": passed, "failed": failed, "skipped": skipped, "errors": errors}


def _project_status(results: list[dict[str, object]]) -> str:
    statuses = {str(result.get("status") or "") for result in results}
    if "timed_out" in statuses:
        return "TIMEOUT"
    if all(status == "passed" for status in statuses):
        return "PASS"
    return "FAIL"


def _project_check_coverage(project: str, results: list[dict[str, object]]) -> dict[str, object]:
    expected = {check.id for check in PROJECTS[project].checks} if project in PROJECTS else set()
    observed = {str(result.get("check")) for result in results if result.get("check")}
    missing = sorted(expected - observed)
    return {
        "coverage": "complete" if not missing else "partial",
        "expected_checks": sorted(expected),
        "observed_checks": sorted(observed),
        "missing_checks": missing,
    }


def build_readiness_artifact(results: list[dict[str, object]], *, timestamp: str | None = None) -> dict[str, object]:
    timestamp = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    grouped: dict[str, list[dict[str, object]]] = {}
    for result in results:
        grouped.setdefault(str(result.get("project") or "unknown"), []).append(result)

    projects: dict[str, dict[str, object]] = {}
    for project, project_results in grouped.items():
        counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        for result in project_results:
            parsed = _check_counts(result)
            for key in counts:
                counts[key] += parsed[key]
        projects[project] = {
            "status": _project_status(project_results),
            **counts,
            **_project_check_coverage(project, project_results),
            "checks": [
                {
                    "check": result.get("check"),
                    "status": result.get("status"),
                    "returncode": result.get("returncode"),
                    "duration_seconds": result.get("duration_seconds"),
                    "command": result.get("command"),
                    "resolved_command": result.get("resolved_command"),
                }
                for result in project_results
            ],
        }

    total = {
        "passed": sum(int(project["passed"]) for project in projects.values()),
        "failed": sum(int(project["failed"]) for project in projects.values()),
        "errors": sum(int(project["errors"]) for project in projects.values()),
        "skipped": sum(int(project["skipped"]) for project in projects.values()),
        "timeout": [name for name, project in projects.items() if project["status"] == "TIMEOUT"],
    }
    return {
        "timestamp": timestamp,
        "source": "project_qc_runner",
        "status": "passed" if exit_code_for_results(results) == 0 else "failed",
        "projects": projects,
        "total": total,
    }


def write_readiness_artifact(results: list[dict[str, object]], path: Path) -> dict[str, object]:
    artifact = build_readiness_artifact(results)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact


def print_human_plan(plan: list[PlanItem]) -> None:
    if not plan:
        print("No checks selected.")
        return
    print("Project QC plan:")
    for item in plan:
        rel_cwd = item.cwd.relative_to(REPO_ROOT)
        print(f"- {item.project}:{item.check.id} ({rel_cwd})")
        print(f"  {command_to_string(item.check.command)}")


def print_human_results(results: list[dict[str, object]]) -> None:
    if not results:
        print("No checks ran.")
        return
    print("Project QC results:")
    for result in results:
        print(f"- {result['project']}:{result['check']} {result['status']} ({result['duration_seconds']}s)")
        if result["status"] != "passed":
            if result["stdout_tail"]:
                print("  stdout tail:")
                print(str(result["stdout_tail"]).rstrip())
            if result["stderr_tail"]:
                print("  stderr tail:")
                print(str(result["stderr_tail"]).rstrip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic QC commands for active projects.")
    parser.add_argument(
        "--project",
        action="append",
        choices=["all", *PROJECTS.keys()],
        help="Project to check. Repeatable. Defaults to all active/maintenance projects.",
    )
    parser.add_argument(
        "--check",
        action="append",
        choices=["test", "lint", "build"],
        help="Check id to run. Repeatable. Defaults to every check defined for the selected projects.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the planned commands without running them.")
    parser.add_argument("--list", action="store_true", help="List configured projects and checks.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output.")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Per-command timeout in seconds.")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop after the first failed check.")
    parser.add_argument(
        "--artifact",
        type=Path,
        default=DEFAULT_ARTIFACT_PATH,
        help="Write the latest project-QC artifact consumed by product_readiness_score.py.",
    )
    parser.add_argument("--no-artifact", action="store_true", help="Do not write the latest project-QC artifact.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        project_names = normalize_project_names(args.project)
    except ValueError as exc:
        parser.error(str(exc))

    plan = build_plan(project_names, args.check)
    payload: dict[str, object]

    if args.list:
        payload = {
            "status": "configured",
            "projects": {
                name: {
                    "path": project.path,
                    "status": project.status,
                    "checks": [
                        {
                            "id": check.id,
                            "description": check.description,
                            "command": command_to_string(check.command),
                        }
                        for check in project.checks
                    ],
                }
                for name, project in PROJECTS.items()
            },
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for name, project in PROJECTS.items():
                print(f"{name} ({project.status}) - {project.path}")
                for check in project.checks:
                    print(f"  - {check.id}: {command_to_string(check.command)}")
        return 0

    if args.dry_run:
        payload = {"status": "planned", "plan": serialize_plan(plan)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print_human_plan(plan)
        return 0

    results = run_plan(plan, args.timeout_seconds, args.stop_on_failure)
    payload = {"status": "passed" if exit_code_for_results(results) == 0 else "failed", "results": results}
    if not args.no_artifact:
        try:
            artifact = write_readiness_artifact(results, args.artifact)
            payload["artifact_path"] = str(args.artifact)
            payload["artifact_status"] = artifact["status"]
        except OSError as exc:
            payload["artifact_error"] = str(exc)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human_results(results)
    return exit_code_for_results(results)


if __name__ == "__main__":
    sys.exit(main())
