# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-056 | Verify next Blind-to-X scheduled run creates `scheduled_*.log` and reports `LastTaskResult=0` | any | HIGH | 2026-03-26 |
| T-057 | Fix blind-to-x false-negative timeout in `workspace/execution/qaqc_runner.py` | Codex | HIGH | 2026-03-26 |
| T-058 | Investigate and fix `shorts-maker-v2` full-suite order-dependent failure | Claude | HIGH | 2026-03-26 |
| T-059 | Fix `knowledge-dashboard` lint errors (`ActivityTimeline.tsx`, `ui/input.tsx`) | Codex | HIGH | 2026-03-26 |
| T-064 | Archive `projects/shorts-maker-v2/tests/legacy` out of pytest discovery after confirming current ShortsFactory fallback needs | any | MEDIUM | 2026-03-27 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-063 | Raise `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py` coverage with mock-heavy unit tests | Codex | 2026-03-27 |
| T-060 | Clean up remaining Python Ruff issues after canonical refactor | Antigravity | 2026-03-27 |
| T-062 | shorts-maker-v2 ?뚯씠?꾨씪??怨좊룄??(StructureStep + ?щ퀎QC + 議곗슜???댁빞湲??? | Claude Code | 2026-03-26 |
| T-061 | Implement Blind-to-X X curation and draft quality redesign | Codex | 2026-03-26 |
| T-055 | Restore Blind-to-X scheduled paths and `C:\btx` ASCII launchers | Codex | 2026-03-26 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
