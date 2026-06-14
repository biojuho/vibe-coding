/**
 * Behavioral tests for private pure helpers in:
 *   AnalysisTab.js       — getMarketPriceForGrade, toMonthKey, normalizeAnalysisItems
 *   ProfitabilityWidget.js — normalizeProfitabilityItems, formatPerHeadFeedCost, formatMonthlyGain
 *
 * Both files import React/Recharts; cannot be loaded in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

const analysisSrc = readFileSync(
	path.join(SRC_ROOT, "components/tabs/AnalysisTab.js"),
	"utf8",
);
const profitSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/ProfitabilityWidget.js"),
	"utf8",
);

// ── AnalysisTab inline re-implementations ─────────────────────────────────────

const GRADE_ORDER = ["1++", "1+", "1", "2", "3", "D"];
const MARKET_GRADE_MAP = { "1++": "grade1pp", "1+": "grade1p", "1": "grade1" };

function getMarketPriceForGrade(marketPrice, grade, gender) {
	if (!marketPrice) return null;
	const key = MARKET_GRADE_MAP[grade];
	if (!key) return null;
	const isBull = typeof gender === "string" && gender.includes("수");
	const tier = isBull ? marketPrice.bull : marketPrice.cow;
	return tier?.[key] ?? null;
}

function toMonthKey(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
			const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
			if (
				Number.isNaN(strictDate.getTime()) ||
				strictDate.toISOString().slice(0, 10) !== dateKey
			) {
				return null;
			}
		}
	}

	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function normalizeAnalysisItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

// ── ProfitabilityWidget inline re-implementations ─────────────────────────────

function normalizeProfitabilityItems(data) {
	return Array.isArray(data)
		? data
				.filter(
					(item) => item && typeof item === "object" && !Array.isArray(item),
				)
				.map((item, index) => ({
					...item,
					id: item.id ?? `profitability-item-${index}`,
				}))
		: [];
}

function formatPerHeadFeedCost(value) {
	if (!Number.isFinite(value) || value <= 0) return null;
	return `${Math.round(value / 1000)}천원`;
}

function formatMonthlyGain(value) {
	if (!Number.isFinite(value) || value <= 0) return null;
	const rounded = Math.round(value * 10) / 10;
	return `${rounded}kg`;
}

// ── Source-grep guards: AnalysisTab ──────────────────────────────────────────

test("AnalysisTab.js getMarketPriceForGrade: MARKET_GRADE_MAP and bull/cow tier", () => {
	assert.match(analysisSrc, /function getMarketPriceForGrade\(marketPrice, grade, gender\)/);
	assert.match(analysisSrc, /MARKET_GRADE_MAP\[grade\]/);
	assert.match(analysisSrc, /gender\.includes\(["']수["']\)/);
	assert.match(analysisSrc, /isBull \? marketPrice\.bull : marketPrice\.cow/);
});

test("AnalysisTab.js toMonthKey uses LOCAL getFullYear/getMonth (not UTC)", () => {
	assert.match(analysisSrc, /function toMonthKey\(value\)/);
	assert.match(analysisSrc, /date\.getFullYear\(\)/);
	assert.match(analysisSrc, /date\.getMonth\(\) \+ 1/);
	// Strict: constructs UTC explicit string for YYYY-MM-DD roundtrip check
	assert.match(analysisSrc, /new Date\(`\$\{dateKey\}T00:00:00\.000Z`\)/);
});

test("AnalysisTab.js normalizeAnalysisItems filters plain objects", () => {
	assert.match(analysisSrc, /function normalizeAnalysisItems\(items\)/);
	assert.match(analysisSrc, /!Array\.isArray\(item\)/);
});

// ── Source-grep guards: ProfitabilityWidget ───────────────────────────────────

test("ProfitabilityWidget.js normalizeProfitabilityItems: id fallback profitability-item-{index}", () => {
	assert.match(profitSrc, /function normalizeProfitabilityItems\(data\)/);
	assert.match(profitSrc, /`profitability-item-\$\{index\}`/);
});

test("ProfitabilityWidget.js formatPerHeadFeedCost: null for non-finite or <=0", () => {
	assert.match(profitSrc, /function formatPerHeadFeedCost\(value\)/);
	assert.match(profitSrc, /!Number\.isFinite\(value\) \|\| value <= 0/);
	assert.match(profitSrc, /Math\.round\(value \/ 1000\)/);
});

test("ProfitabilityWidget.js formatMonthlyGain: null for non-finite or <=0", () => {
	assert.match(profitSrc, /function formatMonthlyGain\(value\)/);
	assert.match(profitSrc, /!Number\.isFinite\(value\) \|\| value <= 0/);
	assert.match(profitSrc, /Math\.round\(value \* 10\) \/ 10/);
});

// ── getMarketPriceForGrade behavioral tests ───────────────────────────────────

test("getMarketPriceForGrade returns null for falsy marketPrice", () => {
	assert.equal(getMarketPriceForGrade(null, "1++", "수"), null);
	assert.equal(getMarketPriceForGrade(undefined, "1+", "암"), null);
	assert.equal(getMarketPriceForGrade(0, "1", "수"), null);
});

test("getMarketPriceForGrade returns null for grades not in MARKET_GRADE_MAP", () => {
	const price = { bull: { grade1pp: 10000 }, cow: { grade1pp: 9000 } };
	// "2", "3", "D" have no entry in MARKET_GRADE_MAP
	assert.equal(getMarketPriceForGrade(price, "2", "수"), null);
	assert.equal(getMarketPriceForGrade(price, "3", "수"), null);
	assert.equal(getMarketPriceForGrade(price, "D", "암"), null);
});

test("getMarketPriceForGrade uses bull tier when gender includes '수'", () => {
	const price = {
		bull: { grade1pp: 10000000, grade1p: 9000000, grade1: 8000000 },
		cow: { grade1pp: 9000000, grade1p: 8000000, grade1: 7000000 },
	};
	assert.equal(getMarketPriceForGrade(price, "1++", "한우 수컷"), 10000000);
	assert.equal(getMarketPriceForGrade(price, "1+", "거세수"), 9000000);
	assert.equal(getMarketPriceForGrade(price, "1", "수"), 8000000);
});

test("getMarketPriceForGrade uses cow tier when gender does not include '수'", () => {
	const price = {
		bull: { grade1pp: 10000000 },
		cow: { grade1pp: 9000000, grade1p: 8000000, grade1: 7000000 },
	};
	assert.equal(getMarketPriceForGrade(price, "1++", "암"), 9000000);
	assert.equal(getMarketPriceForGrade(price, "1++", "암컷"), 9000000);
	assert.equal(getMarketPriceForGrade(price, "1++", null), 9000000);
	assert.equal(getMarketPriceForGrade(price, "1++", undefined), 9000000);
});

test("getMarketPriceForGrade returns null when key missing from tier", () => {
	const price = { bull: {}, cow: { grade1pp: 9000000 } };
	// bull.grade1pp doesn't exist → tier?.[key] = undefined → ?? null
	assert.equal(getMarketPriceForGrade(price, "1++", "수"), null);
});

test("getMarketPriceForGrade returns null when tier itself is missing", () => {
	const price = { cow: { grade1pp: 9000000 } }; // no .bull
	// isBull=true but marketPrice.bull is undefined → tier?.grade1pp = undefined → null
	assert.equal(getMarketPriceForGrade(price, "1++", "수"), null);
});

test("getMarketPriceForGrade grade mappings: 1++ → grade1pp, 1+ → grade1p, 1 → grade1", () => {
	const price = {
		cow: { grade1pp: 1, grade1p: 2, grade1: 3 },
		bull: { grade1pp: 4, grade1p: 5, grade1: 6 },
	};
	assert.equal(getMarketPriceForGrade(price, "1++", "암"), 1);
	assert.equal(getMarketPriceForGrade(price, "1+", "암"), 2);
	assert.equal(getMarketPriceForGrade(price, "1", "암"), 3);
	assert.equal(getMarketPriceForGrade(price, "1++", "수"), 4);
	assert.equal(getMarketPriceForGrade(price, "1+", "수"), 5);
	assert.equal(getMarketPriceForGrade(price, "1", "수"), 6);
});

// ── toMonthKey behavioral tests ────────────────────────────────────────────────

test("toMonthKey returns null for invalid date string", () => {
	assert.equal(toMonthKey("not-a-date"), null);
	assert.equal(toMonthKey("abc"), null);
});

test("toMonthKey returns null for undefined (new Date(undefined) = Invalid Date)", () => {
	assert.equal(toMonthKey(undefined), null);
});

test("toMonthKey returns a YYYY-MM string for a valid date string", () => {
	const result = toMonthKey("2026-06-15");
	assert.match(result, /^\d{4}-\d{2}$/);
});

test("toMonthKey returns a YYYY-MM string for a valid Date instance", () => {
	// Use local noon to avoid midnight timezone shifts across days
	const d = new Date(2026, 5, 15, 12, 0, 0); // June = month 5
	const result = toMonthKey(d);
	assert.equal(result, "2026-06");
});

test("toMonthKey pads single-digit months with leading zero", () => {
	const d = new Date(2026, 0, 15, 12, 0, 0); // January = month 0
	const result = toMonthKey(d);
	assert.equal(result, "2026-01");
});

test("toMonthKey returns null for invalid YYYY-MM-DD (e.g. Feb 30 doesn't roundtrip)", () => {
	assert.equal(toMonthKey("2026-02-30"), null);
	assert.equal(toMonthKey("2026-13-01"), null);
});

test("toMonthKey returns null for Invalid Date instance", () => {
	assert.equal(toMonthKey(new Date("invalid")), null);
});

test("toMonthKey GRADE_ORDER includes grades not in MARKET_GRADE_MAP", () => {
	// Structural: grades 2, 3, D are in display order but not mappable to market price
	assert.ok(GRADE_ORDER.includes("2"));
	assert.ok(GRADE_ORDER.includes("3"));
	assert.ok(GRADE_ORDER.includes("D"));
	assert.ok(!MARKET_GRADE_MAP["2"]);
	assert.ok(!MARKET_GRADE_MAP["3"]);
	assert.ok(!MARKET_GRADE_MAP["D"]);
});

// ── normalizeAnalysisItems behavioral tests ───────────────────────────────────

test("normalizeAnalysisItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeAnalysisItems(null), []);
	assert.deepEqual(normalizeAnalysisItems(undefined), []);
	assert.deepEqual(normalizeAnalysisItems({}), []);
});

test("normalizeAnalysisItems filters null, primitives, and arrays", () => {
	const items = [null, "string", 42, [], { id: "i1" }];
	assert.equal(normalizeAnalysisItems(items).length, 1);
});

test("normalizeAnalysisItems keeps plain objects regardless of content", () => {
	const items = [{ earTag: "001" }, { earTag: "002" }];
	assert.equal(normalizeAnalysisItems(items).length, 2);
});

// ── normalizeProfitabilityItems behavioral tests ──────────────────────────────

test("normalizeProfitabilityItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeProfitabilityItems(null), []);
	assert.deepEqual(normalizeProfitabilityItems(undefined), []);
	assert.deepEqual(normalizeProfitabilityItems({}), []);
});

test("normalizeProfitabilityItems generates fallback id as profitability-item-{index}", () => {
	const items = [{ name: "A" }, { name: "B" }];
	const result = normalizeProfitabilityItems(items);
	assert.equal(result[0].id, "profitability-item-0");
	assert.equal(result[1].id, "profitability-item-1");
});

test("normalizeProfitabilityItems preserves existing id (including 0)", () => {
	const items = [{ id: "existing", name: "A" }, { id: 0, name: "B" }];
	const result = normalizeProfitabilityItems(items);
	assert.equal(result[0].id, "existing");
	assert.equal(result[1].id, 0);
});

test("normalizeProfitabilityItems filters null, primitives, and arrays", () => {
	const data = [null, "string", 42, [], { id: "ok" }];
	assert.equal(normalizeProfitabilityItems(data).length, 1);
});

test("normalizeProfitabilityItems spreads other item fields through", () => {
	const items = [{ id: "p1", cattleName: "소1", profitMargin: 0.15 }];
	const result = normalizeProfitabilityItems(items);
	assert.equal(result[0].cattleName, "소1");
	assert.equal(result[0].profitMargin, 0.15);
});

// ── formatPerHeadFeedCost behavioral tests ────────────────────────────────────

test("formatPerHeadFeedCost returns null for non-finite values", () => {
	assert.equal(formatPerHeadFeedCost(NaN), null);
	assert.equal(formatPerHeadFeedCost(Infinity), null);
	assert.equal(formatPerHeadFeedCost(-Infinity), null);
	assert.equal(formatPerHeadFeedCost(undefined), null);
	assert.equal(formatPerHeadFeedCost(null), null);
});

test("formatPerHeadFeedCost returns null for zero", () => {
	assert.equal(formatPerHeadFeedCost(0), null);
});

test("formatPerHeadFeedCost returns null for negative values", () => {
	assert.equal(formatPerHeadFeedCost(-100), null);
	assert.equal(formatPerHeadFeedCost(-0.1), null);
});

test("formatPerHeadFeedCost returns formatted string for positive finite value", () => {
	assert.equal(formatPerHeadFeedCost(50000), "50천원");
	assert.equal(formatPerHeadFeedCost(1000), "1천원");
	assert.equal(formatPerHeadFeedCost(1500), "2천원"); // Math.round(1500/1000) = 2
	assert.equal(formatPerHeadFeedCost(500), "1천원"); // Math.round(500/1000) = 1
});

test("formatPerHeadFeedCost rounds to nearest thousand", () => {
	// 250000 / 1000 = 250 → "250천원"
	assert.equal(formatPerHeadFeedCost(250000), "250천원");
	// 250499 / 1000 = 250.499... → Math.round → 250
	assert.equal(formatPerHeadFeedCost(250499), "250천원");
	// 250500 / 1000 = 250.5 → Math.round → 251
	assert.equal(formatPerHeadFeedCost(250500), "251천원");
});

// ── formatMonthlyGain behavioral tests ───────────────────────────────────────

test("formatMonthlyGain returns null for non-finite values", () => {
	assert.equal(formatMonthlyGain(NaN), null);
	assert.equal(formatMonthlyGain(Infinity), null);
	assert.equal(formatMonthlyGain(-Infinity), null);
	assert.equal(formatMonthlyGain(null), null);
	assert.equal(formatMonthlyGain(undefined), null);
});

test("formatMonthlyGain returns null for zero", () => {
	assert.equal(formatMonthlyGain(0), null);
});

test("formatMonthlyGain returns null for negative values", () => {
	assert.equal(formatMonthlyGain(-1), null);
	assert.equal(formatMonthlyGain(-0.5), null);
});

test("formatMonthlyGain returns formatted string for positive finite value", () => {
	assert.equal(formatMonthlyGain(1.0), "1kg");
	assert.equal(formatMonthlyGain(0.9), "0.9kg");
	assert.equal(formatMonthlyGain(1.5), "1.5kg");
});

test("formatMonthlyGain rounds to one decimal place", () => {
	// Math.round(1.15 * 10) / 10 = Math.round(11.5) / 10 = 12 / 10 = 1.2
	assert.equal(formatMonthlyGain(1.15), "1.2kg");
	// Math.round(0.94 * 10) / 10 = Math.round(9.4) / 10 = 9 / 10 = 0.9
	assert.equal(formatMonthlyGain(0.94), "0.9kg");
	// Math.round(2.0 * 10) / 10 = 2
	assert.equal(formatMonthlyGain(2.0), "2kg");
});
