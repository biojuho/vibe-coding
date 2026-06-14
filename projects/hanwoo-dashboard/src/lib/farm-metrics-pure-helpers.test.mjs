/**
 * Behavioral tests for farm-metrics.mjs
 *
 * All three exported functions are pure (no Prisma dependency), so we import
 * them directly and test full end-to-end behavior.
 *
 * Private helpers (toFiniteNumber, toPositiveInteger, normalizeFarmMetricOptions,
 * FEED_CATEGORY_KEYS, toValidDate, monthsBetween, isFeedExpense, startOfMonth)
 * are exercised indirectly via the public API plus source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
	computeFarmAdjustments,
	estimateMonthlyFeedCostPerHead,
	estimateMonthlyWeightGainPerHead,
} from "../lib/dashboard/farm-metrics.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/farm-metrics.mjs"),
	"utf8",
);

// ── Source-grep guards: private helpers ─────────────────────────────────────

test("farm-metrics.mjs: toFiniteNumber handles null/undefined/empty-string → 0", () => {
	assert.match(src, /function toFiniteNumber\(value\) \{/);
	assert.match(
		src,
		/if \(value === null \|\| value === undefined \|\| value === ""\) return 0;/,
	);
	assert.match(src, /Number\.isFinite\(amount\) \? amount : 0/);
});

test("farm-metrics.mjs: toPositiveInteger returns fallback for non-positive input", () => {
	assert.match(src, /function toPositiveInteger\(value, fallback\) \{/);
	assert.match(src, /Number\.isFinite\(amount\) && amount > 0 \? Math\.floor\(amount\)/);
});

test("farm-metrics.mjs: FEED_CATEGORY_KEYS contains expected categories", () => {
	assert.match(src, /const FEED_CATEGORY_KEYS = new Set\(\[/);
	assert.match(src, /"feed"/);
	assert.match(src, /"feed-roughage"/);
	assert.match(src, /"feed-concentrate"/);
	assert.match(src, /"roughage"/);
	assert.match(src, /"concentrate"/);
	assert.match(src, /"hay"/);
});

test("farm-metrics.mjs: isFeedExpense checks category against FEED_CATEGORY_KEYS", () => {
	assert.match(src, /function isFeedExpense\(record\) \{/);
	assert.match(src, /FEED_CATEGORY_KEYS\.has\(category\)/);
	assert.match(src, /record\.category.*toLowerCase\(\)/);
});

test("farm-metrics.mjs: monthsBetween uses 30.4375 days per month", () => {
	assert.match(src, /function monthsBetween\(start, end\) \{/);
	assert.match(src, /1000 \* 60 \* 60 \* 24 \* 30\.4375/);
});

test("farm-metrics.mjs: toValidDate guards with NaN check", () => {
	assert.match(src, /function toValidDate\(value\) \{/);
	assert.match(src, /if \(!value\) return null;/);
	assert.match(src, /Number\.isNaN\(date\.getTime\(\)\) \? null : date/);
});

// ── estimateMonthlyFeedCostPerHead: null/empty guards ────────────────────────

test("estimateMonthlyFeedCostPerHead returns null estimate for empty records", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [],
		activeCattleCount: 5,
	});
	assert.equal(result.estimate, null);
	assert.equal(result.sampleSize, 0);
	assert.equal(result.totalFeedSpend, 0);
	assert.equal(result.monthsCovered, 0);
});

test("estimateMonthlyFeedCostPerHead returns null estimate for zero activeCattleCount", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [{ date: new Date(), category: "feed", amount: 100000 }],
		activeCattleCount: 0,
	});
	assert.equal(result.estimate, null);
});

test("estimateMonthlyFeedCostPerHead returns null estimate for negative activeCattleCount", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [{ date: new Date(), category: "feed", amount: 100000 }],
		activeCattleCount: -1,
	});
	assert.equal(result.estimate, null);
});

test("estimateMonthlyFeedCostPerHead returns null estimate for non-array records", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: null,
		activeCattleCount: 5,
	});
	assert.equal(result.estimate, null);
});

test("estimateMonthlyFeedCostPerHead with no options uses defaults", () => {
	const result = estimateMonthlyFeedCostPerHead();
	assert.equal(result.estimate, null);
	assert.equal(result.sampleSize, 0);
});

// ── estimateMonthlyFeedCostPerHead: normal calculation ──────────────────────

test("estimateMonthlyFeedCostPerHead calculates per-head cost correctly", () => {
	const now = new Date("2024-06-15");
	// 600_000 won total feed spend across 6 months with 5 cattle → 600_000 / (6 * 5) = 20_000
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: new Date("2024-06-01"), category: "feed", amount: 200000 },
			{ date: new Date("2024-05-15"), category: "feed", amount: 200000 },
			{ date: new Date("2024-04-10"), category: "concentrate", amount: 200000 },
		],
		activeCattleCount: 5,
		now,
		windowMonths: 6,
	});
	assert.equal(result.estimate, 20000);
	assert.equal(result.sampleSize, 3);
	assert.equal(result.monthsCovered, 3);
});

test("estimateMonthlyFeedCostPerHead rounds the estimate", () => {
	const now = new Date("2024-06-15");
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: new Date("2024-06-01"), category: "feed", amount: 100001 },
		],
		activeCattleCount: 3,
		now,
		windowMonths: 1,
	});
	// 100001 / (1 * 3) = 33333.67 → rounds to 33334
	assert.equal(result.estimate, 33334);
});

test("estimateMonthlyFeedCostPerHead skips non-feed categories", () => {
	const now = new Date("2024-06-15");
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: new Date("2024-06-01"), category: "medicine", amount: 500000 },
			{ date: new Date("2024-06-01"), category: "feed", amount: 100000 },
		],
		activeCattleCount: 2,
		now,
		windowMonths: 1,
	});
	assert.equal(result.sampleSize, 1);
	assert.equal(result.totalFeedSpend, 100000);
});

test("estimateMonthlyFeedCostPerHead skips records outside the window", () => {
	const now = new Date("2024-06-15");
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			// 8 months ago — outside default 6-month window
			{ date: new Date("2023-10-01"), category: "feed", amount: 999999 },
			// within window
			{ date: new Date("2024-06-01"), category: "feed", amount: 120000 },
		],
		activeCattleCount: 2,
		now,
		windowMonths: 6,
	});
	assert.equal(result.sampleSize, 1);
	assert.equal(result.totalFeedSpend, 120000);
});

test("estimateMonthlyFeedCostPerHead recognizes all FEED_CATEGORY_KEYS variants", () => {
	const now = new Date("2024-06-15");
	const categories = [
		"feed",
		"feed-roughage",
		"feed-concentrate",
		"roughage",
		"concentrate",
		"hay",
	];
	for (const category of categories) {
		const result = estimateMonthlyFeedCostPerHead({
			expenseRecords: [{ date: now, category, amount: 60000 }],
			activeCattleCount: 1,
			now,
			windowMonths: 1,
		});
		assert.ok(
			result.sampleSize === 1,
			`category "${category}" should be counted`,
		);
	}
});

test("estimateMonthlyFeedCostPerHead is case-insensitive for category", () => {
	const now = new Date("2024-06-15");
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [{ date: now, category: "FEED", amount: 60000 }],
		activeCattleCount: 1,
		now,
		windowMonths: 1,
	});
	assert.equal(result.sampleSize, 1);
});

test("estimateMonthlyFeedCostPerHead skips records with missing or invalid date", () => {
	const now = new Date("2024-06-15");
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: null, category: "feed", amount: 100000 },
			{ date: "not-a-date", category: "feed", amount: 100000 },
			{ date: now, category: "feed", amount: 50000 },
		],
		activeCattleCount: 1,
		now,
		windowMonths: 1,
	});
	assert.equal(result.sampleSize, 1);
	assert.equal(result.totalFeedSpend, 50000);
});

test("estimateMonthlyFeedCostPerHead counts monthsCovered correctly", () => {
	const now = new Date("2024-06-15");
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: new Date("2024-06-01"), category: "feed", amount: 50000 },
			{ date: new Date("2024-06-15"), category: "feed", amount: 50000 }, // same month
			{ date: new Date("2024-05-10"), category: "feed", amount: 50000 }, // different month
		],
		activeCattleCount: 1,
		now,
		windowMonths: 6,
	});
	assert.equal(result.monthsCovered, 2); // June + May
	assert.equal(result.sampleSize, 3);
});

// ── estimateMonthlyWeightGainPerHead ────────────────────────────────────────

test("estimateMonthlyWeightGainPerHead returns null estimate for empty salesRecords", () => {
	const result = estimateMonthlyWeightGainPerHead({ salesRecords: [] });
	assert.equal(result.estimate, null);
	assert.equal(result.sampleSize, 0);
});

test("estimateMonthlyWeightGainPerHead returns null estimate with no options", () => {
	const result = estimateMonthlyWeightGainPerHead();
	assert.equal(result.estimate, null);
});

test("estimateMonthlyWeightGainPerHead calculates ADG when purchaseDate and purchaseWeight available", () => {
	const now = new Date("2024-06-15");
	const cattleById = new Map([
		[
			"cow1",
			{
				birthDate: new Date("2022-01-01"),
				purchaseDate: new Date("2023-01-01"), // 12 months before sale
				purchaseWeight: 300, // kg at purchase
				weight: 600, // kg at sale
			},
		],
	]);
	const salesRecords = [
		{ cattleId: "cow1", saleDate: new Date("2024-01-01"), weight: 600 },
	];
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 24,
	});
	// 600 - 300 = 300kg gain over 12 months ≈ 25 kg/month
	assert.ok(result.estimate !== null);
	assert.ok(result.estimate > 20 && result.estimate < 30);
	assert.equal(result.sampleSize, 1);
});

test("estimateMonthlyWeightGainPerHead falls back to birthDate when no purchaseDate", () => {
	const now = new Date("2024-06-15");
	// birthDate ~24 months before sale, weight 600, birthWeight fallback 40
	const birthDate = new Date("2022-06-01");
	const saleDate = new Date("2024-06-01");
	const cattleById = new Map([
		[
			"cow2",
			{
				birthDate,
				weight: 600,
			},
		],
	]);
	const salesRecords = [{ cattleId: "cow2", saleDate }];
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 36,
	});
	// (600 - 40) / 24months ≈ 23.33 kg/month → rounds to 23.3
	assert.ok(result.estimate !== null);
	assert.ok(result.estimate > 20 && result.estimate < 30);
	assert.equal(result.sampleSize, 1);
});

test("estimateMonthlyWeightGainPerHead uses custom birthWeightKg fallback", () => {
	const now = new Date("2024-06-15");
	const birthDate = new Date("2022-06-01");
	const saleDate = new Date("2024-06-01");
	const cattleById = new Map([
		[
			"cow3",
			{
				birthDate,
				weight: 600,
			},
		],
	]);
	const salesRecords = [{ cattleId: "cow3", saleDate }];
	const result1 = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 36,
		birthWeightKg: 40,
	});
	const result2 = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 36,
		birthWeightKg: 50,
	});
	// Different birth weights → different estimates
	assert.notEqual(result1.estimate, result2.estimate);
});

test("estimateMonthlyWeightGainPerHead skips sales outside the window", () => {
	const now = new Date("2024-06-15");
	const cattleById = new Map([
		["cow4", { birthDate: new Date("2019-01-01"), weight: 700 }],
	]);
	const salesRecords = [
		// 24 months ago, outside 12-month window
		{ cattleId: "cow4", saleDate: new Date("2022-06-01") },
	];
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 12,
	});
	assert.equal(result.estimate, null);
	assert.equal(result.sampleSize, 0);
});

test("estimateMonthlyWeightGainPerHead skips sale with no matching cattle", () => {
	const now = new Date("2024-06-15");
	const salesRecords = [
		{ cattleId: "unknown_id", saleDate: new Date("2024-05-01") },
	];
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById: new Map(),
		now,
		windowMonths: 12,
	});
	assert.equal(result.estimate, null);
});

test("estimateMonthlyWeightGainPerHead accepts plain object for cattleById", () => {
	const now = new Date("2024-06-15");
	const birthDate = new Date("2022-06-01");
	const saleDate = new Date("2024-06-01");
	const cattleById = {
		cow5: { birthDate, weight: 600 },
	};
	const salesRecords = [{ cattleId: "cow5", saleDate }];
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 36,
	});
	assert.ok(result.estimate !== null);
	assert.equal(result.sampleSize, 1);
});

test("estimateMonthlyWeightGainPerHead averages multiple sales", () => {
	const now = new Date("2024-06-15");
	const birthDate = new Date("2022-06-01");
	const saleDate = new Date("2024-06-01");
	const cattleById = new Map([
		["cowA", { birthDate, weight: 600 }], // ~23.3 kg/month
		["cowB", { birthDate, weight: 700 }], // ~27.5 kg/month
	]);
	const salesRecords = [
		{ cattleId: "cowA", saleDate },
		{ cattleId: "cowB", saleDate },
	];
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords,
		cattleById,
		now,
		windowMonths: 36,
	});
	assert.equal(result.sampleSize, 2);
	assert.ok(result.estimate !== null);
	// Should be between the two individual estimates
	assert.ok(result.estimate > 20 && result.estimate < 30);
});

// ── computeFarmAdjustments ────────────────────────────────────────────────────

test("computeFarmAdjustments falls back to defaults when no data", () => {
	const defaults = {
		defaultMonthlyFeedCost: 150000,
		defaultMonthlyWeightGain: 30,
	};
	const result = computeFarmAdjustments({
		expenseRecords: [],
		salesRecords: [],
		cattleById: new Map(),
		activeCattleCount: 0,
		defaults,
	});
	assert.equal(result.feedCostPerHead, 150000);
	assert.equal(result.weightGainPerHead, 30);
	assert.equal(result.isCustomized, false);
});

test("computeFarmAdjustments sets isCustomized=true when feedCost estimate available", () => {
	const now = new Date("2024-06-15");
	const defaults = { defaultMonthlyFeedCost: 150000, defaultMonthlyWeightGain: 30 };
	const result = computeFarmAdjustments({
		expenseRecords: [
			{ date: now, category: "feed", amount: 450000 },
		],
		salesRecords: [],
		cattleById: new Map(),
		activeCattleCount: 3,
		now,
		defaults,
	});
	assert.equal(result.isCustomized, true);
	assert.ok(Number.isFinite(result.feedCostPerHead));
	assert.notEqual(result.feedCostPerHead, 150000);
});

test("computeFarmAdjustments returns evidence sub-object", () => {
	const defaults = { defaultMonthlyFeedCost: 150000, defaultMonthlyWeightGain: 30 };
	const result = computeFarmAdjustments({ defaults });
	assert.ok("feedCost" in result.evidence);
	assert.ok("weightGain" in result.evidence);
});

test("computeFarmAdjustments handles null/non-object options gracefully", () => {
	assert.doesNotThrow(() => computeFarmAdjustments(null));
	assert.doesNotThrow(() => computeFarmAdjustments(undefined));
	assert.doesNotThrow(() => computeFarmAdjustments([]));
});

test("computeFarmAdjustments uses farm data over defaults when both feed and weight available", () => {
	const now = new Date("2024-06-15");
	const birthDate = new Date("2022-06-01");
	const saleDate = new Date("2024-06-01");
	const cattleById = new Map([["cow1", { birthDate, weight: 600 }]]);
	const defaults = { defaultMonthlyFeedCost: 999999, defaultMonthlyWeightGain: 999 };
	const result = computeFarmAdjustments({
		expenseRecords: [{ date: now, category: "feed", amount: 600000 }],
		salesRecords: [{ cattleId: "cow1", saleDate }],
		cattleById,
		activeCattleCount: 2,
		now,
		defaults,
	});
	// Both estimates are from real data, so neither should be the sentinel value
	assert.notEqual(result.feedCostPerHead, 999999);
	assert.notEqual(result.weightGainPerHead, 999);
	assert.equal(result.isCustomized, true);
});
