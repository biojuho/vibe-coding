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
| T-093 | Re-ran `blind-to-x` project QC and confirmed the staged pipeline remains green after T-091 (`560 passed`, `AST 20/20`, security clear) | Codex | 2026-03-31 |
| T-091 | Finalized the staged `blind-to-x` pipeline cleanup: `pipeline/process.py` is now a slim orchestrator, `pipeline/stages/` is a compatibility layer backed by `pipeline/process_stages/`, and targeted regressions plus project QA/QC rerun passed | Codex | 2026-03-30 |
| T-092 | Full-system audit: restored `blind-to-x` shared QC by fixing `pipeline/process.py` syntax corruption and corrected `health_check.py` to the canonical repo/workspace path contract | Codex | 2026-03-30 |
| T-089 | Migrated all direct `classification_rules.yaml` consumers (3 test files, 7 test classes) to `rules_loader.load_rules()`. 582 passed, 0 failed. | Gemini | 2026-03-30 |
| T-084 | Filled `blind-to-x` external-review `sample-cases.md` with 2 anonymized real pipeline cases (empathetic success + quality gate retry) | Gemini | 2026-03-30 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
