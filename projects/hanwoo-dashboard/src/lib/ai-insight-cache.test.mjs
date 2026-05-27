import assert from "node:assert/strict";
import test from "node:test";

import {
	buildCacheKey,
	buildDayKey,
	cacheSizeForTests,
	clearCacheKey,
	getCachedInsight,
	resetCacheStoreForTests,
	setCachedInsight,
	summaryHash,
} from "./ai-insight-cache.mjs";

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
