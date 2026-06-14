import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

// ── db.js ─────────────────────────────────────────────────────────────────────

const db = readSource("lib/db.js");

test("db uses Prisma 7 PrismaPg driver adapter for Supabase PgBouncer compatibility", () => {
	assert.match(db, /PrismaPg/);
	assert.match(db, /@prisma\/adapter-pg/);
	assert.match(db, /PrismaClient/);
});

test("db configures connection pool with prod/dev sizing (10/5) and timeouts", () => {
	// Production pool max = 10, dev = 5 (Supabase free tier PgBouncer = 15)
	assert.match(db, /NODE_ENV.*production.*10.*5|poolMax.*production.*10.*5/);
	assert.match(db, /idleTimeout: 20/);
	assert.match(db, /connectionTimeout: 10_000/);
});

test("db buildDbSslConfig is exported and reads DB_SSL_CA from env", () => {
	assert.match(db, /export function buildDbSslConfig/);
	assert.match(db, /env\.DB_SSL_CA/);
	assert.match(db, /env\.DB_SSL_REJECT_UNAUTHORIZED === ["']true["']/);
	// Returns ca only when it is a non-empty string
	assert.match(db, /typeof env\.DB_SSL_CA === ["']string["'] && env\.DB_SSL_CA\.trim\(\)/);
});

test("db buildDbSslConfig defaults stay backward-compatible for deployments without CA", () => {
	// When no CA is provided, return { rejectUnauthorized } only (no ca key)
	assert.match(db, /ca \? \{ ca, rejectUnauthorized \} : \{ rejectUnauthorized \}/);
});

test("db falls back to bare PrismaClient when PrismaPg adapter construction fails", () => {
	// CI smoke environments may have an invalid DATABASE_URL — must not crash
	assert.match(db, /Fall back to a bare PrismaClient|fall back to a bare PrismaClient|falling back to bare PrismaClient/);
	assert.match(db, /\} catch \{/);
	assert.match(db, /new PrismaClient\(\{ log: logLevel \}\)/);
});

test("db uses global singleton pattern to prevent multiple Prisma instances in dev HMR", () => {
	assert.match(db, /globalForPrisma\.prisma \?\? createPrismaClient\(\)/);
	assert.match(db, /NODE_ENV !== ["']production["']/);
	assert.match(db, /globalForPrisma\.prisma = prisma/);
});

// ── kape.js ───────────────────────────────────────────────────────────────────

const kape = readSource("lib/kape.js");

test("kape fetchMarketPrice is the single exported function", () => {
	assert.match(kape, /export async function fetchMarketPrice\(\)/);
	// parseKapeResponse is internal — not exported
	assert.doesNotMatch(kape, /export.*parseKapeResponse/);
});

test("kape skips API call when KAPE_SERVICE_KEY env var is absent", () => {
	assert.match(kape, /process\.env\.KAPE_SERVICE_KEY/);
	assert.match(kape, /if \(!apiKey\)/);
	assert.match(kape, /return null/);
});

test("kape retries the last 7 days to handle weekends and holiday auction gaps", () => {
	assert.match(kape, /dayOffset <= 7/);
	assert.match(kape, /for \(let dayOffset = 1; dayOffset <= 7; dayOffset\+\+\)/);
	assert.match(kape, /No KAPE data found for the last 7 days/);
});

test("kape enforces a 12-second total deadline across retries", () => {
	assert.match(kape, /KAPE_TOTAL_DEADLINE_MS = 12000/);
	assert.match(kape, /elapsedMs >= KAPE_TOTAL_DEADLINE_MS/);
	assert.match(kape, /exceeded.*overall deadline/);
});

test("kape per-request timeout is 4 seconds with min(1000ms) floor", () => {
	assert.match(kape, /KAPE_REQUEST_TIMEOUT_MS = 4000/);
	assert.match(kape, /Math\.min\(KAPE_REQUEST_TIMEOUT_MS, remainingMs\)/);
	assert.match(kape, /Math\.max\(1000, KAPE_TOTAL_DEADLINE_MS - elapsedMs\)/);
});

test("kape parseKapeResponse maps KAPE grade codes to grade1pp/grade1p/grade1", () => {
	// gradeMap: 11→grade1pp, 12→grade1p, 13→grade1
	assert.match(kape, /11.*grade1pp|grade1pp.*11/);
	assert.match(kape, /12.*grade1p|grade1p.*12/);
	assert.match(kape, /13.*grade1|grade1.*13/);
	assert.match(kape, /gradeMap/);
});

test("kape parseKapeResponse maps KAPE category codes: 1=bull, 2=cow", () => {
	assert.match(kape, /category === ["']1["']/);
	assert.match(kape, /category === ["']2["']/);
	assert.match(kape, /bull\[grade\] = price/);
	assert.match(kape, /cow\[grade\] = price/);
});

test("kape returns null when all parsed prices are zero (no auction that day)", () => {
	assert.match(kape, /bull\.grade1pp === 0 && bull\.grade1p === 0 && cow\.grade1pp === 0/);
	assert.match(kape, /return null/);
});

test("kape handles non-array single-item KAPE response by wrapping in array", () => {
	assert.match(kape, /Array\.isArray\(items\) \? items : \[items\]/);
});

test("kape uses isTimeoutError to distinguish timeout from other errors in catch", () => {
	assert.match(kape, /isTimeoutError\(error\)/);
	assert.match(kape, /KAPE API timed out/);
});

// ── subscription-queries.js ───────────────────────────────────────────────────

const subQ = readSource("lib/subscription-queries.js");

test("subscription-queries is server-only and imports from prisma db", () => {
	assert.match(subQ, /import ["']server-only["']/);
	assert.match(subQ, /from ["']@\/lib\/db["']/);
});

test("subscription-queries getSubscriptionStatus returns INACTIVE for missing userId", () => {
	assert.match(subQ, /if \(!userId\) return \{ status: ["']INACTIVE["']/);
});

test("subscription-queries calculates daysLeft for ACTIVE subscriptions from nextPaymentDate", () => {
	assert.match(subQ, /status === ["']ACTIVE["']/);
	assert.match(subQ, /nextPaymentDate/);
	assert.match(subQ, /Math\.ceil[\s\S]{0,80}nextPaymentDate/);
	assert.match(subQ, /Math\.max\(0,/);
});

test("subscription-queries calculates daysLeft for TRIAL subscriptions and expires gracefully", () => {
	assert.match(subQ, /status === ["']TRIAL["'] && sub\.trialEndDate/);
	assert.match(subQ, /daysLeft > 0/);
	assert.match(subQ, /return \{ status: ["']INACTIVE["'], daysLeft: 0 \}/);
});

test("subscription-queries fetches most recent subscription record using orderBy createdAt desc", () => {
	assert.match(subQ, /orderBy: \{ createdAt: ["']desc["'] \}/);
	assert.match(subQ, /findFirst/);
});
