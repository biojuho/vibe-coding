from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
# tests/ excluded from code_improver: fake credentials in test fixtures are expected
STATIC_ANALYSIS_TARGETS = ("execution", "scripts", "joolife_hub.py")
RUFF_TARGETS = ("execution", "scripts", "tests", "joolife_hub.py")


def _python_executable() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def _run_command(step_name: str, command: list[str]) -> bool:
    print(f"[STEP] {step_name}")
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        print(f"[FAIL] {step_name} (exit={result.returncode})")
        return False
    print(f"[PASS] {step_name}")
    return True


def _run_ruff_gate(python_exe: str) -> bool:
    print("[STEP] ruff lint")
    cmd = [python_exe, "-m", "ruff", "check", *RUFF_TARGETS]
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        print(f"[FAIL] ruff lint (exit={result.returncode})")
        return False
    print("[PASS] ruff lint")
    return True


def _run_high_severity_gate(python_exe: str) -> bool:
    print("[STEP] Static analysis: high severity")
    for target in STATIC_ANALYSIS_TARGETS:
        cmd = [
            python_exe,
            "execution/code_improver.py",
            target,
            "--format",
            "json",
            "--severity",
            "high",
        ]
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            print(f"[FAIL] code_improver failed for {target} (exit={result.returncode})")
            return False

        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            print(f"[FAIL] code_improver produced invalid JSON for {target}")
            return False

        summary = payload.get("summary", {})
        issues = int(summary.get("total_issues", 0))
        if issues > 0:
            print(f"[FAIL] High severity issues found in {target}: {issues}")
            return False
        print(f"[PASS] {target}: no high severity issues")
    return True


def main() -> int:
    python_exe = _python_executable()
    if python_exe != str(VENV_PYTHON):
        print(
            f"[WARN] Workspace venv python not found at {VENV_PYTHON}. "
            f"Falling back to current interpreter: {python_exe}"
        )

    if not _run_command("smoke_check", [python_exe, "scripts/smoke_check.py"]):
        return 1

    if not _run_command("pytest -q", [python_exe, "-m", "pytest", "-q"]):
        return 1

    if not _run_ruff_gate(python_exe):
        return 1

    if not _run_high_severity_gate(python_exe):
        return 1

    print("[PASS] Quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
