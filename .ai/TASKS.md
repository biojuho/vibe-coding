# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-167 | [ADR-026 Phase 3] `execution/ai_batch_runner.py` 신규 작성 및 비동기형 AI 배치 실행기 | Gemini | Low | 2026-04-09 |
| T-168 | `projects/knowledge-dashboard/CLAUDE.md` 신규 생성 및 `verify.md` 참조로 검증 루틴 정리 | Gemini | Medium | 2026-04-09 |
| T-173 | [code-review-graph P2] Google Embeddings 설치 (`pip install code-review-graph[google-embeddings]`) 및 시맨틱 검색 개선 | Gemini | Low | 2026-04-09 |
| T-174 | [code-review-graph P2] `hanwoo-dashboard` JS 인덱싱 검증 — IMPORTS_FROM 엣지 활용 여부 확인 | Gemini | Low | 2026-04-09 |
| T-176 | [`blind-to-x`] Backfill historical Notion pages and feed `반려 사유` / `위험 신호` into `feedback_loop.py`. | Codex | Medium | 2026-04-09 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-172 | [code-review-graph P1] graph status 확인 (11,083 nodes / 81,106 edges), MCP 설정 검증 완료 | Gemini | 2026-04-09 |
| T-165 | [ADR-026 Phase 2] `.agents/agents/investigator.md` 서브에이전트 정의 파일 작성 완료 | Gemini | 2026-04-09 |
| T-166 | [ADR-026 Phase 2] `.agents/workflows/plan.md` Plan Mode 워크플로우 신규 작성 완료 | Gemini | 2026-04-09 |
| T-175 | [`blind-to-x`] Refocused the Notion review flow around reviewer judgment, added review columns/schema sync, and applied the new schema to the real Notion DB. | Codex | 2026-04-09 |
| T-171 | [code-review-graph P0] Installed the tool, built graphs for `blind-to-x` and `shorts-maker-v2`, connected the MCP server, added `.code-review-graphignore`, and strengthened `/start` + `/verify`. | Gemini | 2026-04-09 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
