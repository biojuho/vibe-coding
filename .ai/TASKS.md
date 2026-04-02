# TASKS - AI Kanban Board

> Read this file at session start and update it before ending the session.

## TODO

| ID    | Task                                                                                                                                                                                                                                 | Owner       | Priority | Created      |
|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|----------|--------------|
| T-121 | Investigate the local-only `KeyboardInterrupt` / runner interruption when `projects/blind-to-x/tests/unit/test_main.py` runs under this terminal wrapper, and confirm whether it is a harness artifact or a real `main.py` regression. | Codex | Medium | 2026-04-01 |
| T-100 | Raise `blind-to-x` coverage to ≥75% (shorts-maker-v2 already at 90% ✅). Current blind-to-x coverage TBD from latest run. | Claude | High | 2026-03-31 |

## IN_PROGRESS

| ID | Task | Owner | Started | Notes |
|----|------|-------|---------|-------|

## DONE (Latest 5)

| ID    | Task                                                                                                                                                                                                                                                                                                  | Completed By | Completed  |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------|
| T-124 | Add frontend smoke coverage for `projects/hanwoo-dashboard` and `projects/knowledge-dashboard` so CI validates auth, payment, and dashboard flows instead of only `lint` and `build`. | Codex | 2026-04-02 |
| T-123 | Closed the `knowledge-dashboard` data exposure follow-up: dashboard and QA/QC payloads now come from internal `data/*.json` through authenticated API routes, the sync script uses repo-relative paths, and the internal payloads are gitignored instead of being served from `public/`. | Codex | 2026-04-02 |
| T-116 | Closed the stale root QC blocker follow-up after confirming the later full shared QA/QC baseline is already `APPROVED`; the old `path_contract` import-pollution issue is now historical context, not an active blocker. | Codex | 2026-04-02 |
| T-125 | Batch 1 debt remediation completed: SQLite `RLock` swaps, silent-failure logging, tighter coverage floors, safer dependency caps, and frontend `tsc --noEmit` CI coverage. | Claude | 2026-04-02 |
| T-122 | Hardened `projects/hanwoo-dashboard` auth and payment boundaries: real server-side auth guards now protect dashboard/actions/payment routes, the proxy delegates to `Auth.js` session authorization, checkout uses a server-prepared order, and payment confirm transactionally upserts `PaymentLog` plus `Subscription`. | Codex | 2026-04-01 |

## Rules

- Use IDs in the form `T-XXX`
- Move tasks from TODO -> IN_PROGRESS when started
- Move tasks from IN_PROGRESS -> DONE when completed
- Keep only the latest 5 items in DONE
- Add newly discovered follow-up work to TODO
