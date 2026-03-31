"""
재무 데이터베이스 - Joolife Hub용.
SQLite 기반 수입/지출 추적.

Usage:
    python workspace/execution/finance_db.py init
    python workspace/execution/finance_db.py add --type expense --amount 15000 --category "식비" --desc "점심"
    python workspace/execution/finance_db.py summary --month 2026-02
    python workspace/execution/finance_db.py export --format csv
"""

import argparse
import csv
import io
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List

DB_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "finance.db"

CATEGORIES = {
    "income": ["급여", "부업", "투자수익", "기타수입"],
    "expense": [
        "식비",
        "교통",
        "주거",
        "통신",
        "쇼핑",
        "의료",
        "교육",
        "여가",
        "구독",
        "기타지출",
    ],
}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE,
            monthly_limit REAL NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def add_transaction(
    type_: str,
    amount: float,
    category: str,
    description: str = "",
    dt: str = None,
) -> int:
    init_db()
    if dt is None:
        dt = date.today().isoformat()
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO transactions (type, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
        (type_, amount, category, description, dt),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def delete_transaction(tid: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM transactions WHERE id = ?", (tid,))
    conn.commit()
    conn.close()
    return True


def get_transactions(month: str = None, category: str = None, limit: int = 200) -> List[Dict]:
    init_db()
    conn = _conn()
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if month:
        query += " AND date LIKE ?"
        params.append(f"{month}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_summary(month: str) -> Dict:
    init_db()
    conn = _conn()
    income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND date LIKE ?",
        (f"{month}%",),
    ).fetchone()[0]
    expense = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND date LIKE ?",
        (f"{month}%",),
    ).fetchone()[0]
    conn.close()
    return {
        "month": month,
        "income": income,
        "expense": expense,
        "net": income - expense,
    }


def get_category_breakdown(month: str) -> List[Dict]:
    init_db()
    conn = _conn()
    rows = conn.execute(
        "SELECT category, type, SUM(amount) as total FROM transactions "
        "WHERE date LIKE ? GROUP BY category, type ORDER BY total DESC",
        (f"{month}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trend(months: int = 6) -> List[Dict]:
    """최근 N개월 월별 수입/지출 추이."""
    init_db()
    conn = _conn()
    rows = conn.execute(
        "SELECT substr(date, 1, 7) as month, type, SUM(amount) as total "
        "FROM transactions GROUP BY month, type ORDER BY month DESC LIMIT ?",
        (months * 2,),
    ).fetchall()
    conn.close()

    # 월별로 그룹핑
    trend = {}
    for r in rows:
        m = r["month"]
        if m not in trend:
            trend[m] = {"month": m, "income": 0, "expense": 0}
        trend[m][r["type"]] = r["total"]

    result = sorted(trend.values(), key=lambda x: x["month"])
    for item in result:
        item["net"] = item["income"] - item["expense"]
    return result


def set_budget(category: str, monthly_limit: float) -> None:
    init_db()
    conn = _conn()
    conn.execute(
        "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
        "ON CONFLICT(category) DO UPDATE SET monthly_limit = ?",
        (category, monthly_limit, monthly_limit),
    )
    conn.commit()
    conn.close()


def get_budgets() -> List[Dict]:
    init_db()
    conn = _conn()
    rows = conn.execute("SELECT * FROM budgets").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def check_budget_alerts(month: str) -> List[Dict]:
    """예산 초과 여부 확인."""
    budgets = get_budgets()
    alerts = []
    for b in budgets:
        conn = _conn()
        spent = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE category = ? AND type = 'expense' AND date LIKE ?",
            (b["category"], f"{month}%"),
        ).fetchone()[0]
        conn.close()
        ratio = spent / b["monthly_limit"] if b["monthly_limit"] > 0 else 0
        if ratio >= 0.8:
            alerts.append(
                {
                    "category": b["category"],
                    "budget": b["monthly_limit"],
                    "spent": spent,
                    "ratio": round(ratio, 2),
                    "over": spent > b["monthly_limit"],
                }
            )
    return alerts


def export_csv(month: str = None) -> str:
    rows = get_transactions(month=month, limit=10000)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "type", "amount", "category", "description", "date"],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r[k] for k in ["id", "type", "amount", "category", "description", "date"]})
    return output.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joolife Finance DB")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init")

    p_add = sub.add_parser("add")
    p_add.add_argument("--type", required=True, choices=["income", "expense"])
    p_add.add_argument("--amount", required=True, type=float)
    p_add.add_argument("--category", required=True)
    p_add.add_argument("--desc", default="")
    p_add.add_argument("--date")

    p_sum = sub.add_parser("summary")
    p_sum.add_argument("--month", required=True)

    p_exp = sub.add_parser("export")
    p_exp.add_argument("--month")
    p_exp.add_argument("--format", choices=["csv", "json"], default="csv")

    args = parser.parse_args()

    if args.cmd == "init":
        init_db()
        print("Database initialized.")
    elif args.cmd == "add":
        tid = add_transaction(args.type, args.amount, args.category, args.desc, args.date)
        print(f"Transaction #{tid} added.")
    elif args.cmd == "summary":
        print(json.dumps(get_monthly_summary(args.month), ensure_ascii=False, indent=2))
    elif args.cmd == "export":
        if args.format == "csv":
            print(export_csv(getattr(args, "month", None)))
        else:
            print(json.dumps(get_transactions(month=getattr(args, "month", None)), ensure_ascii=False, indent=2))
    else:
        parser.print_help()
