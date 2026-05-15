"""Run the known local QC commands for active projects.

The workspace keeps project-specific verification commands in each
project's CLAUDE.md. This script makes those commands deterministic and
repeatable from one entry point without changing the commands themselves.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_TAIL_CHARS = 4000

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
                description="unit pytest without coverage defaults",
                command=("python", "-m", "pytest", "--no-cov", "tests/unit", "-q", "--tb=short", "--maxfail=1"),
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
                description="unit and integration pytest without coverage defaults",
                command=(
                    "python",
                    "-m",
                    "pytest",
                    "--no-cov",
                    "tests/unit",
                    "tests/integration",
                    "-q",
                    "--tb=short",
                    "--maxfail=1",
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


def resolve_command(command: tuple[str, ...]) -> tuple[str, ...]:
    executable = command[0]
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
    resolved_command = resolve_command(item.check.command)
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
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human_results(results)
    return exit_code_for_results(results)


if __name__ == "__main__":
    sys.exit(main())
