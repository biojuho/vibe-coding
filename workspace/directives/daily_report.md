# Daily Report Directive

## Goal

Summarize daily workspace activity from git history, file changes, scheduler logs, and bridge telemetry.

## Tools

- `workspace/execution/daily_report.py`
- `workspace/execution/pages/daily_report.py`
- `workspace/execution/telegram_notifier.py`

## Outputs

- JSON: `.tmp/reports/daily_YYYY-MM-DD.json`
- Main sections: `summary`, `git_activity`, `file_changes`, `scheduler_logs`, `llm_bridge`

## CLI

```bash
python workspace/execution/daily_report.py --date 2026-02-24 --format json
python workspace/execution/daily_report.py --format markdown
python workspace/execution/daily_report.py --format markdown --telegram
```
