# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed session history and `DECISIONS.md` for settled architecture decisions.

## Latest Update

| Date | 2026-04-02 |
| Tool | Codex |
| Work | Closed `T-124` by adding project-local runtime smoke coverage for both frontend apps. `projects/hanwoo-dashboard/scripts/smoke.mjs` now boots the built app and verifies unauthenticated redirects plus payment API rejection, `projects/knowledge-dashboard/scripts/smoke.mjs` now boots the built app and verifies the API-key gate plus authenticated internal data routes, both package.json files expose `npm run smoke`, and `.github/workflows/full-test-matrix.yml` now runs that smoke step in the frontend matrix job. |

## Recent Completed

- `T-125` (`2026-04-02`, Claude): batch 1 debt remediation landed across `blind-to-x`, `shorts-maker-v2`, and CI, including SQLite `RLock` swaps, silent-failure logging, tighter coverage floors, safer dependency caps, and frontend `tsc --noEmit`.
- `T-124` (`2026-04-02`, Codex): runtime smoke scripts are now wired into the frontend CI matrix for `hanwoo-dashboard` and `knowledge-dashboard`.
- `T-122` (`2026-04-01`, Codex): `projects/hanwoo-dashboard` auth and payment ownership now enforce real server-side trust boundaries.
- `T-116` is now historical context, not an active blocker: the later shared QA/QC baseline is already `APPROVED`, so the old `path_contract` import-pollution issue should no longer drive planning.

## Current State

- Shared workspace QA/QC has a later approved baseline on `2026-04-01`: `3066 passed / 0 failed / 0 errors / 29 skipped`.
- `projects/knowledge-dashboard` now serves internal dashboard + QA/QC data from `data/*.json` through authenticated route handlers under `src/app/api/data/*`.
- `projects/knowledge-dashboard/public/dashboard_data.json` and `projects/knowledge-dashboard/public/qaqc_result.json` are removed from the delivery path.
- `projects/knowledge-dashboard/scripts/sync_data.py` now resolves repo-relative paths for `data/`, `.ai/SESSION_LOG.md`, and `workspace/execution/qaqc_history_db.py`.
- `projects/hanwoo-dashboard` and `projects/knowledge-dashboard` now both have project-local runtime smoke scripts exposed as `npm run smoke`, and the frontend matrix job runs that step after build/lint.
- `projects/blind-to-x` still has unrelated user/WIP changes; avoid touching that tree unless the user explicitly redirects the session.

## Verification Highlights

- `python -m py_compile projects/knowledge-dashboard/scripts/sync_data.py` -> **pass**
- `npm run smoke` (`projects/knowledge-dashboard`) -> **pass**
- `npm run smoke` (`projects/hanwoo-dashboard`) -> **pass**
- `npm run lint` (`projects/hanwoo-dashboard`) -> **pass** with the existing `@next/next/no-page-custom-font` warning in `src/app/layout.js`
- `npm run lint` (`projects/knowledge-dashboard`) -> **pass**
- `npm run build` (`projects/knowledge-dashboard`) -> **pass**
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`APPROVED`** / `3066 passed / 0 failed / 0 errors / 29 skipped`
- `venv\Scripts\python.exe -X utf8 -m pytest workspace/tests/test_shorts_manager_helpers.py workspace/tests/test_topic_auto_generator.py workspace/tests/test_vibe_debt_auditor.py -q --tb=short -o addopts= --maxfail=10` -> **68 passed**

## Next Priorities

1. Fix `T-120`: `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` still fails with `ModuleNotFoundError: No module named 'fastapi'`.
2. Investigate `T-121`: determine whether `projects/blind-to-x/tests/unit/test_main.py` interruptions are a terminal-wrapper artifact or a real regression.
3. Continue the remaining audit follow-up `T-100` for `blind-to-x` coverage.

## Notes

- Keep `projects/knowledge-dashboard/data/*.json` internal-only; they are now gitignored and should not move back under `public/`.
- `workspace/tests/test_frontends.py` exists as a parallel untracked smoke-test approach from another tool; it was not wired into CI in this session, so treat it as adjacent WIP rather than part of the tracked frontend-smoke path.
- On Windows, prefer `workspace/execution/health_check.py` for targeted environment diagnosis because it forces UTF-8 console output.
- `coverage run` remains the reliable measurement path for `shorts-maker-v2`; `pytest-cov` can still misbehave with duplicate root/project paths on this machine.
- `CostDatabase._connect()` is still a live compatibility surface in `projects/blind-to-x`; do not remove it just because `_conn()` exists.
