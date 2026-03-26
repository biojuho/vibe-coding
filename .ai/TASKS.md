# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-056 | Verify next Blind-to-X scheduled run creates `scheduled_*.log` and reports `LastTaskResult=0` | any | HIGH | 2026-03-26 |
| T-057 | Fix blind-to-x false-negative timeout in `workspace/execution/qaqc_runner.py` | Codex | HIGH | 2026-03-26 |
| T-058 | Investigate and fix `shorts-maker-v2` full-suite order-dependent failure | Claude | HIGH | 2026-03-26 |
| T-059 | Fix `knowledge-dashboard` lint errors (`ActivityTimeline.tsx`, `ui/input.tsx`) | Codex | HIGH | 2026-03-26 |
| T-060 | Clean up remaining Python Ruff issues after canonical refactor | any | MEDIUM | 2026-03-26 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-061 | Implement Blind-to-X X curation and draft quality redesign | Codex | 2026-03-26 |
| T-055 | Restore Blind-to-X scheduled paths and `C:\btx` ASCII launchers | Codex | 2026-03-26 |
| T-054 | Complete trend-based auto-topic generation (`--auto-topic`) | Antigravity | 2026-03-26 |
| T-053 | Confirm empty legacy `shorts-maker-v2/` root and reflect moved-project status | Antigravity | 2026-03-26 |
| T-050-B | Restore test suite after `__init__.py` lazy-import monkeypatch fix | Antigravity | 2026-03-26 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
