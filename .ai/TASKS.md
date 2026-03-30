# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-091 | Extract `_run_*_stage()` helpers from `pipeline/process.py` into dedicated stage modules and remove `_process_single_post_legacy` | Codex | Low | 2026-03-30 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| T-092 | Full-system audit: restored `blind-to-x` shared QC by fixing `pipeline/process.py` syntax corruption and corrected `health_check.py` to the canonical repo/workspace path contract | Codex | 2026-03-30 |
| T-089 | Migrated all direct `classification_rules.yaml` consumers (3 test files, 7 test classes) to `rules_loader.load_rules()`. 582 passed, 0 failed. | Gemini | 2026-03-30 |
| T-084 | Filled `blind-to-x` external-review `sample-cases.md` with 2 anonymized real pipeline cases (empathetic success + quality gate retry) | Gemini | 2026-03-30 |
| T-087 | Fixed critical SyntaxError in `pipeline/process.py` (orphaned legacy params without `def`); `py_compile` + full 582-test suite now passes | Gemini | 2026-03-30 |
| T-082 | `caption_pillow.py` coverage uplift to 97%; ruff lint clean | Gemini | 2026-03-30 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
