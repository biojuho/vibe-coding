"""
API 사용량 추적기 - Joolife Hub용.
API 호출 로깅 + 사용량 대시보드 데이터 제공.

Usage (as library):
    from execution.api_usage_tracker import log_api_call, get_usage_summary
    log_api_call(provider="anthropic", model="claude-sonnet-4", tokens_input=500, tokens_output=200)

Usage (CLI):
    python workspace/execution/api_usage_tracker.py summary [--days 30]
    python workspace/execution/api_usage_tracker.py check-keys
"""

import argparse
import json
import os
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

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
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "moonshot-v1-8k": {"input": 0.00015, "output": 0.00015},
    "glm-4-flash": {"input": 0.0, "output": 0.0},
    "grok-2": {"input": 0.002, "output": 0.01},
}

# 월간 예산 (USD) - 환경변수로 오버라이드 가능
MONTHLY_BUDGET_USD = float(os.getenv("MONTHLY_LLM_BUDGET_USD", "30.0"))

# 프리미엄 모델 기준 가격 (절감 효과 계산용, per 1K tokens)
PREMIUM_BASELINE = {"input": 0.003, "output": 0.015}  # claude-sonnet-4 기준

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _validate_identifier(name: str) -> str:
    candidate = (name or "").strip()
    if not IDENTIFIER_PATTERN.fullmatch(candidate):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return candidate


def _table_info_sql(table: str) -> str:
    safe_table = _validate_identifier(table)
    return f"PRAGMA table_info({safe_table})"


_ALLOWED_DEFINITIONS = re.compile(
    r"^(TEXT|INTEGER|REAL|BLOB|NUMERIC)"
    r"(\s+(DEFAULT\s+('[^']*'|NULL|\d+(\.\d+)?)|NOT\s+NULL))*$",
    re.IGNORECASE,
)


def _add_column_sql(table: str, column: str, definition: str) -> str:
    safe_table = _validate_identifier(table)
    safe_column = _validate_identifier(column)
    if not _ALLOWED_DEFINITIONS.fullmatch(definition.strip()):
        raise ValueError(f"Invalid column definition: {definition!r}")
    return f"ALTER TABLE {safe_table} ADD COLUMN {safe_column} {definition}"


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
            bridge_mode TEXT DEFAULT '',
            reason_codes TEXT DEFAULT '[]',
            repair_count INTEGER DEFAULT 0,
            fallback_used INTEGER DEFAULT 0,
            language_score REAL DEFAULT NULL,
            provider_used TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now','localtime'))
        )
        """
    )
    _ensure_columns(
        conn,
        "api_calls",
        {
            "bridge_mode": "TEXT DEFAULT ''",
            "reason_codes": "TEXT DEFAULT '[]'",
            "repair_count": "INTEGER DEFAULT 0",
            "fallback_used": "INTEGER DEFAULT 0",
            "language_score": "REAL DEFAULT NULL",
            "provider_used": "TEXT DEFAULT ''",
        },
    )
    conn.commit()
    conn.close()


def _ensure_columns(
    conn: sqlite3.Connection,
    table: str,
    columns: Dict[str, str],
) -> None:
    existing_rows = conn.execute(_table_info_sql(table)).fetchall()
    existing = {row["name"] for row in existing_rows}
    for column, definition in columns.items():
        if column not in existing:
            conn.execute(_add_column_sql(table, column, definition))


def log_api_call(
    provider: str,
    model: str = "",
    endpoint: str = "",
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_usd: float = 0,
    caller_script: str = "",
    bridge_mode: str = "",
    reason_codes: List[str] | None = None,
    repair_count: int = 0,
    fallback_used: bool = False,
    language_score: float | None = None,
    provider_used: str = "",
) -> None:
    """API 호출 기록. 다른 execution 스크립트에서 import해서 사용."""
    init_db()
    # 비용 자동 계산 (명시하지 않은 경우)
    if cost_usd == 0 and model in PRICING:
        p = PRICING[model]
        cost_usd = (tokens_input / 1000 * p["input"]) + (tokens_output / 1000 * p["output"])

    conn = _conn()
    conn.execute(
        "INSERT INTO api_calls (provider, model, endpoint, tokens_input, tokens_output, cost_usd, caller_script, "
        "bridge_mode, reason_codes, repair_count, fallback_used, language_score, provider_used) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            provider,
            model,
            endpoint,
            tokens_input,
            tokens_output,
            cost_usd,
            caller_script,
            bridge_mode,
            json.dumps(reason_codes or [], ensure_ascii=False),
            repair_count,
            int(fallback_used),
            language_score,
            provider_used or provider,
        ),
    )
    conn.commit()
    conn.close()


def get_usage_summary(days: int = 30) -> Dict:
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    total_calls = conn.execute("SELECT COUNT(*) FROM api_calls WHERE timestamp >= ?", (since,)).fetchone()[0]
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


def get_bridge_activity_for_date(target_date: date) -> Dict:
    """Return bridge validation activity for a single day."""
    init_db()
    conn = _conn()
    since = f"{target_date.isoformat()} 00:00:00"
    until = f"{target_date.isoformat()} 23:59:59"
    rows = conn.execute(
        "SELECT bridge_mode, reason_codes, repair_count, fallback_used, language_score, provider_used "
        "FROM api_calls WHERE timestamp >= ? AND timestamp <= ? AND bridge_mode != ''",
        (since, until),
    ).fetchall()
    conn.close()

    summary = {
        "total_calls": 0,
        "shadow_calls": 0,
        "enforce_calls": 0,
        "repair_calls": 0,
        "fallback_calls": 0,
        "average_language_score": None,
        "reason_codes": {},
        "by_provider": {},
    }
    scores: List[float] = []

    for row in rows:
        summary["total_calls"] += 1
        mode = row["bridge_mode"] or ""
        if mode == "shadow":
            summary["shadow_calls"] += 1
        elif mode == "enforce":
            summary["enforce_calls"] += 1

        repair_count = int(row["repair_count"] or 0)
        fallback_used = bool(row["fallback_used"])
        provider_used = row["provider_used"] or ""
        language_score = row["language_score"]

        if repair_count > 0:
            summary["repair_calls"] += 1
        if fallback_used:
            summary["fallback_calls"] += 1
        if provider_used:
            summary["by_provider"][provider_used] = summary["by_provider"].get(provider_used, 0) + 1
        if language_score is not None:
            scores.append(float(language_score))

        raw_reason_codes = row["reason_codes"] or "[]"
        try:
            reason_codes = json.loads(raw_reason_codes)
        except json.JSONDecodeError:
            reason_codes = []
        for code in reason_codes:
            summary["reason_codes"][code] = summary["reason_codes"].get(code, 0) + 1

    if scores:
        summary["average_language_score"] = round(sum(scores) / len(scores), 4)
    summary["top_reason_codes"] = [
        {"reason_code": reason, "count": count}
        for reason, count in sorted(
            summary["reason_codes"].items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    return summary


def get_bridge_daily_breakdown(days: int = 30) -> List[Dict]:
    """Return daily bridge activity counts for charting."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT substr(timestamp, 1, 10) as day, "
        "COUNT(*) as calls, "
        "SUM(CASE WHEN bridge_mode = 'shadow' THEN 1 ELSE 0 END) as shadow_calls, "
        "SUM(CASE WHEN bridge_mode = 'enforce' THEN 1 ELSE 0 END) as enforce_calls, "
        "SUM(CASE WHEN repair_count > 0 THEN 1 ELSE 0 END) as repair_calls, "
        "SUM(CASE WHEN fallback_used > 0 THEN 1 ELSE 0 END) as fallback_calls, "
        "AVG(language_score) as average_language_score "
        "FROM api_calls WHERE timestamp >= ? AND bridge_mode != '' "
        "GROUP BY day ORDER BY day",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bridge_reason_breakdown(days: int = 30) -> List[Dict]:
    """Return aggregated bridge reason codes for charting."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT reason_codes FROM api_calls WHERE timestamp >= ? AND bridge_mode != ''",
        (since,),
    ).fetchall()
    conn.close()

    counts: Dict[str, int] = {}
    for row in rows:
        raw = row["reason_codes"] or "[]"
        try:
            reason_codes = json.loads(raw)
        except json.JSONDecodeError:
            reason_codes = []
        for code in reason_codes:
            counts[code] = counts.get(code, 0) + 1

    return [
        {"reason_code": reason, "count": count}
        for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def get_bridge_provider_breakdown(days: int = 30) -> List[Dict]:
    """Return provider-level bridge quality metrics."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT provider_used, reason_codes, repair_count, fallback_used, language_score "
        "FROM api_calls WHERE timestamp >= ? AND bridge_mode != ''",
        (since,),
    ).fetchall()
    conn.close()

    stats: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        provider = row["provider_used"] or "unknown"
        bucket = stats.setdefault(
            provider,
            {
                "provider": provider,
                "bridge_calls": 0,
                "issue_calls": 0,
                "repair_attempts": 0,
                "repair_successes": 0,
                "fallback_calls": 0,
                "language_scores": [],
            },
        )
        bucket["bridge_calls"] += 1
        if row["fallback_used"]:
            bucket["fallback_calls"] += 1
        if row["language_score"] is not None:
            bucket["language_scores"].append(float(row["language_score"]))

        raw_reason_codes = row["reason_codes"] or "[]"
        try:
            reason_codes = json.loads(raw_reason_codes)
        except json.JSONDecodeError:
            reason_codes = []
        if reason_codes:
            bucket["issue_calls"] += 1

        repair_count = int(row["repair_count"] or 0)
        if repair_count > 0:
            bucket["repair_attempts"] += 1
            if not reason_codes:
                bucket["repair_successes"] += 1

    breakdown: List[Dict] = []
    for provider, bucket in stats.items():
        bridge_calls = int(bucket["bridge_calls"])
        issue_calls = int(bucket["issue_calls"])
        repair_attempts = int(bucket["repair_attempts"])
        repair_successes = int(bucket["repair_successes"])
        scores = bucket["language_scores"]
        breakdown.append(
            {
                "provider": provider,
                "bridge_calls": bridge_calls,
                "issue_calls": issue_calls,
                "bridge_failure_rate": round((issue_calls / bridge_calls) * 100, 2) if bridge_calls else 0.0,
                "repair_attempts": repair_attempts,
                "repair_successes": repair_successes,
                "repair_success_rate": (
                    round((repair_successes / repair_attempts) * 100, 2) if repair_attempts else None
                ),
                "fallback_calls": int(bucket["fallback_calls"]),
                "average_language_score": round(sum(scores) / len(scores), 4) if scores else None,
            }
        )

    return sorted(breakdown, key=lambda item: (-item["bridge_calls"], item["provider"]))


def get_blind_to_x_summary(days: int = 30) -> Dict:
    """blind-to-x 파이프라인 API 사용 요약 (caller_script 필터)."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT provider, COUNT(*) as calls, "
        "SUM(tokens_input) as input_tokens, "
        "SUM(tokens_output) as output_tokens, "
        "SUM(cost_usd) as cost "
        "FROM api_calls "
        "WHERE timestamp >= ? AND caller_script LIKE '%blind-to-x%' "
        "GROUP BY provider ORDER BY calls DESC",
        (since,),
    ).fetchall()
    conn.close()

    provider_rows = [dict(r) for r in rows]
    total_cost = sum(r.get("cost") or 0.0 for r in provider_rows)
    total_calls = sum(r.get("calls") or 0 for r in provider_rows)
    return {
        "providers": provider_rows,
        "total_calls": total_calls,
        "total_cost_usd": round(total_cost, 5),
    }


def get_model_breakdown(days: int = 30) -> List[Dict]:
    """모델별 비용 및 호출 수 집계."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT model, provider, COUNT(*) as calls, "
        "SUM(tokens_input) as input_tokens, "
        "SUM(tokens_output) as output_tokens, "
        "SUM(cost_usd) as cost "
        "FROM api_calls WHERE timestamp >= ? "
        "GROUP BY model, provider ORDER BY cost DESC, calls DESC",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_summary(months: int = 6) -> List[Dict]:
    """월별 비용 집계 (최근 N개월)."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT substr(timestamp, 1, 7) as month, "
        "COUNT(*) as calls, "
        "SUM(tokens_input + tokens_output) as tokens, "
        "SUM(cost_usd) as cost "
        "FROM api_calls WHERE timestamp >= ? "
        "GROUP BY month ORDER BY month",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_task_breakdown(days: int = 30) -> List[Dict]:
    """caller_script(task) 별 비용 집계."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT caller_script, COUNT(*) as calls, "
        "SUM(tokens_input + tokens_output) as tokens, "
        "SUM(cost_usd) as cost "
        "FROM api_calls WHERE timestamp >= ? "
        "GROUP BY caller_script ORDER BY cost DESC, calls DESC",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_fallback_analysis(days: int = 30) -> Dict:
    """폴백 체인 사용 통계."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    total = conn.execute("SELECT COUNT(*) FROM api_calls WHERE timestamp >= ?", (since,)).fetchone()[0]
    fallback_count = conn.execute(
        "SELECT COUNT(*) FROM api_calls WHERE timestamp >= ? AND fallback_used = 1",
        (since,),
    ).fetchone()[0]
    by_provider = conn.execute(
        "SELECT provider_used, COUNT(*) as calls, SUM(cost_usd) as cost "
        "FROM api_calls WHERE timestamp >= ? AND fallback_used = 1 "
        "GROUP BY provider_used ORDER BY calls DESC",
        (since,),
    ).fetchall()
    conn.close()
    return {
        "total_calls": total,
        "fallback_calls": fallback_count,
        "fallback_rate": round(fallback_count / total * 100, 2) if total else 0.0,
        "by_provider": [dict(r) for r in by_provider],
    }


def get_savings_estimate(days: int = 30) -> Dict:
    """프리미엄 모델 대비 절감 효과 추정 (30일 rolling)."""
    init_db()
    conn = _conn()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT tokens_input, tokens_output, cost_usd FROM api_calls WHERE timestamp >= ?",
        (since,),
    ).fetchall()
    conn.close()

    actual_cost = 0.0
    premium_cost = 0.0
    for r in rows:
        inp = r["tokens_input"] or 0
        out = r["tokens_output"] or 0
        actual_cost += r["cost_usd"] or 0.0
        premium_cost += (inp / 1000 * PREMIUM_BASELINE["input"]) + (out / 1000 * PREMIUM_BASELINE["output"])
    saved = premium_cost - actual_cost
    return {
        "actual_cost_usd": round(actual_cost, 4),
        "premium_baseline_usd": round(premium_cost, 4),
        "savings_usd": round(saved, 4),
        "savings_pct": round(saved / premium_cost * 100, 2) if premium_cost > 0 else 0.0,
    }


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
