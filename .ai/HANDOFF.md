# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed session history and `DECISIONS.md` for settled architecture decisions.

## Latest Update
| Date | 2026-04-03 |
| Tool | Codex |
| Work | **System QC completed and the shared gate is now `REJECTED` again.** `workspace/scripts/doctor.py` still passes, but `workspace/scripts/quality_gate.py` now fails with **46 root failures** concentrated in `workspace/tests/test_scheduler_engine.py` after `workspace/execution/scheduler_engine.py` switched its public task runners to async and memoized DB initialization across `DB_PATH` changes. `workspace/execution/qaqc_runner.py` also returns **`REJECTED`** (`2471 passed / 46 failed / 1 errors / 1 skipped`), and targeted reruns confirmed two live `blind-to-x` regressions: `pipeline/process_stages/fetch_stage.py` now assumes `scrape_post_with_retry()` exists, and `pipeline/draft_prompts.py` interpolates `newsletter_block` even when `newsletter` output was not requested. Separately, the DEEP runner currently under-exercises `blind-to-x` because it launches pytest from the project root while passing absolute test paths, which can exit `0` with no collected output on this Windows setup. |

## Previous Update
| Date | 2026-04-02 |
| Tool | Codex |
| Work | **`T-132` is now implemented in `hanwoo-dashboard`.** The dashboard page now batches its initial reads with `Promise.all`, notifications are derived from the in-memory cattle list instead of a second client-side fetch, the market widget reuses server-provided initial data on first render, `src/app/layout.js` now uses `next/font` instead of manual Google font links, README stack/docs now match the live Next.js 16 + PostgreSQL setup, and the `lodash` override now resolves to `4.18.1` so `npm audit --omit=dev` is clean. Verification passed for `npm install`, `npm run lint`, `npm run build`, `npm audit --omit=dev`, and `npm ls lodash --depth=2`. |

## Previous Update
| Date | 2026-04-02 |
| Tool | Codex |
| Work | **Architectural/vibe-coding audit completed for `hanwoo-dashboard`.** Local verification showed `npm run lint` and `npm run build` still passed, so there was no immediate build-breaking hallucinated import/library issue, but the review found a monolithic `DashboardClient` + `actions.js` pair, duplicate client-side fetch paths for notifications/market data, broad `router.refresh()` / `revalidatePath('/')` coupling, stale README stack claims (`Next.js 14` + `SQLite` vs the live `Next.js 16.2.1` + Postgres/Prisma stack), and a high-severity `lodash@4.17.23` advisory via `recharts`. |

## Previous Update

| Date | 2026-04-02 |
| Tool | Antigravity |
| Work | **100x Scalability Phase 3-6 완료 + QC APPROVED.** `cost_db_pg.py` (PostgreSQL 연결 풀 2..10), `task_queue.py` (Celery 분산 큐 + LocalSemaphore 폴백), `observability.py` (OpenTelemetry 10 메트릭 + No-op 폴백) 생성. QC에서 4건 발견 (A-6 close 누락, A-3 SCAN 무한루프, A-8 walrus, A-7 싱글톤 리셋) → 전수 수정. 41 tests passed / 0 failed. |

## Previous Update

| Date | 2026-04-02 |
| Tool | Codex |
| Work | **`T-129` now has executable DB-audit tooling.** Added `projects/hanwoo-dashboard/scripts/verify-db-indexes.mjs`, wired `npm run db:verify-indexes`, and drafted `projects/hanwoo-dashboard/prisma/manual/2026-04-02_scale_index_backfill.sql`. The script inventories live indexes, checks schema-vs-live coverage, prints missing `CREATE INDEX CONCURRENTLY` statements, and runs `EXPLAIN` probes once a real `DATABASE_URL` is available. Current blocker: `projects/hanwoo-dashboard/.env` still contains the Supabase placeholder password, so live inventory / plan capture could not be completed yet. |

## Previous Update

| Date | 2026-04-02 |
| Tool | Claude |
| Work | **QC 3라운드 → 전 영역 0 failed APPROVED.** 회귀 5건 수정: ① `governance_checks.py` backtick 파싱 + `INDEX.md` `_ci_*` 4개 등록. ② `test_notion_shorts_sync` `_conn()` context manager 수정. ③ `test_frontends` `_kill_stale_nextjs_server()` 추가 (Next.js lock PID 자동 정리). ④ `media_step` `visual_primary` failure 기록 추가. ⑤ `_last_video_primary_failed` 플래그로 비용 다운그레이드 vs 실제 실패 분기. 최종: workspace 1210 / blind-to-x 810 / shorts-maker-v2 1282 — 전부 passed. |

## Previous Update

| Date | 2026-04-02 |
| Tool | Claude |
| Work | **Production-ready 코드 리뷰 + QC 완료.** `content_db._conn()` @contextmanager 전환으로 연결 누수 해소, quality_gate STANDARD PASS. 최종 **1233 passed / ruff All checks / 0 high severity**. |


## Recent Completed

- `T-128` (`2026-04-02`, Claude): `content_db._conn()` @contextmanager 전환으로 연결 누수 완전 해소, quality_gate STANDARD PASS.
- `T-127` (`2026-04-02`, Codex): `knowledge-dashboard` auth moved to a signed `httpOnly` session cookie, the data routes now trust `src/lib/dashboard-auth.ts`, node tests cover the insight engine, and smoke coverage verifies the new session flow.
- `T-126` (`2026-04-02`, Antigravity): `DashboardCharts.tsx` was hardened against dirty inputs (NaN/null/arrays) via query normalization, stable empty-array references, and notebook dataset capping.
- `T-125` (`2026-04-02`, Claude): batch 1 debt remediation landed across `blind-to-x`, `shorts-maker-v2`, and CI, including SQLite `RLock` swaps, silent-failure logging, tighter coverage floors, safer dependency caps, and frontend `tsc --noEmit`.
- `T-124` (`2026-04-02`, Codex): runtime smoke scripts are now wired into the frontend CI matrix for `hanwoo-dashboard` and `knowledge-dashboard`.
- `T-123` (`2026-04-02`, Codex): `knowledge-dashboard` now serves dashboard and QA/QC payloads from internal `data/*.json` via authenticated route handlers instead of `public/*.json`.
- `T-116` is now historical context, not an active blocker: the later shared QA/QC baseline is already `APPROVED`, so the old `path_contract` import-pollution issue should no longer drive planning.

## Current State

- Latest shared QA/QC attempt on `2026-04-03` is **`REJECTED`**: `2471 passed / 46 failed / 1 errors / 1 skipped`. The last approved shared baseline is still `2026-04-01`: `3066 passed / 0 failed / 0 errors / 29 skipped`.
- `workspace/execution/scheduler_engine.py` is currently a live minefield: `run_task()` / `run_due_tasks()` were changed to async without preserving the existing sync contract, `_execute_subprocess()` disappeared, and `_DB_INITIALIZED` now short-circuits schema setup across later `DB_PATH` changes, which is why `workspace/tests/test_scheduler_engine.py` now drives the 46-root-failure cluster.
- `workspace/execution/qaqc_runner.py` currently launches `blind-to-x` pytest runs from `projects/blind-to-x` while also passing absolute `tests/unit` and `tests/integration` paths. On this Windows machine that can exit `0` with no collected output, so the DEEP report can silently miss real `blind-to-x` failures unless the paths are made project-relative or the cwd changes.
- `projects/blind-to-x` now has two confirmed non-harness regressions from the latest QC pass: `pipeline/process_stages/fetch_stage.py` requires `scrape_post_with_retry()` and breaks compatibility with stub/caller implementations that only expose `scrape_post()`, and `pipeline/draft_prompts.py` interpolates `newsletter_block` even when `output_formats` excludes `newsletter`.
- `projects/knowledge-dashboard` now serves internal dashboard + QA/QC data from `data/*.json` through `src/app/api/data/*`.
- `projects/knowledge-dashboard/public/dashboard_data.json` and `projects/knowledge-dashboard/public/qaqc_result.json` are removed from the delivery path.
- `projects/knowledge-dashboard/scripts/sync_data.py` now resolves repo-relative paths for `data/`, `.ai/SESSION_LOG.md`, and `workspace/execution/qaqc_history_db.py`.
- `projects/knowledge-dashboard` analytics run through `src/lib/dashboard-insights.ts`, which buckets sparse/missing language metadata, computes diversity and coverage metrics, derives a weighted health score, emits recommendation cards for the chart UI, and treats large `Unspecified` language buckets as metadata gaps instead of stack concentration.
- `projects/knowledge-dashboard` browser auth now goes through `src/app/api/auth/session/route.ts` plus `src/lib/dashboard-auth.ts`; the UI exchanges `DASHBOARD_API_KEY` for a signed `httpOnly` session cookie instead of persisting the raw key in `localStorage`.
- `projects/knowledge-dashboard/src/app/page.tsx` validates authenticated route payload shapes before calling `setData`, keeps QA/QC payload failures non-fatal, and renders a dedicated load-error state for non-auth failures.
- `projects/knowledge-dashboard` now has local node tests for `src/lib/dashboard-insights.ts`, and the project smoke script verifies unauthorized requests plus session-cookie success paths against `/api/data/*`.
- `projects/hanwoo-dashboard` and `projects/knowledge-dashboard` both have project-local runtime smoke scripts exposed as `npm run smoke`, and the frontend matrix job runs that step after build/lint.
- `docs/designs/2026-04-02-hanwoo-dashboard-scale-hardening-design.md` now captures the actionable `T-129` week-1 scale-hardening plan for `hanwoo-dashboard`.
- `projects/hanwoo-dashboard/scripts/verify-db-indexes.mjs` now provides the Day-1 `T-129` audit path: it inventories `pg_indexes`, checks expected schema indexes, checks scale-candidate indexes, prints missing `CREATE INDEX CONCURRENTLY` statements, and runs targeted `EXPLAIN (ANALYZE, BUFFERS)` probes when the real DB URL is present.
- `projects/hanwoo-dashboard/prisma/manual/2026-04-02_scale_index_backfill.sql` now contains the first-pass concurrent index backfill draft that should be trimmed to only live-missing indexes after the audit script runs against the real database.
- `projects/hanwoo-dashboard/src/lib/redis.js` and `projects/hanwoo-dashboard/src/lib/queue.js` now establish the Redis/BullMQ foundation with cache-vs-queue connection separation, safe no-config behavior, queue names, and default retry/backoff settings.
- `projects/hanwoo-dashboard/prisma/schema.prisma` now includes `OutboxStatus`, `OutboxEvent`, `DashboardSnapshot`, `NotificationSummary`, and `MarketPriceSnapshot`, with matching generated Prisma model files under `src/generated/prisma/models/`.
- `projects/hanwoo-dashboard/src/lib/dashboard/cache.js`, `projects/hanwoo-dashboard/src/lib/dashboard/events.js`, and `projects/hanwoo-dashboard/src/lib/dashboard/read-models.js` now provide cache key builders, Redis JSON helpers, outbox CRUD helpers, and read-model persistence/cache wrappers for summary, notifications, and market prices.
- `projects/hanwoo-dashboard/prisma/manual/2026-04-02_read_models.sql` now contains the first-pass SQL draft for the outbox and read-model tables.
- `projects/hanwoo-dashboard` still has a broader scale-hardening backlog on `2026-04-02`: `src/components/DashboardClient.js` and `src/lib/actions.js` remain large coupling hubs, but the first-render duplicate fetches for notifications/market data are now removed, README stack drift is corrected, and the font/dependency drift found in the review is closed.
- `src/proxy.js` and `src/auth.js` remain aligned with current Next.js 16/Auth.js guidance, and `src/app/layout.js` now follows the recommended `next/font` path instead of manual font `<link>` tags.
- `projects/blind-to-x` still has unrelated user/WIP changes; avoid touching that tree unless the user explicitly redirects the session.

## Verification Highlights

- `venv\Scripts\python.exe -X utf8 workspace\scripts\doctor.py` -> **pass**
- `venv\Scripts\python.exe -X utf8 workspace\scripts\quality_gate.py` -> **fail** (`46` root failures, all concentrated in `workspace/tests/test_scheduler_engine.py`)
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`REJECTED`** / `2471 passed / 46 failed / 1 errors / 1 skipped`
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_scheduler_engine.py::test_execute_subprocess_success -q --tb=short -o addopts=` -> **fail** (`AttributeError: module 'execution.scheduler_engine' has no attribute '_execute_subprocess'`)
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_cost_controls.py::test_review_only_still_generates_image_and_records_draft projects\blind-to-x\tests\integration\test_p0_enhancements.py::test_build_prompt_has_yaml_system_role -q --tb=short -o addopts=` -> **2 failed**
- `python -m py_compile projects/knowledge-dashboard/scripts/sync_data.py` -> **pass**
- `npm run smoke` (`projects/knowledge-dashboard`) -> **pass**
- `npm run smoke` (`projects/hanwoo-dashboard`) -> **pass**
- `npm install` (`projects/hanwoo-dashboard`) -> **pass**
- `npm run lint` (`projects/hanwoo-dashboard`) -> **pass**
- `npm run build` (`projects/hanwoo-dashboard`) -> **pass** on `Next.js 16.2.1`
- `npm audit --omit=dev` (`projects/hanwoo-dashboard`) -> **0 vulnerabilities**
- `npm ls lodash --depth=2` (`projects/hanwoo-dashboard`) -> **`lodash@4.18.1` via `recharts@2.15.4`**
- `npm run lint` (`projects/knowledge-dashboard`) -> **pass**
- `npm run build` (`projects/knowledge-dashboard`) -> **pass**
- `npm test` (`projects/knowledge-dashboard`) -> **pass** (3 insight-engine tests)
- `venv\Scripts\python.exe -X utf8 -m pytest workspace/tests/test_shorts_manager_helpers.py workspace/tests/test_topic_auto_generator.py workspace/tests/test_vibe_debt_auditor.py -q --tb=short -o addopts= --maxfail=10` -> **68 passed**

## Next Priorities

1. Fix `T-133`: restore the stable `workspace/execution/scheduler_engine.py` contract by either wrapping the new async helpers or migrating all sync callers/tests together, and remove the `_DB_INITIALIZED` cross-db short circuit.
2. Fix `T-135`: repair `workspace/execution/qaqc_runner.py` blind-to-x test discovery so the DEEP QC pass actually exercises that project on Windows.
3. Fix `T-134`: close the two confirmed `blind-to-x` regressions in `fetch_stage.py` and `draft_prompts.py`.
4. Fix `T-120`: `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` still fails with `ModuleNotFoundError: No module named 'fastapi'`.
5. Continue `T-129`: scale-harden `hanwoo-dashboard` before higher traffic lands by validating real DB indexes, introducing cached read models, and splitting the remaining `DashboardClient` / `actions.js` hubs.

## Notes

- Keep `projects/knowledge-dashboard/data/*.json` internal-only; they are now gitignored and should not move back under `public/`.
- `projects/knowledge-dashboard` still accepts a bearer header on `/api/data/*` for deterministic smoke/ops callers, but browser access should go through the signed session cookie path.
- `workspace/tests/test_frontends.py` exists as a parallel untracked smoke-test approach from another tool; it was not wired into CI in this session, so treat it as adjacent WIP rather than part of the tracked frontend-smoke path.
- On Windows, prefer `workspace/execution/health_check.py` for targeted environment diagnosis because it forces UTF-8 console output.
- `coverage run` remains the reliable measurement path for `shorts-maker-v2`; `pytest-cov` can still misbehave with duplicate root/project paths on this machine.
- `CostDatabase._connect()` is still a live compatibility surface in `projects/blind-to-x`; do not remove it just because `_conn()` exists.
- Do not flip `workspace/execution/scheduler_engine.py` public entrypoints to async without a compatibility wrapper; the Streamlit dashboard and many root tests still call `run_task()` / `run_due_tasks()` synchronously.
- Until `T-135` lands, avoid trusting `qaqc_runner.py` blind-to-x counts at face value; the runner's exact absolute-path pytest command can return success with no output from inside `projects/blind-to-x`.
- Scale-review evidence worth carrying forward:
- `projects/hanwoo-dashboard/src/app/page.js` now batches initial dashboard reads with `Promise.all`, but it still aggregates many concerns in a single page-level load.
- `projects/hanwoo-dashboard/src/lib/actions.js` still relies on full-list reads plus `revalidatePath('/')` for most mutations.
- Post-build chunk listing showed a largest emitted chunk of about `868 KB` in `hanwoo-dashboard` and about `516 KB` in `knowledge-dashboard`, so bundle partitioning remains a live performance concern.
- `npm run db:verify-indexes -- --skip-explain` is currently expected to stop early with a placeholder warning until the real pooled Postgres URL is supplied in `projects/hanwoo-dashboard/.env`.
- Immediate `T-129` follow-up should wire the home summary path plus the remaining market/notification read surfaces to the new cache/read-model helpers before tackling the larger route split.
