# API Monitoring Directive

## Goal

Track API usage, estimate cost, and expose shared KPIs in the workspace dashboard.

## Tools

- `workspace/execution/api_usage_tracker.py`
- `workspace/execution/pages/api_monitor.py`

## Data

- SQLite path: `.tmp/api_usage.db`
- Table: `api_calls`
- Important fields: `provider`, `model`, `endpoint`, `tokens_input`, `tokens_output`, `cost_usd`, `caller_script`, `timestamp`

## KPI Targets

- `scheduler_success_rate`
- `scheduler_backlog`
- `api_calls_per_day`
- `agent_startup_failures`

## CLI

```bash
python workspace/execution/api_usage_tracker.py check-keys
python workspace/execution/api_usage_tracker.py summary --days 30
python workspace/execution/api_usage_tracker.py daily
python workspace/execution/api_usage_tracker.py providers
python workspace/execution/api_usage_tracker.py alerts --expected-providers openai,anthropic,google
```

## Daily Alert Flow

- Run `alerts` from cron or n8n once per day.
- Exit code `0` means no alerts; exit code `1` means at least one anomaly was found.
- Current anomaly checks: high fallback rate, total cost spike versus the prior window, and configured-but-dead expected providers.
