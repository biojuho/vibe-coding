# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner  | Priority | Created    |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|----------|------------|
| T-121 | Investigate the local-only `KeyboardInterrupt` / runner interruption when `projects/blind-to-x/tests/unit/test_main.py` runs under this terminal wrapper, and confirm whether it is a harness artifact or a real `main.py` regression. | Codex  | Medium   | 2026-04-01 |
| T-100 | Raise `blind-to-x` coverage to ≥75% (shorts-maker-v2 90% ✅, blind-to-x 69% — pipeline쪽 보강 필요, 스크래퍼는 브라우저 의존으로 제외). | Claude | High     | 2026-03-31 |
| T-128 | `test_cost_tracker_uses_persisted_daily_totals` 전체 실행 시 fail, 단독 pass — 테스트 격리 문제. 실행 순서 의존성 원인 규명 및 수정. | Claude | Medium   | 2026-04-02 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|
| T-129 | Scale-harden `projects/hanwoo-dashboard` for 100x traffic: verify real DB indexes/migrations, add cached read models plus pagination, and split the monolithic dashboard client to reduce refresh and bundle pressure. | Codex | 2026-04-02 | Design doc created at `docs/designs/2026-04-02-hanwoo-dashboard-scale-hardening-design.md`; next step is live index verification plus migration drafting. |

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-127 | Production-hardened `knowledge-dashboard` after the analytics upgrade: browser auth now exchanges `DASHBOARD_API_KEY` for a signed `httpOnly` session cookie, `/api/data/*` trusts shared auth helpers, node tests cover the insight engine, and smoke coverage verifies the session flow end to end. | Codex        | 2026-04-02 |
| T-126 | Upgraded `knowledge-dashboard` analytics visualizations and insight logic to Pro-level UX with Recharts custom tooltips, robust long-tail language handling, robust division-by-zero checks, and passed `/qa-qc` pipeline.                                                                              | Antigravity  | 2026-04-02 |
| T-125 | Batch 1 debt remediation completed: SQLite `RLock` swaps, silent-failure logging, tighter coverage floors, safer dependency caps, and frontend `tsc --noEmit` CI coverage.                                                                                                                           | Claude       | 2026-04-02 |
| T-124 | Add frontend smoke coverage for `projects/hanwoo-dashboard` and `projects/knowledge-dashboard` so CI validates auth, payment, and dashboard flows instead of only `lint` and `build`.                                                                                                                 | Codex        | 2026-04-02 |
| T-123 | Closed the `knowledge-dashboard` data exposure follow-up: dashboard and QA/QC payloads now come from internal `data/*.json` through authenticated API routes, the sync script uses repo-relative paths, and the internal payloads are gitignored instead of being served from `public/`.              | Codex        | 2026-04-02 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
