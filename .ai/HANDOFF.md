# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for detailed session history and `DECISIONS.md` for settled architecture decisions.

## Latest Update
| Date | 2026-04-04 |
| Tool | Codex |
| Work | **Ran the shared operator ladder after the latest `blind-to-x` work.** `workspace/scripts/doctor.py` stayed clean (`PASS=9 / WARN=0 / FAIL=0`). `workspace/scripts/quality_gate.py` still gets a green pytest run (`1233 passed / 1 skipped`) but the overall `STANDARD` gate currently **fails** on `ruff` because `workspace/scripts/migrate_to_workspace_db.py` has two placeholder-free f-strings (`F541` at lines 117 and 139). `workspace/execution/qaqc_runner.py` finished **`CONDITIONALLY_APPROVED`** with **`3511 passed / 0 failed / 0 errors / 10 skipped`**; the remaining actionable item is the security-scan finding on `projects/blind-to-x/pipeline/escalation_queue.py` (`Potential SQL injection via f-string` around `UPDATE escalation_events SET {', '.join(updates)}`), while governance is `CLEAR` and AST checks are `20/20`. |

## Previous Update
| Date | 2026-04-04 |
| Tool | Antigravity |
| Work | **Viral Escalation Engine 구현 완료 (blind-to-x).** 4-레이어 실시간 바이럴 감지 시스템 전체 구축: `spike_detector.py` (engagement velocity 추적, TTL/size eviction), `escalation_queue.py` (SQLite WAL 영속 큐, 7단계 상태머신), `express_draft.py` (60초 SLA 경량 초안, 기존 provider 체인 래핑), `escalation_runner.py` (독립 데몬, --once/--daemon/--dry-run). 기존 모듈 연동: `notification.py`에 `send_surge_alert()` 추가, `trend_monitor.py`에 velocity 메트릭 추가, `config.yaml`에 `escalation:` 블록(10 파라미터) 추가. 테스트 40/40 passed, 전체 스위트 958 passed / 0 failed 회귀 없음. |

## Previous Update
| Date | 2026-04-04 |
| Tool | Codex |
| Work | **Cleared the remaining targeted `blind-to-x` warning debt in the newly-covered scale modules.** `projects/blind-to-x/pipeline/models.py` now uses Pydantic v2 `@field_validator(..., mode="before")` instead of the deprecated v1 `@validator`, and `projects/blind-to-x/pipeline/observability.py::_is_async()` now uses `inspect.iscoroutinefunction` instead of the deprecated `asyncio.iscoroutinefunction`. Verification passed with no warnings on the targeted suites: **`48 passed`** for `projects/blind-to-x/tests/unit/test_observability_and_task_queue.py` and **`20 passed`** across `test_db_backend.py`, `test_task_queue.py`, and `test_cost_db_pg.py`, plus `py_compile` on both patched modules. |

## Previous Update
| Date | 2026-04-04 |
| Tool | Codex |
| Work | **Closed the remaining focused `blind-to-x` scale-module test gap locally.** Earlier in the session `projects/blind-to-x/tests/unit/test_task_queue.py` and `test_cost_db_pg.py` were added for the queue and PostgreSQL backends; this follow-up adds `projects/blind-to-x/tests/unit/test_db_backend.py` for `RedisCacheBackend`, `DistributedRateLimiter`, `DistributedLock`, and the cache/rate-limit factories using stubbed Redis clients, while also validating the existing local WIP file `projects/blind-to-x/tests/unit/test_observability_and_task_queue.py` (`48 passed`) so `observability.py` is already exercised without duplicating it. Targeted verification now passes for **`test_task_queue.py` (`4 passed`)**, **`test_cost_db_pg.py` (`10 passed`)**, **`test_db_backend.py` (`6 passed`)**, and **`test_observability_and_task_queue.py` (`48 passed`)**. Remaining note: `pipeline.models` still emits a Pydantic V1 `@validator` warning, and `pipeline/observability.py` emits an `asyncio.iscoroutinefunction` deprecation warning that should be migrated to `inspect.iscoroutinefunction` before Python 3.16. |

## Previous Update
| Date | 2026-04-03 |
| Tool | Codex |
| Work | **Closed the 2026-04-03 QC regressions and refreshed the focused gates.** `workspace/execution/scheduler_engine.py` is sync-compatible again (`run_task()`, `run_due_tasks()`, `_execute_subprocess()`) and no longer skips DB schema init after `DB_PATH` changes, which brought `workspace/scripts/quality_gate.py` back to **pass** (`1233 passed / 1 skipped`). In `projects/blind-to-x`, `pipeline/process_stages/fetch_stage.py` again falls back to `scrape_post()`, `pipeline/draft_prompts.py` now guards `newsletter_block`, and `pipeline/image_generator.py` generic prompts once again include topic scenes such as `Korean office workers...`, which cleared the last integration failure. `workspace/execution/qaqc_runner.py --project blind-to-x` now returns **`APPROVED`** (`873 passed / 0 failed / 0 errors / 9 skipped`) after the Windows relative-path fix. Full all-project DEEP QC was not rerun in this session. |

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

| Tool | Status | Summary of Results | Next Priorities |
| :--- | :--- | :--- | :--- |
| **Codex** | **STABLE** | `FAST` is green, root pytest inside `STANDARD` is green (`1233 passed / 1 skipped`), and `DEEP` is `CONDITIONALLY_APPROVED` (`3511 passed / 0 failed / 0 errors / 10 skipped`), but the current local `STANDARD` gate is blocked by a `ruff` `F541` lint failure in `workspace/scripts/migrate_to_workspace_db.py`. | T-139 STANDARD lint fix, T-140 escalation-queue security triage, T-120 dependency gap, T-128 isolation bug, T-129 scale hardening, T-100 coverage. |

- `T-133`: `scheduler_engine.py` sync contract is restored; no `_DB_INITIALIZED` short-circuit issues.
- `T-134`: `blind-to-x` regressions (scraper and newsletter guards) are fixed and verified via targeted tests.
- `T-135`: `qaqc_runner.py` discovery logic on Windows is confirmed to work from both root and project subdirectories.
- `projects/knowledge-dashboard` now serves internal dashboard + QA/QC data from `data/*.json` through `src/app/api/data/*`.
- `projects/knowledge-dashboard/public/dashboard_data.json` and `projects/knowledge-dashboard/public/qaqc_result.json` are removed from the delivery path.
- `projects/knowledge-dashboard/scripts/sync_data.py` now resolves repo-relative paths for `data/`, `.ai/SESSION_LOG.md`, and `workspace/execution/qaqc_history_db.py`.
- `projects/knowledge-dashboard` analytics run through `src/lib/dashboard-insights.ts`, which buckets sparse/missing language metadata, computes diversity and coverage metrics, derives a weighted health score, emits recommendation cards for the chart UI, and treats large `Unspecified` language buckets as metadata gaps instead of stack concentration.
- `projects/knowledge-dashboard` browser auth now goes through `src/app/api/auth/session/route.ts` plus `src/lib/dashboard-auth.ts`; the UI exchanges `DASHBOARD_API_KEY` for a signed `httpOnly` session cookie instead of persisting the raw key in `localStorage`.
- `projects/knowledge-dashboard/src/app/page.tsx` validates authenticated route payload shapes before calling `setData`, keeps QA/QC payload failures non-fatal, and renders a dedicated load-error state for non-auth failures.
- `projects/knowledge-dashboard` now has local node tests for `src/lib/dashboard-insights.ts`, and the project smoke script verifies unauthorized requests plus session-cookie success paths against `/api/data/*`.
- `projects/blind-to-x/tests/unit/test_task_queue.py` now covers local queue ordering/progress, exception-to-`None` handling, Celery fallback, and singleton fallback when Celery boot fails.
- `projects/blind-to-x/tests/unit/test_cost_db_pg.py` now covers `PostgresCostDatabase.record_draft()` update/insert branching, `get_today_summary()` aggregation + zero fallback, and `get_circuit_skip_hours()` threshold mapping using stubbed DB connections instead of a live PostgreSQL instance.
- `projects/blind-to-x/tests/unit/test_db_backend.py` now covers `RedisCacheBackend` JSON/raw handling, scan-based clear behavior, `DistributedRateLimiter` script/fail-open logic, `DistributedLock` acquire/release, and the Redis-backed factory fallbacks using stub clients.
- `projects/blind-to-x/tests/unit/test_observability_and_task_queue.py` already exists locally as adjacent WIP and currently passes (`48 passed`), so `observability.py` has local coverage even though this file is still untracked.
- `projects/blind-to-x/pipeline/models.py` warning cleanup is now landed: the shared models use Pydantic v2 `field_validator`, so the earlier V1 validator deprecation warning is gone from the focused suite.
- `projects/blind-to-x/pipeline/observability.py::_is_async()` now uses `inspect.iscoroutinefunction`, so the earlier Python 3.14+ deprecation warning is gone from the focused suite.
- `workspace/scripts/migrate_to_workspace_db.py` currently blocks `workspace/scripts/quality_gate.py` on two trivial `ruff` `F541` findings because lines 117 and 139 use f-strings without placeholders.
- `workspace/execution/qaqc_runner.py` currently ends `CONDITIONALLY_APPROVED` rather than `APPROVED` because the security scan still flags an actionable `Potential SQL injection via f-string` in `projects/blind-to-x/pipeline/escalation_queue.py` around `UPDATE escalation_events SET {', '.join(updates)}`.
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
- `venv\Scripts\python.exe -X utf8 workspace\scripts\quality_gate.py` -> **pass** (`1233 passed / 1 skipped`)
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_scheduler_engine.py -q --tb=short -o addopts=` -> **71 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_qaqc_runner.py workspace\tests\test_qaqc_runner_extended.py -q --tb=short -o addopts=` -> **32 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_cost_controls.py::test_review_only_still_generates_image_and_records_draft projects\blind-to-x\tests\integration\test_p0_enhancements.py::test_build_prompt_has_yaml_system_role -q --tb=short -o addopts=` -> **2 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_cost_controls.py projects\blind-to-x\tests\integration\test_p0_enhancements.py -q --tb=short -o addopts=` -> **18 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_image_generator.py -q --tb=short -o addopts=` -> **47 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\integration\test_p2_enhancements.py -q --tb=short -o addopts=` -> **6 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_task_queue.py -q --tb=short -o addopts=` -> **4 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_cost_db_pg.py -q --tb=short -o addopts=` -> **10 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_db_backend.py -q --tb=short -o addopts=` -> **6 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_observability_and_task_queue.py -q --tb=short -o addopts=` -> **48 passed**
- `venv\Scripts\python.exe -X utf8 -m py_compile projects\blind-to-x\pipeline\models.py projects\blind-to-x\pipeline\observability.py` -> **pass**
- `venv\Scripts\python.exe -X utf8 -m pytest projects\blind-to-x\tests\unit\test_db_backend.py projects\blind-to-x\tests\unit\test_task_queue.py projects\blind-to-x\tests\unit\test_cost_db_pg.py -q --tb=short -o addopts=` -> **20 passed**
- `venv\Scripts\python.exe -X utf8 workspace\scripts\doctor.py` -> **pass** (`PASS=9 / WARN=0 / FAIL=0`)
- `venv\Scripts\python.exe -X utf8 workspace\scripts\quality_gate.py` -> **fail** (`ruff` `F541` at `workspace/scripts/migrate_to_workspace_db.py:117` and `:139`; pytest still **1233 passed / 1 skipped**)
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`CONDITIONALLY_APPROVED`** / `3511 passed / 0 failed / 0 errors / 10 skipped` / security actionable issue in `projects/blind-to-x/pipeline/escalation_queue.py`
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py --project blind-to-x` -> **`APPROVED`** / `873 passed / 0 failed / 0 errors / 9 skipped`
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

1. Fix `T-139`: clear the `ruff` `F541` lint failure in `workspace/scripts/migrate_to_workspace_db.py` so `workspace/scripts/quality_gate.py` returns green again.
2. Fix or triage `T-140`: resolve the actionable SQL-injection-style security finding in `projects/blind-to-x/pipeline/escalation_queue.py` so `workspace/execution/qaqc_runner.py` can move from `CONDITIONALLY_APPROVED` to `APPROVED`.
3. Fix `T-120`: `workspace/tests/test_auto_schedule_paths.py::test_n8n_bridge_defaults_use_canonical_paths` still fails with `ModuleNotFoundError: No module named 'fastapi'`.
4. Fix `T-128`: isolate `test_cost_tracker_uses_persisted_daily_totals` and close the remaining cross-test interference thread.
5. Continue `T-129`: scale-harden `hanwoo-dashboard` before higher traffic lands by validating real DB indexes, introducing cached read models, and splitting the remaining `DashboardClient` / `actions.js` hubs.

## Notes

- Keep `projects/knowledge-dashboard/data/*.json` internal-only; they are now gitignored and should not move back under `public/`.
- `projects/knowledge-dashboard` still accepts a bearer header on `/api/data/*` for deterministic smoke/ops callers, but browser access should go through the signed session cookie path.
- `workspace/tests/test_frontends.py` exists as a parallel untracked smoke-test approach from another tool; it was not wired into CI in this session, so treat it as adjacent WIP rather than part of the tracked frontend-smoke path.
- On Windows, prefer `workspace/execution/health_check.py` for targeted environment diagnosis because it forces UTF-8 console output.
- `coverage run` remains the reliable measurement path for `shorts-maker-v2`; `pytest-cov` can still misbehave with duplicate root/project paths on this machine.
- `CostDatabase._connect()` is still a live compatibility surface in `projects/blind-to-x`; do not remove it just because `_conn()` exists.
- Do not flip `workspace/execution/scheduler_engine.py` public entrypoints to async without a compatibility wrapper; the Streamlit dashboard and many root tests still call `run_task()` / `run_due_tasks()` synchronously.
- When adding project-local pytest runs to `workspace/execution/qaqc_runner.py`, keep paths relative to that run's `cwd` on Windows or pytest can collect nothing while still returning success.
- Scale-review evidence worth carrying forward:
- `projects/hanwoo-dashboard/src/app/page.js` now batches initial dashboard reads with `Promise.all`, but it still aggregates many concerns in a single page-level load.
- `projects/hanwoo-dashboard/src/lib/actions.js` still relies on full-list reads plus `revalidatePath('/')` for most mutations.
- Post-build chunk listing showed a largest emitted chunk of about `868 KB` in `hanwoo-dashboard` and about `516 KB` in `knowledge-dashboard`, so bundle partitioning remains a live performance concern.
- `npm run db:verify-indexes -- --skip-explain` is currently expected to stop early with a placeholder warning until the real pooled Postgres URL is supplied in `projects/hanwoo-dashboard/.env`.
- Immediate `T-129` follow-up should wire the home summary path plus the remaining market/notification read surfaces to the new cache/read-model helpers before tackling the larger route split.
