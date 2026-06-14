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

// ── constants.js ──────────────────────────────────────────────────────────────

const constants = readSource("lib/constants.js");

test("constants exports correct estrus cycle parameters for Korean hanwoo management", () => {
	// Hanwoo estrus cycle is 21 days; alert window is 3 days before
	assert.match(constants, /ESTRUS_CYCLE_DAYS = 21/);
	assert.match(constants, /ESTRUS_ALERT_WINDOW = 3/);
});

test("constants exports correct calving parameters for pregnant cattle tracking", () => {
	// Hanwoo gestation period is 285 days; alert window is 14 days before
	assert.match(constants, /CALVING_DAYS = 285/);
	assert.match(constants, /CALVING_ALERT_WINDOW = 14/);
});

test("constants exports all 6 breed status options in Korean", () => {
	const breeds = ["송아지", "육성우", "번식우", "임신우", "비육우", "씨수소"];
	for (const breed of breeds) {
		assert.ok(constants.includes(breed), `Missing breed: ${breed}`);
	}
	assert.match(constants, /BREED_STATUS_OPTIONS/);
});

test("constants STATUS_COLORS has bg/text/dot for all 6 breeds", () => {
	assert.match(constants, /STATUS_COLORS/);
	// Each breed has 3 color properties
	const colorEntries = constants.match(/\{ bg:/g) || [];
	assert.ok(colorEntries.length >= 6, "Expected at least 6 breed color entries");
	assert.match(constants, /dot:/);
});

test("constants exports 3 buildings with Korean names and pen counts", () => {
	assert.match(constants, /BUILDINGS/);
	assert.match(constants, /1동/);
	assert.match(constants, /2동/);
	assert.match(constants, /3동/);
	assert.match(constants, /penCount: 32/);
	// All 3 buildings have penCount 32
	const penCounts = constants.match(/penCount: 32/g) || [];
	assert.equal(penCounts.length, 3);
});

test("constants exports Namwon GPS coordinates for weather API", () => {
	// Namwon, North Jeolla Province — location of the reference farm
	assert.match(constants, /NAMWON_LAT = 35\.446/);
	assert.match(constants, /NAMWON_LNG = 127\.344/);
});

test("constants FEED_STANDARDS covers all 6 breeds with roughage and concentrate fields", () => {
	assert.match(constants, /FEED_STANDARDS/);
	const breeds = ["송아지", "육성우", "번식우", "임신우", "비육우", "씨수소"];
	for (const breed of breeds) {
		assert.ok(constants.includes(breed), `FEED_STANDARDS missing breed: ${breed}`);
	}
	assert.match(constants, /roughage:/);
	assert.match(constants, /roughageKg:/);
	assert.match(constants, /concentrate:/);
	assert.match(constants, /concentrateKg:/);
	assert.match(constants, /note:/);
});

// ── utils.js ──────────────────────────────────────────────────────────────────

const utils = readSource("lib/utils.js");

test("utils getMonthAge uses calendar-month difference with max(1,...) floor", () => {
	assert.match(utils, /getMonthAge/);
	assert.match(utils, /\(today\.getFullYear\(\) - date\.getFullYear\(\)\) \* 12/);
	assert.match(utils, /Math\.max\(\s*1,/);
});

test("utils getNextEstrusDate advances by ESTRUS_CYCLE_DAYS until after today", () => {
	assert.match(utils, /getNextEstrusDate/);
	assert.match(utils, /next\.setDate\(next\.getDate\(\) \+ ESTRUS_CYCLE_DAYS\)/);
	assert.match(utils, /while \(next <= today\)/);
});

test("utils getCalvingDate adds CALVING_DAYS to pregnancy start date", () => {
	assert.match(utils, /getCalvingDate/);
	assert.match(utils, /CALVING_DAYS \* DAY_MS/);
});

test("utils toLocalInputDate uses local calendar components to avoid KST/UTC day shift", () => {
	// Using toISOString() shifts the day for UTC+9 users before 09:00 — this
	// comment is in the source explaining why getFullYear/Month/Date are used instead.
	assert.match(utils, /toLocalInputDate/);
	assert.match(utils, /getFullYear\(\)/);
	assert.match(utils, /getMonth\(\) \+ 1/);
	assert.match(utils, /getDate\(\)/);
	assert.doesNotMatch(utils, /toISOString\(\)\.slice\(0, 10\)/);
});

test("utils calcTHI uses standard livestock temperature-humidity index formula", () => {
	// Standard formula: 1.8*T + 32 - (0.55 - 0.0055*RH) * (1.8*T - 26)
	assert.match(utils, /calcTHI/);
	assert.match(utils, /1\.8 \* temp \+ 32/);
	assert.match(utils, /0\.55 - 0\.0055 \* humidity/);
	assert.match(utils, /1\.8 \* temp - 26/);
});

test("utils getTHILevel returns 4 levels with Korean labels at correct thresholds", () => {
	assert.match(utils, /getTHILevel/);
	// Thresholds: <72 정상, <78 주의, <89 경고, else 위험
	assert.match(utils, /thi < 72/);
	assert.match(utils, /thi < 78/);
	assert.match(utils, /thi < 89/);
	assert.match(utils, /정상/);
	assert.match(utils, /주의/);
	assert.match(utils, /경고/);
	assert.match(utils, /위험/);
});

test("utils getLivestockWeatherAlerts triggers heat warnings at 33°C and danger at 35°C", () => {
	assert.match(utils, /getLivestockWeatherAlerts/);
	assert.match(utils, /day\.tempMax >= 35/);
	assert.match(utils, /day\.tempMax >= 33/);
	assert.match(utils, /폭염 경보/);
	assert.match(utils, /고온 주의/);
});

test("utils getLivestockWeatherAlerts triggers cold warnings at -5°C and danger at -10°C", () => {
	assert.match(utils, /day\.tempMin <= -10/);
	assert.match(utils, /day\.tempMin <= -5/);
	assert.match(utils, /한파 경보/);
	assert.match(utils, /저온 주의/);
});

test("utils getLivestockWeatherAlerts triggers rain warning at 80% precipitation probability", () => {
	assert.match(utils, /day\.precipProb >= 80/);
	assert.match(utils, /강수 확률/);
});

test("utils formatMoney uses Korean number format via Intl.NumberFormat", () => {
	assert.match(utils, /formatMoney/);
	assert.match(utils, /new Intl\.NumberFormat\(["']ko-KR["']\)/);
});

test("utils toFiniteNumber falls back for non-finite values", () => {
	assert.match(utils, /toFiniteNumber/);
	assert.match(utils, /Number\.isFinite\(amount\) \? amount : fallback/);
});

test("utils normalizes malformed weather forecast input before iterating", () => {
	assert.match(utils, /normalizeLivestockWeatherForecast/);
	assert.match(utils, /Array\.isArray\(forecast\)/);
	assert.match(utils, /isLivestockWeatherForecastDay/);
	assert.match(utils, /!Array\.isArray\(day\)/);
});

// ── offlineQueue.js ───────────────────────────────────────────────────────────

const queue = readSource("lib/offlineQueue.js");

test("offlineQueue uses stable localStorage key names", () => {
	assert.match(queue, /QUEUE_KEY = ["']joolife-offline-queue["']/);
	assert.match(queue, /DEAD_LETTER_KEY = ["']joolife-offline-dead-letter["']/);
});

test("offlineQueue caps dead letter queue at 100 entries", () => {
	assert.match(queue, /DEAD_LETTER_LIMIT = 100/);
	assert.match(queue, /queue\.slice\(-DEAD_LETTER_LIMIT\)/);
});

test("offlineQueue normalizeQueueItem rejects items without a non-empty action string", () => {
	assert.match(queue, /normalizeQueueItem/);
	assert.match(queue, /typeof item\.action !== ["']string["']/);
	assert.match(queue, /item\.action\.length === 0/);
	assert.match(queue, /return null/);
});

test("offlineQueue preserves retry metadata fields from offline-sync-state", () => {
	// offlineQueue delegates metadata normalization to normalizeOfflineQueueMetadata
	assert.match(queue, /normalizeOfflineQueueMetadata/);
	assert.match(queue, /\.\.\.normalizeOfflineQueueMetadata\(item\)/);
	// The spread occurs inside normalizeQueueItem's return object
	assert.match(queue, /return \{[\s\S]{1,400}\.\.\.normalizeOfflineQueueMetadata\(item\)/);
});

test("offlineQueue exports all 9 public APIs", () => {
	const apis = [
		"getQueue",
		"getDeadLetterQueue",
		"enqueue",
		"setQueue",
		"setDeadLetterQueue",
		"appendDeadLetterQueue",
		"clearQueue",
		"clearDeadLetterQueue",
		"queueSize",
	];
	for (const api of apis) {
		assert.ok(queue.includes(api), `Missing export: ${api}`);
	}
});

test("offlineQueue is a no-op in non-browser environments (SSR safe)", () => {
	// All write paths guard typeof window === "undefined"
	assert.match(queue, /typeof window === ["']undefined["']/);
});

test("offlineQueue enqueue wraps normalizeQueueItem and returns null for invalid actions", () => {
	assert.match(queue, /export function enqueue\(action, args\)/);
	assert.match(queue, /const nextItem = normalizeQueueItem\(\{ action, args/);
	assert.match(queue, /if \(!nextItem\) \{/);
	assert.match(queue, /return null/);
});
