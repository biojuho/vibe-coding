# Hanwoo Dashboard 100x Scale Hardening Design

## Summary

This document turns the `T-129` scale review into an implementation-ready plan for `projects/hanwoo-dashboard`.

The chosen direction is:

1. Keep Next.js as the BFF layer.
2. Move dashboard reads away from "load whole tables on every request".
3. Introduce Redis-backed cache and queue infrastructure.
4. Split the monolithic client dashboard into route-level and widget-level boundaries.
5. Add read models so summaries, notifications, and analytics are cheap to serve.

This plan is intentionally scoped for a first production hardening pass, not a full microservice rewrite.

## Goals

- Keep the existing product behavior intact for end users.
- Reduce database load on the dashboard home path by at least one order of magnitude.
- Remove full-page `router.refresh()` as the default post-mutation pattern.
- Make notification, market-price, and analytics refreshes asynchronous.
- Create a migration path that can support 100x more rows and concurrent users.

## Non-Goals

- Rewriting auth or payment again.
- Splitting the app into separate deployable services in week 1.
- Migrating every screen to a new data layer at once.

## Current Evidence

### Read Path

- `projects/hanwoo-dashboard/src/app/page.js` performs 8 serial reads on each dynamic request.
- `projects/hanwoo-dashboard/src/lib/actions.js` still contains broad `findMany()` patterns and in-process aggregations for notifications, expenses, history, diagnostics, and sales.
- `projects/knowledge-dashboard/src/app/api/data/dashboard/route.ts` reads and parses the full JSON file for every request and `src/app/page.tsx` always fetches with `cache: "no-store"`.

### Write Path

- Most mutations in `projects/hanwoo-dashboard/src/lib/actions.js` call `revalidatePath('/')`.
- `projects/hanwoo-dashboard/src/components/DashboardClient.js` then follows up with `router.refresh()` after many mutations.
- Side effects such as history writes, notifications, and data recomputation still happen on request threads.

### Frontend

- `projects/hanwoo-dashboard/src/components/DashboardClient.js` imports nearly all tabs, widgets, modals, and mutation handlers into one client boundary.
- Heavy list and analytics transforms still happen in render-facing components such as `SalesTab.js`, `AnalysisTab.js`, `FinancialChartWidget.js`, and `CattleDetailModal.js`.
- Post-build output showed a largest emitted chunk of about `868 KB` for `hanwoo-dashboard` and about `516 KB` for `knowledge-dashboard`.

### Schema / Index Risk

- `projects/hanwoo-dashboard/prisma/schema.prisma` declares several composite indexes.
- The checked-in SQL migration under `projects/hanwoo-dashboard/prisma/migrations/20260302103049_phase1_relations/migration.sql` does not contain those composite indexes.
- We should assume the live database may be missing critical indexes until verified.

## Chosen Architecture

```text
Browser
  -> Next.js app router / BFF
     -> Redis cache
     -> Postgres primary
     -> Read models (snapshot + rollups)
     -> BullMQ queue

HTTP writes
  -> DB transaction
  -> outbox event insert
  -> fast response

Worker
  -> consumes outbox / queue events
  -> refreshes dashboard snapshots
  -> refreshes notification summary
  -> refreshes market price snapshot
  -> warms Redis keys
```

## Week 1 Rollout

### Day 1: Database Verification and Safe Indexing

- Verify live indexes with `pg_indexes`.
- Run `EXPLAIN (ANALYZE, BUFFERS)` on:
  - active cattle list
  - sales list by date
  - expense list by date/category
  - cattle history by cattle and date
  - notification candidate query
- Add missing indexes using `CREATE INDEX CONCURRENTLY`.
- Add a new Prisma migration only after the live SQL diff is confirmed.

### Day 2: Read Model and Cache Foundations

- Add Redis connection helper.
- Add BullMQ queue bootstrap.
- Add `OutboxEvent`, `DashboardSnapshot`, `NotificationSummary`, and `MarketPriceSnapshot`.
- Introduce read-model helpers under `src/lib/dashboard/`.

### Day 3: Home Dashboard Decomposition

- Replace the current home page "8 serial reads" with one summary snapshot read and one paginated cattle query.
- Convert notifications and market price to cache-backed reads.
- Remove broad `revalidatePath('/')` from non-home updates where possible.

### Day 4: Client Boundary Split

- Split `DashboardClient` into route-level segments:
  - dashboard shell
  - cattle view
  - feed view
  - sales view
  - analysis view
- Lazy-load heavy widgets and charts.
- Introduce query-based invalidation instead of full refresh where the UI stays client-driven.

### Day 5: Worker Refresh and Observability

- Worker consumes write events and updates snapshots.
- Add diagnostics for:
  - cache hit rate
  - queue lag
  - snapshot age
  - slow query count
- Add smoke coverage for cache-miss and queue-processed states.

## Proposed File Layout

### New Files

- `projects/hanwoo-dashboard/src/lib/redis.js`
- `projects/hanwoo-dashboard/src/lib/queue.js`
- `projects/hanwoo-dashboard/src/lib/dashboard/cache.js`
- `projects/hanwoo-dashboard/src/lib/dashboard/queries.js`
- `projects/hanwoo-dashboard/src/lib/dashboard/read-models.js`
- `projects/hanwoo-dashboard/src/lib/dashboard/events.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/summary/route.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/cattle/route.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/notifications/route.js`
- `projects/hanwoo-dashboard/src/app/api/dashboard/sales/route.js`
- `projects/hanwoo-dashboard/scripts/dashboard-worker.mjs`

### Existing Files to Refactor

- `projects/hanwoo-dashboard/src/app/page.js`
- `projects/hanwoo-dashboard/src/components/DashboardClient.js`
- `projects/hanwoo-dashboard/src/lib/actions.js`
- `projects/hanwoo-dashboard/src/lib/kape.js`
- `projects/hanwoo-dashboard/src/components/widgets/MarketPriceWidget.js`
- `projects/hanwoo-dashboard/src/components/widgets/NotificationWidget.js`

## Read API Design

### 1. Dashboard Summary

`GET /api/dashboard/summary`

Returns:

- headcount summary
- monthly revenue/cost/profit rollup
- building occupancy summary
- current farm settings
- snapshot freshness metadata

Response target:

- under 50 ms on cache hit
- under 200 ms on cache miss

### 2. Cattle List

`GET /api/dashboard/cattle?buildingId=&penNumber=&status=&cursor=&limit=50`

Rules:

- default `limit=50`
- cursor pagination over `updatedAt, id`
- select only fields required by list view
- no embedded history payload

### 3. Notifications

`GET /api/dashboard/notifications`

Rules:

- backed by `NotificationSummary`
- worker-generated
- max 20 records returned

### 4. Sales List

`GET /api/dashboard/sales?from=&to=&cursor=&limit=50`

Rules:

- date-range constrained
- cost/profit numbers come from read model or pre-joined projection, not client-side full-array loops

## Cache Design

### Redis Keys

```text
hd:dashboard:summary:v1:{farmId}
hd:dashboard:cattle:list:v1:{farmId}:{buildingId}:{penNumber}:{status}:{cursor}:{limit}
hd:dashboard:cattle:history:v1:{cattleId}:{cursor}:{limit}
hd:dashboard:notifications:v1:{farmId}
hd:dashboard:sales:v1:{farmId}:{from}:{to}:{cursor}:{limit}
hd:market-price:latest:v1
hd:market-price:day:v1:{issueDate}
```

### Suggested TTLs

- summary: `30s`
- cattle list pages: `60s`
- cattle detail history: `120s`
- notifications: `15s`
- sales pages: `60s`
- market price latest: `3600s`

### Invalidation Rules

- `CATTLE_CREATED`, `CATTLE_UPDATED`, `CATTLE_ARCHIVED`
  - invalidate cattle list pages for affected building and global summary
  - enqueue notification summary rebuild
- `SALE_RECORDED`
  - invalidate sales pages and dashboard summary
- `EXPENSE_RECORDED`, `FEED_RECORDED`
  - invalidate summary and analysis rollups
- `FARM_SETTINGS_UPDATED`
  - invalidate summary only
- `MARKET_PRICE_REFRESHED`
  - replace `hd:market-price:latest:v1`

## Queue Design

### Recommendation

Use `BullMQ + Redis` first.

Why not Kafka in week 1:

- single application deployment today
- side effects are internal and bounded
- lower operational cost and much faster adoption

When to revisit Kafka:

- multiple independent consumers
- cross-service event contracts
- replay and partitioning become real requirements

### Job Types

```text
dashboard.snapshot.refresh
dashboard.notifications.refresh
dashboard.market-price.refresh
dashboard.cache.warm
payments.post-confirm
```

### Runtime Settings

- worker concurrency: `10` to start
- retry attempts: `5`
- backoff: exponential, base `3000ms`
- dead-letter bucket after final failure

## Database and Read Model Draft

### Prisma Draft

```prisma
enum OutboxStatus {
  PENDING
  PROCESSING
  DONE
  FAILED
}

model OutboxEvent {
  id          String       @id @default(cuid())
  topic       String
  aggregateId String?
  payload     Json
  status      OutboxStatus @default(PENDING)
  attempts    Int          @default(0)
  availableAt DateTime     @default(now())
  createdAt   DateTime     @default(now())
  updatedAt   DateTime     @updatedAt

  @@index([status, availableAt, createdAt])
  @@index([topic, createdAt])
}

model DashboardSnapshot {
  key         String   @id
  payload     Json
  version     Int      @default(1)
  generatedAt DateTime @default(now())
  staleAt     DateTime

  @@index([staleAt])
}

model NotificationSummary {
  key         String   @id
  payload     Json
  generatedAt DateTime @default(now())
}

model MarketPriceSnapshot {
  id           String   @id @default(cuid())
  issueDate    DateTime @unique
  isRealtime   Boolean  @default(false)
  bullGrade1pp Int
  bullGrade1p  Int
  bullGrade1   Int
  cowGrade1pp  Int
  cowGrade1p   Int
  cowGrade1    Int
  source       String
  fetchedAt    DateTime @default(now())

  @@index([fetchedAt])
}
```

### SQL Index Draft

```sql
create index concurrently if not exists idx_cattle_active_updated
  on "Cattle" ("isArchived", "updatedAt" desc);

create index concurrently if not exists idx_cattle_building_pen_active
  on "Cattle" ("buildingId", "penNumber", "updatedAt" desc)
  where "isArchived" = false;

create index concurrently if not exists idx_cattle_status_estrus
  on "Cattle" ("status", "lastEstrus")
  where "isArchived" = false;

create index concurrently if not exists idx_cattle_status_pregnancy
  on "Cattle" ("status", "pregnancyDate")
  where "isArchived" = false;

create index concurrently if not exists idx_sales_date_desc
  on "SalesRecord" ("saleDate" desc);

create index concurrently if not exists idx_sales_cattle_date
  on "SalesRecord" ("cattleId", "saleDate" desc);

create index concurrently if not exists idx_expense_date_category
  on "ExpenseRecord" ("date" desc, "category");

create index concurrently if not exists idx_expense_cattle_date
  on "ExpenseRecord" ("cattleId", "date" desc);

create index concurrently if not exists idx_schedule_date_completed
  on "ScheduleEvent" ("date", "isCompleted");

create index concurrently if not exists idx_history_cattle_eventdate
  on "CattleHistory" ("cattleId", "eventDate" desc);
```

### Verification Query

```sql
select schemaname, tablename, indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and tablename in (
    'Cattle',
    'SalesRecord',
    'ExpenseRecord',
    'ScheduleEvent',
    'CattleHistory'
  )
order by tablename, indexname;
```

## Request Path Changes

### Before

```text
page load
  -> auth
  -> getCattleList()
  -> getSalesRecords()
  -> getFeedStandards()
  -> getInventory()
  -> getScheduleEvents()
  -> getFeedHistory()
  -> getBuildings()
  -> getFarmSettings()
  -> getExpenseRecords()
```

### After

```text
page load
  -> auth
  -> getDashboardSummary()
      -> Redis summary key
      -> fallback to DashboardSnapshot / DB query
  -> getCattlePage(limit=50)
  -> lazy-load sales/feed/analysis routes or widgets on demand
```

## Frontend Refactor Plan

### Routing

Move from one giant client page to route-segmented dashboard pages:

- `/dashboard`
- `/dashboard/cattle`
- `/dashboard/feed`
- `/dashboard/sales`
- `/dashboard/analysis`
- `/dashboard/settings`

### Component Boundaries

- Keep server page shells small.
- Use `next/dynamic` for:
  - `FinancialChartWidget`
  - `AIChatWidget`
  - `PaymentWidget`
  - large modals with charts
- Replace repeated `router.refresh()` with targeted query invalidation.

### Data Strategy

- server components for initial shell and summary
- TanStack Query only for interactive client lists and mutation invalidation
- cursor pagination for list screens
- virtualization once row count exceeds `200`

### Query Keys

```text
['dashboard-summary']
['cattle-list', buildingId, penNumber, status, cursor, limit]
['cattle-history', cattleId, cursor, limit]
['notifications']
['sales-list', from, to, cursor, limit]
['market-price-latest']
```

## Example Mutation Flow

### Create Cattle

```text
POST /api/dashboard/cattle
  -> DB transaction
     -> insert Cattle
     -> insert OutboxEvent(topic='CATTLE_CREATED')
  -> return 201

worker
  -> refresh summary snapshot
  -> refresh notifications
  -> warm affected cattle list pages

client
  -> invalidate ['dashboard-summary']
  -> invalidate ['cattle-list', ...]
```

## Observability

Add lightweight diagnostics first:

- cache hit ratio
- queue depth
- oldest pending outbox age
- snapshot age in seconds
- p95 for summary route
- p95 for cattle list route

Suggested SLOs:

- dashboard summary p95 under `250ms`
- cattle list p95 under `300ms`
- queue lag under `30s`
- snapshot freshness under `60s`

## Risks and Safeguards

### Risk

Indexes declared in Prisma may not exist in production.

Safeguard:

- verify with `pg_indexes` before app changes
- create indexes concurrently
- rerun `EXPLAIN ANALYZE`

### Risk

Queue adoption can introduce eventual consistency surprises.

Safeguard:

- summary payload returns `generatedAt`
- UI displays "last refreshed" metadata
- keep direct DB fallback on cache miss

### Risk

Introducing React Query everywhere can overcomplicate the app.

Safeguard:

- scope it to dashboard list/detail screens only
- keep marketing, auth, legal pages server-rendered and simple

## Implementation Tasks

- [ ] **T-129-1 Verify live indexes and query plans** `priority:1` `phase:data` `time:60min`
  - files: `projects/hanwoo-dashboard/prisma/schema.prisma`, new migration under `projects/hanwoo-dashboard/prisma/migrations/*`
  - run index inventory query
  - add only verified-missing indexes
  - record `EXPLAIN ANALYZE` before/after

- [ ] **T-129-2 Add queue and cache foundations** `priority:1` `phase:infra` `deps:T-129-1` `time:90min`
  - files: `src/lib/redis.js`, `src/lib/queue.js`, `package.json`
  - add `ioredis` and `bullmq`
  - create reusable bootstrap helpers

- [ ] **T-129-3 Add read-model tables** `priority:1` `phase:model` `deps:T-129-1` `time:60min`
  - files: `prisma/schema.prisma`, migration SQL
  - add `OutboxEvent`, `DashboardSnapshot`, `NotificationSummary`, `MarketPriceSnapshot`

- [ ] **T-129-4 Replace home summary reads** `priority:1` `phase:api` `deps:T-129-2,T-129-3` `time:120min`
  - files: `src/app/page.js`, `src/lib/dashboard/*`, `src/app/api/dashboard/summary/route.js`
  - serve summary from snapshot/cache
  - paginate cattle list

- [ ] **T-129-5 Split client boundaries** `priority:2` `phase:ui` `deps:T-129-4` `time:180min`
  - files: `src/components/DashboardClient.js`, new route pages and feature components
  - lazy-load heavy widgets
  - move route-specific logic out of the single client root

- [ ] **T-129-6 Remove broad refresh invalidation** `priority:2` `phase:ui` `deps:T-129-5` `time:90min`
  - files: `src/lib/actions.js`, client mutation hooks/components
  - replace `revalidatePath('/')` and `router.refresh()` where possible

- [ ] **T-129-7 Add worker and diagnostics** `priority:2` `phase:ops` `deps:T-129-3` `time:120min`
  - files: `scripts/dashboard-worker.mjs`, `src/app/admin/diagnostics/page.js`, `src/components/admin/DiagnosticsPageClient.js`
  - surface cache freshness and queue lag

## Recommended Starting Order

Start with `T-129-1` and `T-129-3` before touching UI code.

Reason:

- If indexes are missing, every other optimization will be hiding a real DB problem.
- If read models are not defined first, frontend splitting can still end up consuming expensive raw queries.

