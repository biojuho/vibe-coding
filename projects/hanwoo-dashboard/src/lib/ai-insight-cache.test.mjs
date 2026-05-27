import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
	buildCacheKey,
	buildDayKey,
	cacheSizeForTests,
	clearCacheKey,
	dropCachedInsight,
	getCachedInsight,
	loadCachedInsight,
	resetCacheStoreForTests,
	saveCachedInsight,
	setCachedInsight,
	summaryHash,
} from "./ai-insight-cache.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

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

function makeInsights() {
	return [
		{ title: "발정 점검", body: "오늘 발정 가능성이 높은 ...", priority: "high" },
		{ title: "출하 검토", body: "출하 후보 1두 ...", priority: "medium" },
		{ title: "사료 회전", body: "사료 재고 ...", priority: "low" },
	];
}

test("buildDayKey returns Asia/Seoul YYYY-MM-DD for a known UTC instant", () => {
	// 2026-05-27 20:00 UTC == 2026-05-28 05:00 Asia/Seoul
	const instant = new Date("2026-05-27T20:00:00Z");
	assert.equal(buildDayKey(instant), "2026-05-28");
	// 2026-05-27 14:59 UTC == 2026-05-27 23:59 Asia/Seoul
	assert.equal(buildDayKey(new Date("2026-05-27T14:59:00Z")), "2026-05-27");
});

test("buildDayKey falls back to current day for invalid Date input", () => {
	assert.match(buildDayKey(null), /^\d{4}-\d{2}-\d{2}$/);
	assert.match(buildDayKey(new Date("invalid-date")), /^\d{4}-\d{2}-\d{2}$/);
	assert.match(buildDayKey(undefined), /^\d{4}-\d{2}-\d{2}$/);
});

test("summaryHash is deterministic and order-insensitive", () => {
	const a = summaryHash({ totalHeadcount: 10, thi: 72, alerts: [1, 2] });
	const b = summaryHash({ alerts: [1, 2], thi: 72, totalHeadcount: 10 });
	assert.equal(a, b);
	assert.equal(a.length, 16);
});

test("summaryHash differs when underlying data changes", () => {
	const a = summaryHash({ totalHeadcount: 10 });
	const b = summaryHash({ totalHeadcount: 11 });
	assert.notEqual(a, b);
});

test("summaryHash tolerates circular and non-json summary values", () => {
	const circular = { totalHeadcount: 10 };
	circular.self = circular;

	assert.equal(summaryHash(circular).length, 16);
	assert.equal(summaryHash(() => "ignored").length, 16);
});

test("buildCacheKey composes userId, dayKey, and summaryHash", () => {
	const key = buildCacheKey({
		userId: "user-123",
		dayKey: "2026-05-27",
		summary: { totalHeadcount: 5 },
	});
	assert.equal(
		key,
		`user-123:2026-05-27:${summaryHash({ totalHeadcount: 5 })}`,
	);
});

test("buildCacheKey defaults missing userId and dayKey safely", () => {
	const key = buildCacheKey({ summary: { totalHeadcount: 5 } });
	assert.match(key, /^anon:\d{4}-\d{2}-\d{2}:[0-9a-f]{16}$/);
});

test("buildCacheKey tolerates malformed helper input", () => {
	assert.match(buildCacheKey(null), /^anon:\d{4}-\d{2}-\d{2}:[0-9a-f]{16}$/);
	assert.match(buildCacheKey("bad-input"), /^anon:\d{4}-\d{2}-\d{2}:[0-9a-f]{16}$/);
});

test("setCachedInsight stores ai source and returns cached entry with age", () => {
	resetCacheStoreForTests();
	const key = "user-1:2026-05-27:hash";
	const stored = setCachedInsight(
		key,
		{ insights: makeInsights(), source: "ai" },
		1_700_000_000_000,
	);
	assert.equal(stored.source, "ai");
	assert.equal(stored.insights.length, 3);
	assert.equal(stored.ageSeconds, 0);

	const after = getCachedInsight(key, 1_700_000_010_000);
	assert.equal(after.ageSeconds, 10);
});

test("setCachedInsight rejects heuristic source and malformed payloads", () => {
	resetCacheStoreForTests();
	const key = "u:d:h";
	assert.equal(
		setCachedInsight(key, { insights: makeInsights(), source: "heuristic" }),
		null,
	);
	assert.equal(setCachedInsight(key, null), null);
	assert.equal(setCachedInsight(key, { source: "ai" }), null);
	assert.equal(setCachedInsight(key, { insights: "not-array", source: "ai" }), null);
	assert.equal(getCachedInsight(key), null);
});

test("clearCacheKey lets forceRefresh paths bypass the cache", () => {
	resetCacheStoreForTests();
	const key = "u:d:h";
	setCachedInsight(key, { insights: makeInsights(), source: "ai" });
	assert.notEqual(getCachedInsight(key), null);
	assert.equal(clearCacheKey(key), true);
	assert.equal(getCachedInsight(key), null);
});

test("setCachedInsight prunes oldest entries when capacity exceeded", () => {
	resetCacheStoreForTests();
	for (let i = 0; i < 5; i += 1) {
		setCachedInsight(
			`k-${i}`,
			{ insights: makeInsights(), source: "ai" },
			Date.now(),
			{ maxEntries: 3 },
		);
	}
	assert.equal(cacheSizeForTests(), 3);
	assert.equal(getCachedInsight("k-0"), null);
	assert.equal(getCachedInsight("k-1"), null);
	assert.notEqual(getCachedInsight("k-2"), null);
	assert.notEqual(getCachedInsight("k-4"), null);
});

test("cache read and write helpers tolerate malformed metadata input", () => {
	resetCacheStoreForTests();
	const key = "u:d:h";
	const stored = setCachedInsight(
		key,
		{ insights: makeInsights(), source: "ai" },
		"bad-now",
		null,
	);

	assert.equal(stored.source, "ai");
	assert.equal(Number.isFinite(stored.generatedAt), true);
	assert.equal(Number.isFinite(stored.ageSeconds), true);
	assert.equal(Number.isFinite(getCachedInsight(key, "bad-now").ageSeconds), true);
});

test("getCachedInsight rejects malformed key input", () => {
	assert.equal(getCachedInsight(null), null);
	assert.equal(getCachedInsight(""), null);
	assert.equal(getCachedInsight(undefined), null);
});

test("loadCachedInsight falls back to in-memory Map when Redis is not configured", async () => {
	await withoutRedisConfiguration(async () => {
		resetCacheStoreForTests();
		const key = "redis-fallback:test:hash";
		assert.equal(await loadCachedInsight(key), null);

		const stored = await saveCachedInsight(
			key,
			{ insights: makeInsights(), source: "ai" },
			1_700_000_000_000,
		);
		assert.equal(stored.backend, "memory");
		assert.equal(stored.source, "ai");
		assert.equal(stored.insights.length, 3);

		const hit = await loadCachedInsight(key, 1_700_000_005_000);
		assert.equal(hit.backend, "memory");
		assert.equal(hit.source, "ai");
		assert.equal(hit.ageSeconds, 5);
	});
});

test("saveCachedInsight rejects non-AI source on both backends", async () => {
	await withoutRedisConfiguration(async () => {
		resetCacheStoreForTests();
		const key = "non-ai:test:hash";
		assert.equal(
			await saveCachedInsight(key, { insights: makeInsights(), source: "heuristic" }),
			null,
		);
		assert.equal(await saveCachedInsight(key, null), null);
		assert.equal(await saveCachedInsight(key, { insights: "x", source: "ai" }), null);
		assert.equal(await loadCachedInsight(key), null);
	});
});

test("dropCachedInsight on memory backend removes the key and returns true", async () => {
	await withoutRedisConfiguration(async () => {
		resetCacheStoreForTests();
		const key = "drop-mem:test:hash";
		await saveCachedInsight(key, { insights: makeInsights(), source: "ai" });
		assert.notEqual(await loadCachedInsight(key), null);
		const dropped = await dropCachedInsight(key);
		assert.equal(dropped, true);
		assert.equal(await loadCachedInsight(key), null);
	});
});

test("loadCachedInsight/saveCachedInsight/dropCachedInsight reject malformed key input", async () => {
	await withoutRedisConfiguration(async () => {
		assert.equal(await loadCachedInsight(null), null);
		assert.equal(await loadCachedInsight(""), null);
		assert.equal(await saveCachedInsight(null, { insights: makeInsights(), source: "ai" }), null);
		assert.equal(await saveCachedInsight("", { insights: makeInsights(), source: "ai" }), null);
		assert.equal(await dropCachedInsight(null), false);
		assert.equal(await dropCachedInsight(""), false);
	});
});

test("ai-insight-cache source wires Redis backing through shared ensureRedisConnection helper", () => {
	const source = readFileSync(path.join(__dirname, "ai-insight-cache.mjs"), "utf8");
	// Redis backing must go through the shared helper module — not a private IORedis instance.
	assert.match(source, /from "\.\/redis\.js"/);
	assert.match(source, /ensureRedisConnection\("cache"\)/);
	assert.match(source, /isRedisConfigured\(\)/);
	// AI-insight-specific 24h TTL via SET EX
	assert.match(source, /"EX",\s*REDIS_TTL_SECONDS/);
	assert.match(source, /REDIS_TTL_SECONDS\s*=\s*24\s*\*\s*60\s*\*\s*60/);
	// Namespaced key prefix so other Redis consumers don't collide
	assert.match(source, /REDIS_KEY_PREFIX\s*=\s*"ai-insight:"/);
});
