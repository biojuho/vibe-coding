"""
System health check script for the n8n bridge.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def default_btx_dir(repo_root: Path = ROOT_DIR) -> Path:
    return repo_root / "projects" / "blind-to-x"


def env_candidates(btx_dir: Path | None = None, repo_root: Path = ROOT_DIR) -> list[Path]:
    resolved_btx = Path(btx_dir or default_btx_dir(repo_root))
    return [
        resolved_btx / ".env",
        repo_root / ".env",
    ]


BTX_DIR = Path(os.getenv("BTX_DIR") or default_btx_dir())
sys.path.insert(0, str(BTX_DIR))

from dotenv import load_dotenv

for env_candidate in env_candidates(BTX_DIR):
    if env_candidate.exists():
        load_dotenv(env_candidate)


def check_notion_api() -> dict:
    try:
        import httpx

        db_id = os.getenv("NOTION_DATABASE_ID", "")
        token = os.getenv("NOTION_API_KEY", "") or os.getenv("NOTION_TOKEN", "")
        if not db_id or not token:
            return {"status": "error", "message": "NOTION_DATABASE_ID or NOTION_TOKEN missing"}

        resp = httpx.get(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            title = resp.json().get("title", [{}])[0].get("plain_text", "Unknown")
            return {"status": "ok", "message": f"DB connection OK: {title}"}
        return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def check_llm_api() -> dict:
    try:
        import httpx

        api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            return {"status": "warning", "message": "GEMINI_API_KEY missing (fallback chain still available)"}

        resp = httpx.get(
            f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
            timeout=10,
        )
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return {"status": "ok", "message": f"Gemini connection OK ({len(models)} models available)"}
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def check_disk_space() -> dict:
    try:
        usage = shutil.disk_usage("C:\\")
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        used_pct = (usage.used / usage.total) * 100
        status = "ok" if free_gb > 10 else ("warning" if free_gb > 5 else "error")
        return {
            "status": status,
            "message": f"C: {free_gb:.1f}GB free ({used_pct:.0f}% used, total {total_gb:.0f}GB)",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def check_python_env() -> dict:
    try:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        missing = []
        for pkg in ["playwright", "httpx", "notion_client", "dotenv"]:
            try:
                __import__(pkg.replace("-", "_"))
            except ImportError:
                missing.append(pkg)

        if missing:
            return {"status": "warning", "message": f"Python {version} | missing packages: {', '.join(missing)}"}
        return {"status": "ok", "message": f"Python {version} | required packages available"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def check_recent_logs() -> dict:
    try:
        log_dir = Path(__file__).parent / "logs"
        if not log_dir.exists():
            return {"status": "ok", "message": "No logs directory yet"}

        log_files = sorted(log_dir.glob("bridge_*.jsonl"), reverse=True)
        if not log_files:
            return {"status": "ok", "message": "No execution history yet"}

        latest = log_files[0]
        with open(latest, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

        if not lines:
            return {"status": "ok", "message": "Latest log file is empty"}

        last_entry = json.loads(lines[-1])
        last_status = last_entry.get("status", "unknown")
        last_time = last_entry.get("timestamp", "unknown")
        last_cmd = last_entry.get("command", "unknown")
        return {
            "status": "ok" if last_status == "success" else "warning",
            "message": f"Last run: {last_cmd} ({last_status}) @ {last_time}",
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def run_healthcheck() -> dict:
    checks = {
        "notion_api": check_notion_api(),
        "llm_api": check_llm_api(),
        "disk_space": check_disk_space(),
        "python_env": check_python_env(),
        "recent_logs": check_recent_logs(),
    }

    statuses = [item["status"] for item in checks.values()]
    if "error" in statuses:
        overall = "unhealthy"
    elif "warning" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "overall_status": overall,
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    result = run_healthcheck()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    exit_codes = {"healthy": 0, "degraded": 1, "unhealthy": 2}
    sys.exit(exit_codes.get(result["overall_status"], 2))
