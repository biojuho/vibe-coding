# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID | Task | Owner | Priority | Created |
|---|---|---|---|---|
| T-165 | [ADR-026 Phase 2] `.agents/agents/investigator.md` 서브에이전트 정의 파일 작성 — Explore 단계 병렬 탐색용 | Gemini | High | 2026-04-09 |
| T-166 | [ADR-026 Phase 2] Plan Mode 전용 워크플로우 신설 (`.agents/workflows/plan.md`) — Implementation Plan 작성 → 사용자 승인 → Code 단계 진입 형식화 | Gemini | Medium | 2026-04-09 |
| T-167 | [ADR-026 Phase 3] `execution/ai_batch_runner.py` 신규 작성 — 비대화형 AI 배치 실행기 | Gemini | Low | 2026-04-09 |
| T-168 | `projects/knowledge-dashboard/CLAUDE.md` 신규 생성 — verify.md 참조표와 일관성 유지 | Gemini | Medium | 2026-04-09 |
| T-164 | Harden the `hanwoo-dashboard` subscription success client against malformed/non-JSON confirmation responses so retry/failure UI stays deterministic even if the route returns an unexpected body. | Codex | Medium | 2026-04-08 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|---|---|---|---|---|
| T-161 | `hanwoo-dashboard` UX/UI polish pass owned by another tool. | Claude | 2026-04-07 | Leave unrelated UI work untouched unless the user explicitly redirects the session. |

## DONE (Latest 5)

| ID | Task | Completed By | Completed |
|---|---|---|---|
| T-ADR026-P1 | ADR-026 Phase 1: Claude Code 7 Lessons 기반 멀티-AI 지침 계층화 — 루트 지침 강화, 프로젝트별 CLAUDE.md 3개 신규, /verify 워크플로우 신설, QC 완료 | Gemini | 2026-04-09 |
| T-163 | Run a fresh post-fix SRE scan across the active projects, confirm what still reproduces, and close any newly confirmed reliability regression. | Codex | 2026-04-08 |
| T-162 | Harden the `hanwoo-dashboard` offline sync queue with retry caps/dead-letter handling and stabilize notification timestamps so alert cards do not drift on refresh. | Codex | 2026-04-07 |
| T-160 | Harden the remaining `hanwoo-dashboard` client-side refresh/read fetches so post-mutation summary updates and auxiliary dashboard reads fail softly on timeout or malformed payloads. | Codex | 2026-04-07 |
| T-159 | Harden the `hanwoo-dashboard` weather fetch path in `DashboardClient` so timeouts and shape drift degrade cleanly instead of silently breaking the widget. | Codex | 2026-04-07 |

## Rules

- Use IDs in the form `T-XXX`.
- Move tasks from `TODO` -> `IN_PROGRESS` when started.
- Move tasks from `IN_PROGRESS` -> `DONE` when completed.
- Keep only the latest 5 items in `DONE`.
- Add newly discovered follow-up work to `TODO`.
