# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed session history and `DECISIONS.md` for settled architecture decisions.

## Latest Update
| Date | 2026-04-02 |
| Tool | Codex |
| Work | **Architectural/vibe-coding audit completed for `hanwoo-dashboard`.** Local verification shows `npm run lint` and `npm run build` still pass, so there is no immediate build-breaking hallucinated import/library issue, but the review found a monolithic `DashboardClient` + `actions.js` pair, duplicate client-side fetch paths for notifications/market data, broad `router.refresh()` / `revalidatePath('/')` coupling, stale README stack claims (`Next.js 14` + `SQLite` vs the live `Next.js 16.2.1` + Postgres/Prisma stack), and `npm audit --omit=dev` still reports a high-severity `lodash@4.17.23` advisory via `recharts`. Official-doc cross-check also confirmed that `src/proxy.js` matches the current Next.js 16 Proxy surface, while the custom font `<link>` tags in `src/app/layout.js` should move to `next/font`. |

## Previous Update
| Date | 2026-04-02 |
| Tool | Codex |
| Work | **`T-129` foundation code now exists in `hanwoo-dashboard`.** Added `bullmq` + `ioredis`, `src/lib/redis.js`, `src/lib/queue.js`, `src/lib/dashboard/cache.js`, `src/lib/dashboard/events.js`, and `src/lib/dashboard/read-models.js`. Prisma now declares `OutboxEvent`, `DashboardSnapshot`, `NotificationSummary`, and `MarketPriceSnapshot`, with matching draft SQL in `projects/hanwoo-dashboard/prisma/manual/2026-04-02_read_models.sql`. Verification passed for `npm run db:generate`, `npx prisma validate`, targeted ESLint on the new helper files, and direct Node imports for the Redis/BullMQ surfaces. Current blocker remains the placeholder `DATABASE_URL`, so live DB index inventory / `EXPLAIN` is still pending. |

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

- Shared workspace QA/QC has a later approved baseline on `2026-04-01`: `3066 passed / 0 failed / 0 errors / 29 skipped`.
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
- `projects/hanwoo-dashboard` still has a review-confirmed vibe-coding debt cluster on `2026-04-02`: `src/app/page.js` does 8 serial reads, `src/components/DashboardClient.js` (667 lines) and `src/lib/actions.js` (682 lines) form a high-coupling hub, notifications/market widgets refetch data from client `useEffect`, and the README still describes `Next.js 14` + `SQLite` even though the live stack is `Next.js 16.2.1` + Postgres/Prisma.
- `src/proxy.js` and `src/auth.js` are aligned with current Next.js 16/Auth.js guidance, so the clearest official-doc drift is the manual font-loading pattern in `src/app/layout.js` plus the stale README/dependency story, not the auth/proxy surface.
- `projects/blind-to-x` still has unrelated user/WIP changes; avoid touching that tree unless the user explicitly redirects the session.

## Verification Highlights

- `python -m py_compile projects/knowledge-dashboard/scripts/sync_data.py` -> **pass**
- `npm run smoke` (`projects/knowledge-dashboard`) -> **pass**
- `npm run smoke` (`projects/hanwoo-dashboard`) -> **pass**
- `npm run lint` (`projects/hanwoo-dashboard`) -> **pass** with the existing `@next/next/no-page-custom-font` warning in `src/app/layout.js`
- `npm run build` (`projects/hanwoo-dashboard`) -> **pass** on `Next.js 16.2.1`
- `npm audit --omit=dev` (`projects/hanwoo-dashboard`) -> **1 high** (`lodash@4.17.23` via `recharts`)
- `npm run lint` (`projects/knowledge-dashboard`) -> **pass**
- `npm run build` (`projects/knowledge-dashboard`) -> **pass**
- `npm test` (`projects/knowledge-dashboard`) -> **pass** (3 insight-engine tests)
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`APPROVED`** / `3066 passed / 0 failed / 0 errors / 29 skipped`
- `venv\Scripts\python.exe -X utf8 -m pytest workspace/tests/test_shorts_manager_helpers.py workspace/tests/test_topic_auto_generator.py workspace/tests/test_vibe_debt_auditor.py -q --tb=short -o addopts= --maxfail=10` -> **68 passed**

## Next Priorities

1. Fix `T-120`: `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` still fails with `ModuleNotFoundError: No module named 'fastapi'`.
2. Investigate `T-121`: determine whether `projects/blind-to-x/tests/unit/test_main.py` interruptions are a terminal-wrapper artifact or a real regression.
3. Continue the remaining audit follow-up `T-100` for `blind-to-x` coverage.
4. Review `T-129`: scale-harden `hanwoo-dashboard` before higher traffic lands by validating real DB indexes, introducing cached read models, and splitting the monolithic dashboard client.
5. Pick up `T-132`: clean up the review-confirmed vibe-coding drift in `hanwoo-dashboard` (duplicate widget fetches, manual font links, stale README stack docs, vulnerable lodash path).

## Notes

- Keep `projects/knowledge-dashboard/data/*.json` internal-only; they are now gitignored and should not move back under `public/`.
- `projects/knowledge-dashboard` still accepts a bearer header on `/api/data/*` for deterministic smoke/ops callers, but browser access should go through the signed session cookie path.
- `workspace/tests/test_frontends.py` exists as a parallel untracked smoke-test approach from another tool; it was not wired into CI in this session, so treat it as adjacent WIP rather than part of the tracked frontend-smoke path.
- On Windows, prefer `workspace/execution/health_check.py` for targeted environment diagnosis because it forces UTF-8 console output.
- `coverage run` remains the reliable measurement path for `shorts-maker-v2`; `pytest-cov` can still misbehave with duplicate root/project paths on this machine.
- `CostDatabase._connect()` is still a live compatibility surface in `projects/blind-to-x`; do not remove it just because `_conn()` exists.
- Scale-review evidence worth carrying forward:
- `projects/hanwoo-dashboard/src/app/page.js` still performs 8 serial dashboard reads on every dynamic request.
- `projects/hanwoo-dashboard/src/lib/actions.js` still relies on full-list reads plus `revalidatePath('/')` for most mutations.
- Post-build chunk listing showed a largest emitted chunk of about `868 KB` in `hanwoo-dashboard` and about `516 KB` in `knowledge-dashboard`, so bundle partitioning remains a live performance concern.
- `npm run db:verify-indexes -- --skip-explain` is currently expected to stop early with a placeholder warning until the real pooled Postgres URL is supplied in `projects/hanwoo-dashboard/.env`.
- Immediate `T-129` follow-up should wire `getNotifications()`, `getRealTimeMarketPrice()`, and the home summary path to the new cache/read-model helpers before tackling the larger route split.
