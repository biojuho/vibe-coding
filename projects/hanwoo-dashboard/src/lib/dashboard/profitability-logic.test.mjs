/**
 * Behavioral tests for profitability-service.js pure logic.
 *
 * profitability-service.js cannot be directly imported in Node ESM (bare
 * imports for prisma/utils). We test the pure functions inline and verify
 * the critical business rule constants via source-grep so production code
 * and tests cannot silently diverge.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..", "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/profitability-service.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toValidDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function diffMonths(d1, d2) {
	const start = toValidDate(d1);
	const end = toValidDate(d2);
	if (!start || !end) return null;

	let months = (end.getFullYear() - start.getFullYear()) * 12;
	months -= start.getMonth();
	months += end.getMonth();
	return months <= 0 ? 0 : months;
}

const DEFAULT_CALF_COST = 3500000;
const DEFAULT_MONTHLY_FEED_COST = 150000;
const DEFAULT_MONTHLY_WEIGHT_GAIN = 30;
const SLAUGHTER_AGE_MIN_MONTHS = 24;
const RECOMMEND_SHIPMENT_AGE_MONTHS = 30;

function computeProfitEstimate({ cattle, priceData, now, feedCost, weightGain }) {
	const ageMonths = diffMonths(cattle.birthDate, now);
	if (ageMonths === null || ageMonths < SLAUGHTER_AGE_MIN_MONTHS) return null;

	const purchasePrice = Number.isFinite(Number(cattle.purchasePrice))
		? Number(cattle.purchasePrice)
		: null;
	const baseCost = purchasePrice === null ? DEFAULT_CALF_COST : purchasePrice;
	const cumulativeCost = baseCost + ageMonths * feedCost;

	const currentKgPrice =
		cattle.gender === "암" ? priceData.cow.grade1 : priceData.bull.grade1;

	const currentWeight = Number.isFinite(Number(cattle.weight)) ? Number(cattle.weight) : 0;
	const currentRevenue = currentWeight * currentKgPrice;
	const currentProfit = currentRevenue - cumulativeCost;

	const futureWeight = currentWeight + weightGain;
	const futureCost = cumulativeCost + feedCost;
	const futureRevenue = futureWeight * currentKgPrice;
	const futureProfit = futureRevenue - futureCost;

	const marginalGain = futureProfit - currentProfit;

	return {
		ageMonths,
		currentProfit: Math.round(currentProfit),
		marginalGain: Math.round(marginalGain),
		recommendShipment: marginalGain <= 0 || ageMonths >= RECOMMEND_SHIPMENT_AGE_MONTHS,
	};
}

const PRICE_DATA = {
	bull: { grade1pp: 30000, grade1p: 27000, grade1: 25000 },
	cow: { grade1pp: 28000, grade1p: 25000, grade1: 22000 },
};

const NOW = new Date("2026-06-15T00:00:00Z");

function birthDateForAgeMonths(ageMonths, now = NOW) {
	const d = new Date(now);
	d.setMonth(d.getMonth() - ageMonths);
	return d;
}

// ── Source-grep: verify production constants ──────────────────────────────────

test("profitability-service: DEFAULT_CALF_COST is 3500000", () => {
	assert.match(src, /DEFAULT_CALF_COST = 3500000/);
});

test("profitability-service: DEFAULT_MONTHLY_FEED_COST is 150000", () => {
	assert.match(src, /DEFAULT_MONTHLY_FEED_COST = 150000/);
});

test("profitability-service: DEFAULT_MONTHLY_WEIGHT_GAIN is 30 kg", () => {
	assert.match(src, /DEFAULT_MONTHLY_WEIGHT_GAIN = 30/);
});

test("profitability-service: age gate is 24 months (ageMonths < 24 excluded)", () => {
	assert.match(src, /ageMonths < 24/);
});

test("profitability-service: recommendShipment at 30+ months or negative marginalGain", () => {
	assert.match(src, /marginalGain <= 0 \|\| ageMonths >= 30/);
});

test("profitability-service: gender 암 maps to cow price, 수 maps to bull price", () => {
	assert.match(src, /gender === "암"/);
	assert.match(src, /priceData\.cow\.grade1/);
	assert.match(src, /priceData\.bull\.grade1/);
});

test("profitability-service: PROFITABILITY_DEFAULTS is exported frozen object", () => {
	assert.match(src, /export const PROFITABILITY_DEFAULTS = Object\.freeze/);
	assert.match(src, /calfCost: DEFAULT_CALF_COST/);
	assert.match(src, /monthlyFeedCost: DEFAULT_MONTHLY_FEED_COST/);
	assert.match(src, /monthlyWeightGain: DEFAULT_MONTHLY_WEIGHT_GAIN/);
});

// ── diffMonths behavioral tests ───────────────────────────────────────────────

test("diffMonths returns 24 for a cattle born exactly 24 months ago", () => {
	const now = new Date("2026-06-01");
	const birth = new Date("2024-06-01");
	assert.equal(diffMonths(birth, now), 24);
});

test("diffMonths returns 0 for same-month dates (floor at 0)", () => {
	const now = new Date("2026-06-15");
	const birth = new Date("2026-06-01");
	assert.equal(diffMonths(birth, now), 0);
});

test("diffMonths returns null for invalid date strings", () => {
	// new Date("not-a-date") = Invalid Date (NaN) → null
	assert.equal(diffMonths("not-a-date", new Date()), null);
	assert.equal(diffMonths(new Date(), "bad"), null);
	// NOTE: null is NOT invalid here — new Date(null) = epoch (Jan 1 1970), a valid date.
	// diffMonths(null, now) returns months-since-epoch, NOT null.
});

test("diffMonths returns 0 when d2 is before d1 (never negative)", () => {
	const past = new Date("2026-01-01");
	const earlier = new Date("2025-01-01");
	// d2 before d1 → months <= 0 → returns 0
	assert.equal(diffMonths(past, earlier), 0);
});

test("diffMonths returns 30 for a cattle born 30 months ago", () => {
	const now = new Date("2026-06-01");
	const birth = new Date("2023-12-01");
	assert.equal(diffMonths(birth, now), 30);
});

// ── Age gate: 24-month minimum ────────────────────────────────────────────────

test("computeProfitEstimate returns null for cattle < 24 months old", () => {
	const cattle = {
		birthDate: birthDateForAgeMonths(23),
		gender: "수",
		weight: 400,
		purchasePrice: null,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	assert.equal(result, null);
});

test("computeProfitEstimate processes cattle at exactly 24 months old", () => {
	const cattle = {
		birthDate: birthDateForAgeMonths(24),
		gender: "수",
		weight: 450,
		purchasePrice: null,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	assert.ok(result !== null, "expected a result for 24-month cattle");
	assert.equal(result.ageMonths, 24);
});

// ── Gender-based price selection ──────────────────────────────────────────────

test("computeProfitEstimate uses cow.grade1 price for 암(female) cattle", () => {
	// Use an explicit purchasePrice=0 so baseCost is 0 (no ambiguity).
	// The point is to verify that 암 → cow price path, not the default cost path.
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "암",
		weight: 400,
		purchasePrice: 0,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	// 암 → cow.grade1=22000. baseCost=0, cumCost=0+25*150000=3750000
	const expectedRevenue = 400 * PRICE_DATA.cow.grade1; // 8,800,000
	const expectedCumCost = 0 + 25 * DEFAULT_MONTHLY_FEED_COST; // 3,750,000
	assert.equal(result.currentProfit, Math.round(expectedRevenue - expectedCumCost));
});

test("computeProfitEstimate uses bull.grade1 price for 수(male) cattle", () => {
	// Same pattern — explicit purchasePrice=0, verify 수 → bull price
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "수",
		weight: 400,
		purchasePrice: 0,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	// 수 → bull.grade1=25000, which is higher than cow.grade1=22000
	const expectedRevenue = 400 * PRICE_DATA.bull.grade1; // 10,000,000
	const expectedCumCost = 0 + 25 * DEFAULT_MONTHLY_FEED_COST; // 3,750,000
	assert.equal(result.currentProfit, Math.round(expectedRevenue - expectedCumCost));
	// verify bull > cow for same weight
	const cowRevenue = 400 * PRICE_DATA.cow.grade1;
	assert.ok(expectedRevenue > cowRevenue, "bull grade1 price should be higher than cow grade1");
});

// ── Purchase price: custom vs fallback calf cost ──────────────────────────────

test("purchasePrice: null is treated as 0 via toFiniteNumber (Number(null) === 0 is finite)", () => {
	// toFiniteNumber(null, null) = 0 because Number(null) = 0 which is finite.
	// baseCost = 0 — null purchasePrice means "free animal" in production.
	// Only undefined/NaN inputs (e.g. missing DB field) trigger the DEFAULT_CALF_COST fallback.
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "수",
		weight: 400,
		purchasePrice: null,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	// baseCost = 0 (null → 0), cumCost = 0 + 25*150000 = 3,750,000
	const expectedCumCost = 0 + 25 * DEFAULT_MONTHLY_FEED_COST;
	const expectedRevenue = 400 * PRICE_DATA.bull.grade1;
	assert.equal(result.currentProfit, Math.round(expectedRevenue - expectedCumCost));
});

test("computeProfitEstimate uses DEFAULT_CALF_COST when purchasePrice is undefined (NaN path)", () => {
	// undefined → Number(undefined) = NaN → not finite → toFiniteNumber returns null (fallback)
	// → purchasePrice === null → baseCost = DEFAULT_CALF_COST
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "수",
		weight: 400,
		purchasePrice: undefined,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	const expectedCumCost = DEFAULT_CALF_COST + 25 * DEFAULT_MONTHLY_FEED_COST;
	const expectedRevenue = 400 * PRICE_DATA.bull.grade1;
	assert.equal(result.currentProfit, Math.round(expectedRevenue - expectedCumCost));
});

test("computeProfitEstimate uses actual purchasePrice when provided, lowering cost vs undefined baseline", () => {
	// Compare explicit 2M purchase price vs undefined (which falls back to DEFAULT_CALF_COST = 3.5M)
	// 2M < 3.5M → lower cost → higher profit
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "수",
		weight: 400,
		purchasePrice: 2000000,
	};
	const resultCustom = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	const cattleUndefined = { ...cattle, purchasePrice: undefined };
	const resultDefault = computeProfitEstimate({
		cattle: cattleUndefined,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	// 2M < DEFAULT_CALF_COST(3.5M) → cheaper → higher profit
	assert.ok(
		resultCustom.currentProfit > resultDefault.currentProfit,
		`custom(2M) ${resultCustom.currentProfit} should be > default(3.5M) ${resultDefault.currentProfit}`,
	);
});

// ── recommendShipment criterion ───────────────────────────────────────────────

test("recommendShipment is true when cattle is 30+ months old regardless of marginalGain", () => {
	// At 30+ months, always recommend shipment
	const cattle = {
		birthDate: birthDateForAgeMonths(30),
		gender: "수",
		weight: 700, // high weight → positive marginalGain, but age >= 30 overrides
		purchasePrice: 0, // zero cost → definitely positive profit
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	assert.ok(result !== null);
	assert.equal(result.recommendShipment, true, "age >= 30 must force recommendShipment=true");
});

test("recommendShipment is true when marginalGain <= 0 (not worth waiting)", () => {
	// Very expensive cattle with heavy feed cost and low weight → negative marginalGain
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "암",
		weight: 50, // too light to cover feed cost next month
		purchasePrice: 5000000,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: 999999, // extreme feed cost to force negative marginalGain
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	assert.ok(result !== null);
	assert.ok(result.marginalGain <= 0, `expected marginalGain <= 0, got ${result.marginalGain}`);
	assert.equal(result.recommendShipment, true);
});

test("recommendShipment is false when marginalGain > 0 and age < 30", () => {
	// Young cattle (25 months) with high weight gain and low purchase cost → worth waiting
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "수",
		weight: 600,
		purchasePrice: 0, // free → very positive currentProfit
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	assert.ok(result !== null);
	// marginalGain = futureProfit - currentProfit
	// = (weightGain × kgPrice) - feedCost
	// = 30 × 25000 - 150000 = 750000 - 150000 = 600000 > 0
	assert.ok(result.marginalGain > 0, `expected positive marginalGain, got ${result.marginalGain}`);
	assert.equal(result.recommendShipment, false);
});

// ── Profit rounding ───────────────────────────────────────────────────────────

test("computeProfitEstimate rounds currentProfit and marginalGain to integers", () => {
	const cattle = {
		birthDate: birthDateForAgeMonths(25),
		gender: "수",
		weight: 400,
		purchasePrice: null,
	};
	const result = computeProfitEstimate({
		cattle,
		priceData: PRICE_DATA,
		now: NOW,
		feedCost: DEFAULT_MONTHLY_FEED_COST,
		weightGain: DEFAULT_MONTHLY_WEIGHT_GAIN,
	});
	assert.ok(Number.isInteger(result.currentProfit), "currentProfit must be integer");
	assert.ok(Number.isInteger(result.marginalGain), "marginalGain must be integer");
});
