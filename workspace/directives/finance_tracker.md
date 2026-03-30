# Finance Tracker Directive

## Goal

Track personal income and expenses, summarize monthly performance, and surface budget alerts.

## Tools

- `workspace/execution/finance_db.py`
- `workspace/execution/pages/finance_tracker.py`

## Storage

- SQLite path: `.tmp/finance.db`
- Tables: `transactions`, `budgets`
- Currency: KRW

## CLI

```bash
python workspace/execution/finance_db.py init
python workspace/execution/finance_db.py add --type expense --amount 15000 --category "식비" --desc "점심"
python workspace/execution/finance_db.py summary --month 2026-02
python workspace/execution/finance_db.py export --format csv
```
