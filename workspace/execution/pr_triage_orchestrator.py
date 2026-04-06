"""
Run read-only PR-style triage inside an isolated linked git worktree.

This orchestration layer sits on top of `pr_triage_worktree.py`:

- prepare an isolated worktree session
- auto-select a repo-specific validation profile
- run read-only validation commands inside the isolated checkout
- persist a triage report plus per-command logs under the session folder
- optionally clean up the linked worktree while keeping the report artifacts
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

WORKSPACE_DIR = Path(__file__).resolve().parents[1]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from execution.pr_triage_worktree import cleanup_session, prepare_session  # noqa: E402
from path_contract import REPO_ROOT  # noqa: E402

VENV_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

NPM_CMD = shutil.which("npm.cmd") or shutil.which("npm") or "npm"


@dataclass(frozen=True)
class ValidationCommand:
    name: str
    args: tuple[str, ...]
    timeout_sec: int = 600
    required_worktree_paths: tuple[str, ...] = ()
    required_source_paths: tuple[str, ...] = ()
    env_mode: str = "default"


@dataclass(frozen=True)
class ValidationProfile:
    name: str
    description: str
    commands: tuple[ValidationCommand, ...]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _slugify(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "._-" else "-" for char in value.strip())
    return cleaned.strip("-._") or "artifact"


def _load_package_json(repo_root: Path) -> dict[str, Any]:
    package_path = repo_root / "package.json"
    if not package_path.is_file():
        return {}
    return json.loads(package_path.read_text(encoding="utf-8"))


def _python_pytest_command(
    name: str,
    *paths: str,
    timeout_sec: int = 900,
    extra_args: tuple[str, ...] = (),
) -> ValidationCommand:
    return ValidationCommand(
        name=name,
        args=(
            str(VENV_PYTHON),
            "-X",
            "utf8",
            "-m",
            "pytest",
            *paths,
            "-q",
            "--tb=short",
            "--no-header",
            "-o",
            "addopts=",
            "-x",
            *extra_args,
        ),
        timeout_sec=timeout_sec,
        required_worktree_paths=paths,
    )


def _python_ruff_command(*paths: str, timeout_sec: int = 300) -> ValidationCommand:
    return ValidationCommand(
        name="ruff-check",
        args=(str(VENV_PYTHON), "-m", "ruff", "check", *paths),
        timeout_sec=timeout_sec,
    )


def _npm_script_command(
    name: str,
    script: str,
    *,
    timeout_sec: int = 900,
    required_worktree_paths: tuple[str, ...] = ("package.json",),
) -> ValidationCommand:
    return ValidationCommand(
        name=name,
        args=(NPM_CMD, "run", script),
        timeout_sec=timeout_sec,
        required_worktree_paths=required_worktree_paths,
        required_source_paths=("node_modules",),
        env_mode="node",
    )


def _build_blind_to_x_profile(_repo_root: Path) -> ValidationProfile:
    return ValidationProfile(
        name="blind-to-x",
        description="Python pipeline validation for blind-to-x with unit + integration test slices.",
        commands=(
            _python_pytest_command("pytest-unit", "tests/unit"),
            _python_pytest_command(
                "pytest-integration",
                "tests/integration",
                extra_args=("--ignore=tests/integration/test_curl_cffi.py",),
            ),
        ),
    )


def _build_shorts_profile(_repo_root: Path) -> ValidationProfile:
    return ValidationProfile(
        name="shorts-maker-v2",
        description="Python validation for shorts-maker-v2 with focused tests plus Ruff.",
        commands=(
            _python_pytest_command("pytest", "tests/unit", "tests/integration", timeout_sec=1200),
            _python_ruff_command("src", "tests"),
        ),
    )


def _build_hanwoo_profile(_repo_root: Path) -> ValidationProfile:
    return ValidationProfile(
        name="hanwoo-dashboard",
        description="Next.js validation for hanwoo-dashboard using lint + build in the isolated worktree.",
        commands=(
            _npm_script_command("npm-lint", "lint", timeout_sec=600),
            _npm_script_command("npm-build", "build", timeout_sec=1200),
        ),
    )


def _build_knowledge_profile(_repo_root: Path) -> ValidationProfile:
    return ValidationProfile(
        name="knowledge-dashboard",
        description="Next.js validation for knowledge-dashboard using lint + build in the isolated worktree.",
        commands=(
            _npm_script_command("npm-lint", "lint", timeout_sec=600),
            _npm_script_command("npm-build", "build", timeout_sec=1200),
        ),
    )


def _build_word_chain_profile(_repo_root: Path) -> ValidationProfile:
    return ValidationProfile(
        name="word-chain",
        description="Vite/React validation for word-chain using lint, test, and build.",
        commands=(
            _npm_script_command("npm-lint", "lint", timeout_sec=600),
            _npm_script_command("npm-test", "test", timeout_sec=900),
            _npm_script_command("npm-build", "build", timeout_sec=900),
        ),
    )


def _build_suika_profile(_repo_root: Path) -> ValidationProfile:
    return ValidationProfile(
        name="suika-game-v2",
        description="Vite build validation for suika-game-v2.",
        commands=(_npm_script_command("npm-build", "build", timeout_sec=900),),
    )


def _build_python_generic_profile(repo_root: Path) -> ValidationProfile:
    commands: list[ValidationCommand] = []
    if (repo_root / "tests").exists():
        commands.append(_python_pytest_command("pytest", "tests"))
    if any((repo_root / candidate).exists() for candidate in ("pyproject.toml", "ruff.toml", ".ruff.toml")):
        commands.append(_python_ruff_command("."))
    if not commands:
        raise ValueError(f"Could not infer generic Python validation commands for {repo_root}")
    return ValidationProfile(
        name="python-generic",
        description="Generic Python validation using discovered tests/configuration.",
        commands=tuple(commands),
    )


def _build_node_generic_profile(repo_root: Path) -> ValidationProfile:
    package_data = _load_package_json(repo_root)
    scripts = package_data.get("scripts", {})
    commands: list[ValidationCommand] = []
    for script_name in ("lint", "test", "build"):
        if script_name in scripts:
            commands.append(_npm_script_command(f"npm-{script_name}", script_name))
    if not commands:
        raise ValueError(f"Could not infer generic Node validation commands for {repo_root}")
    return ValidationProfile(
        name="node-generic",
        description="Generic Node validation driven by package.json scripts.",
        commands=tuple(commands),
    )


PROFILE_BUILDERS: dict[str, Callable[[Path], ValidationProfile]] = {
    "blind-to-x": _build_blind_to_x_profile,
    "shorts-maker-v2": _build_shorts_profile,
    "hanwoo-dashboard": _build_hanwoo_profile,
    "knowledge-dashboard": _build_knowledge_profile,
    "word-chain": _build_word_chain_profile,
    "suika-game-v2": _build_suika_profile,
    "python-generic": _build_python_generic_profile,
    "node-generic": _build_node_generic_profile,
}


def resolve_profile_name(repo_root: Path, requested_profile: str | None = None) -> str:
    if requested_profile and requested_profile != "auto":
        if requested_profile not in PROFILE_BUILDERS:
            raise ValueError(
                f"Unknown profile: {requested_profile}. Available profiles: {', '.join(sorted(PROFILE_BUILDERS))}"
            )
        return requested_profile

    repo_name = repo_root.name
    if repo_name in PROFILE_BUILDERS:
        return repo_name

    if (repo_root / "package.json").is_file():
        return "node-generic"

    if any((repo_root / candidate).is_file() for candidate in ("pyproject.toml", "pytest.ini", "requirements.txt")):
        return "python-generic"

    raise ValueError(f"Could not auto-detect a validation profile for {repo_root}")


def build_validation_profile(repo_root: Path, requested_profile: str | None = None) -> ValidationProfile:
    profile_name = resolve_profile_name(repo_root, requested_profile)
    return PROFILE_BUILDERS[profile_name](repo_root)


def _node_env(source_repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    node_modules = source_repo / "node_modules"
    bin_dir = node_modules / ".bin"

    path_parts = [str(bin_dir)] if bin_dir.exists() else []
    current_path = env.get("PATH", "")
    if current_path:
        path_parts.append(current_path)
    if path_parts:
        env["PATH"] = os.pathsep.join(path_parts)

    node_path_parts = [str(node_modules)] if node_modules.exists() else []
    current_node_path = env.get("NODE_PATH", "")
    if current_node_path:
        node_path_parts.append(current_node_path)
    if node_path_parts:
        env["NODE_PATH"] = os.pathsep.join(node_path_parts)

    env.setdefault("CI", "1")
    env.setdefault("NEXT_TELEMETRY_DISABLED", "1")
    return env


def _missing_paths(base: Path, rel_paths: tuple[str, ...]) -> list[str]:
    return [rel_path for rel_path in rel_paths if not (base / rel_path).exists()]


def _command_status(returncode: int) -> str:
    return "PASS" if returncode == 0 else "FAIL"


def _log_preview(value: str, limit: int = 4000) -> str:
    if len(value) <= limit:
        return value
    head = value[: limit - 32]
    return head + "\n...[truncated]..."


def run_validation_command(
    command: ValidationCommand,
    *,
    source_repo: Path,
    worktree_path: Path,
    logs_dir: Path,
) -> dict[str, Any]:
    missing_worktree = _missing_paths(worktree_path, command.required_worktree_paths)
    missing_source = _missing_paths(source_repo, command.required_source_paths)
    if missing_worktree or missing_source:
        missing_bits = []
        if missing_worktree:
            missing_bits.append(f"worktree: {', '.join(missing_worktree)}")
        if missing_source:
            missing_bits.append(f"source: {', '.join(missing_source)}")
        return {
            "name": command.name,
            "status": "SKIP",
            "message": "Missing required paths -> " + " | ".join(missing_bits),
            "args": list(command.args),
            "duration_sec": 0.0,
        }

    env = os.environ.copy() if command.env_mode == "default" else _node_env(source_repo)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            list(command.args),
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=command.timeout_sec,
            env=env,
        )
        duration = round(time.perf_counter() - started, 2)
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        log_name = f"{len(list(logs_dir.glob('*.log'))):02d}-{_slugify(command.name)}.log"
        log_path = logs_dir / log_name
        log_path.write_text(
            "\n".join(
                [
                    f"# command: {' '.join(command.args)}",
                    f"# cwd: {worktree_path}",
                    f"# status: {_command_status(completed.returncode)}",
                    f"# returncode: {completed.returncode}",
                    "",
                    "## stdout",
                    stdout_text,
                    "",
                    "## stderr",
                    stderr_text,
                ]
            ),
            encoding="utf-8",
        )
        return {
            "name": command.name,
            "status": _command_status(completed.returncode),
            "message": "",
            "args": list(command.args),
            "returncode": completed.returncode,
            "duration_sec": duration,
            "stdout_preview": _log_preview(stdout_text),
            "stderr_preview": _log_preview(stderr_text),
            "log_path": str(log_path),
        }
    except subprocess.TimeoutExpired as exc:
        duration = round(time.perf_counter() - started, 2)
        return {
            "name": command.name,
            "status": "TIMEOUT",
            "message": f"Timed out after {command.timeout_sec}s",
            "args": list(command.args),
            "duration_sec": duration,
            "stdout_preview": _log_preview(exc.stdout or ""),
            "stderr_preview": _log_preview(exc.stderr or ""),
        }
    except FileNotFoundError as exc:
        duration = round(time.perf_counter() - started, 2)
        return {
            "name": command.name,
            "status": "ERROR",
            "message": str(exc),
            "args": list(command.args),
            "duration_sec": duration,
        }


def summarize_validation_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "passed": sum(1 for result in results if result["status"] == "PASS"),
        "failed": sum(1 for result in results if result["status"] == "FAIL"),
        "timeouts": sum(1 for result in results if result["status"] == "TIMEOUT"),
        "errors": sum(1 for result in results if result["status"] == "ERROR"),
        "skipped": sum(1 for result in results if result["status"] == "SKIP"),
    }

    if counts["errors"] > 0:
        overall = "ERROR"
    elif counts["failed"] > 0:
        overall = "FAIL"
    elif counts["timeouts"] > 0:
        overall = "TIMEOUT"
    elif counts["passed"] == 0:
        overall = "SKIP"
    else:
        overall = "PASS"

    return {"status": overall, "counts": counts}


def run_triage(
    repo_path: Path,
    head_ref: str,
    *,
    base_ref: str | None = None,
    label: str | None = None,
    requested_profile: str | None = None,
    metadata: dict[str, Any] | None = None,
    keep_worktree: bool = False,
) -> dict[str, Any]:
    manifest = prepare_session(
        repo_path,
        head_ref,
        base_ref=base_ref,
        label=label,
        metadata=metadata,
    )
    session_dir = Path(manifest["session_dir"])
    worktree_path = Path(manifest["worktree_path"])
    source_repo = Path(manifest["repo_path"])
    report_path = session_dir / "triage-report.json"
    logs_dir = session_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    cleanup_result: dict[str, Any] | None = None
    try:
        profile = build_validation_profile(source_repo, requested_profile)
        results = [
            run_validation_command(command, source_repo=source_repo, worktree_path=worktree_path, logs_dir=logs_dir)
            for command in profile.commands
        ]
        summary = summarize_validation_results(results)
        report = {
            "created_at": _utc_now(),
            "repo_path": str(source_repo),
            "session_dir": str(session_dir),
            "profile": {
                "name": profile.name,
                "description": profile.description,
                "command_count": len(profile.commands),
            },
            "manifest_path": manifest["artifacts"]["manifest_path"],
            "conflict_state_path": manifest["artifacts"]["conflict_state_path"],
            "manifest": manifest,
            "validation": {
                **summary,
                "results": results,
            },
            "cleanup": None,
            "next_action": (
                "Run pr_triage_worktree.py cleanup later if you kept the linked worktree."
                if keep_worktree
                else "Linked worktree removed; session artifacts kept for review."
            ),
        }
        if not keep_worktree:
            cleanup_result = cleanup_session(session_dir, keep_session_dir=True)
            report["cleanup"] = cleanup_result

        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report
    except Exception:
        if not keep_worktree:
            cleanup_result = cleanup_session(session_dir, keep_session_dir=True)
        raise
    finally:
        if cleanup_result and report_path.exists():
            persisted = json.loads(report_path.read_text(encoding="utf-8"))
            persisted["cleanup"] = cleanup_result
            report_path.write_text(json.dumps(persisted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("--metadata-json must decode to a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated read-only PR triage with repo-specific validation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--repo-path", required=True, help="Local path to the target git repo")
    run_parser.add_argument("--head-ref", required=True, help="Branch, tag, or commit to check out")
    run_parser.add_argument("--base-ref", help="Optional base ref for conflict preflight")
    run_parser.add_argument("--label", help="Optional stable label such as pr-123")
    run_parser.add_argument(
        "--profile",
        default="auto",
        help=f"Validation profile name or 'auto' (default). Choices: {', '.join(sorted(PROFILE_BUILDERS))}",
    )
    run_parser.add_argument("--metadata-json", help="Optional JSON object to persist into the session manifest")
    run_parser.add_argument(
        "--keep-worktree",
        action="store_true",
        help="Keep the linked worktree after validation; otherwise only the JSON/log artifacts remain",
    )

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--session-dir", required=True, help="Session directory created by triage run")
    cleanup_parser.add_argument(
        "--keep-session-dir",
        action="store_true",
        help="Remove the linked worktree but keep the session folder and JSON artifacts",
    )

    subparsers.add_parser("profiles")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            payload = run_triage(
                Path(args.repo_path),
                args.head_ref,
                base_ref=args.base_ref,
                label=args.label,
                requested_profile=args.profile,
                metadata=_load_metadata(args.metadata_json),
                keep_worktree=args.keep_worktree,
            )
        elif args.command == "cleanup":
            payload = cleanup_session(Path(args.session_dir), keep_session_dir=args.keep_session_dir)
        else:
            payload = {"profiles": sorted(PROFILE_BUILDERS)}
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "result": payload}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
