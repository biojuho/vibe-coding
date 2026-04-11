"""
System health check for targeted diagnostic drill-down.

This is the detailed troubleshooting tool in the shared operator ladder.
Use it after the FAST or STANDARD checks when you need subsystem detail.

Usage (CLI):
    python workspace/execution/health_check.py
    python workspace/execution/health_check.py --category api
    python workspace/execution/health_check.py --json

Usage (library):
    from execution.health_check import run_all_checks
    results = run_all_checks()
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKSPACE_DIR.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

load_dotenv(REPO_ROOT / ".env")

from execution._logging import logger  # noqa: E402
from execution.governance_checks import run_governance_checks  # noqa: E402

_WORKSPACE_ROOT = WORKSPACE_DIR
_ROOT = REPO_ROOT

# Operator ladder role:
# - DIAGNOSTIC drill-down tool
# - Reach for this after FAST/STANDARD checks when you need subsystem detail
# - Not the default daily gate

# Status constants
STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"

# Required directories
REQUIRED_DIRS = [
    ("execution/", _WORKSPACE_ROOT / "execution"),
    ("directives/", _WORKSPACE_ROOT / "directives"),
    (".tmp/", _ROOT / ".tmp"),
]

# Required files
REQUIRED_FILES = [
    (".env", _ROOT / ".env"),
    ("CLAUDE.md", _ROOT / "CLAUDE.md"),
]

# API connectivity checks
API_CHECKS = [
    {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "url": "https://api.openai.com/v1/models",
        "auth_header": "Bearer",
    },
    {
        "name": "Notion",
        "env_key": "NOTION_API_KEY",
        "url": "https://api.notion.com/v1/users/me",
        "auth_header": "Bearer",
        "extra_headers": {"Notion-Version": "2022-06-28"},
    },
    {
        "name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "url": None,  # Presence-only check to avoid consuming credits
    },
    {
        "name": "Google (Gemini)",
        "env_key": "GOOGLE_API_KEY",
        "url": None,
    },
    {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "url": "https://api.deepseek.com/models",
        "auth_header": "Bearer",
    },
    {
        "name": "Moonshot",
        "env_key": "MOONSHOT_API_KEY",
        "url": "https://api.moonshot.cn/v1/models",
        "auth_header": "Bearer",
        "auth_failure_status": STATUS_WARN,
        "auth_failure_detail": "401 Unauthorized - optional fallback provider disabled until key is refreshed",
        "permission_failure_status": STATUS_WARN,
        "permission_failure_detail": "403 Forbidden - optional fallback provider disabled until permissions are fixed",
    },
    {
        "name": "Zhipu AI",
        "env_key": "ZHIPUAI_API_KEY",
        "url": None,  # Presence-only check; no standard /models endpoint
    },
    {
        "name": "xAI (Grok)",
        "env_key": "XAI_API_KEY",
        "url": "https://api.x.ai/v1/models",
        "auth_header": "Bearer",
    },
    {
        "name": "Groq",
        "env_key": "GROQ_API_KEY",
        "url": "https://api.groq.com/openai/v1/models",
        "auth_header": "Bearer",
    },
    {
        "name": "Cloudinary",
        "env_keys": ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"],
        "url": None,
    },
]

# Database checks — 모든 워크스페이스 도메인은 workspace.db 단일 파일로 통합 (2026-04-04)
DB_CHECKS = [
    ("workspace.db", _ROOT / ".tmp" / "workspace.db"),
]


# Individual check helpers
def _check_result(name: str, category: str, status: str, detail: str = "") -> Dict:
    return {
        "name": name,
        "category": category,
        "status": status,
        "detail": detail,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def check_env_vars() -> List[Dict]:
    """Check whether required environment variables are present."""
    results = []
    all_keys = set()
    for api in API_CHECKS:
        keys = api.get("env_keys", [api["env_key"]] if "env_key" in api else [])
        all_keys.update(keys)

    for key in sorted(all_keys):
        val = os.getenv(key, "")
        if val:
            results.append(_check_result(key, "env", STATUS_OK, f"set ({len(val)} chars)"))
        else:
            results.append(_check_result(key, "env", STATUS_WARN, "not set"))
    return results


def _check_single_api(api: Dict) -> Dict:
    """Check one API target; intended for parallel execution."""
    name = api["name"]

    if "env_keys" in api:
        missing = [k for k in api["env_keys"] if not os.getenv(k, "")]
        if missing:
            return _check_result(name, "api", STATUS_WARN, f"missing keys: {', '.join(missing)}")
        return _check_result(name, "api", STATUS_OK, "all keys set")

    env_key = api.get("env_key", "")
    api_key = os.getenv(env_key, "")
    if not api_key:
        return _check_result(name, "api", STATUS_WARN, f"{env_key} not set")

    url = api.get("url")
    if not url:
        return _check_result(name, "api", STATUS_OK, "key present (no ping endpoint)")

    headers = {"Authorization": f"{api.get('auth_header', 'Bearer')} {api_key}"}
    headers.update(api.get("extra_headers", {}))
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return _check_result(name, "api", STATUS_OK, "connected")
        elif resp.status_code == 401:
            return _check_result(
                name,
                "api",
                api.get("auth_failure_status", STATUS_FAIL),
                api.get("auth_failure_detail", "401 Unauthorized - token invalid/expired"),
            )
        elif resp.status_code == 403:
            return _check_result(
                name,
                "api",
                api.get("permission_failure_status", STATUS_FAIL),
                api.get("permission_failure_detail", "403 Forbidden - insufficient permissions"),
            )
        elif resp.status_code == 429:
            return _check_result(name, "api", STATUS_WARN, "429 Rate Limited")
        else:
            return _check_result(name, "api", STATUS_WARN, f"HTTP {resp.status_code}")
    except requests.ConnectionError:
        return _check_result(name, "api", STATUS_FAIL, "connection failed")
    except requests.Timeout:
        return _check_result(name, "api", STATUS_FAIL, "timeout (10s)")
    except Exception as exc:
        return _check_result(name, "api", STATUS_FAIL, str(exc))


def check_api_connections() -> List[Dict]:
    """Check API connectivity and auth with parallel requests where possible."""
    # Preserve the original display order by writing results back by index.
    futures_map: Dict = {}
    results: List[Dict] = [None] * len(API_CHECKS)  # type: ignore[list-item]

    with ThreadPoolExecutor(max_workers=min(len(API_CHECKS), 8)) as executor:
        for idx, api in enumerate(API_CHECKS):
            future = executor.submit(_check_single_api, api)
            futures_map[future] = idx

        for future in as_completed(futures_map):
            idx = futures_map[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                results[idx] = _check_result(API_CHECKS[idx]["name"], "api", STATUS_FAIL, f"unexpected error: {exc}")

    return results


def check_directories() -> List[Dict]:
    """Check whether required directories exist."""
    results = []
    for name, path in REQUIRED_DIRS:
        if path.is_dir():
            results.append(_check_result(name, "filesystem", STATUS_OK, str(path)))
        else:
            results.append(_check_result(name, "filesystem", STATUS_FAIL, f"missing: {path}"))
    return results


def check_files() -> List[Dict]:
    """Check whether required files exist."""
    results = []
    for name, path in REQUIRED_FILES:
        if path.is_file():
            results.append(_check_result(name, "filesystem", STATUS_OK, str(path)))
        else:
            results.append(_check_result(name, "filesystem", STATUS_FAIL, f"missing: {path}"))
    return results


def check_databases() -> List[Dict]:
    """Check SQLite database file availability and integrity."""
    results = []
    for name, path in DB_CHECKS:
        if not path.exists():
            results.append(_check_result(name, "database", STATUS_SKIP, "not created yet"))
            continue
        try:
            conn = sqlite3.connect(str(path))
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            results.append(_check_result(name, "database", STATUS_OK, f"tables: {', '.join(tables)}"))
        except Exception as exc:
            results.append(_check_result(name, "database", STATUS_FAIL, str(exc)))
    return results


def check_venv() -> List[Dict]:
    """Check Python virtual environment availability and activation state."""
    venv_path = _ROOT / "venv"
    in_venv = hasattr(os.sys, "real_prefix") or (hasattr(os.sys, "base_prefix") and os.sys.base_prefix != os.sys.prefix)
    if in_venv:
        return [_check_result("venv", "environment", STATUS_OK, f"active (prefix: {os.sys.prefix})")]
    elif venv_path.is_dir():
        return [_check_result("venv", "environment", STATUS_WARN, "exists but not activated")]
    else:
        return [_check_result("venv", "environment", STATUS_FAIL, "venv/ directory not found")]


def check_git() -> List[Dict]:
    """Check that the repo looks like a Git working tree."""
    git_dir = _ROOT / ".git"
    if git_dir.is_dir():
        return [_check_result("git", "environment", STATUS_OK, str(git_dir))]
    return [_check_result("git", "environment", STATUS_FAIL, ".git directory not found")]


# API key format patterns (prefix -> regex)
_KEY_FORMAT_PATTERNS: Dict[str, Tuple[str, re.Pattern[str]]] = {
    "OPENAI_API_KEY": ("sk-...", re.compile(r"^sk-.{20,}")),
    "ANTHROPIC_API_KEY": ("sk-ant-...", re.compile(r"^sk-ant-.{20,}")),
    "XAI_API_KEY": ("xai-...", re.compile(r"^xai-.{10,}")),
    "DEEPSEEK_API_KEY": ("sk-...", re.compile(r"^sk-.{20,}")),
    "MOONSHOT_API_KEY": ("sk-...", re.compile(r"^sk-.{20,}")),
    "GOOGLE_API_KEY": ("AIza...", re.compile(r"^AIza.{30,}")),
    "GEMINI_API_KEY": ("AIza...", re.compile(r"^AIza.{30,}")),
    "NOTION_API_KEY": ("ntn_...", re.compile(r"^(ntn_|secret_).{20,}")),
    "YOUTUBE_API_KEY": ("AIza...", re.compile(r"^AIza.{30,}")),
    "GROQ_API_KEY": ("gsk_...", re.compile(r"^gsk_.{20,}")),
}

# Lightweight validation endpoints (GET only, no credit consumption)
_KEY_VALIDATION_ENDPOINTS: Dict[str, Dict] = {
    "OPENAI_API_KEY": {
        "url": "https://api.openai.com/v1/models",
        "auth_header": "Bearer",
    },
    "DEEPSEEK_API_KEY": {
        "url": "https://api.deepseek.com/models",
        "auth_header": "Bearer",
    },
    "MOONSHOT_API_KEY": {
        "url": "https://api.moonshot.cn/v1/models",
        "auth_header": "Bearer",
        "auth_failure_status": STATUS_WARN,
        "auth_failure_detail": "invalid or expired (401) - optional fallback provider disabled",
        "permission_failure_status": STATUS_WARN,
        "permission_failure_detail": "forbidden (403) - optional fallback provider disabled",
    },
    "XAI_API_KEY": {
        "url": "https://api.x.ai/v1/models",
        "auth_header": "Bearer",
    },
    "GROQ_API_KEY": {
        "url": "https://api.groq.com/openai/v1/models",
        "auth_header": "Bearer",
    },
    "NOTION_API_KEY": {
        "url": "https://api.notion.com/v1/users/me",
        "auth_header": "Bearer",
        "extra_headers": {"Notion-Version": "2022-06-28"},
    },
}


def check_api_key_health() -> List[Dict]:
    """Check API key presence, format, and lightweight validity.

    For each known API key environment variable:
    - Check if the key is set (non-empty)
    - Validate key format (prefix pattern)
    - If a lightweight validation endpoint exists, ping it to verify auth
    Returns a list of check results in the standard format.
    """
    results: List[Dict] = []

    # Collect all known API key env vars from API_CHECKS + format patterns
    all_key_names: List[str] = []
    for api in API_CHECKS:
        if "env_key" in api:
            all_key_names.append(api["env_key"])
        if "env_keys" in api:
            all_key_names.extend(api["env_keys"])
    # Add keys from format patterns not already covered
    for k in _KEY_FORMAT_PATTERNS:
        if k not in all_key_names:
            all_key_names.append(k)

    # Deduplicate while preserving order
    seen: set = set()
    unique_keys: List[str] = []
    for k in all_key_names:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    for env_key in unique_keys:
        value = os.getenv(env_key, "")
        check_name = f"key:{env_key}"

        # 1) Not set
        if not value:
            results.append(_check_result(check_name, "api", STATUS_WARN, "key not set"))
            continue

        # 2) Format validation
        if env_key in _KEY_FORMAT_PATTERNS:
            expected_prefix, pattern = _KEY_FORMAT_PATTERNS[env_key]
            if not pattern.match(value):
                results.append(
                    _check_result(check_name, "api", STATUS_WARN, f"unexpected format (expected {expected_prefix})")
                )
                continue

        # 3) Lightweight endpoint validation (if available)
        if env_key in _KEY_VALIDATION_ENDPOINTS:
            ep = _KEY_VALIDATION_ENDPOINTS[env_key]
            headers = {"Authorization": f"{ep.get('auth_header', 'Bearer')} {value}"}
            headers.update(ep.get("extra_headers", {}))
            try:
                resp = requests.get(ep["url"], headers=headers, timeout=8)
                if resp.status_code == 200:
                    results.append(_check_result(check_name, "api", STATUS_OK, "valid (auth ok)"))
                elif resp.status_code == 401:
                    results.append(
                        _check_result(
                            check_name,
                            "api",
                            ep.get("auth_failure_status", STATUS_FAIL),
                            ep.get("auth_failure_detail", "invalid or expired (401)"),
                        )
                    )
                elif resp.status_code == 403:
                    results.append(
                        _check_result(
                            check_name,
                            "api",
                            ep.get("permission_failure_status", STATUS_FAIL),
                            ep.get("permission_failure_detail", "forbidden (403) - check permissions"),
                        )
                    )
                elif resp.status_code == 429:
                    results.append(
                        _check_result(check_name, "api", STATUS_WARN, "rate limited (429) - key likely valid")
                    )
                else:
                    results.append(_check_result(check_name, "api", STATUS_WARN, f"HTTP {resp.status_code}"))
            except requests.ConnectionError:
                results.append(_check_result(check_name, "api", STATUS_FAIL, "connection failed"))
            except requests.Timeout:
                results.append(_check_result(check_name, "api", STATUS_WARN, "timeout (8s) - key format ok"))
            except Exception as exc:
                results.append(_check_result(check_name, "api", STATUS_FAIL, str(exc)))
        else:
            # No validation endpoint: format-only check passed
            results.append(_check_result(check_name, "api", STATUS_OK, "key set, format ok (no ping endpoint)"))

    return results


def check_env_completeness() -> List[Dict]:
    """Compare .env against .env.example and report missing/extra keys.

    Parses both files for KEY=value lines, ignoring comments and blank lines.
    Returns check results indicating missing keys (in example but not in .env)
    and extra keys (in .env but not in example).
    """
    env_path = _ROOT / ".env"
    example_path = _ROOT / ".env.example"

    if not example_path.is_file():
        return [_check_result("env_completeness", "env", STATUS_SKIP, ".env.example not found")]
    if not env_path.is_file():
        return [_check_result("env_completeness", "env", STATUS_FAIL, ".env file not found")]

    def _parse_keys(filepath: Path) -> set:
        keys: set = set()
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if key:
                        keys.add(key)
        return keys

    env_keys = _parse_keys(env_path)
    example_keys = _parse_keys(example_path)

    missing = sorted(example_keys - env_keys)
    extra = sorted(env_keys - example_keys)

    results: List[Dict] = []

    if missing:
        results.append(
            _check_result(
                "env_completeness:missing",
                "env",
                STATUS_WARN,
                f"keys in .env.example but not in .env: {', '.join(missing)}",
            )
        )
    if extra:
        results.append(
            _check_result(
                "env_completeness:extra", "env", STATUS_OK, f"extra keys in .env (not in example): {', '.join(extra)}"
            )
        )
    if not missing and not extra:
        results.append(
            _check_result("env_completeness", "env", STATUS_OK, f".env matches .env.example ({len(env_keys)} keys)")
        )

    return results


# Main execution helpers
def run_all_checks(category: Optional[str] = None) -> List[Dict]:
    """Run all health checks, optionally filtered to one category."""
    all_results: List[Dict] = []

    checkers = [
        ("env", check_env_vars),
        ("env", check_env_completeness),
        ("api", check_api_connections),
        ("api", check_api_key_health),
        ("filesystem", check_directories),
        ("filesystem", check_files),
        ("database", check_databases),
        ("environment", check_venv),
        ("environment", check_git),
        ("governance", run_governance_checks),
    ]

    for cat, checker in checkers:
        if category and cat != category:
            continue
        try:
            all_results.extend(checker())
        except Exception as exc:
            logger.error("checker %s failed: %s", cat, exc)
            all_results.append(_check_result(f"{cat}_checker", cat, STATUS_FAIL, str(exc)))

    return all_results


def get_summary(results: List[Dict]) -> Dict:
    """Summarize the result set into counts and an overall status."""
    counts = {STATUS_OK: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_SKIP: 0}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    if counts[STATUS_FAIL] > 0:
        overall = STATUS_FAIL
    elif counts[STATUS_WARN] > 0:
        overall = STATUS_WARN
    else:
        overall = STATUS_OK

    return {"overall": overall, "counts": counts, "total": len(results)}


def _print_report(results: List[Dict]) -> None:
    """Print a terminal-friendly diagnostic report."""
    ICONS = {STATUS_OK: "[OK]", STATUS_WARN: "[WARN]", STATUS_FAIL: "[FAIL]", STATUS_SKIP: "[SKIP]"}

    print("=" * 50)
    print("Health Check - DIAGNOSTIC Drill-Down")
    print("Role: targeted troubleshooting, not the default fast/standard/deep gate")
    print("=" * 50)

    current_cat = ""
    for r in results:
        if r["category"] != current_cat:
            current_cat = r["category"]
            print(f"\n{'=' * 50}")
            print(f"  [{current_cat.upper()}]")
            print(f"{'=' * 50}")
        icon = ICONS.get(r["status"], "?")
        detail = f" :: {r['detail']}" if r["detail"] else ""
        print(f"  {icon} {r['name']}{detail}")

    summary = get_summary(results)
    print(f"\n{'=' * 50}")
    overall_icon = ICONS.get(summary["overall"], "?")
    c = summary["counts"]
    print(f"  {overall_icon} Overall: {summary['overall'].upper()}")
    print(f"     OK={c[STATUS_OK]}  WARN={c[STATUS_WARN]}  FAIL={c[STATUS_FAIL]}  SKIP={c[STATUS_SKIP]}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Joolife System Health Check (diagnostic drill-down)",
        epilog=(
            "Operator ladder: doctor.py = FAST readiness, "
            "quality_gate.py = STANDARD local gate, "
            "qaqc_runner.py = DEEP shared approval, "
            "health_check.py = DIAGNOSTIC drill-down."
        ),
    )
    parser.add_argument(
        "--category",
        choices=["env", "api", "filesystem", "database", "environment", "governance"],
        help="Filter to one health-check category",
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args()

    results = run_all_checks(category=args.category)

    if args.json:
        output = {"results": results, "summary": get_summary(results)}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        _print_report(results)
