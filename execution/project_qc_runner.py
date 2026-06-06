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
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_TAIL_CHARS = 4000
PROJECT_QC_RUN_ID = f"{os.getpid()}-{time.time_ns()}"
PROJECT_QC_HEARTBEAT_SECONDS = max(0, int(os.environ.get("PROJECT_QC_HEARTBEAT_SECONDS", "10")))
PROJECT_QC_HEARTBEAT_STREAM = os.environ.get("PROJECT_QC_HEARTBEAT_STREAM", "stderr").strip().lower()
PROJECT_QC_TRANSIENT_RETRIES = max(0, int(os.environ.get("PROJECT_QC_TRANSIENT_RETRIES", "2")))
PROJECT_QC_TRANSIENT_RETRY_SECONDS = max(0, int(os.environ.get("PROJECT_QC_TRANSIENT_RETRY_SECONDS", "15")))
DEFAULT_ARTIFACT_PATH = REPO_ROOT / ".tmp" / "project_qc_runner_latest.json"
DEFAULT_PARTIAL_ARTIFACT_PATH = REPO_ROOT / ".tmp" / "project_qc_runner_partial_latest.json"
READINESS_ARTIFACT_SCHEMA_VERSION = 3
NEXT_BUILD_LOCK_TEXT = "Another next build process is already running"

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
                description="unit pytest with coverage disabled and repo-local basetemp",
                command=(
                    "python",
                    "-m",
                    "pytest",
                    "--no-cov",
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
                description="unit and integration pytest with coverage disabled and repo-local basetemp",
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
            CheckCommand(id="smoke", description="Runtime smoke", command=("npm", "run", "smoke")),
        ),
    ),
    "knowledge-dashboard": ProjectChecks(
        path="projects/knowledge-dashboard",
        status="maintenance",
        checks=(
            CheckCommand(id="test", description="Node test suite", command=("npm", "test")),
            CheckCommand(id="lint", description="ESLint", command=("npm", "run", "lint")),
            CheckCommand(id="build", description="Next production build", command=("npm", "run", "build")),
            CheckCommand(id="smoke", description="Runtime smoke", command=("npm", "run", "smoke")),
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


def run_subprocess_capture(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    stdout_thread = threading.Thread(target=_drain_stream, args=(process.stdout, stdout_parts), daemon=True)
    stderr_thread = threading.Thread(target=_drain_stream, args=(process.stderr, stderr_parts), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        returncode = process.wait()
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        raise subprocess.TimeoutExpired(command, timeout, "".join(stdout_parts), "".join(stderr_parts)) from exc

    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    return subprocess.CompletedProcess(command, returncode, "".join(stdout_parts), "".join(stderr_parts))


def _drain_stream(stream, output: list[str]) -> None:
    if stream is None:
        return
    with stream:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            output.append(chunk)


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
    heartbeat_stop = threading.Event()
    heartbeat_thread: threading.Thread | None = None
    attempts = 0
    transient_retry_count = 0
    transient_retry_reason = ""
    if PROJECT_QC_HEARTBEAT_SECONDS:
        heartbeat_thread = threading.Thread(
            target=_emit_subprocess_heartbeat,
            args=(heartbeat_stop, item),
            daemon=True,
        )
        heartbeat_thread.start()
    try:
        env = build_subprocess_env(item)
        while True:
            attempts += 1
            completed = run_subprocess_capture(
                resolved_command,
                cwd=item.cwd,
                env=env,
                timeout=timeout_seconds,
            )
            if not _is_transient_next_build_lock(completed):
                break
            if transient_retry_count >= PROJECT_QC_TRANSIENT_RETRIES:
                break
            transient_retry_count += 1
            transient_retry_reason = "next_build_lock"
            if PROJECT_QC_TRANSIENT_RETRY_SECONDS:
                time.sleep(PROJECT_QC_TRANSIENT_RETRY_SECONDS)
        duration = time.monotonic() - started
        status = "passed" if completed.returncode == 0 else "failed"
        result = {
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
        if attempts > 1:
            result["attempts"] = attempts
            result["transient_retry_count"] = transient_retry_count
            result["transient_retry_reason"] = transient_retry_reason
        return result
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
    finally:
        heartbeat_stop.set()
        if heartbeat_thread:
            heartbeat_thread.join(timeout=1)


def _is_transient_next_build_lock(completed: subprocess.CompletedProcess[str]) -> bool:
    if completed.returncode == 0:
        return False
    output = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    return NEXT_BUILD_LOCK_TEXT in output


def _emit_subprocess_heartbeat(stop: threading.Event, item: PlanItem) -> None:
    stream = sys.stdout if PROJECT_QC_HEARTBEAT_STREAM == "stdout" else sys.stderr
    while not stop.wait(PROJECT_QC_HEARTBEAT_SECONDS):
        print(
            f"[project-qc] {item.project}/{item.check.id} still running",
            file=stream,
            flush=True,
        )


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
    return sum(
        int(match.group(1))
        for match in re.finditer(
            rf"^[^\w\r\n]*{re.escape(word)}\s+(\d+)\s*$",
            output,
            flags=re.ASCII | re.MULTILINE,
        )
    )


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


def _run_git_text(command: tuple[str, ...], repo_root: Path = REPO_ROOT) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _dirty_paths_from_status(status: str) -> list[str]:
    paths: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if path:
            paths.append(path)
    return paths


def _git_metadata(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    if not (repo_root / ".git").exists():
        return {"available": False, "head_sha": None, "branch": None, "dirty_count": None, "dirty_paths": []}

    head_sha = _run_git_text(("git", "rev-parse", "HEAD"), repo_root)
    branch = _run_git_text(("git", "branch", "--show-current"), repo_root)
    dirty_paths = _dirty_paths_from_status(_run_git_text(("git", "status", "--porcelain"), repo_root))
    return {
        "available": bool(head_sha),
        "head_sha": head_sha or None,
        "branch": branch or None,
        "dirty_count": len(dirty_paths),
        "dirty_paths": dirty_paths,
    }


def build_readiness_artifact(
    results: list[dict[str, object]],
    *,
    timestamp: str | None = None,
    git_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
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
        "schema_version": READINESS_ARTIFACT_SCHEMA_VERSION,
        "git": git_metadata if git_metadata is not None else _git_metadata(),
        "status": "passed" if exit_code_for_results(results) == 0 else "failed",
        "projects": projects,
        "total": total,
    }


def artifact_has_full_workspace_coverage(artifact: dict[str, object]) -> bool:
    projects = artifact.get("projects")
    if not isinstance(projects, dict):
        return False
    if set(projects) != set(PROJECTS):
        return False
    return all(isinstance(project, dict) and project.get("coverage") == "complete" for project in projects.values())


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _select_artifact_write_path(path: Path, artifact: dict[str, object]) -> tuple[Path, bool, str]:
    if _same_path(path, DEFAULT_ARTIFACT_PATH) and not artifact_has_full_workspace_coverage(artifact):
        return (
            DEFAULT_PARTIAL_ARTIFACT_PATH,
            False,
            "partial project-QC run did not overwrite canonical full-workspace latest artifact",
        )
    return path, _same_path(path, DEFAULT_ARTIFACT_PATH), ""


def write_readiness_artifact(results: list[dict[str, object]], path: Path) -> tuple[dict[str, object], Path, bool, str]:
    artifact = build_readiness_artifact(results)
    write_path, canonical_latest_written, note = _select_artifact_write_path(path, artifact)
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact, write_path, canonical_latest_written, note


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
        choices=["test", "lint", "build", "smoke"],
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
            artifact, artifact_path, canonical_latest_written, artifact_note = write_readiness_artifact(
                results,
                args.artifact,
            )
            payload["artifact_path"] = str(artifact_path)
            payload["artifact_status"] = artifact["status"]
            payload["artifact_full_workspace_coverage"] = artifact_has_full_workspace_coverage(artifact)
            payload["artifact_canonical_latest_written"] = canonical_latest_written
            if artifact_note:
                payload["artifact_note"] = artifact_note
        except OSError as exc:
            payload["artifact_error"] = str(exc)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human_results(results)
    return exit_code_for_results(results)


if __name__ == "__main__":
    sys.exit(main())
