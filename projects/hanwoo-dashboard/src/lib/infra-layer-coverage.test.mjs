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

// ── redis.js ──────────────────────────────────────────────────────────────────

const redis = readSource("lib/redis.js");

test("redis exports all 6 public APIs", () => {
	const apis = [
		"isRedisConfigured",
		"getRedisKeyPrefix",
		"createRedisClient",
		"getRedisClient",
		"ensureRedisConnection",
		"closeRedisClients",
	];
	for (const api of apis) {
		assert.ok(redis.includes(api), `Missing export: ${api}`);
	}
});

test("redis uses hd as default key prefix when REDIS_KEY_PREFIX env is absent", () => {
	assert.match(redis, /DEFAULT_REDIS_KEY_PREFIX = ["']hd["']/);
	assert.match(redis, /process\.env\.REDIS_KEY_PREFIX \?\? DEFAULT_REDIS_KEY_PREFIX/);
});

test("redis has 4 roles: cache/producer use eager-fail, worker/events use offline queue", () => {
	assert.match(redis, /REDIS_ROLE_OPTIONS/);
	// cache and producer: quick-fail (maxRetriesPerRequest: 1, enableOfflineQueue: false)
	assert.match(redis, /maxRetriesPerRequest: 1/);
	assert.match(redis, /enableOfflineQueue: false/);
	// worker and events: resilient (maxRetriesPerRequest: null, enableOfflineQueue: true)
	assert.match(redis, /maxRetriesPerRequest: null/);
	assert.match(redis, /enableOfflineQueue: true/);
});

test("redis reads URL from REDIS_URL with fallback to BULLMQ_REDIS_URL", () => {
	assert.match(redis, /process\.env\.REDIS_URL \?\? process\.env\.BULLMQ_REDIS_URL \?\? null/);
});

test("redis retry strategy caps backoff at 20 seconds", () => {
	assert.match(redis, /createRetryStrategy/);
	assert.match(redis, /Math\.min\(attempt \* 1000, 20000\)/);
});

test("redis createRedisClient uses lazyConnect to defer connection until first use", () => {
	assert.match(redis, /lazyConnect: true/);
	assert.match(redis, /retryStrategy: createRetryStrategy/);
});

test("redis uses global singleton pattern for cache and producer roles", () => {
	assert.match(redis, /__hanwooRedisCache/);
	assert.match(redis, /__hanwooRedisProducer/);
	assert.match(redis, /globalForRedis\[singletonKey\]/);
});

test("redis worker and events roles are not singletonized (new client per call)", () => {
	// getSingletonKey returns null for non-cached roles → createRedisClient called fresh
	assert.match(redis, /getSingletonKey\(role\)/);
	assert.match(redis, /if \(!singletonKey\)/);
	assert.match(redis, /return createRedisClient\(role\)/);
});

test("redis closeRedisClients quits all singleton clients and removes them from global", () => {
	assert.match(redis, /closeRedisClients/);
	assert.match(redis, /await client\.quit\(\)/);
	assert.match(redis, /delete globalForRedis\[singletonKey\]/);
});

test("redis isRedisConfigured returns false when REDIS_URL is absent", () => {
	assert.match(redis, /export function isRedisConfigured\(\)/);
	assert.match(redis, /Boolean\(getRedisUrl\(\)\)/);
});

// ── actions barrel ────────────────────────────────────────────────────────────

const actions = readSource("lib/actions.js");

test("actions barrel re-exports cancelSubscription from subscription domain", () => {
	assert.match(actions, /export \{ cancelSubscription \} from ["']\.\/actions\/subscription["']/);
});

test("actions barrel covers all 9 domain modules", () => {
	const domains = [
		"./actions/building",
		"./actions/cattle",
		"./actions/expense",
		"./actions/farm-settings",
		"./actions/feed",
		"./actions/inventory",
		"./actions/market",
		"./actions/notification",
		"./actions/sales",
		"./actions/schedule",
		"./actions/subscription",
		"./actions/system",
	];
	for (const domain of domains) {
		assert.ok(actions.includes(domain), `Missing domain in barrel: ${domain}`);
	}
});

// ── actions/subscription.js ───────────────────────────────────────────────────

const subscription = readSource("lib/actions/subscription.js");

test("cancelSubscription wraps Prisma lookup in try/catch for connection-failure resilience", () => {
	assert.match(subscription, /try \{[\s\S]{1,100}prisma\.subscription\.findFirst/);
	assert.match(subscription, /ok: false, message:/);
});

test("cancelSubscription wraps Prisma update in try/catch to prevent unhandled rejection", () => {
	assert.match(subscription, /try \{[\s\S]{1,100}prisma\.subscription\.update/);
});

// ── actions/market.js ────────────────────────────────────────────────────────

const market = readSource("lib/actions/market.js");

test("getRealTimeMarketPrice wraps live KAPE fetch in try/catch and falls back gracefully", () => {
	assert.match(market, /try \{[\s\S]{1,80}rawMarketPrice = await fetchMarketPrice\(\)/);
	assert.match(market, /cachedMarketPrice \?\? buildUnavailableMarketPrice\(\)/);
});

// ── actions/system.js ────────────────────────────────────────────────────────

const system = readSource("lib/actions/system.js");

test("lookupCattleTag validates tagNumber format before calling mtrace API", () => {
	assert.match(system, /TAG_NUMBER_RE/);
	assert.match(system, /typeof tagNumber !== ["']string["'] \|\| !TAG_NUMBER_RE\.test\(tagNumber\)/);
	assert.match(system, /유효하지 않은 이력번호 형식입니다/);
});

test("getProfitabilityData wraps estimate calculation in try/catch", () => {
	assert.match(system, /getProfitabilityData/);
	assert.match(system, /try \{[\s\S]{1,80}return await getProfitabilityEstimates\(\)/);
});

// ── payment routes ────────────────────────────────────────────────────────────

const paymentPrepare = readSource("app/api/payments/prepare/route.js");
const paymentConfirm = readSource("app/api/payments/confirm/route.js");

test("payments/prepare applies per-user rate limiting with 429 response", () => {
	assert.match(paymentPrepare, /checkRateLimit/);
	assert.match(paymentPrepare, /payment-prepare:/);
	assert.match(paymentPrepare, /status: 429/);
	assert.match(paymentPrepare, /Retry-After/);
});

test("payments/prepare returns 500 for unexpected server errors not 400", () => {
	// 400 = bad client input; 500 = unexpected server fault
	assert.doesNotMatch(paymentPrepare, /결제를 준비하지 못했습니다[\s\S]{0,80}status: 400/);
	assert.match(paymentPrepare, /결제를 준비하지 못했습니다[\s\S]{0,80}status: 500/);
});

test("payments/confirm applies per-user rate limiting with 429 response", () => {
	assert.match(paymentConfirm, /checkRateLimit/);
	assert.match(paymentConfirm, /payment-confirm:/);
	assert.match(paymentConfirm, /status: 429/);
	assert.match(paymentConfirm, /Retry-After/);
});

// ── actions/cattle.js and actions/sales.js ────────────────────────────────────

const cattleActions = readSource("lib/actions/cattle.js");
const salesActions = readSource("lib/actions/sales.js");

test("getCattleList has a hard CATTLE_LIST_LIMIT cap to prevent full-table scan", () => {
	assert.match(cattleActions, /CATTLE_LIST_LIMIT = 2000/);
	assert.match(cattleActions, /take: CATTLE_LIST_LIMIT/);
});

test("getArchivedCattle also applies CATTLE_LIST_LIMIT cap", () => {
	const takeCount = (cattleActions.match(/take: CATTLE_LIST_LIMIT/g) || []).length;
	assert.ok(takeCount >= 2, "Expected ≥2 uses of CATTLE_LIST_LIMIT take cap");
});

test("getSalesRecords has a SALES_RECORD_LIMIT cap to prevent full-table scan", () => {
	assert.match(salesActions, /SALES_RECORD_LIMIT = 5000/);
	assert.match(salesActions, /take: SALES_RECORD_LIMIT/);
});

// ── AI routes ─────────────────────────────────────────────────────────────────

const insightRoute = readSource("app/api/ai/insight/route.js");
const chatRoute = readSource("app/api/ai/chat/route.js");

test("AI insight route exports maxDuration=60 to prevent Vercel platform timeout", () => {
	assert.match(insightRoute, /export const maxDuration = 60/);
});

test("AI chat route exports maxDuration=60 for SSE stream duration", () => {
	assert.match(chatRoute, /export const maxDuration = 60/);
});

// ── ErrorBoundary ─────────────────────────────────────────────────────────────

const errorBoundary = readSource("components/ErrorBoundary.js");

test("ErrorBoundary error div has role=alert for screen reader announcement on error", () => {
	assert.match(errorBoundary, /role="alert"/);
	assert.match(errorBoundary, /aria-live="assertive"/);
});

// ── Prisma schema indices ─────────────────────────────────────────────────────

const schema = readFileSync(
	path.join(SRC_ROOT, "..", "prisma", "schema.prisma"),
	"utf8",
);

test("Subscription model has composite userId+status index for AI/subscription queries", () => {
	assert.match(schema, /@@index\(\[userId, status\]\)/);
});

test("ExpenseRecord model has buildingId+date index for per-barn expense aggregation", () => {
	assert.match(schema, /@@index\(\[buildingId, date\]\)/);
});

// ── Dashboard API: Cache-Control private, no-store ────────────────────────────

const cattleRoute = readSource("app/api/dashboard/cattle/route.js");
const salesRoute = readSource("app/api/dashboard/sales/route.js");
const summaryRoute = readSource("app/api/dashboard/summary/route.js");

test("dashboard/cattle route sets Cache-Control private, no-store on user data", () => {
	assert.match(cattleRoute, /Cache-Control.*private.*no-store|private.*no-store.*Cache-Control/);
});

test("dashboard/sales route sets Cache-Control private, no-store on user data", () => {
	assert.match(salesRoute, /Cache-Control.*private.*no-store|private.*no-store.*Cache-Control/);
});

test("dashboard/summary route sets Cache-Control private, no-store on user data", () => {
	assert.match(summaryRoute, /Cache-Control.*private.*no-store|private.*no-store.*Cache-Control/);
});

