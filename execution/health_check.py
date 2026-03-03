"""
시스템 헬스 체크 - 디버깅 프로세스 Step 0 자동화.
API 연결, 토큰 유효성, 환경 변수, 파일/DB 상태를 일괄 점검.

Usage (CLI):
    python execution/health_check.py                # 전체 점검
    python execution/health_check.py --category api  # API만 점검
    python execution/health_check.py --json          # JSON 출력

Usage (library):
    from execution.health_check import run_all_checks
    results = run_all_checks()
"""

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent

# ── 상태 상수 ──────────────────────────────────────────────
STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"

# ── 필수 디렉토리 ──────────────────────────────────────────
REQUIRED_DIRS = [
    ("execution/", _ROOT / "execution"),
    ("directives/", _ROOT / "directives"),
    (".tmp/", _ROOT / ".tmp"),
]

# ── 필수 파일 ──────────────────────────────────────────────
REQUIRED_FILES = [
    (".env", _ROOT / ".env"),
    ("CLAUDE.md", _ROOT / "CLAUDE.md"),
]

# ── API 엔드포인트 점검 정의 ───────────────────────────────
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
        "url": None,  # 키 존재만 확인 (credit 소모 방지)
    },
    {
        "name": "Google (Gemini)",
        "env_key": "GOOGLE_API_KEY",
        "url": None,
    },
    {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "url": None,
    },
    {
        "name": "Moonshot",
        "env_key": "MOONSHOT_API_KEY",
        "url": None,
    },
    {
        "name": "Zhipu AI",
        "env_key": "ZHIPUAI_API_KEY",
        "url": None,
    },
    {
        "name": "xAI (Grok)",
        "env_key": "XAI_API_KEY",
        "url": None,
    },
    {
        "name": "Cloudinary",
        "env_keys": ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"],
        "url": None,
    },
]

# ── DB 파일 점검 ───────────────────────────────────────────
DB_CHECKS = [
    ("api_usage.db", _ROOT / ".tmp" / "api_usage.db"),
    ("content.db", _ROOT / ".tmp" / "content.db"),
    ("scheduler.db", _ROOT / ".tmp" / "scheduler.db"),
    ("debug_history.db", _ROOT / ".tmp" / "debug_history.db"),
]


# ── 개별 점검 함수들 ──────────────────────────────────────


def _check_result(name: str, category: str, status: str, detail: str = "") -> Dict:
    return {
        "name": name,
        "category": category,
        "status": status,
        "detail": detail,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def check_env_vars() -> List[Dict]:
    """필수 환경 변수 존재 여부 점검."""
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


def check_api_connections() -> List[Dict]:
    """API 엔드포인트 연결 및 인증 점검."""
    results = []
    for api in API_CHECKS:
        name = api["name"]

        # 다중 키 체크 (Cloudinary 등)
        if "env_keys" in api:
            missing = [k for k in api["env_keys"] if not os.getenv(k, "")]
            if missing:
                results.append(_check_result(name, "api", STATUS_WARN, f"missing keys: {', '.join(missing)}"))
            else:
                results.append(_check_result(name, "api", STATUS_OK, "all keys set"))
            continue

        env_key = api.get("env_key", "")
        api_key = os.getenv(env_key, "")

        if not api_key:
            results.append(_check_result(name, "api", STATUS_WARN, f"{env_key} not set"))
            continue

        url = api.get("url")
        if not url:
            results.append(_check_result(name, "api", STATUS_OK, "key present (no ping endpoint)"))
            continue

        # 실제 API ping
        headers = {"Authorization": f"{api.get('auth_header', 'Bearer')} {api_key}"}
        headers.update(api.get("extra_headers", {}))
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                results.append(_check_result(name, "api", STATUS_OK, "connected"))
            elif resp.status_code == 401:
                results.append(_check_result(name, "api", STATUS_FAIL, "401 Unauthorized - token invalid/expired"))
            elif resp.status_code == 403:
                results.append(_check_result(name, "api", STATUS_FAIL, "403 Forbidden - insufficient permissions"))
            elif resp.status_code == 429:
                results.append(_check_result(name, "api", STATUS_WARN, "429 Rate Limited"))
            else:
                results.append(_check_result(name, "api", STATUS_WARN, f"HTTP {resp.status_code}"))
        except requests.ConnectionError:
            results.append(_check_result(name, "api", STATUS_FAIL, "connection failed"))
        except requests.Timeout:
            results.append(_check_result(name, "api", STATUS_FAIL, "timeout (10s)"))
        except Exception as exc:
            results.append(_check_result(name, "api", STATUS_FAIL, str(exc)))

    return results


def check_directories() -> List[Dict]:
    """필수 디렉토리 존재 여부 점검."""
    results = []
    for name, path in REQUIRED_DIRS:
        if path.is_dir():
            results.append(_check_result(name, "filesystem", STATUS_OK, str(path)))
        else:
            results.append(_check_result(name, "filesystem", STATUS_FAIL, f"missing: {path}"))
    return results


def check_files() -> List[Dict]:
    """필수 파일 존재 여부 점검."""
    results = []
    for name, path in REQUIRED_FILES:
        if path.is_file():
            results.append(_check_result(name, "filesystem", STATUS_OK, str(path)))
        else:
            results.append(_check_result(name, "filesystem", STATUS_FAIL, f"missing: {path}"))
    return results


def check_databases() -> List[Dict]:
    """SQLite DB 파일 상태 점검."""
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
    """Python venv 활성화 상태 점검."""
    venv_path = _ROOT / "venv"
    in_venv = hasattr(os.sys, "real_prefix") or (
        hasattr(os.sys, "base_prefix") and os.sys.base_prefix != os.sys.prefix
    )
    if in_venv:
        return [_check_result("venv", "environment", STATUS_OK, f"active (prefix: {os.sys.prefix})")]
    elif venv_path.is_dir():
        return [_check_result("venv", "environment", STATUS_WARN, "exists but not activated")]
    else:
        return [_check_result("venv", "environment", STATUS_FAIL, "venv/ directory not found")]


def check_git() -> List[Dict]:
    """Git 상태 점검."""
    git_dir = _ROOT / ".git"
    if git_dir.is_dir():
        return [_check_result("git", "environment", STATUS_OK, str(git_dir))]
    return [_check_result("git", "environment", STATUS_FAIL, ".git directory not found")]


# ── 메인 실행 ──────────────────────────────────────────────


def run_all_checks(category: Optional[str] = None) -> List[Dict]:
    """모든 헬스 체크 실행. category로 필터링 가능."""
    all_results: List[Dict] = []

    checkers = [
        ("env", check_env_vars),
        ("api", check_api_connections),
        ("filesystem", check_directories),
        ("filesystem", check_files),
        ("database", check_databases),
        ("environment", check_venv),
        ("environment", check_git),
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
    """점검 결과 요약 통계."""
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
    """터미널용 컬러 리포트 출력."""
    ICONS = {STATUS_OK: "✅", STATUS_WARN: "⚠️", STATUS_FAIL: "❌", STATUS_SKIP: "⏭️"}

    current_cat = ""
    for r in results:
        if r["category"] != current_cat:
            current_cat = r["category"]
            print(f"\n{'─' * 50}")
            print(f"  [{current_cat.upper()}]")
            print(f"{'─' * 50}")
        icon = ICONS.get(r["status"], "?")
        detail = f" — {r['detail']}" if r["detail"] else ""
        print(f"  {icon} {r['name']}{detail}")

    summary = get_summary(results)
    print(f"\n{'═' * 50}")
    overall_icon = ICONS.get(summary["overall"], "?")
    c = summary["counts"]
    print(f"  {overall_icon} Overall: {summary['overall'].upper()}")
    print(f"     OK={c[STATUS_OK]}  WARN={c[STATUS_WARN]}  FAIL={c[STATUS_FAIL]}  SKIP={c[STATUS_SKIP]}")
    print(f"{'═' * 50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife System Health Check")
    parser.add_argument(
        "--category",
        choices=["env", "api", "filesystem", "database", "environment"],
        help="점검 카테고리 필터",
    )
    parser.add_argument("--json", action="store_true", help="JSON 형식 출력")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )

    results = run_all_checks(category=args.category)

    if args.json:
        output = {"results": results, "summary": get_summary(results)}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        _print_report(results)
