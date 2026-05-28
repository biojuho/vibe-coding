import assert from "node:assert/strict";
import test from "node:test";

import {
	computeFarmAdjustments,
	estimateMonthlyFeedCostPerHead,
	estimateMonthlyWeightGainPerHead,
} from "./farm-metrics.mjs";

const NOW = new Date("2026-05-20T00:00:00Z");

test("estimateMonthlyFeedCostPerHead returns null when no records", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [],
		activeCattleCount: 10,
		now: NOW,
	});
	assert.equal(result.estimate, null);
	assert.equal(result.sampleSize, 0);
	assert.equal(result.totalFeedSpend, 0);
});

test("estimateMonthlyFeedCostPerHead returns null when no active cattle", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: "2026-05-01", category: "feed", amount: 500000 },
		],
		activeCattleCount: 0,
		now: NOW,
	});
	assert.equal(result.estimate, null);
});

test("estimateMonthlyFeedCostPerHead averages over 6 months and active cattle", () => {
	// 5 feed records totaling 900,000원 over 3 distinct months, 10 active cattle, 6-month window
	// → 900,000 / (6 * 10) = 15,000원
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: "2026-04-10", category: "feed", amount: 200000 },
			{ date: "2026-03-15", category: "feed", amount: 200000 },
			{ date: "2026-02-20", category: "feed", amount: 250000 },
			{ date: "2026-04-22", category: "feed", amount: 100000 },
			{ date: "2026-03-30", category: "feed", amount: 150000 },
		],
		activeCattleCount: 10,
		now: NOW,
	});
	assert.equal(result.estimate, 15000);
	assert.equal(result.sampleSize, 5);
	assert.equal(result.totalFeedSpend, 900000);
	assert.equal(result.monthsCovered, 3);
});

test("estimateMonthlyFeedCostPerHead ignores non-feed and out-of-window records", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: "2026-05-01", category: "medicine", amount: 200000 },
			{ date: "2025-09-01", category: "feed", amount: 999999 }, // outside 6-month window
			{ date: "2026-04-01", category: "Feed", amount: 100000 }, // case-insensitive
			{ date: "2026-04-15", category: "concentrate", amount: 50000 },
			["2026-04-20", "feed", 999999],
			{ date: "not-a-date", category: "feed", amount: 500000 },
			{ date: "2026-04-10", category: "feed", amount: -1000 }, // negative ignored
		],
		activeCattleCount: 5,
		now: NOW,
	});
	// Only the case-insensitive feed + concentrate count = 150,000원 / (6*5) = 5,000원
	assert.equal(result.estimate, 5000);
	assert.equal(result.sampleSize, 2);
	assert.equal(result.totalFeedSpend, 150000);
});

test("estimateMonthlyFeedCostPerHead falls back for malformed window months", () => {
	const result = estimateMonthlyFeedCostPerHead({
		expenseRecords: [
			{ date: "2026-04-10", category: "feed", amount: 600000 },
		],
		activeCattleCount: 10,
		now: NOW,
		windowMonths: 0,
	});

	assert.equal(result.estimate, 10000);
	assert.equal(Number.isFinite(result.estimate), true);
});

test("estimateMonthlyFeedCostPerHead ignores malformed top-level options", () => {
	for (const value of [null, [], "bad-options"]) {
		const result = estimateMonthlyFeedCostPerHead(value);

		assert.equal(result.estimate, null);
		assert.equal(result.sampleSize, 0);
		assert.equal(result.totalFeedSpend, 0);
		assert.equal(result.monthsCovered, 0);
	}
});

test("estimateMonthlyWeightGainPerHead returns null when no sales", () => {
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords: [],
		cattleById: new Map(),
		now: NOW,
	});
	assert.equal(result.estimate, null);
});

test("estimateMonthlyWeightGainPerHead uses purchase date+weight when available", () => {
	const cattleById = new Map([
		[
			"c1",
			{
				birthDate: "2024-05-01",
				purchaseDate: "2025-05-20",
				purchaseWeight: 250,
				weight: 700,
			},
		],
	]);
	// 700 - 250 = 450 kg gain over ~12 months → ~37.5 kg/month
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords: [
			{ cattleId: "c1", saleDate: "2026-05-20", weight: 700 },
		],
		cattleById,
		now: NOW,
	});
	assert.equal(result.sampleSize, 1);
	assert.ok(Math.abs(result.estimate - 37.5) < 1, `got ${result.estimate}`);
});

test("estimateMonthlyWeightGainPerHead falls back to birth date + default birth weight", () => {
	const cattleById = new Map([
		[
			"c2",
			{
				birthDate: "2024-05-20", // exactly 24 months before NOW
				weight: 700,
			},
		],
	]);
	// 700 - 40 = 660 kg over 24 months → ~27.5 kg/month
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords: [{ cattleId: "c2", saleDate: "2026-05-20", weight: 700 }],
		cattleById,
		now: NOW,
	});
	assert.equal(result.sampleSize, 1);
	assert.ok(Math.abs(result.estimate - 27.5) < 1, `got ${result.estimate}`);
});

test("estimateMonthlyWeightGainPerHead ignores out-of-window and malformed", () => {
	const cattleById = new Map([
		["good", { birthDate: "2024-01-01", weight: 700 }],
		["loss", { birthDate: "2024-01-01", weight: 30 }], // implausible loss
	]);
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords: [
			{ cattleId: "good", saleDate: "2026-05-15", weight: 700 },
			["good", "2026-05-15", 9999],
			{ cattleId: "missing", saleDate: "2026-05-15", weight: 700 },
			{ cattleId: "loss", saleDate: "2026-05-15", weight: 30 },
			{ cattleId: "good", saleDate: "2024-01-01", weight: 700 }, // outside 12mo window
		],
		cattleById,
		now: NOW,
	});
	assert.equal(result.sampleSize, 1);
	assert.ok(result.estimate > 0);
});

test("estimateMonthlyWeightGainPerHead ignores array cattle lookup values", () => {
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords: [
			{ cattleId: "array-cattle", saleDate: "2026-05-15", weight: 700 },
		],
		cattleById: {
			"array-cattle": ["2024-01-01", 700],
		},
		now: NOW,
	});

	assert.equal(result.estimate, null);
	assert.equal(result.sampleSize, 0);
});

test("estimateMonthlyWeightGainPerHead falls back for malformed window months", () => {
	const cattleById = new Map([["good", { birthDate: "2024-01-01", weight: 700 }]]);
	const result = estimateMonthlyWeightGainPerHead({
		salesRecords: [
			{ cattleId: "good", saleDate: "2026-05-15", weight: 700 },
		],
		cattleById,
		now: NOW,
		windowMonths: -1,
	});

	assert.equal(result.sampleSize, 1);
	assert.equal(Number.isFinite(result.estimate), true);
	assert.ok(result.estimate > 0);
});

test("estimateMonthlyWeightGainPerHead ignores malformed top-level options", () => {
	for (const value of [null, [], "bad-options"]) {
		const result = estimateMonthlyWeightGainPerHead(value);

		assert.equal(result.estimate, null);
		assert.equal(result.sampleSize, 0);
	}
});

test("computeFarmAdjustments falls back to defaults when farm data is missing", () => {
	const result = computeFarmAdjustments({
		expenseRecords: [],
		salesRecords: [],
		cattleById: new Map(),
		activeCattleCount: 0,
		now: NOW,
		defaults: {
			defaultMonthlyFeedCost: 150000,
			defaultMonthlyWeightGain: 30,
		},
	});
	assert.equal(result.feedCostPerHead, 150000);
	assert.equal(result.weightGainPerHead, 30);
	assert.equal(result.isCustomized, false);
});

test("computeFarmAdjustments returns customized values when farm data is available", () => {
	const cattleById = new Map([
		["c1", { birthDate: "2024-05-20", weight: 700 }],
	]);
	const result = computeFarmAdjustments({
		expenseRecords: [
			{ date: "2026-04-10", category: "feed", amount: 600000 },
		],
		salesRecords: [{ cattleId: "c1", saleDate: "2026-05-20", weight: 700 }],
		cattleById,
		activeCattleCount: 10,
		now: NOW,
		defaults: {
			defaultMonthlyFeedCost: 150000,
			defaultMonthlyWeightGain: 30,
		},
	});
	// 600,000 / (6 * 10) = 10,000
	assert.equal(result.feedCostPerHead, 10000);
	assert.ok(result.weightGainPerHead > 0 && result.weightGainPerHead < 50);
	assert.equal(result.isCustomized, true);
	assert.ok(result.evidence.feedCost.sampleSize >= 1);
	assert.ok(result.evidence.weightGain.sampleSize >= 1);
});

test("computeFarmAdjustments ignores malformed options and defaults", () => {
	for (const value of [null, [], "bad-options", { defaults: null }]) {
		const result = computeFarmAdjustments(value);

		assert.equal(result.feedCostPerHead, undefined);
		assert.equal(result.weightGainPerHead, undefined);
		assert.equal(result.isCustomized, false);
		assert.equal(result.evidence.feedCost.sampleSize, 0);
		assert.equal(result.evidence.weightGain.sampleSize, 0);
	}
});
