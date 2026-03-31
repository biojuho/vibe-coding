# Scheduler Directive

## Goal

Register, execute, and monitor recurring workspace tasks with structured logging and failure controls.

## Tools

- `workspace/execution/scheduler_engine.py`
- `workspace/execution/scheduler_worker.py`
- `workspace/execution/pages/scheduler_dashboard.py`
- `workspace/execution/telegram_notifier.py`

## Storage

- SQLite path: `.tmp/scheduler.db`
- Main tables: `tasks`, `task_logs`

## CLI

```bash
python workspace/execution/scheduler_engine.py add --name "Backup" --exec python --args "workspace/scripts/backup_data.py --with-env" --cwd . --cron "0 9 * * *" --timeout 300
python workspace/execution/scheduler_engine.py run-due
python workspace/execution/scheduler_engine.py logs --limit 30
python workspace/execution/scheduler_engine.py kpis --days 7
python workspace/execution/scheduler_worker.py --interval 30
```
