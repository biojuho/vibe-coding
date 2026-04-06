import process from "node:process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { config as loadEnv } from "dotenv";
import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "../src/generated/prisma/client.ts";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

loadEnv({ path: path.resolve(__dirname, "..", ".env"), quiet: true });

const inventorySql = `
select
  schemaname,
  tablename,
  indexname,
  indexdef
from pg_indexes
where schemaname = 'public'
  and tablename in (
    'Cattle',
    'SalesRecord',
    'ExpenseRecord',
    'ScheduleEvent',
    'CattleHistory',
    'FeedRecord',
    'InventoryItem'
  )
order by tablename, indexname;
`;

const schemaIndexExpectations = [
  {
    key: "schema:cattle:building_status",
    table: "Cattle",
    intent: "baseline list filters by building and status",
    fragments: ['public."Cattle"', '("buildingId", "status")'],
  },
  {
    key: "schema:cattle:status_archived",
    table: "Cattle",
    intent: "baseline active cattle filters",
    fragments: ['public."Cattle"', '("status", "isArchived")'],
  },
  {
    key: "schema:cattle:building_pen",
    table: "Cattle",
    intent: "baseline building and pen lookups",
    fragments: ['public."Cattle"', '("buildingId", "penNumber")'],
  },
  {
    key: "schema:sales:saledate",
    table: "SalesRecord",
    intent: "baseline sale date range queries",
    fragments: ['public."SalesRecord"', '("saleDate")'],
  },
  {
    key: "schema:sales:cattle_saledate",
    table: "SalesRecord",
    intent: "baseline cattle sale history queries",
    fragments: ['public."SalesRecord"', '("cattleId", "saleDate")'],
  },
  {
    key: "schema:inventory:category",
    table: "InventoryItem",
    intent: "baseline inventory category filters",
    fragments: ['public."InventoryItem"', '("category")'],
  },
  {
    key: "schema:schedule:date_done",
    table: "ScheduleEvent",
    intent: "baseline schedule dashboard query",
    fragments: ['public."ScheduleEvent"', '("date", "isCompleted")'],
  },
  {
    key: "schema:schedule:cattle_date",
    table: "ScheduleEvent",
    intent: "baseline cattle schedule lookup",
    fragments: ['public."ScheduleEvent"', '("cattleId", "date")'],
  },
  {
    key: "schema:feed:building_date",
    table: "FeedRecord",
    intent: "baseline building feed history",
    fragments: ['public."FeedRecord"', '("buildingId", "date")'],
  },
  {
    key: "schema:expense:date",
    table: "ExpenseRecord",
    intent: "baseline expense date query",
    fragments: ['public."ExpenseRecord"', '("date")'],
  },
  {
    key: "schema:expense:cattle_date",
    table: "ExpenseRecord",
    intent: "baseline cattle expense history",
    fragments: ['public."ExpenseRecord"', '("cattleId", "date")'],
  },
  {
    key: "schema:expense:category_date",
    table: "ExpenseRecord",
    intent: "baseline category expense query",
    fragments: ['public."ExpenseRecord"', '("category", "date")'],
  },
  {
    key: "schema:history:cattle_eventdate",
    table: "CattleHistory",
    intent: "baseline cattle history lookup",
    fragments: ['public."CattleHistory"', '("cattleId", "eventDate")'],
  },
  {
    key: "schema:history:eventtype_eventdate",
    table: "CattleHistory",
    intent: "baseline history reporting by event type",
    fragments: ['public."CattleHistory"', '("eventType", "eventDate")'],
  },
];

const scaleCandidateIndexes = [
  {
    key: "scale:cattle:active_updated",
    table: "Cattle",
    intent: "home dashboard active cattle list ordered by updatedAt",
    fragments: ['public."Cattle"', '("isArchived", "updatedAt" desc)'],
    statement: `
create index concurrently if not exists idx_cattle_active_updated
  on "Cattle" ("isArchived", "updatedAt" desc);
`.trim(),
  },
  {
    key: "scale:cattle:building_pen_active",
    table: "Cattle",
    intent: "building and pen list page for active cattle",
    fragments: [
      'public."Cattle"',
      '("buildingId", "penNumber", "updatedAt" desc)',
      'where ("isArchived" = false)',
    ],
    statement: `
create index concurrently if not exists idx_cattle_building_pen_active
  on "Cattle" ("buildingId", "penNumber", "updatedAt" desc)
  where "isArchived" = false;
`.trim(),
  },
  {
    key: "scale:cattle:status_estrus",
    table: "Cattle",
    intent: "notification scan for estrus candidates",
    fragments: [
      'public."Cattle"',
      '("status", "lastEstrus")',
      'where ("isArchived" = false)',
    ],
    statement: `
create index concurrently if not exists idx_cattle_status_estrus
  on "Cattle" ("status", "lastEstrus")
  where "isArchived" = false;
`.trim(),
  },
  {
    key: "scale:cattle:status_pregnancy",
    table: "Cattle",
    intent: "notification scan for calving candidates",
    fragments: [
      'public."Cattle"',
      '("status", "pregnancyDate")',
      'where ("isArchived" = false)',
    ],
    statement: `
create index concurrently if not exists idx_cattle_status_pregnancy
  on "Cattle" ("status", "pregnancyDate")
  where "isArchived" = false;
`.trim(),
  },
  {
    key: "scale:sales:date_desc",
    table: "SalesRecord",
    intent: "latest sales pages sorted by most recent date",
    fragments: ['public."SalesRecord"', '("saleDate" desc)'],
    statement: `
create index concurrently if not exists idx_sales_date_desc
  on "SalesRecord" ("saleDate" desc);
`.trim(),
  },
  {
    key: "scale:sales:cattle_date_desc",
    table: "SalesRecord",
    intent: "per-cattle sale history sorted by recent date",
    fragments: ['public."SalesRecord"', '("cattleId", "saleDate" desc)'],
    statement: `
create index concurrently if not exists idx_sales_cattle_date
  on "SalesRecord" ("cattleId", "saleDate" desc);
`.trim(),
  },
  {
    key: "scale:expense:date_category",
    table: "ExpenseRecord",
    intent: "expense list filtered by date and category",
    fragments: ['public."ExpenseRecord"', '("date" desc, "category")'],
    statement: `
create index concurrently if not exists idx_expense_date_category
  on "ExpenseRecord" ("date" desc, "category");
`.trim(),
  },
  {
    key: "scale:expense:cattle_date_desc",
    table: "ExpenseRecord",
    intent: "per-cattle expense history sorted by recent date",
    fragments: ['public."ExpenseRecord"', '("cattleId", "date" desc)'],
    statement: `
create index concurrently if not exists idx_expense_cattle_date
  on "ExpenseRecord" ("cattleId", "date" desc);
`.trim(),
  },
  {
    key: "scale:schedule:date_completed",
    table: "ScheduleEvent",
    intent: "upcoming schedule widget",
    fragments: ['public."ScheduleEvent"', '("date", "isCompleted")'],
    statement: `
create index concurrently if not exists idx_schedule_date_completed
  on "ScheduleEvent" ("date", "isCompleted");
`.trim(),
  },
  {
    key: "scale:history:cattle_eventdate_desc",
    table: "CattleHistory",
    intent: "cattle detail history sorted by recent event date",
    fragments: ['public."CattleHistory"', '("cattleId", "eventDate" desc)'],
    statement: `
create index concurrently if not exists idx_history_cattle_eventdate
  on "CattleHistory" ("cattleId", "eventDate" desc);
`.trim(),
  },
];

const explainProbes = [
  {
    name: "active_cattle_dashboard",
    sql: `
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, "tagNumber", name, status, "buildingId", "penNumber", "updatedAt"
FROM "Cattle"
WHERE "isArchived" = false
ORDER BY "updatedAt" DESC, id DESC
LIMIT 50;
`.trim(),
  },
  {
    name: "building_pen_active",
    sql: `
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, "tagNumber", name, status, "buildingId", "penNumber", "updatedAt"
FROM "Cattle"
WHERE "isArchived" = false
  AND "buildingId" = (
    SELECT id
    FROM "Building"
    ORDER BY "createdAt" ASC
    LIMIT 1
  )
ORDER BY "penNumber" ASC, "updatedAt" DESC
LIMIT 50;
`.trim(),
  },
  {
    name: "sales_recent",
    sql: `
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, "saleDate", price, "cattleId"
FROM "SalesRecord"
WHERE "saleDate" >= now() - interval '180 days'
ORDER BY "saleDate" DESC
LIMIT 50;
`.trim(),
  },
  {
    name: "expense_by_category",
    sql: `
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, "date", category, amount, "cattleId"
FROM "ExpenseRecord"
WHERE "date" >= now() - interval '180 days'
  AND category = coalesce(
    (SELECT category FROM "ExpenseRecord" WHERE category IS NOT NULL LIMIT 1),
    'GENERAL'
  )
ORDER BY "date" DESC
LIMIT 50;
`.trim(),
  },
  {
    name: "cattle_history_recent",
    sql: `
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, "cattleId", "eventType", "eventDate"
FROM "CattleHistory"
WHERE "cattleId" = (
  SELECT "cattleId"
  FROM "CattleHistory"
  ORDER BY "eventDate" DESC
  LIMIT 1
)
ORDER BY "eventDate" DESC
LIMIT 20;
`.trim(),
  },
  {
    name: "notification_candidates",
    sql: `
EXPLAIN (ANALYZE, BUFFERS)
WITH estrus_status AS (
  SELECT status
  FROM "Cattle"
  WHERE "isArchived" = false
    AND "lastEstrus" IS NOT NULL
  ORDER BY "updatedAt" DESC
  LIMIT 1
),
pregnancy_status AS (
  SELECT status
  FROM "Cattle"
  WHERE "isArchived" = false
    AND "pregnancyDate" IS NOT NULL
  ORDER BY "updatedAt" DESC
  LIMIT 1
)
SELECT id, status, "lastEstrus", "pregnancyDate", "updatedAt"
FROM "Cattle"
WHERE "isArchived" = false
  AND (
    (status = (SELECT status FROM estrus_status) AND "lastEstrus" IS NOT NULL)
    OR (status = (SELECT status FROM pregnancy_status) AND "pregnancyDate" IS NOT NULL)
  )
ORDER BY "updatedAt" DESC
LIMIT 100;
`.trim(),
  },
];

function normalize(value) {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function isPlaceholderDatabaseUrl(value) {
  return (
    !value ||
    value.includes("YOUR_PASSWORD") ||
    value.includes("postgresql://...") ||
    value.includes("DATABASE_URL_MISSING") ||
    value.includes("DOTENV_PLACEHOLDER")
  );
}

function matchesExpectation(indexdef, fragments) {
  const normalized = normalize(indexdef);
  return fragments.every((fragment) => normalized.includes(normalize(fragment)));
}

function groupByTable(indexRows) {
  return indexRows.reduce((accumulator, row) => {
    const rows = accumulator.get(row.tablename) ?? [];
    rows.push(row);
    accumulator.set(row.tablename, rows);
    return accumulator;
  }, new Map());
}

function evaluateExpectations(indexRows, expectations) {
  return expectations.map((expectation) => {
    const matched = indexRows.find((row) => matchesExpectation(row.indexdef, expectation.fragments));
    return {
      ...expectation,
      status: matched ? "present" : "missing",
      matchedIndexName: matched?.indexname ?? null,
      matchedDefinition: matched?.indexdef ?? null,
    };
  });
}

function printInventory(groupedIndexes) {
  console.log("== Index Inventory ==");
  for (const [table, rows] of groupedIndexes.entries()) {
    console.log(`\n[${table}] ${rows.length} indexes`);
    for (const row of rows) {
      console.log(`- ${row.indexname}`);
      console.log(`  ${row.indexdef}`);
    }
  }
}

function printExpectationSection(title, results) {
  const presentCount = results.filter((result) => result.status === "present").length;
  const missingCount = results.length - presentCount;

  console.log(`\n== ${title} ==`);
  console.log(`present=${presentCount} missing=${missingCount}`);

  for (const result of results) {
    const prefix = result.status === "present" ? "[ok]" : "[missing]";
    console.log(`${prefix} ${result.key} -> ${result.intent}`);
    if (result.matchedIndexName) {
      console.log(`  matched: ${result.matchedIndexName}`);
    }
  }
}

async function runExplainPlans(prisma) {
  console.log("\n== EXPLAIN ANALYZE ==");

  for (const probe of explainProbes) {
    console.log(`\n[${probe.name}]`);
    const rows = await prisma.$queryRawUnsafe(probe.sql);
    for (const row of rows) {
      const line = row["QUERY PLAN"] ?? Object.values(row)[0];
      console.log(line);
    }
  }
}

function printMissingSql(results) {
  const statements = results
    .filter((result) => result.status === "missing")
    .map((result) => result.statement);

  if (statements.length === 0) {
    console.log("\n== Missing Scale SQL ==");
    console.log("No missing scale candidate indexes detected.");
    return;
  }

  console.log("\n== Missing Scale SQL ==");
  console.log("-- Run outside an explicit BEGIN/COMMIT block.");
  for (const statement of statements) {
    console.log(`${statement}\n`);
  }
}

async function main() {
  const databaseUrl = process.env.DATABASE_URL;
  const shouldSkipExplain = process.argv.includes("--skip-explain");

  if (isPlaceholderDatabaseUrl(databaseUrl)) {
    console.error("DATABASE_URL is missing or still uses the placeholder value in projects/hanwoo-dashboard/.env.");
    console.error("Add the real pooled Postgres URL first, then rerun `npm run db:verify-indexes`.");
    process.exitCode = 2;
    return;
  }

  const adapter = new PrismaPg({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
    pool: {
      max: 2,
      idleTimeout: 20,
    },
  });

  const prisma = new PrismaClient({
    adapter,
    log: ["warn", "error"],
  });

  try {
    const indexRows = await prisma.$queryRawUnsafe(inventorySql);
    const groupedIndexes = groupByTable(indexRows);
    const schemaResults = evaluateExpectations(indexRows, schemaIndexExpectations);
    const scaleResults = evaluateExpectations(indexRows, scaleCandidateIndexes);

    printInventory(groupedIndexes);
    printExpectationSection("Schema Index Coverage", schemaResults);
    printExpectationSection("Scale Candidate Coverage", scaleResults);
    printMissingSql(scaleResults);

    if (!shouldSkipExplain) {
      await runExplainPlans(prisma);
    }
  } finally {
    await prisma.$disconnect();
  }
}

main().catch((error) => {
  console.error("\nverify-db-indexes failed");
  console.error(error);
  process.exitCode = 1;
});
