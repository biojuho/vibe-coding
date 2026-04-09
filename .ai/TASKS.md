# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-165 | [ADR-026 Phase 2] `.agents/agents/investigator.md` 서브에이전트 정의 파일 작성 및 Explore 단계 병렬 탐색화 | Gemini | High | 2026-04-09 |
| T-166 | [ADR-026 Phase 2] Plan Mode 전용 워크플로우 (`.agents/workflows/plan.md`) 및 Implementation Plan 작성 후 사용자 확인 뒤 Code 단계 진입 정착화 | Gemini | Medium | 2026-04-09 |
| T-167 | [ADR-026 Phase 3] `execution/ai_batch_runner.py` 신규 작성 및 비동기형 AI 배치 실행기 | Gemini | Low | 2026-04-09 |
| T-168 | `projects/knowledge-dashboard/CLAUDE.md` 신규 생성 및 `verify.md` 참조로 검증 루틴 정리 | Gemini | Medium | 2026-04-09 |
| T-172 | [code-review-graph P1] Antigravity 재시작 후 MCP 도구 실제 호출 검증 (`get_impact_radius`, `get_architecture_overview`) | Gemini | High | 2026-04-09 |
| T-173 | [code-review-graph P2] Google Embeddings 설치 (`pip install code-review-graph[google-embeddings]`) 및 시맨틱 검색 개선 | Gemini | Low | 2026-04-09 |
| T-174 | [code-review-graph P2] `hanwoo-dashboard` JS 인덱싱 검증 — IMPORTS_FROM 엣지 활용 여부 확인 | Gemini | Low | 2026-04-09 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-171 | [code-review-graph P0] 설치, blind-to-x + shorts-maker-v2 그래프 빌드, MCP 서버 연동, .code-review-graphignore 설정, /start + /verify 워크플로우 강화 완료 | Gemini | 2026-04-09 |
| T-170 | Cleaned the remaining repo-wide Ruff debt in `projects/shorts-maker-v2` by aligning legacy-test security ignores with the existing test policy and fixing the import-order hotspots so `python -m ruff check .` now passes end-to-end. | Codex | 2026-04-09 |
| T-169 | Fix the confirmed deep-debug reliability regressions across `blind-to-x`, `shorts-maker-v2`, and `hanwoo-dashboard`. | Codex | 2026-04-09 |
| T-ADR026-P1 | ADR-026 Phase 1: Claude Code 7 Lessons 기반 멀티 AI 지침 계층화, 프로젝트별 `CLAUDE.md` 3종 신규 생성, `/verify` 워크플로우 정착, QC 완료 | Gemini | 2026-04-09 |
| T-163 | Run a fresh post-fix SRE scan across the active projects, confirm what still reproduces, and close any newly confirmed reliability regression. | Codex | 2026-04-08 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
