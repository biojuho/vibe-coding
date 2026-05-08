/**
 * Prisma 7 Runtime Stability Test
 * ================================
 * Validates the Prisma 7 Rust-free client + PrismaPg driver adapter
 * stack used by hanwoo-dashboard.
 *
 * Test categories:
 *   1. Client Generation — generated artefact integrity
 *   2. Adapter Construction — PrismaPg constructor edge cases
 *   3. Connection Pool — pool config propagation
 *   4. Graceful Failures — error recovery & disconnect
 *   5. Live CRUD E2E — full round-trip (requires active DB)
 *
 * Usage:
 *   node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --experimental-strip-types scripts/prisma7-runtime-test.mjs
 *   node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --experimental-strip-types scripts/prisma7-runtime-test.mjs --live
 */

import process from "node:process";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { config as loadEnv } from "dotenv";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

loadEnv({ path: path.resolve(__dirname, "..", ".env"), quiet: true });

const LIVE_MODE = process.argv.includes("--live");

// ============================================================
// Helpers
// ============================================================

let passed = 0;
let failed = 0;
let skipped = 0;

function ok(name) {
  passed++;
  console.log(`  ✓ ${name}`);
}

function fail(name, error) {
  failed++;
  console.error(`  ✗ ${name}`);
  console.error(`    ${error.message ?? error}`);
}

function skip(name, reason) {
  skipped++;
  console.log(`  ⊘ ${name} — ${reason}`);
}

function isPlaceholderUrl(url) {
  return (
    !url ||
    url.includes("YOUR_PASSWORD") ||
    url.includes("postgresql://...") ||
    url.includes("DATABASE_URL_MISSING")
  );
}

function describeRunMode() {
  if (!LIVE_MODE) {
    return "OFFLINE (no DB)";
  }

  return isPlaceholderUrl(process.env.DATABASE_URL)
    ? "LIVE requested (DATABASE_URL missing/placeholder)"
    : "LIVE (DB connected)";
}

// ============================================================
// 1. Client Generation
// ============================================================

async function testClientGeneration() {
  console.log("\n── 1. Client Generation ──");

  // 1-1: PrismaClient import
  try {
    const { PrismaClient } = await import("../src/generated/prisma/client.ts");
    assert.ok(PrismaClient, "PrismaClient should be importable");
    assert.equal(typeof PrismaClient, "function", "PrismaClient should be a constructor");
    ok("PrismaClient import");
  } catch (e) {
    fail("PrismaClient import", e);
    return; // fatal — skip remaining client tests
  }

  // 1-2: All 16 model delegates exist
  try {
    const { PrismaClient } = await import("../src/generated/prisma/client.ts");
    const { PrismaPg } = await import("@prisma/adapter-pg");
    // Construct a throwaway client to inspect model delegates.
    // PrismaPg requires a connection string, but we just need structure.
    const adapter = new PrismaPg({
      connectionString: "postgresql://test:test@localhost:5432/test",
    });
    const client = new PrismaClient({ adapter });

    const expectedModels = [
      "user",
      "farmSettings",
      "building",
      "cattle",
      "salesRecord",
      "feedStandard",
      "inventoryItem",
      "scheduleEvent",
      "feedRecord",
      "subscription",
      "paymentLog",
      "expenseRecord",
      "cattleHistory",
      "outboxEvent",
      "dashboardSnapshot",
      "notificationSummary",
      "marketPriceSnapshot",
    ];

    const missing = expectedModels.filter((m) => !(m in client));
    assert.equal(missing.length, 0, `Missing model delegates: ${missing.join(", ")}`);
    ok(`All ${expectedModels.length} model delegates present`);

    await client.$disconnect().catch(() => {});
  } catch (e) {
    fail("Model delegates", e);
  }

  // 1-3: Enum export
  try {
    const { OutboxStatus } = await import("../src/generated/prisma/client.ts");
    assert.ok(OutboxStatus, "OutboxStatus enum should be exported");
    assert.equal(OutboxStatus.PENDING, "PENDING");
    assert.equal(OutboxStatus.PROCESSING, "PROCESSING");
    assert.equal(OutboxStatus.DONE, "DONE");
    assert.equal(OutboxStatus.FAILED, "FAILED");
    ok("OutboxStatus enum values");
  } catch (e) {
    fail("OutboxStatus enum", e);
  }

  // 1-4: Browser module (client-side safe)
  try {
    const browser = await import("../src/generated/prisma/browser.ts");
    assert.ok(browser, "browser.ts should be importable");
    ok("Browser module import");
  } catch (e) {
    fail("Browser module", e);
  }
}

// ============================================================
// 2. Adapter Construction
// ============================================================

async function testAdapterConstruction() {
  console.log("\n── 2. PrismaPg Adapter Construction ──");

  const { PrismaPg } = await import("@prisma/adapter-pg");

  // 2-1: Basic construction with connection string
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:5432/db",
    });
    assert.ok(adapter, "Adapter should construct with connection string");
    ok("Basic connection string");
  } catch (e) {
    fail("Basic connection string", e);
  }

  // 2-2: Construction with SSL options (Supabase pattern)
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:6543/db",
      ssl: { rejectUnauthorized: false },
    });
    assert.ok(adapter, "Adapter should construct with SSL options");
    ok("SSL config (rejectUnauthorized: false)");
  } catch (e) {
    fail("SSL config", e);
  }

  // 2-3: Construction with pool config
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:5432/db",
      pool: {
        max: 15,
        idleTimeout: 30,
      },
    });
    assert.ok(adapter, "Adapter should construct with pool config");
    ok("Pool config (max=15, idleTimeout=30)");
  } catch (e) {
    fail("Pool config", e);
  }

  // 2-4: Full production config (matches db.js)
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@pooler.supabase.com:6543/postgres",
      ssl: { rejectUnauthorized: false },
      pool: {
        max: 10,
        idleTimeout: 20,
      },
    });
    assert.ok(adapter, "Full production config should construct");
    ok("Full production config (pooler + SSL + pool)");
  } catch (e) {
    fail("Full production config", e);
  }
}

// ============================================================
// 3. Connection Pool Behavior
// ============================================================

async function testConnectionPool() {
  console.log("\n── 3. Connection Pool Config ──");

  const { PrismaClient } = await import("../src/generated/prisma/client.ts");
  const { PrismaPg } = await import("@prisma/adapter-pg");

  // 3-1: Dev pool size (5)
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:5432/db",
      pool: { max: 5, idleTimeout: 20 },
    });
    const client = new PrismaClient({
      adapter,
      log: ["warn", "error"],
    });
    assert.ok(client, "Dev pool config client should construct");
    ok("Dev pool (max=5)");
    await client.$disconnect().catch(() => {});
  } catch (e) {
    fail("Dev pool", e);
  }

  // 3-2: Production pool size (10)
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:5432/db",
      ssl: { rejectUnauthorized: false },
      pool: { max: 10, idleTimeout: 20 },
    });
    const client = new PrismaClient({
      adapter,
      log: ["error"],
    });
    assert.ok(client, "Production pool config client should construct");
    ok("Production pool (max=10)");
    await client.$disconnect().catch(() => {});
  } catch (e) {
    fail("Production pool", e);
  }

  // 3-3: Minimal pool size (1) — edge case
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:5432/db",
      pool: { max: 1 },
    });
    const client = new PrismaClient({ adapter });
    assert.ok(client, "Pool max=1 should construct");
    ok("Minimal pool (max=1)");
    await client.$disconnect().catch(() => {});
  } catch (e) {
    fail("Minimal pool", e);
  }
}

// ============================================================
// 4. Graceful Error Handling
// ============================================================

async function testGracefulErrors() {
  console.log("\n── 4. Graceful Error Handling ──");

  const { PrismaClient } = await import("../src/generated/prisma/client.ts");
  const { PrismaPg } = await import("@prisma/adapter-pg");

  // 4-1: Query against unreachable host should fail gracefully
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://invalid:invalid@127.0.0.1:59999/nonexistent",
      pool: { max: 1, idleTimeout: 1 },
    });
    const client = new PrismaClient({ adapter, log: [] });

    let errored = false;
    try {
      // This should timeout / connection refused rapidly on localhost
      await Promise.race([
        client.user.findMany(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error("timeout")), 5000)
        ),
      ]);
    } catch {
      errored = true;
    }

    assert.ok(errored, "Query against unreachable host should throw");
    ok("Unreachable host → graceful error");

    await client.$disconnect().catch(() => {});
  } catch (e) {
    fail("Unreachable host error", e);
  }

  // 4-2: Double disconnect should be safe
  try {
    const adapter = new PrismaPg({
      connectionString: "postgresql://user:pass@host:5432/db",
    });
    const client = new PrismaClient({ adapter, log: [] });

    await client.$disconnect().catch(() => {});
    await client.$disconnect().catch(() => {});
    ok("Double $disconnect() is safe");
  } catch (e) {
    fail("Double disconnect", e);
  }

  // 4-3: db.js fallback pattern (bare PrismaClient when adapter fails)
  try {
    // Simulate the fallback path in db.js: when PrismaPg throws,
    // a bare PrismaClient is constructed instead.
    let usedFallback = false;
    let client;

    try {
      // Force adapter creation failure by passing null connectionString
      const adapter = new PrismaPg({ connectionString: null });
      client = new PrismaClient({ adapter, log: [] });
    } catch {
      // Fallback: bare PrismaClient (matches db.js line 26)
      client = new PrismaClient({ log: [] });
      usedFallback = true;
    }

    // If adapter didn't throw, check whether bare PrismaClient works anyway
    assert.ok(client, "Fallback PrismaClient should construct");
    if (usedFallback) {
      ok("Adapter failure → bare PrismaClient fallback");
    } else {
      ok("Adapter accepted null (no fallback needed)");
    }

    await client.$disconnect().catch(() => {});
  } catch (e) {
    fail("Fallback pattern", e);
  }
}

// ============================================================
// 5. Live CRUD E2E (requires --live flag + active DB)
// ============================================================

async function testLiveCrud() {
  console.log("\n── 5. Live CRUD E2E ──");

  const databaseUrl = process.env.DATABASE_URL;

  if (isPlaceholderUrl(databaseUrl)) {
    const reason =
      "DATABASE_URL is missing or placeholder — set a real Supabase URL before running --live";
    if (LIVE_MODE) {
      fail("Live CRUD tests", new Error(reason));
    } else {
      skip("Live CRUD tests", reason);
    }
    return;
  }

  if (!LIVE_MODE) {
    skip(
      "Live CRUD tests",
      "Pass --live flag to enable (requires active Supabase project)"
    );
    return;
  }

  const { PrismaClient } = await import("../src/generated/prisma/client.ts");
  const { PrismaPg } = await import("@prisma/adapter-pg");

  const adapter = new PrismaPg({
    connectionString: databaseUrl,
    ssl: { rejectUnauthorized: false },
    pool: { max: 2, idleTimeout: 10 },
  });

  const prisma = new PrismaClient({ adapter, log: ["warn", "error"] });

  try {
    // 5-1: Connection health
    try {
      const result = await prisma.$queryRawUnsafe("SELECT 1 AS health");
      assert.ok(Array.isArray(result), "Health check should return array");
      assert.equal(result[0]?.health, 1);
      ok("Connection health (SELECT 1)");
    } catch (e) {
      fail("Connection health", e);
      return; // No point continuing if we can't connect
    }

    // 5-2: Read — list buildings
    try {
      const buildings = await prisma.building.findMany({ take: 5 });
      assert.ok(Array.isArray(buildings), "Buildings query should return array");
      ok(`Read buildings (${buildings.length} rows)`);
    } catch (e) {
      fail("Read buildings", e);
    }

    // 5-3: Read — active cattle count
    try {
      const count = await prisma.cattle.count({
        where: { isArchived: false },
      });
      assert.ok(typeof count === "number", "Count should be a number");
      ok(`Active cattle count = ${count}`);
    } catch (e) {
      fail("Active cattle count", e);
    }

    // 5-4: Write + Delete — CRD cycle with DashboardSnapshot
    const testKey = `_prisma7_stability_test_${Date.now()}`;
    try {
      // Create
      const snapshot = await prisma.dashboardSnapshot.create({
        data: {
          key: testKey,
          payload: { test: true, ts: Date.now() },
          version: 999,
          staleAt: new Date(Date.now() + 60_000),
        },
      });
      assert.equal(snapshot.key, testKey);
      ok("Create DashboardSnapshot");

      // Read back
      const found = await prisma.dashboardSnapshot.findUnique({
        where: { key: testKey },
      });
      assert.ok(found, "Created snapshot should be findable");
      assert.equal(found.version, 999);
      ok("Read back created snapshot");

      // Update
      const updated = await prisma.dashboardSnapshot.update({
        where: { key: testKey },
        data: { version: 1000 },
      });
      assert.equal(updated.version, 1000);
      ok("Update snapshot version");

      // Delete
      await prisma.dashboardSnapshot.delete({
        where: { key: testKey },
      });
      const deleted = await prisma.dashboardSnapshot.findUnique({
        where: { key: testKey },
      });
      assert.equal(deleted, null);
      ok("Delete snapshot (cleanup)");
    } catch (e) {
      fail("CRD cycle", e);
      // Attempt cleanup
      await prisma.dashboardSnapshot
        .delete({ where: { key: testKey } })
        .catch(() => {});
    }

    // 5-5: Transaction — atomic multi-model write
    try {
      const txTestKey = `_prisma7_tx_test_${Date.now()}`;

      await prisma.$transaction(async (tx) => {
        await tx.dashboardSnapshot.create({
          data: {
            key: txTestKey,
            payload: { tx: true },
            version: 1,
            staleAt: new Date(Date.now() + 60_000),
          },
        });

        await tx.notificationSummary.upsert({
          where: { key: txTestKey },
          update: { payload: { tx: true } },
          create: { key: txTestKey, payload: { tx: true } },
        });
      });

      // Verify both writes landed
      const snap = await prisma.dashboardSnapshot.findUnique({
        where: { key: txTestKey },
      });
      const notif = await prisma.notificationSummary.findUnique({
        where: { key: txTestKey },
      });
      assert.ok(snap, "Transaction: snapshot should exist");
      assert.ok(notif, "Transaction: notification should exist");
      ok("Transaction — atomic multi-model write");

      // Cleanup
      await prisma.dashboardSnapshot.delete({ where: { key: txTestKey } }).catch(() => {});
      await prisma.notificationSummary.delete({ where: { key: txTestKey } }).catch(() => {});
    } catch (e) {
      fail("Transaction", e);
    }

    // 5-6: Transaction rollback
    try {
      const rollbackKey = `_prisma7_rollback_${Date.now()}`;

      let rolledBack = false;
      try {
        await prisma.$transaction(async (tx) => {
          await tx.dashboardSnapshot.create({
            data: {
              key: rollbackKey,
              payload: { shouldRollback: true },
              version: 1,
              staleAt: new Date(Date.now() + 60_000),
            },
          });
          throw new Error("deliberate rollback");
        });
      } catch {
        rolledBack = true;
      }

      assert.ok(rolledBack, "Transaction should have thrown");
      const ghost = await prisma.dashboardSnapshot.findUnique({
        where: { key: rollbackKey },
      });
      assert.equal(ghost, null, "Rolled-back write should not persist");
      ok("Transaction rollback — no phantom writes");
    } catch (e) {
      fail("Transaction rollback", e);
    }

    // 5-7: JSON field handling
    try {
      const jsonKey = `_prisma7_json_test_${Date.now()}`;
      const complexPayload = {
        counts: { total: 42, active: 37 },
        alerts: ["estrus", "vaccination"],
        nested: { deep: { value: true } },
      };

      const created = await prisma.dashboardSnapshot.create({
        data: {
          key: jsonKey,
          payload: complexPayload,
          version: 1,
          staleAt: new Date(Date.now() + 60_000),
        },
      });

      assert.deepEqual(created.payload, complexPayload);
      ok("JSON field — complex nested payload");

      await prisma.dashboardSnapshot.delete({ where: { key: jsonKey } }).catch(() => {});
    } catch (e) {
      fail("JSON field", e);
    }

    // 5-8: Concurrent reads (pool stress)
    try {
      const queries = Array.from({ length: 10 }, () =>
        prisma.building.count()
      );
      const results = await Promise.all(queries);
      assert.ok(
        results.every((r) => typeof r === "number"),
        "All concurrent reads should return numbers"
      );
      ok(`Concurrent reads — ${results.length} parallel queries`);
    } catch (e) {
      fail("Concurrent reads", e);
    }
  } finally {
    await prisma.$disconnect();
    ok("Clean $disconnect()");
  }
}

// ============================================================
// Runner
// ============================================================

async function main() {
  console.log("╔════════════════════════════════════════╗");
  console.log("║  Prisma 7 Runtime Stability Test       ║");
  console.log("║  hanwoo-dashboard                      ║");
  console.log("╚════════════════════════════════════════╝");
  console.log(`Mode: ${describeRunMode()}`);

  await testClientGeneration();
  await testAdapterConstruction();
  await testConnectionPool();
  await testGracefulErrors();
  await testLiveCrud();

  console.log("\n════════════════════════════════════════");
  console.log(`  Passed: ${passed}  Failed: ${failed}  Skipped: ${skipped}`);
  console.log("════════════════════════════════════════\n");

  if (failed > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error("\nPrisma 7 runtime test crashed:");
  console.error(error);
  process.exitCode = 1;
});
