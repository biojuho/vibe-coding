"""
Fast readiness check for the shared workspace operator ladder.

Use this first after Python, package, venv, or env-var changes.
Escalate to `python workspace/execution/health_check.py --category ...` for
diagnostics and `python workspace/scripts/quality_gate.py` for the standard
local pre-commit gate.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from path_contract import REPO_ROOT


@dataclass
class CheckResult:
    status: str  # PASS | WARN | FAIL
    name: str
    detail: str
    remedy: str = ""


VENV_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"
ROOT_ENV = REPO_ROOT / ".env"
WORKSPACE_ENV = WORKSPACE / ".env"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _read_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _check_interpreter(results: List[CheckResult]) -> None:
    current_exe = Path(sys.executable).resolve()
    if current_exe == VENV_PYTHON.resolve():
        results.append(CheckResult("PASS", "Interpreter", f"Using venv python: {current_exe}"))
    elif VENV_PYTHON.exists():
        results.append(
            CheckResult(
                "WARN",
                "Interpreter",
                f"Current python is not workspace venv: {current_exe}",
                remedy=r".\venv\Scripts\python.exe scripts\doctor.py",
            )
        )
    else:
        results.append(
            CheckResult(
                "FAIL",
                "Interpreter",
                f"Workspace venv python not found at {VENV_PYTHON}",
                remedy="py -3 -m venv venv",
            )
        )


def _check_virtualenv(results: List[CheckResult]) -> None:
    in_venv = (sys.prefix != sys.base_prefix) or bool(os.environ.get("VIRTUAL_ENV"))
    if in_venv:
        results.append(CheckResult("PASS", "Virtualenv", "Virtual environment is active."))
    else:
        results.append(
            CheckResult(
                "WARN",
                "Virtualenv",
                "Virtual environment does not look active.",
                remedy=r"call venv\Scripts\activate",
            )
        )


def _check_required_packages(results: List[CheckResult]) -> None:
    required = [
        ("streamlit", "streamlit"),
        ("croniter", "croniter"),
        ("gTTS", "gtts"),
    ]
    for label, module in required:
        if _module_exists(module):
            results.append(CheckResult("PASS", f"Package:{label}", f"Module '{module}' is importable."))
        else:
            results.append(
                CheckResult(
                    "FAIL",
                    f"Package:{label}",
                    f"Module '{module}' is missing.",
                    remedy=rf"{VENV_PYTHON} -m pip install {label}",
                )
            )


def _check_duckduckgo_package(results: List[CheckResult]) -> None:
    if _module_exists("ddgs") or _module_exists("duckduckgo_search"):
        details = "ddgs found" if _module_exists("ddgs") else "duckduckgo_search found"
        results.append(CheckResult("PASS", "Package:DuckDuckGo", details))
    else:
        results.append(
            CheckResult(
                "WARN",
                "Package:DuckDuckGo",
                "Neither ddgs nor duckduckgo_search is installed.",
                remedy=rf"{VENV_PYTHON} -m pip install ddgs",
            )
        )


def _check_google_genai_package(results: List[CheckResult]) -> None:
    google_legacy = _module_exists("google.generativeai")
    google_new = _module_exists("google.genai")
    if google_legacy or google_new:
        if google_new and google_legacy:
            detail = "google.genai and google.generativeai found"
        elif google_new:
            detail = "google.genai found"
        else:
            detail = "google.generativeai found (legacy)"
        results.append(CheckResult("PASS", "Package:Google GenAI", detail))
    else:
        results.append(
            CheckResult(
                "FAIL",
                "Package:Google GenAI",
                "Neither google.generativeai nor google.genai is installed.",
                remedy=rf"{VENV_PYTHON} -m pip install google-genai",
            )
        )


def _check_env_files(results: List[CheckResult]) -> Dict[str, str]:
    root_env = _read_env_file(ROOT_ENV)
    workspace_env = _read_env_file(WORKSPACE_ENV)
    merged_env = {**root_env, **workspace_env}

    if ROOT_ENV.exists() or WORKSPACE_ENV.exists():
        results.append(
            CheckResult(
                "PASS",
                ".env Files",
                f"Detected env files: root={ROOT_ENV.exists()}, workspace={WORKSPACE_ENV.exists()}",
            )
        )
    else:
        results.append(
            CheckResult(
                "FAIL",
                ".env Files",
                "No .env file found in repo root or workspace.",
                remedy="Copy template and set API keys before running app.",
            )
        )
    return merged_env


def _check_llm_keys(results: List[CheckResult], merged_env: Dict[str, str]) -> None:
    provider = (merged_env.get("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai").lower()
    openai_key = merged_env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    google_key = merged_env.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if provider == "openai" and not openai_key:
        results.append(
            CheckResult(
                "WARN",
                "LLM Key",
                "LLM_PROVIDER=openai but OPENAI_API_KEY is missing.",
                remedy="Set OPENAI_API_KEY in .env or switch LLM_PROVIDER=google.",
            )
        )
    elif provider == "google" and not google_key:
        results.append(
            CheckResult(
                "WARN",
                "LLM Key",
                "LLM_PROVIDER=google but GOOGLE_API_KEY is missing.",
                remedy="Set GOOGLE_API_KEY in .env or switch LLM_PROVIDER=openai.",
            )
        )
    elif not (openai_key or google_key):
        results.append(
            CheckResult(
                "WARN",
                "LLM Key",
                "No LLM API key found (OPENAI_API_KEY / GOOGLE_API_KEY).",
                remedy="Add at least one LLM API key in .env.",
            )
        )
    else:
        results.append(CheckResult("PASS", "LLM Key", "At least one LLM API key is configured."))


def run_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    _check_interpreter(results)
    _check_virtualenv(results)
    _check_required_packages(results)
    _check_duckduckgo_package(results)
    _check_google_genai_package(results)
    merged_env = _check_env_files(results)
    _check_llm_keys(results, merged_env)
    return results


def print_report(results: List[CheckResult]) -> int:
    print("=" * 72)
    print("Joolife Doctor - FAST Readiness Check")
    print("=" * 72)
    print("Role: quick operator readiness after env/python/package changes")
    print("Escalate: health_check.py for diagnostics, quality_gate.py for local validation")
    print("-" * 72)
    for item in results:
        print(f"[{item.status}] {item.name}: {item.detail}")
        if item.remedy:
            print(f"    Remedy: {item.remedy}")
    print("-" * 72)

    fails = [x for x in results if x.status == "FAIL"]
    warns = [x for x in results if x.status == "WARN"]
    print(f"Summary: PASS={len(results) - len(fails) - len(warns)} WARN={len(warns)} FAIL={len(fails)}")
    print(f"Python: {sys.executable}")
    print(f"Workspace: {WORKSPACE}")
    if not fails:
        print("Next: run `python workspace/scripts/quality_gate.py` before local handoff or commit.")
    print("=" * 72)
    return 1 if fails else 0


def main() -> int:
    return print_report(run_checks())


if __name__ == "__main__":
    raise SystemExit(main())
