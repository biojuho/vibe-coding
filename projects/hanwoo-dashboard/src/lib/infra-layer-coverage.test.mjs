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

test("payments/prepare rejects customerKey not matching session user (IDOR guard) with 403", () => {
	// Prevents user A from initiating a payment order attributed to user B's customerKey
	assert.match(paymentPrepare, /buildCustomerKey\(session\.user\.id\)/);
	assert.match(paymentPrepare, /customerKey !== body\?\.customerKey/);
	assert.match(paymentPrepare, /결제 고객 정보가 현재 로그인 사용자와 일치하지 않습니다/);
	assert.match(paymentPrepare, /status: 403/);
});

test("payments/prepare rejects amount not matching PREMIUM_SUBSCRIPTION price (price tampering)", () => {
	// The server recalculates amount from the product constant — client cannot alter it
	assert.match(paymentPrepare, /amount !== PREMIUM_SUBSCRIPTION\.amount/);
	assert.match(paymentPrepare, /결제 금액이 구독 상품 금액과 일치하지 않습니다/);
	assert.match(paymentPrepare, /status: 400/);
});

test("payments/prepare success response carries Cache-Control: no-store to prevent orderId caching", () => {
	// The prepare response includes orderId (derived from customerKey + timestamp).
	// Caching it could allow a stale orderId to be replayed — no-store forces re-fetch.
	assert.match(paymentPrepare, /"Cache-Control":\s*"no-store"/);
});

test("payments/confirm applies per-user rate limiting with 429 response", () => {
	assert.match(paymentConfirm, /checkRateLimit/);
	assert.match(paymentConfirm, /payment-confirm:/);
	assert.match(paymentConfirm, /status: 429/);
	assert.match(paymentConfirm, /Retry-After/);
});

test("payments/confirm verifies orderId belongs to session user (IDOR guard) with 403 response", () => {
	// Prevents user A from confirming user B's payment by submitting B's orderId
	assert.match(paymentConfirm, /parseCustomerKeyFromOrderId/);
	assert.match(paymentConfirm, /buildCustomerKey\(session\.user\.id\)/);
	assert.match(paymentConfirm, /orderCustomerKey !== expectedCustomerKey/);
	assert.match(paymentConfirm, /이 결제 요청은 현재 로그인 사용자와 일치하지 않습니다/);
	assert.match(paymentConfirm, /status: 403/);
});

test("payments/confirm validates amount matches PREMIUM_SUBSCRIPTION price to prevent price tampering", () => {
	// Prevents a client from submitting amount=1 to get a subscription for less
	assert.match(paymentConfirm, /amount !== PREMIUM_SUBSCRIPTION\.amount/);
	assert.match(paymentConfirm, /결제 금액이 구독 상품 금액과 일치하지 않습니다/);
});

test("payments/confirm uses atomic Prisma transaction to prevent partial payment/subscription state", () => {
	// PaymentLog upsert + Subscription upsert must both succeed or both fail
	assert.match(paymentConfirm, /prisma\.\$transaction/);
	assert.match(paymentConfirm, /paymentLog\.upsert/);
	assert.match(paymentConfirm, /subscription\.upsert/);
});

test("payments/confirm fails fast with 500 when TOSS_PAYMENTS_SECRET_KEY env var is missing", () => {
	// Missing secret key means we cannot call the Toss API at all — fail explicitly
	// rather than sending an unauthenticated request that would return 401 from Toss.
	assert.match(paymentConfirm, /process\.env\.TOSS_PAYMENTS_SECRET_KEY/);
	assert.match(paymentConfirm, /!secretKey/);
	assert.match(paymentConfirm, /결제 설정이 완료되지 않았습니다/);
});

test("payments/confirm uses Toss Basic auth header (secret-key:empty-password base64)", () => {
	// Toss Payments API requires Basic auth with secretKey as the username and empty password.
	// Using the secret key directly as a Bearer token would be rejected.
	assert.match(paymentConfirm, /Buffer\.from\(`\$\{secretKey\}:`\)\.toString\("base64"\)/);
	assert.match(paymentConfirm, /Authorization.*Basic \$\{basicAuth\}/);
});

test("payments/confirm is idempotent: DONE order returns success without re-confirming Toss", () => {
	// A client retry after a lost success response must not re-call Toss confirm
	// (Toss would reject a second confirm for the same orderId anyway).
	assert.match(paymentConfirm, /existingLog\?\.status === "DONE"/);
	assert.match(paymentConfirm, /paymentLog\.findUnique/);
	assert.match(paymentConfirm, /success: true/);
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

test("AI insight route returns 403 SUBSCRIPTION_REQUIRED for INACTIVE subscribers", () => {
	assert.match(insightRoute, /getSubscriptionStatus/);
	assert.match(insightRoute, /status.*INACTIVE/);
	assert.match(insightRoute, /status: 403/);
	assert.match(insightRoute, /SUBSCRIPTION_REQUIRED/);
});

test("AI chat route returns 403 SUBSCRIPTION_REQUIRED for INACTIVE subscribers", () => {
	assert.match(chatRoute, /getSubscriptionStatus/);
	assert.match(chatRoute, /status.*INACTIVE/);
	assert.match(chatRoute, /status: 403/);
	assert.match(chatRoute, /SUBSCRIPTION_REQUIRED/);
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

// ── Dashboard list-queries: validation error class ────────────────────────────

const listQueriesSrc = readSource("lib/dashboard/list-queries.js");

test("list-queries exports DashboardQueryValidationError for typed error handling in routes", () => {
	assert.match(listQueriesSrc, /export class DashboardQueryValidationError extends Error/);
	assert.match(listQueriesSrc, /this\.name = ["']DashboardQueryValidationError["']/);
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

test("dashboard/cattle route returns 400 on DashboardQueryValidationError for bad query params", () => {
	// Prevents crash when client sends ?limit=abc or ?penNumber=xyz — must 400 not 500
	assert.match(cattleRoute, /DashboardQueryValidationError/);
	assert.match(cattleRoute, /error instanceof DashboardQueryValidationError/);
	assert.match(cattleRoute, /status: 400/);
});

test("dashboard/sales route returns 400 on DashboardQueryValidationError for bad query params", () => {
	const salesRouteSrc = readSource("app/api/dashboard/sales/route.js");
	assert.match(salesRouteSrc, /DashboardQueryValidationError/);
	assert.match(salesRouteSrc, /error instanceof DashboardQueryValidationError/);
	assert.match(salesRouteSrc, /status: 400/);
});

// ── Auth routes: password length guard ───────────────────────────────────────

const registerRoute = readSource("app/api/auth/register/route.js");
const changePasswordRoute = readSource("app/api/auth/change-password/route.js");
const authValidation = readSource("lib/auth-validation.mjs");

test("auth-validation module enforces MAX_PASSWORD_LENGTH=72 to prevent bcrypt DoS via long passwords", () => {
	// MAX_PASSWORD_LENGTH is now shared between register and change-password routes
	assert.match(authValidation, /export const MAX_PASSWORD_LENGTH = 72/);
	assert.match(authValidation, /password\.length > MAX_PASSWORD_LENGTH/);
	assert.match(authValidation, /최대.*MAX_PASSWORD_LENGTH.*자까지 입력할 수 있습니다/);
});

test("register route imports validateRegistrationPayload from auth-validation (not duplicating logic)", () => {
	assert.match(registerRoute, /validateRegistrationPayload/);
	assert.match(registerRoute, /auth-validation/);
});

test("change-password route imports validateChangePasswordPayload from auth-validation (not duplicating logic)", () => {
	assert.match(changePasswordRoute, /validateChangePasswordPayload/);
	assert.match(changePasswordRoute, /auth-validation/);
});

// ── Auth routes: rate limiting ────────────────────────────────────────────────

test("register route applies IP-based rate limiting (5 req/hr) to prevent account enumeration", () => {
	assert.match(registerRoute, /checkRateLimit/);
	assert.match(registerRoute, /register:/);
	assert.match(registerRoute, /maxRequests: 5/);
	assert.match(registerRoute, /windowMs: 3600000/);
	assert.match(registerRoute, /status: 429/);
	assert.match(registerRoute, /Retry-After/);
});

test("change-password route applies per-user rate limiting (5 req/hr) to prevent brute-force", () => {
	assert.match(changePasswordRoute, /checkRateLimit/);
	assert.match(changePasswordRoute, /change-password.*session\.user\.id/);
	assert.match(changePasswordRoute, /maxRequests: 5/);
	assert.match(changePasswordRoute, /windowMs: 3600000/);
	assert.match(changePasswordRoute, /status: 429/);
	assert.match(changePasswordRoute, /Retry-After/);
});

// ── Dashboard API: per-user rate limiting ─────────────────────────────────────

test("dashboard/cattle route applies per-user rate limiting to prevent abuse", () => {
	assert.match(cattleRoute, /checkRateLimit/);
	assert.match(cattleRoute, /dashboard-cattle.*session\.user\.id/);
	assert.match(cattleRoute, /status: 429/);
});

test("dashboard/sales route applies per-user rate limiting to prevent abuse", () => {
	assert.match(salesRoute, /checkRateLimit/);
	assert.match(salesRoute, /dashboard-sales.*session\.user\.id/);
	assert.match(salesRoute, /status: 429/);
});

test("dashboard/summary route applies per-user rate limiting to prevent abuse", () => {
	assert.match(summaryRoute, /checkRateLimit/);
	assert.match(summaryRoute, /dashboard-summary.*session\.user\.id/);
	assert.match(summaryRoute, /status: 429/);
});

// ── Dashboard list-queries: page-size cap ─────────────────────────────────────

const listQueries = readSource("lib/dashboard/list-queries.js");

test("dashboard list-queries enforces MAX_LIMIT=100 to prevent oversized DB fetches", () => {
	assert.match(listQueries, /const MAX_LIMIT = 100/);
	assert.match(listQueries, /Math\.min\(parsed, MAX_LIMIT\)/);
});

test("dashboard list-queries applies MAX_LIMIT cap in both cattle and sales parsers", () => {
	// Both parseCattleListQuery and parseSalesListQuery must delegate to parseLimit
	const parseLimitCount = (listQueries.match(/parseLimit\(/g) || []).length;
	assert.ok(parseLimitCount >= 2, `Expected parseLimit used ≥2 times, found ${parseLimitCount}`);
});

// ── AI routes: per-user rate limiting ────────────────────────────────────────

test("AI insight route applies per-user rate limiting (20 req/hr) to prevent Gemini quota exhaustion", () => {
	// Premium subscribers could exhaust the Gemini quota without rate limiting
	assert.match(insightRoute, /checkRateLimit/);
	assert.match(insightRoute, /ai-insight.*session\.user\.id|ai-insight.*userId/);
	assert.match(insightRoute, /maxRequests: 20/);
	assert.match(insightRoute, /windowMs: 3600000/);
	assert.match(insightRoute, /status: 429/);
	assert.match(insightRoute, /Retry-After/);
});

test("AI chat route applies per-user rate limiting (30 req/hr) to prevent Gemini quota exhaustion", () => {
	// Chat is more interactive than insights so gets a slightly higher limit
	assert.match(chatRoute, /checkRateLimit/);
	assert.match(chatRoute, /ai-chat.*session\.user\.id|ai-chat.*userId/);
	assert.match(chatRoute, /maxRequests: 30/);
	assert.match(chatRoute, /windowMs: 3600000/);
	assert.match(chatRoute, /status: 429/);
	assert.match(chatRoute, /Retry-After/);
});

// ── ai-chat-api.mjs: message limits ──────────────────────────────────────────

const aiChatApi = readSource("lib/ai-chat-api.mjs");

test("ai-chat-api enforces maxMessageLength=1000 to prevent prompt-injection via long inputs", () => {
	// Very long messages can be used to push system instructions out of context or flood the model
	assert.match(aiChatApi, /maxMessageLength: 1000/);
	assert.match(aiChatApi, /message\.length > AI_CHAT_LIMITS\.maxMessageLength/);
	// Error message references the constant so it stays in sync with the limit value
	assert.match(aiChatApi, /AI_CHAT_LIMITS\.maxMessageLength.*자 이내로 입력해 주세요/);
});

test("ai-chat-api caps history at maxHistoryItems=20 to prevent context exhaustion", () => {
	// Unlimited history lets a user fill the context window and push out the system instruction
	assert.match(aiChatApi, /maxHistoryItems: 20/);
	assert.match(aiChatApi, /AI_CHAT_LIMITS\.maxHistoryItems/);
});

test("ai-chat-api exports AiChatValidationError for typed error handling in routes", () => {
	assert.match(aiChatApi, /export class AiChatValidationError extends Error/);
	assert.match(aiChatApi, /this\.name = ["']AiChatValidationError["']/);
});

test("ai-chat-api fails fast with 500 when GEMINI_API_KEY is missing", () => {
	// Without an API key the route would produce an unclear Gemini SDK error;
	// the explicit guard surfaces a user-friendly error and prevents a confusing 400/200 with empty stream.
	assert.match(aiChatApi, /if \(!apiKey\)/);
	assert.match(aiChatApi, /AI 비서 설정이 완료되지 않았습니다/);
});

// ── Expense action: atomic transaction ───────────────────────────────────────

const expenseAction = readSource("lib/actions/expense.js");

test("createExpenseRecord uses atomic Prisma transaction to prevent duplicate expense on outbox failure", () => {
	// Without the transaction, an outbox write failure after expenseRecord.create
	// returns a false failure, and the client retry creates a duplicate expense
	assert.match(expenseAction, /prisma\.\$transaction/);
	assert.match(expenseAction, /expenseRecord\.create/);
	assert.match(expenseAction, /createOutboxEvent/);
});

test("createExpenseRecord validates expense input before DB write", () => {
	assert.match(expenseAction, /validateExpenseRecordInput/);
	assert.match(expenseAction, /validation\.success/);
	assert.match(expenseAction, /success: false/);
});

// ── /api/health ───────────────────────────────────────────────────────────────

const healthRoute = readSource("app/api/health/route.js");

test("health route skips DB probe during build phase (NEXT_PHASE / CI)", () => {
	assert.match(healthRoute, /NEXT_PHASE.*phase-production-build|phase-production-build.*NEXT_PHASE/);
	assert.match(healthRoute, /CI.*===.*"1"|CI.*=== '1'/);
	assert.match(healthRoute, /isBuildPhase/);
	assert.match(healthRoute, /buildHealthResponse.*skipped.*true|skipped: true/s);
});

test("health route probes DB with Prisma.$queryRaw and returns 200 on success", () => {
	assert.match(healthRoute, /prisma\.\$queryRaw/);
	assert.match(healthRoute, /connected: true/);
	assert.match(healthRoute, /buildHealthResponse/);
	assert.doesNotMatch(healthRoute, /status: 503/);
});

test("health route returns degraded response without exposing raw error in production", () => {
	assert.match(healthRoute, /connected: false/);
	assert.match(healthRoute, /isProductionLike.*NODE_ENV.*production|NODE_ENV.*production.*isProductionLike/);
	assert.match(healthRoute, /isProductionLike \? undefined : error/);
	assert.match(healthRoute, /console\.error.*Health check database warning/);
});

// ── health-response.mjs ───────────────────────────────────────────────────────

const healthResponseLib = readSource("lib/health-response.mjs");

test("buildHealthResponse returns 200+healthy on connected=true, 503+degraded on connected=false", () => {
	assert.match(healthResponseLib, /status: "healthy"/);
	assert.match(healthResponseLib, /database: "connected"/);
	assert.match(healthResponseLib, /status: "degraded"/);
	assert.match(healthResponseLib, /database: "disconnected"/);
	assert.match(healthResponseLib, /init: \{ status: 503 \}/);
	assert.match(healthResponseLib, /init: \{ status: 200 \}/);
});

test("normalizeHealthWarning accepts Error objects and strings, falls back to default", () => {
	assert.match(healthResponseLib, /value instanceof Error/);
	assert.match(healthResponseLib, /typeof value === "string"/);
	assert.match(healthResponseLib, /DEFAULT_DATABASE_WARNING/);
	assert.match(healthResponseLib, /Database connectivity issue/);
	assert.doesNotMatch(healthResponseLib, /warning: error\.message/);
});

// ── actions/building.js ───────────────────────────────────────────────────────

const buildingAction = readSource("lib/actions/building.js");

test("createBuilding validates input before DB write and returns error on invalid data", () => {
	assert.match(buildingAction, /validateBuildingInput/);
	assert.match(buildingAction, /validation\.success/);
	assert.match(buildingAction, /success: false/);
});

test("createBuilding uses buildingMutationSchema with name (max 40) and penCount (1–200)", () => {
	const validationLib = readSource("lib/action-validation.mjs");
	assert.match(validationLib, /buildingMutationSchema/);
	assert.match(validationLib, /name.*requiredText.*40|requiredText.*40.*name/);
	assert.match(validationLib, /penCount.*requiredPositiveInt.*200|requiredPositiveInt.*200.*penCount/);
	assert.match(validationLib, /칸 수는 1 이상이어야 합니다/);
});

// ── actions/feed.js ───────────────────────────────────────────────────────────

const feedAction = readSource("lib/actions/feed.js");

test("createFeedRecord validates input before DB write and returns error on invalid data", () => {
	assert.match(feedAction, /validateFeedRecordInput/);
	assert.match(feedAction, /validation\.success/);
	assert.match(feedAction, /success: false/);
});

test("feedRecordSchema enforces required roughage and concentrate as positive numbers", () => {
	const validationLib = readSource("lib/action-validation.mjs");
	assert.match(validationLib, /feedRecordSchema/);
	assert.match(validationLib, /roughage.*requiredPositiveNumber|requiredPositiveNumber.*roughage/);
	assert.match(validationLib, /concentrate.*requiredPositiveNumber|requiredPositiveNumber.*concentrate/);
	assert.match(validationLib, /조사료량은 0보다 커야 합니다/);
	assert.match(validationLib, /배합사료량은 0보다 커야 합니다/);
});

// ── actions/schedule.js ───────────────────────────────────────────────────────

const scheduleAction = readSource("lib/actions/schedule.js");

test("createScheduleEvent validates input before DB write and returns error on invalid data", () => {
	assert.match(scheduleAction, /validateScheduleEventInput/);
	assert.match(scheduleAction, /validation\.success/);
	assert.match(scheduleAction, /success: false/);
});

test("scheduleEventSchema enforces title (max 120), date, and type enum", () => {
	const validationLib = readSource("lib/action-validation.mjs");
	assert.match(validationLib, /scheduleEventSchema/);
	assert.match(validationLib, /title.*requiredText.*120|requiredText.*120.*title/);
	assert.match(validationLib, /z\.enum\(\["General", "Vaccination", "Checkup", "Breeding", "Other"\]\)/);
	assert.match(validationLib, /일정을 등록할 제목을 입력해 주세요/);
});

test("toggleEventCompletion guards id and isCompleted type before DB update", () => {
	assert.match(scheduleAction, /typeof isCompleted !== "boolean"/);
	assert.match(scheduleAction, /typeof id === "string" \? id\.trim\(\) : ""/);
	assert.match(scheduleAction, /if \(!normalizedId\)/);
});

// ── actions/inventory.js ──────────────────────────────────────────────────────

const inventoryAction = readSource("lib/actions/inventory.js");

test("addInventoryItem validates input before DB write and returns error on invalid data", () => {
	assert.match(inventoryAction, /validateInventoryItemInput/);
	assert.match(inventoryAction, /validation\.success/);
	assert.match(inventoryAction, /success: false/);
});

test("updateInventoryQuantity validates quantity before DB update", () => {
	assert.match(inventoryAction, /validateInventoryQuantityInput/);
	assert.match(inventoryAction, /validation\.success/);
});

// ── auth-credentials: timing equalization ────────────────────────────────────

const authCredentials = readSource("lib/auth-credentials.mjs");

test("authorizeCredentials uses TIMING_DUMMY_HASH to prevent username enumeration via timing side-channel", () => {
	// Without a dummy bcrypt.compare on user-not-found, login response time leaks
	// valid usernames (~1ms unknown vs ~100ms wrong-password). OWASP Auth Cheat Sheet.
	assert.match(authCredentials, /TIMING_DUMMY_HASH/);
	assert.match(authCredentials, /bcrypt\.compare\(password, TIMING_DUMMY_HASH\)/);
	assert.match(authCredentials, /Dummy compare equalizes timing|dummy compare/i);
});

// ── actions/farm-settings.js ──────────────────────────────────────────────────

const farmSettingsAction = readSource("lib/actions/farm-settings.js");

test("updateFarmSettings validates input before upsert and returns error on invalid data", () => {
	assert.match(farmSettingsAction, /validateFarmSettingsInput/);
	assert.match(farmSettingsAction, /validation\.success/);
	assert.match(farmSettingsAction, /success: false/);
});

// ── actions/cattle.js: atomic transaction ─────────────────────────────────────

const cattleAction = readSource("lib/actions/cattle.js");

test("createCattle uses atomic Prisma transaction (row + history + outbox) to prevent phantom cattle on outbox failure", () => {
	// Without the transaction, an outbox write failure after cattle.create
	// returns a false failure; a retry then hits the tagNumber unique constraint
	// for a row the user believes was never saved — creating a confusing duplicate error.
	assert.match(cattleAction, /prisma\.\$transaction/);
	assert.match(cattleAction, /tx\.cattle\.create/);
	assert.match(cattleAction, /recordCattleHistory/);
	assert.match(cattleAction, /createOutboxEvent/);
});

test("createCattle validates cattle input before DB write", () => {
	assert.match(cattleAction, /validateCattleMutationInput/);
	assert.match(cattleAction, /validation\.success/);
	assert.match(cattleAction, /success: false/);
});

test("createCattle detects duplicate tagNumber via Prisma P2002 and returns friendly message", () => {
	// tagNumber has a unique constraint — a clean 409-like response beats a 500
	assert.match(cattleAction, /isCattleTagDuplicateError/);
	assert.match(cattleAction, /P2002/);
	assert.match(cattleAction, /이미 등록된 이력번호입니다/);
});

test("recordCalving uses atomic Prisma transaction (mother update + calf create + history + outbox)", () => {
	// Without the transaction, a calf could be created while the mother's status fails to update
	// or the history entry is lost — leaving inconsistent state that the UI can't resolve.
	assert.match(cattleAction, /export async function recordCalving/);
	// The calving transaction creates the calf inside the same tx as mother update
	assert.match(cattleAction, /tx\.cattle\.create[\s\S]{0,200}송아지/);
	assert.match(cattleAction, /tx\.cattleHistory\.createMany/);
});

test("deleteCattle (archive) uses atomic Prisma transaction to prevent orphaned history on outbox failure", () => {
	// Without the transaction, the cattle.update (isArchived=true) could succeed while the
	// outbox write fails, leaving an archived cattle with no dashboard cache invalidation event.
	assert.match(cattleAction, /isArchived: true/);
	assert.match(cattleAction, /archivedAt: new Date\(\)/);
	// The archive must be atomic with history + outbox
	assert.match(cattleAction, /await prisma\.\$transaction/);
	assert.match(cattleAction, /tx\.cattle\.update[\s\S]{0,100}isArchived: true/);
});

// ── actions/sales.js: atomic transaction ──────────────────────────────────────

const salesAction = readSource("lib/actions/sales.js");

test("createSalesRecord uses atomic Prisma transaction to prevent duplicate sale on outbox failure", () => {
	// SalesRecord has no unique constraint — without the transaction an outbox failure
	// after salesRecord.create returns a false failure and the retry creates a duplicate sale.
	assert.match(salesAction, /prisma\.\$transaction/);
	assert.match(salesAction, /tx\.salesRecord\.create/);
	assert.match(salesAction, /createOutboxEvent/);
});

test("createSalesRecord validates sales input before DB write", () => {
	assert.match(salesAction, /validateSalesRecordInput/);
	assert.match(salesAction, /validation\.success/);
	assert.match(salesAction, /success: false/);
});

