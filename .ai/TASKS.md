# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|----|------|-------|----------|---------|
| T-100 | Raise the remaining project coverage follow-up from the system audit so `shorts-maker-v2` and `blind-to-x` reach their documented target floors | Codex | Medium | 2026-03-31 |
| T-101 | Reduce shared MCP control-plane overhead by limiting concurrent AI tool runs and replacing `server-filesystem` with lighter read/glob usage | Codex | High | 2026-03-31 |
| T-102 | Add the remaining Shorts golden render follow-up from the audit plan so the renderer escape hatch has a pinned 30-second verification path | Codex | Medium | 2026-03-31 |
| T-105 | Fix 5 pre-existing test failures: ShortsFactory module registration (4) + cp949 encoding (1) | Any | Medium | 2026-03-30 |
| T-106 | Apply ruff format to remaining 10 unformatted files in `workspace/` | Any | Low | 2026-03-30 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|----|------|--------------|-----------|
| ad-hoc | Migrated Notion schema validations and payload logic from `review_status` to `status` across `projects/blind-to-x` and successfully passed 582 suite tests. | Gemini | 2026-03-31 |
| T-098 | Added a control-plane meta-QC gate: `governance_checks.py` now verifies required `.ai` files, stale relay claims, directive mapping drift, and tracked backlog linkage, and QA/QC can no longer end at `APPROVED` when governance fails | Codex | 2026-03-31 |
| T-097 | Reconciled the control-plane ownership map by mapping the local inference / agentic coding stack in `INDEX.md` and `local_inference.md`, including `graph_engine.py`, `workers.py`, `code_evaluator.py`, and `governance_checks.py` | Codex | 2026-03-31 |
| T-099 | Linked the open system-audit follow-ups to active `.ai/TASKS.md` items with enforced `[TASK: T-XXX]` references so backlog drift is now machine-checked | Codex | 2026-03-31 |
| T-095 | Documented the latest shared QC security triage details for `projects/blind-to-x/pipeline/cost_db.py` so the two remaining machine-reported findings are clearly recorded as false positives | Codex | 2026-03-31 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
