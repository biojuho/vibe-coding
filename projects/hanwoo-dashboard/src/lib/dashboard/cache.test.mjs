import assert from "node:assert/strict";
import test from "node:test";
import {
	buildCattleHistoryKey,
	buildCattleListKey,
	buildCattleListKeyPrefix,
	buildDashboardSummaryKey,
	buildMarketPriceDayKey,
	buildMarketPriceLatestKey,
	buildNotificationsKey,
	buildSalesListKey,
	buildSalesListKeyPrefix,
	deleteCachedKeys,
	deleteCachedKeysByPrefixes,
} from "./cache.js";

function withoutRedisConfiguration(callback) {
	const originalRedisUrl = process.env.REDIS_URL;
	const originalBullmqRedisUrl = process.env.BULLMQ_REDIS_URL;

	delete process.env.REDIS_URL;
	delete process.env.BULLMQ_REDIS_URL;

	try {
		return callback();
	} finally {
		if (typeof originalRedisUrl === "undefined") {
			delete process.env.REDIS_URL;
		} else {
			process.env.REDIS_URL = originalRedisUrl;
		}

		if (typeof originalBullmqRedisUrl === "undefined") {
			delete process.env.BULLMQ_REDIS_URL;
		} else {
			process.env.BULLMQ_REDIS_URL = originalBullmqRedisUrl;
		}
	}
}

test("dashboard list cache keys tolerate malformed filter objects", () => {
	assert.equal(
		buildCattleListKey(null),
		"dashboard:cattle:list:v1:default:all:all:all:all:50",
	);
	assert.equal(
		buildSalesListKey(null),
		"dashboard:sales:v1:default:all:all:start:50",
	);
});

test("dashboard cache delete helpers tolerate malformed key lists", async () => {
	await withoutRedisConfiguration(async () => {
		assert.equal(await deleteCachedKeys(null), 0);
		assert.equal(await deleteCachedKeysByPrefixes(null), 0);
	});
});

// ── Key builder behavioral tests ──────────────────────────────────────────────

test("buildDashboardSummaryKey includes version segment and farmId", () => {
	assert.equal(buildDashboardSummaryKey("farm-1"), "dashboard:summary:v1:farm-1");
	assert.equal(buildDashboardSummaryKey(), "dashboard:summary:v1:default");
	assert.equal(buildDashboardSummaryKey(null), "dashboard:summary:v1:default");
});

test("buildCattleListKey segments match filter fields in order", () => {
	assert.equal(
		buildCattleListKey({ farmId: "f1", buildingId: "b2", status: "사육중", limit: 25 }),
		"dashboard:cattle:list:v1:f1:b2:all:사육중:all:25",
	);
});

test("buildCattleListKey defaults all segments to all/50 for empty filters", () => {
	assert.equal(
		buildCattleListKey({}),
		"dashboard:cattle:list:v1:default:all:all:all:all:50",
	);
});

test("buildCattleListKeyPrefix contains only farmId after the version segment", () => {
	assert.equal(
		buildCattleListKeyPrefix("farm-99"),
		"dashboard:cattle:list:v1:farm-99",
	);
	assert.equal(
		buildCattleListKeyPrefix(),
		"dashboard:cattle:list:v1:default",
	);
});

test("buildCattleHistoryKey encodes cattleId, cursor, and limit", () => {
	assert.equal(
		buildCattleHistoryKey("cattle-1", "cursor-abc", 10),
		"dashboard:cattle:history:v1:cattle-1:cursor-abc:10",
	);
	assert.equal(
		buildCattleHistoryKey(null),
		"dashboard:cattle:history:v1:unknown:start:20",
	);
});

test("buildNotificationsKey includes farmId", () => {
	assert.equal(
		buildNotificationsKey("farm-42"),
		"dashboard:notifications:v1:farm-42",
	);
	assert.equal(buildNotificationsKey(), "dashboard:notifications:v1:default");
});

test("buildSalesListKey segments match from/to/cursor/limit in order", () => {
	assert.equal(
		buildSalesListKey({ farmId: "f1", from: "2026-01-01", to: "2026-06-30", limit: 20 }),
		"dashboard:sales:v1:f1:2026-01-01:2026-06-30:start:20",
	);
});

test("buildSalesListKeyPrefix contains only farmId", () => {
	assert.equal(buildSalesListKeyPrefix("f2"), "dashboard:sales:v1:f2");
});

test("buildMarketPriceLatestKey returns a stable fixed key", () => {
	assert.equal(buildMarketPriceLatestKey(), "market-price:latest:v1");
});

test("buildMarketPriceDayKey includes the issueDate segment", () => {
	assert.equal(buildMarketPriceDayKey("2026-06-15"), "market-price:day:v1:2026-06-15");
	assert.equal(buildMarketPriceDayKey(null), "market-price:day:v1:unknown");
});
