-- T-129-3 read-model and outbox foundation
-- This draft is intentionally separate from prisma/migrations until the live index audit
-- and rollout order are confirmed for the production database.

do $$
begin
  if not exists (
    select 1
    from pg_type
    where typname = 'OutboxStatus'
  ) then
    create type "OutboxStatus" as enum ('PENDING', 'PROCESSING', 'DONE', 'FAILED');
  end if;
end $$;

create table if not exists "OutboxEvent" (
  id text primary key,
  topic text not null,
  "aggregateId" text,
  payload jsonb not null,
  status "OutboxStatus" not null default 'PENDING',
  attempts integer not null default 0,
  "availableAt" timestamptz not null default now(),
  "createdAt" timestamptz not null default now(),
  "updatedAt" timestamptz not null default now()
);

create index if not exists idx_outbox_status_available_created
  on "OutboxEvent" (status, "availableAt", "createdAt");

create index if not exists idx_outbox_topic_created
  on "OutboxEvent" (topic, "createdAt");

create table if not exists "DashboardSnapshot" (
  key text primary key,
  payload jsonb not null,
  version integer not null default 1,
  "generatedAt" timestamptz not null default now(),
  "staleAt" timestamptz not null
);

create index if not exists idx_dashboard_snapshot_stale_at
  on "DashboardSnapshot" ("staleAt");

create table if not exists "NotificationSummary" (
  key text primary key,
  payload jsonb not null,
  "generatedAt" timestamptz not null default now()
);

create table if not exists "MarketPriceSnapshot" (
  id text primary key,
  "issueDate" timestamptz not null unique,
  "isRealtime" boolean not null default false,
  "bullGrade1pp" integer not null,
  "bullGrade1p" integer not null,
  "bullGrade1" integer not null,
  "cowGrade1pp" integer not null,
  "cowGrade1p" integer not null,
  "cowGrade1" integer not null,
  source text not null,
  "fetchedAt" timestamptz not null default now()
);

create index if not exists idx_market_price_snapshot_fetched_at
  on "MarketPriceSnapshot" ("fetchedAt");
