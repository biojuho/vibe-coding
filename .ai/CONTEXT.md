# Vibe Coding Context

> Local-only workspace. Do not push, pull, or deploy from this repo unless the user explicitly changes that policy.

## Workspace Summary

- Name: `Vibe Coding (Joolife)`
- Purpose: shared AI tooling plus multiple product projects
- Root runtime: Python 3.14, `pytest`, `ruff`, `venv`, `.env`
- Canonical path contract:
  - `workspace/...` for root-owned automation and docs
  - `projects/<name>/...` for product repos
  - `infrastructure/...` for MCP/services

## Active Projects

| Project | Status | Stack | Canonical Path |
|---|---|---|---|
| `blind-to-x` | Active | Python pipeline, Notion, Cloudinary | `projects/blind-to-x` |
| `shorts-maker-v2` | Active | Python, MoviePy, Edge TTS, OpenAI, Google GenAI, Pillow | `projects/shorts-maker-v2` |
| `hanwoo-dashboard` | Active | Next.js, React, Prisma, Tailwind | `projects/hanwoo-dashboard` |
| `knowledge-dashboard` | Maintenance | Next.js, TypeScript, Tailwind | `projects/knowledge-dashboard` |
| `suika-game-v2` | Frozen | Vite, Vanilla JS, Matter.js | `projects/suika-game-v2` |
| `word-chain` | Frozen | React, Vite, Tailwind | `projects/word-chain` |

## Canonical Structure

```text
Vibe coding/
├── .ai/
├── .agents/
├── .claude/
├── .github/
├── .tmp/
├── _archive/
├── infrastructure/
├── projects/
│   ├── blind-to-x/
│   ├── hanwoo-dashboard/
│   ├── knowledge-dashboard/
│   ├── shorts-maker-v2/
│   ├── suika-game-v2/
│   └── word-chain/
├── workspace/
│   ├── directives/
│   ├── execution/
│   │   └── pages/
│   ├── scripts/
│   └── tests/
└── venv/
```

## Current State

> ⚠️ [상태 이전 및 분리 알림]
> - 매일 변동되는 작업 상태(진행 중인 이슈, 테스트 커버리지)
> - 일시적인 버그나 회피 패턴(Minefield)
> - 최신 품질 및 배포 로그 (Quality Notes)
> 
> 해당 내용들은 이제 토큰 최적화를 위해 **`.ai/STATUS.md`** 파일에서 관리됩니다.
> (※ 관련결정사항: [ADR-018 in DECISIONS.md])
> 최근 `blind-to-x` staged-pipeline cleanup 상태(`T-091`, 2026-03-30)도 `STATUS.md`와 `HANDOFF.md`를 우선 참조하세요.

## Shared Services

- MCP servers are configured via `.mcp.json` and related files at repo root.
- Telegram bot and other external providers use root `.env`.
- Shared operator ladder on `2026-03-31`: `workspace/scripts/doctor.py` = `FAST` readiness, `workspace/scripts/quality_gate.py` = `STANDARD` local validation, `workspace/execution/qaqc_runner.py` = `DEEP` shared approval, and `workspace/execution/health_check.py` = `DIAGNOSTIC` drill-down. `workspace/directives/operator_workflow.md` is the canonical guide.
- Shared control-plane health is checked through `workspace/execution/health_check.py`, with governance-specific validation implemented in `workspace/execution/governance_checks.py` and surfaced in `workspace/execution/qaqc_runner.py`.
- `.github/workflows/full-test-matrix.yml` and `.github/workflows/root-quality-gate.yml` were realigned on `2026-04-01` to the live repo layout: workspace checks come from `workspace/`, Python project jobs run from `projects/blind-to-x` and `projects/shorts-maker-v2`, and frontend jobs run from `projects/hanwoo-dashboard` plus `projects/knowledge-dashboard`.
- `workspace/execution/vibe_debt_auditor.py` now walks all parent `tests/` directories when estimating `test_gap`, which avoids false positives for modules under `workspace/execution/**` whose matching tests live in `workspace/tests/`.
- `workspace/execution/repo_map.py` and `workspace/execution/context_selector.py` now provide deterministic repo-map scoring plus budgeted context selection for `workspace/execution/graph_engine.py`. Repo-map summaries are persisted in `.tmp/repo_map_cache.db` so unchanged files can be reused across builder instances. The selector defaults to `workspace/` unless a prompt explicitly targets `projects/` or `infrastructure/`.
- `workspace/execution/pr_triage_worktree.py` now provides a local-only PR-style isolation primitive: it creates disposable linked worktrees under `.tmp/pr_triage_worktrees/`, records `manifest.json` plus `conflict-state.json`, and avoids implicit remote GitHub side effects.
- `workspace/execution/pr_triage_orchestrator.py` now wraps that isolation helper with repo-specific validation profiles, per-command logs, and a durable `triage-report.json` artifact while defaulting to cleanup that removes only the linked worktree and keeps the session folder for review.
- `infrastructure/` remains top-level and is not part of `workspace/`.
- The active audit-owned coverage follow-up is still `T-100`: `projects/blind-to-x` improved to **71%** on `2026-03-31`, while `projects/shorts-maker-v2` remains above its floor at **91%**.
- `projects/shorts-maker-v2` has a dual package shape: repo-root `shorts_maker_v2/` is a namespace bridge in front of `src/shorts_maker_v2/`. Tests import the bridge first, so package-level exports like `run_cli` must be kept aligned there.
- `projects/blind-to-x/pipeline/draft_cache.py` now applies SQLite `busy_timeout` plus a best-effort WAL checkpoint after commit so cached draft writes are more visible to fresh connections in follow-up reads. `T-119` is closed in the current worktree after sequential reruns.
- The old `T-116` root import-pollution blocker is now historical context: the later shared QA/QC artifact is `APPROVED`, so the `path_contract` pollution issue is no longer an active blocker.
- A new local-only follow-up `T-121` tracks `projects/blind-to-x/tests/unit/test_main.py` hitting `KeyboardInterrupt` under the current terminal wrapper. Treat it as a harness/verification issue until a clean reproduction proves a product regression.
- `projects/hanwoo-dashboard` auth/payment boundaries were hardened on `2026-04-01`: `src/lib/auth-guard.js` is the shared server-side gate, `src/proxy.js` now re-exports `auth` as the Next.js 16 proxy surface, and the dashboard/admin/subscription pages plus all exported server actions/payment APIs now require an authenticated session.
- `projects/hanwoo-dashboard` subscription flow now uses `src/lib/subscription.js` helpers plus `src/app/api/payments/prepare/route.js` for server-issued order data. `src/app/api/payments/confirm/route.js` validates session ownership through `customerKey`, re-checks the premium amount, verifies Toss confirmation, and transactionally upserts `PaymentLog` plus `Subscription`.
- Latest `hanwoo-dashboard` verification on `2026-04-01`: `npm run lint` passes with only the existing `@next/next/no-page-custom-font` warning in `src/app/layout.js`, and `npm run build` passes after the auth/payment refactor.
- A targeted vibe-coding architecture audit on `2026-04-02` confirmed there is no immediate build-breaking hallucinated import in `projects/hanwoo-dashboard` (`npm run lint` and `npm run build` both pass), but it also confirmed a monolithic `src/components/DashboardClient.js` (667 lines) and `src/lib/actions.js` (682 lines), duplicate client-side fetches for notifications and market prices, and broad `router.refresh()` / `revalidatePath('/')` coupling that will make changes cascade easily.
- The same audit found documentation/dependency drift in `projects/hanwoo-dashboard`: `README.md` still claims `Next.js 14` + `SQLite`, while the live app runs `Next.js 16.2.1` with Postgres/Prisma; `npm audit --omit=dev` reports a high-severity `lodash@4.17.23` issue via `recharts`; and the custom Google font `<link>` tags in `src/app/layout.js` should be replaced with `next/font` per current Next.js guidance.
- `T-132` landed on `2026-04-02`: `src/app/page.js` now batches initial dashboard reads with `Promise.all`, `src/lib/notifications.js` derives alert cards from the in-memory cattle list, `src/components/widgets/MarketPriceWidget.js` and `src/components/widgets/NotificationWidget.js` reuse server-provided data instead of doing a redundant first-render fetch, `src/app/layout.js` now uses `next/font`, README docs now match the live stack, and `npm audit --omit=dev` is clean with `lodash@4.18.1`.
- Frontend smoke coverage now exists on `2026-04-02`: `projects/hanwoo-dashboard/scripts/smoke.mjs` checks login redirects plus unauthenticated payment API rejection, `projects/knowledge-dashboard/scripts/smoke.mjs` checks the API-key gate plus authenticated internal data routes, both apps expose `npm run smoke`, and `.github/workflows/full-test-matrix.yml` runs that smoke step in the frontend matrix job.
- `docs/designs/2026-04-02-hanwoo-dashboard-scale-hardening-design.md` now exists as the actionable week-1 design package for `T-129` scale hardening on `projects/hanwoo-dashboard`.
- `projects/hanwoo-dashboard/scripts/verify-db-indexes.mjs` now exists for `T-129` Day 1: it uses the existing Prisma stack to inventory `pg_indexes`, compare live coverage against schema and scale-hardening expectations, print missing `CREATE INDEX CONCURRENTLY` statements, and run targeted `EXPLAIN (ANALYZE, BUFFERS)` probes.
- `projects/hanwoo-dashboard/prisma/manual/2026-04-02_scale_index_backfill.sql` is the first-pass manual concurrent-index draft. It is intentionally outside `prisma/migrations/` because the live DB diff still needs to be verified first and the current `.env` keeps `DATABASE_URL` on a placeholder password.
- `projects/hanwoo-dashboard` now has Redis/BullMQ foundation code on `2026-04-02`: `src/lib/redis.js` separates cache connections from queue connections, `src/lib/queue.js` exposes named BullMQ queues with default retries/backoff, and the project now depends on `bullmq` plus `ioredis`.
- `projects/hanwoo-dashboard/prisma/schema.prisma` now declares `OutboxStatus`, `OutboxEvent`, `DashboardSnapshot`, `NotificationSummary`, and `MarketPriceSnapshot`, with a companion SQL draft at `projects/hanwoo-dashboard/prisma/manual/2026-04-02_read_models.sql`.
- `projects/hanwoo-dashboard/src/lib/dashboard/cache.js`, `src/lib/dashboard/events.js`, and `src/lib/dashboard/read-models.js` now provide the initial cache-key, outbox, and read-model abstraction layer that future routes/actions should consume instead of direct full-table scans.
- `projects/knowledge-dashboard` now treats dashboard + QA/QC payloads as internal data on `2026-04-02`: `src/app/api/data/dashboard/route.ts` and `src/app/api/data/qaqc/route.ts` serve `data/*.json`, the public JSON payloads were removed, `scripts/sync_data.py` now uses repo-relative `data/` and `.ai/SESSION_LOG.md` paths, and `.gitignore` ignores `data/*.json`.
- `projects/knowledge-dashboard` analytics were upgraded again on `2026-04-02`: `src/lib/dashboard-insights.ts` now computes search-aware diversity, dominant-language share, notebook coverage, median depth, a weighted health score, and recommendation cards, while `src/components/DashboardCharts.tsx` uses those derived metrics instead of inline ad-hoc chart math.
- `projects/knowledge-dashboard` browser auth was tightened again on `2026-04-02`: `src/app/api/auth/session/route.ts` exchanges `DASHBOARD_API_KEY` for a signed `httpOnly` session cookie backed by `src/lib/dashboard-auth.ts`, `src/app/page.tsx` validates authenticated route payload shapes before storing dashboard state, keeps QA/QC route failures non-fatal, and separates auth errors from generic data-load failures in the UI. `src/lib/dashboard-insights.ts` also treats large `Unspecified` language buckets as metadata gaps instead of a dominant stack.
- `projects/knowledge-dashboard` now has local node coverage on `src/lib/dashboard-insights.ts`, and `scripts/smoke.mjs` asserts both unauthorized API rejection and successful session-cookie access to `/api/data/*`.
- Latest `knowledge-dashboard` verification on `2026-04-02`: `python -m py_compile scripts/sync_data.py`, `npm run lint`, `npm run build`, `npm test`, and `npm run smoke` all pass.
- Roadmap-style directives are reference context by default; active execution priority is expected to come from `.ai/TASKS.md` and `.ai/HANDOFF.md`.
