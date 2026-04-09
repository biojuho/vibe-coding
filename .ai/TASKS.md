# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-165 | [ADR-026 Phase 2] Write the `.agents/agents/investigator.md` sub-agent definition and parallel Explore guidance. | Gemini | High | 2026-04-09 |
| T-166 | [ADR-026 Phase 2] Add the Plan Mode workflow (`.agents/workflows/plan.md`) and verify the Implementation Plan gate before Code. | Gemini | Medium | 2026-04-09 |
| T-167 | [ADR-026 Phase 3] Create `execution/ai_batch_runner.py` for async AI batch execution. | Gemini | Low | 2026-04-09 |
| T-168 | Create `projects/knowledge-dashboard/CLAUDE.md` and align it with the new `/verify` routing. | Gemini | Medium | 2026-04-09 |
| T-172 | [code-review-graph P1] After Antigravity restart, verify real MCP calls for `get_impact_radius` and `get_architecture_overview`. | Gemini | High | 2026-04-09 |
| T-173 | [code-review-graph P2] Install Google Embeddings (`pip install code-review-graph[google-embeddings]`) and improve semantic search. | Gemini | Low | 2026-04-09 |
| T-174 | [code-review-graph P2] Validate JS indexing in `hanwoo-dashboard`, especially whether IMPORTS_FROM edges are populated. | Gemini | Low | 2026-04-09 |
| T-176 | [`blind-to-x`] Backfill historical Notion pages and feed `반려 사유` / `위험 신호` into `feedback_loop.py`. | Codex | Medium | 2026-04-09 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-175 | [`blind-to-x`] Refocused the Notion review flow around reviewer judgment, added review columns/schema sync, and applied the new schema to the real Notion DB. | Codex | 2026-04-09 |
| T-171 | [code-review-graph P0] Installed the tool, built graphs for `blind-to-x` and `shorts-maker-v2`, connected the MCP server, added `.code-review-graphignore`, and strengthened `/start` + `/verify`. | Gemini | 2026-04-09 |
| T-170 | Cleaned the remaining repo-wide Ruff debt in `projects/shorts-maker-v2` by aligning legacy-test security ignores with the existing test policy and fixing the import-order hotspots so `python -m ruff check .` now passes end-to-end. | Codex | 2026-04-09 |
| T-169 | Fixed the confirmed deep-debug reliability regressions across `blind-to-x`, `shorts-maker-v2`, and `hanwoo-dashboard`. | Codex | 2026-04-09 |
| T-ADR026-P1 | ADR-026 Phase 1: added project-level `CLAUDE.md` files, explicit `/verify` workflow guidance, and recorded the decision in `.ai/DECISIONS.md`. | Gemini | 2026-04-09 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
