/**
 * Behavioral tests for private pure helpers in FinancialChartWidget.js:
 *   toMonthKey                          — Date/string → "YYYY-MM" or null
 *   normalizeFinancialChartItems        — array filter (plain objects, no id requirement)
 *   normalizeFinancialChartWidgetOptions — object guard
 *   buildFallbackChartData              — per-month aggregation of sales/expenses/profit
 *   buildSeriesChartData                — maps seriesData rows to chart entries
 *
 * FinancialChartWidget.js imports React and recharts; cannot load in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "components/widgets/FinancialChartWidget.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

const REVENUE_KEY = "revenue";
const EXPENSE_KEY = "expense";
const PROFIT_KEY = "profit";

function toFiniteNumber(value) {
	const n = Number(value);
	return Number.isFinite(n) ? n : 0;
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

function normalizeFinancialChartItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeFinancialChartWidgetOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

// Inline aggregation (mirrors the component's non-React logic)
function buildFallbackChartData(saleRecords, expenseRecords, recentKeys) {
	const safeSales = normalizeFinancialChartItems(saleRecords);
	const safeCosts = normalizeFinancialChartItems(expenseRecords);

	const salesByMonth = {};
	safeSales.forEach((record) => {
		const key = toMonthKey(record.saleDate);
		if (!key) return;
		salesByMonth[key] = (salesByMonth[key] || 0) + toFiniteNumber(record.price);
	});

	const expensesByMonth = {};
	safeCosts.forEach((record) => {
		const key = toMonthKey(record.date);
		if (!key) return;
		expensesByMonth[key] =
			(expensesByMonth[key] || 0) + toFiniteNumber(record.amount);
	});

	return recentKeys.map((key) => ({
		name: key,
		[REVENUE_KEY]: salesByMonth[key] || 0,
		[EXPENSE_KEY]: Math.floor(expensesByMonth[key] || 0),
		[PROFIT_KEY]: (salesByMonth[key] || 0) - (expensesByMonth[key] || 0),
	}));
}

function buildSeriesChartData(seriesData) {
	return normalizeFinancialChartItems(seriesData).map((row) => ({
		name: row.month,
		[REVENUE_KEY]: toFiniteNumber(row.revenue),
		[EXPENSE_KEY]: Math.floor(toFiniteNumber(row.expense)),
		[PROFIT_KEY]: toFiniteNumber(row.profit),
	}));
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("FinancialChartWidget.js defines toMonthKey with local-time YYYY-MM format", () => {
	assert.match(src, /function toMonthKey\(value\)/);
	assert.match(src, /date\.getFullYear\(\)/);
	assert.match(src, /date\.getMonth\(\) \+ 1/);
	assert.match(src, /\.padStart\(2, ["']0["']\)/);
});

test("FinancialChartWidget.js normalizeFinancialChartItems filters plain objects", () => {
	assert.match(src, /function normalizeFinancialChartItems\(items\)/);
	assert.match(src, /!Array\.isArray\(item\)/);
});

test("FinancialChartWidget.js normalizeFinancialChartWidgetOptions returns object or {}", () => {
	assert.match(src, /function normalizeFinancialChartWidgetOptions\(options\)/);
	assert.match(src, /typeof options === ["']object["'] && !Array\.isArray\(options\)/);
});

test("FinancialChartWidget.js aggregates saleRecords by saleDate key", () => {
	assert.match(src, /const key = toMonthKey\(record\.saleDate\);/);
	assert.match(src, /salesByMonth\[key\]/);
});

test("FinancialChartWidget.js aggregates expenseRecords by date key", () => {
	assert.match(src, /const key = toMonthKey\(record\.date\);/);
	assert.match(src, /expensesByMonth\[key\]/);
});

test("FinancialChartWidget.js uses Math.floor on expense values", () => {
	assert.match(src, /Math\.floor\(expensesByMonth\[key\]/);
});

test("FinancialChartWidget.js uses seriesData branch when safeSeriesData.length > 0", () => {
	assert.match(src, /safeSeriesData\.length > 0/);
	assert.match(src, /Math\.floor\(toFiniteNumber\(row\.expense\)\)/);
});

// ── toMonthKey behavioral tests ───────────────────────────────────────────────

test("toMonthKey returns null for invalid date strings", () => {
	assert.equal(toMonthKey("not-a-date"), null);
	assert.equal(toMonthKey("abc"), null);
	assert.equal(toMonthKey(undefined), null);
});

test("toMonthKey returns null for calendar-impossible YYYY-MM-DD strings", () => {
	assert.equal(toMonthKey("2026-02-31"), null);
	assert.equal(toMonthKey("2026-13-01"), null);
});

test("toMonthKey returns YYYY-MM for valid Date instance", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = toMonthKey(d);
	assert.ok(/^\d{4}-\d{2}$/.test(result), `should match YYYY-MM: ${result}`);
});

test("toMonthKey pads single-digit months with leading zero", () => {
	const jan = new Date(2026, 0, 15, 12, 0, 0);
	const result = toMonthKey(jan);
	assert.ok(result.endsWith("-01"), `expected -01 in ${result}`);
});

// ── normalizeFinancialChartItems behavioral tests ────────────────────────────

test("normalizeFinancialChartItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeFinancialChartItems(null), []);
	assert.deepEqual(normalizeFinancialChartItems(undefined), []);
	assert.deepEqual(normalizeFinancialChartItems({}), []);
});

test("normalizeFinancialChartItems filters null, primitives, and arrays", () => {
	const items = [null, "string", 42, [], { id: "ok" }];
	assert.equal(normalizeFinancialChartItems(items).length, 1);
});

test("normalizeFinancialChartItems keeps plain objects regardless of id", () => {
	const items = [{ saleDate: "2026-06-15" }, { a: 1 }];
	assert.equal(normalizeFinancialChartItems(items).length, 2);
});

// ── normalizeFinancialChartWidgetOptions behavioral tests ────────────────────

test("normalizeFinancialChartWidgetOptions returns input for valid object", () => {
	const obj = { saleRecords: [] };
	assert.equal(normalizeFinancialChartWidgetOptions(obj), obj);
});

test("normalizeFinancialChartWidgetOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeFinancialChartWidgetOptions(null), {});
	assert.deepEqual(normalizeFinancialChartWidgetOptions(undefined), {});
	assert.deepEqual(normalizeFinancialChartWidgetOptions([]), {});
});

// ── buildFallbackChartData behavioral tests ───────────────────────────────────

test("buildFallbackChartData produces zero-valued entry for months with no data", () => {
	const result = buildFallbackChartData([], [], ["2026-06"]);
	assert.equal(result.length, 1);
	assert.deepEqual(result[0], {
		name: "2026-06",
		revenue: 0,
		expense: 0,
		profit: 0,
	});
});

test("buildFallbackChartData aggregates single sale record", () => {
	const sales = [{ saleDate: "2026-06-15", price: 5000000 }];
	const result = buildFallbackChartData(sales, [], ["2026-06"]);
	assert.equal(result[0].revenue, 5000000);
	assert.equal(result[0].profit, 5000000);
	assert.equal(result[0].expense, 0);
});

test("buildFallbackChartData aggregates single expense record", () => {
	const expenses = [{ date: "2026-06-10", amount: 1000000 }];
	const result = buildFallbackChartData([], expenses, ["2026-06"]);
	assert.equal(result[0].expense, 1000000);
	assert.equal(result[0].revenue, 0);
	assert.equal(result[0].profit, -1000000);
});

test("buildFallbackChartData sums multiple records in the same month", () => {
	const sales = [
		{ saleDate: "2026-06-10", price: 3000000 },
		{ saleDate: "2026-06-20", price: 2000000 },
	];
	const result = buildFallbackChartData(sales, [], ["2026-06"]);
	assert.equal(result[0].revenue, 5000000);
});

test("buildFallbackChartData separates records by month", () => {
	const sales = [
		{ saleDate: "2026-05-15", price: 4000000 },
		{ saleDate: "2026-06-15", price: 6000000 },
	];
	const result = buildFallbackChartData(sales, [], ["2026-05", "2026-06"]);
	assert.equal(result[0].revenue, 4000000);
	assert.equal(result[1].revenue, 6000000);
});

test("buildFallbackChartData floors expense values to integer", () => {
	const expenses = [{ date: "2026-06-10", amount: 1500500.7 }];
	const result = buildFallbackChartData([], expenses, ["2026-06"]);
	assert.equal(result[0].expense, 1500500);
});

test("buildFallbackChartData ignores records with invalid saleDate", () => {
	const sales = [
		{ saleDate: "invalid-date", price: 9999999 },
		{ saleDate: "2026-06-15", price: 1000 },
	];
	const result = buildFallbackChartData(sales, [], ["2026-06"]);
	assert.equal(result[0].revenue, 1000);
});

test("buildFallbackChartData ignores null/primitive entries in saleRecords", () => {
	const sales = [null, "string", { saleDate: "2026-06-15", price: 2000 }];
	const result = buildFallbackChartData(sales, [], ["2026-06"]);
	assert.equal(result[0].revenue, 2000);
});

test("buildFallbackChartData computes profit as revenue minus expense", () => {
	const sales = [{ saleDate: "2026-06-15", price: 8000000 }];
	const expenses = [{ date: "2026-06-05", amount: 3000000 }];
	const result = buildFallbackChartData(sales, expenses, ["2026-06"]);
	assert.equal(result[0].profit, 5000000);
});

test("buildFallbackChartData handles negative profit (expense > revenue)", () => {
	const sales = [{ saleDate: "2026-06-15", price: 1000000 }];
	const expenses = [{ date: "2026-06-05", amount: 4000000 }];
	const result = buildFallbackChartData(sales, expenses, ["2026-06"]);
	assert.equal(result[0].profit, -3000000);
});

// ── buildSeriesChartData behavioral tests ─────────────────────────────────────

test("buildSeriesChartData returns empty array for empty seriesData", () => {
	assert.deepEqual(buildSeriesChartData([]), []);
});

test("buildSeriesChartData maps seriesData rows to chart entries", () => {
	const seriesData = [
		{ month: "2026-06", revenue: 5000000, expense: 2000000, profit: 3000000 },
	];
	const result = buildSeriesChartData(seriesData);
	assert.equal(result.length, 1);
	assert.equal(result[0].name, "2026-06");
	assert.equal(result[0].revenue, 5000000);
	assert.equal(result[0].expense, 2000000);
	assert.equal(result[0].profit, 3000000);
});

test("buildSeriesChartData floors expense values to integer", () => {
	const seriesData = [
		{ month: "2026-06", revenue: 1000, expense: 1500.75, profit: -500.75 },
	];
	const result = buildSeriesChartData(seriesData);
	assert.equal(result[0].expense, 1500);
});

test("buildSeriesChartData coerces string numbers to Number", () => {
	const seriesData = [
		{ month: "2026-06", revenue: "5000000", expense: "2000000", profit: "3000000" },
	];
	const result = buildSeriesChartData(seriesData);
	assert.equal(result[0].revenue, 5000000);
	assert.equal(result[0].profit, 3000000);
});

test("buildSeriesChartData filters non-object entries in seriesData", () => {
	const seriesData = [
		null,
		"string",
		{ month: "2026-06", revenue: 1000, expense: 0, profit: 1000 },
	];
	const result = buildSeriesChartData(seriesData);
	assert.equal(result.length, 1);
});
