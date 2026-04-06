-- T-129-1 scale hardening index backfill
-- Run each statement against production or staging outside an explicit BEGIN/COMMIT block.
-- These statements use CONCURRENTLY so they should be applied from a SQL console, migration runner,
-- or DBA workflow that does not wrap the whole file in a transaction.

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
