"""
API 사용량 추적기 - Joolife Hub용.
API 호출 로깅 + 사용량 대시보드 데이터 제공.

Usage (as library):
    from execution.api_usage_tracker import log_api_call, get_usage_summary
    log_api_call(provider="anthropic", model="claude-sonnet-4", tokens_input=500, tokens_output=200)

Usage (CLI):
    python execution/api_usage_tracker.py summary [--days 30]
    python execution/api_usage_tracker.py check-keys
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "api_usage.db"

# API 키 이름 매핑
API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "zhipuai": "ZHIPUAI_API_KEY",
    "xai": "XAI_API_KEY",
    "github": "GITHUB_PERSONAL_ACCESS_TOKEN",
    "notion": "NOTION_API_KEY",
}

# 토큰당 대략적 비용 (USD, per 1K tokens)
PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-sonnet-4": {"input": 0.003, "output": 0.015},
    "claude-haiku-3.5": {"input": 0.0008, "output": 0.004},
    "gemini-pro": {"input": 0.00025, "output": 0.0005},
}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model TEXT DEFAULT '',
            endpoint TEXT DEFAULT '',
            tokens_input INTEGER DEFAULT 0,
            tokens_output INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            caller_script TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now','localtime'))
        )
        """
    )
    conn.commit()
    conn.close()


def log_api_call(
    provider: str,
    model: str = "",
    endpoint: str = "",
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0,
    caller_script: str = "",
) -> None:
    """API 호출 기록. 다른 execution 스크립트에서 import해서 사용."""
    init_db()
    # 비용 자동 계산 (명시하지 않은 경우)
    if cost_usd == 0 and model in PRICING:
        p = PRICING[model]
        cost_usd = (tokens_input / 1000 * p["input"]) + (
            tokens_output / 1000 * p["output"]
        )

    conn = _conn()
    conn.execute(
        "INSERT INTO api_calls (provider, model, endpoint, tokens_input, tokens_output, cost_usd, caller_script) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (provider, model, endpoint, tokens_input, tokens_output, cost_usd, caller_script),
    )
    conn.commit()
    conn.close()


def get_usage_summary(days: int = 30) -> Dict:
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    total_calls = conn.execute(
        "SELECT COUNT(*) FROM api_calls WHERE timestamp >= ?", (since,)
    ).fetchone()[0]
    total_tokens = conn.execute(
        "SELECT COALESCE(SUM(tokens_input + tokens_output), 0) FROM api_calls WHERE timestamp >= ?",
        (since,),
    ).fetchone()[0]
    total_cost = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM api_calls WHERE timestamp >= ?",
        (since,),
    ).fetchone()[0]
    conn.close()

    return {
        "days": days,
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
    }


def get_daily_breakdown(days: int = 30) -> List[Dict]:
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT substr(timestamp, 1, 10) as day, "
        "COUNT(*) as calls, "
        "SUM(tokens_input) as input_tokens, "
        "SUM(tokens_output) as output_tokens, "
        "SUM(cost_usd) as cost "
        "FROM api_calls WHERE timestamp >= ? "
        "GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_provider_breakdown(days: int = 30) -> List[Dict]:
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT provider, COUNT(*) as calls, "
        "SUM(tokens_input + tokens_output) as tokens, "
        "SUM(cost_usd) as cost "
        "FROM api_calls WHERE timestamp >= ? "
        "GROUP BY provider ORDER BY calls DESC",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_api_keys() -> Dict[str, bool]:
    """각 프로바이더의 API 키 설정 여부 확인."""
    result = {}
    for provider, env_name in API_KEYS.items():
        key = os.getenv(env_name, "")
        result[provider] = bool(key and len(key) > 5)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife API Usage Tracker")
    sub = parser.add_subparsers(dest="cmd")

    p_sum = sub.add_parser("summary")
    p_sum.add_argument("--days", type=int, default=30)

    sub.add_parser("check-keys")
    sub.add_parser("daily")
    sub.add_parser("providers")

    args = parser.parse_args()

    if args.cmd == "summary":
        print(json.dumps(get_usage_summary(args.days), indent=2))
    elif args.cmd == "check-keys":
        print(json.dumps(check_api_keys(), indent=2))
    elif args.cmd == "daily":
        print(json.dumps(get_daily_breakdown(), indent=2))
    elif args.cmd == "providers":
        print(json.dumps(get_provider_breakdown(), indent=2))
    else:
        parser.print_help()
