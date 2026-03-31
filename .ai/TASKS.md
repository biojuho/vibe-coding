# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-095 | Documented the latest shared QC security triage details for `projects/blind-to-x/pipeline/cost_db.py` so the two remaining machine-reported findings are clearly recorded as false positives | Codex | 2026-03-31 |
| T-094 | Re-ran full shared workspace QC and confirmed all three scopes remain green (`2870 passed`, AST 20/20, security clear, scheduler ready) | Codex | 2026-03-31 |
| T-093 | Re-ran `blind-to-x` project QC and confirmed the staged pipeline remains green after T-091 (`560 passed`, `AST 20/20`, security clear) | Codex | 2026-03-31 |
| T-091 | Finalized the staged `blind-to-x` pipeline cleanup: `pipeline/process.py` is now a slim orchestrator, `pipeline/stages/` is a compatibility layer backed by `pipeline/process_stages/`, and targeted regressions plus project QA/QC rerun passed | Codex | 2026-03-30 |
| T-092 | Full-system audit: restored `blind-to-x` shared QC by fixing `pipeline/process.py` syntax corruption and corrected `health_check.py` to the canonical repo/workspace path contract | Codex | 2026-03-30 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
