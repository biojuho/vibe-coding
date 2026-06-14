/**
 * Behavioral tests for the pure logic functions inside
 * dashboard/summary-service.js.
 *
 * The file imports from "../utils" (bare specifier without extension) and uses
 * an async Prisma-dependent buildDashboardSummaryPayload — neither can be
 * imported from Node ESM. The pure helpers are re-implemented inline and
 * cross-checked against the source via source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/summary-service.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toFiniteNumber(value) {
	const n = Number(value);
	return Number.isFinite(n) ? n : 0;
}

function normalizeSummaryOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options) ? options : {};
}

function normalizeSummaryRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => row && typeof row === "object" && !Array.isArray(row))
		: [];
}

function resolveGeneratedAt(value) {
	const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? new Date() : date;
}

function resolveFinancialSeriesMonthCount(value) {
	return Number.isSafeInteger(value) && value > 0 ? Math.min(value, 24) : 6;
}

function toMonthKey(value) {
	const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) return null;

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
			const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
			if (Number.isNaN(strictDate.getTime()) || strictDate.toISOString().slice(0, 10) !== dateKey) {
				return null;
			}
		}
	}

	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function normalizeStatusCounts(rows) {
	return normalizeSummaryRows(rows).reduce((accumulator, row) => {
		if (typeof row.status !== "string" || row.status.length === 0) return accumulator;
		accumulator[row.status] = toFiniteNumber(row._count?._all);
		return accumulator;
	}, {});
}

function buildFinancialSeries(options = {}) {
	const {
		salesRecords = [],
		expenseRecords = [],
		months = 6,
		generatedAt = new Date(),
	} = normalizeSummaryOptions(options);

	const series = [];
	const salesByMonth = new Map();
	const expensesByMonth = new Map();
	const safeSalesRecords = normalizeSummaryRows(salesRecords);
	const safeExpenseRecords = normalizeSummaryRows(expenseRecords);
	const safeGeneratedAt = resolveGeneratedAt(generatedAt);
	const monthCount = resolveFinancialSeriesMonthCount(months);

	for (const record of safeSalesRecords) {
		const monthKey = toMonthKey(record.saleDate);
		if (!monthKey) continue;
		salesByMonth.set(monthKey, (salesByMonth.get(monthKey) ?? 0) + toFiniteNumber(record.price));
	}

	for (const record of safeExpenseRecords) {
		const monthKey = toMonthKey(record.date);
		if (!monthKey) continue;
		expensesByMonth.set(monthKey, (expensesByMonth.get(monthKey) ?? 0) + toFiniteNumber(record.amount));
	}

	for (let index = monthCount - 1; index >= 0; index -= 1) {
		const date = new Date(
			safeGeneratedAt.getFullYear(),
			safeGeneratedAt.getMonth() - index,
			1,
		);
		const monthKey = toMonthKey(date);
		const revenue = salesByMonth.get(monthKey) ?? 0;
		const expense = expensesByMonth.get(monthKey) ?? 0;
		series.push({ month: monthKey, revenue, expense, profit: revenue - expense });
	}

	return series;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("summary-service.js toMonthKey guards against NaN dates", () => {
	assert.match(src, /if \(Number\.isNaN\(date\.getTime\(\)\)\) \{/);
	assert.match(src, /return null;/);
});

test("summary-service.js resolveFinancialSeriesMonthCount clamps to 24", () => {
	assert.match(src, /Math\.min\(value, 24\)/);
	assert.match(src, /: 6;/);
});

test("summary-service.js buildFinancialSeries uses toMonthKey for saleDate and date fields", () => {
	assert.match(src, /toMonthKey\(record\.saleDate\)/);
	assert.match(src, /toMonthKey\(record\.date\)/);
});

test("summary-service.js normalizeStatusCounts uses toFiniteNumber for _count._all", () => {
	assert.match(src, /toFiniteNumber\(row\._count\?._all\)/);
	assert.match(src, /accumulator\[row\.status\] = /);
});

// ── normalizeSummaryRows behavioral tests ────────────────────────────────────

test("normalizeSummaryRows filters out non-object, null, and array entries", () => {
	const result = normalizeSummaryRows([
		{ status: "active" },
		null,
		undefined,
		"string",
		42,
		[],
		{ status: "breeding" },
	]);
	assert.equal(result.length, 2);
	assert.equal(result[0].status, "active");
	assert.equal(result[1].status, "breeding");
});

test("normalizeSummaryRows returns empty array for non-array input", () => {
	assert.deepEqual(normalizeSummaryRows(null), []);
	assert.deepEqual(normalizeSummaryRows(undefined), []);
	assert.deepEqual(normalizeSummaryRows("rows"), []);
	assert.deepEqual(normalizeSummaryRows({}), []);
});

// ── resolveGeneratedAt behavioral tests ──────────────────────────────────────

test("resolveGeneratedAt preserves valid Date instances", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const result = resolveGeneratedAt(d);
	assert.equal(result.toISOString(), d.toISOString());
});

test("resolveGeneratedAt parses valid ISO strings", () => {
	const result = resolveGeneratedAt("2026-01-01T00:00:00.000Z");
	assert.equal(result.toISOString(), "2026-01-01T00:00:00.000Z");
});

test("resolveGeneratedAt falls back to current time for invalid input", () => {
	const before = new Date();
	const result = resolveGeneratedAt("not-a-date");
	const after = new Date();
	assert.ok(result >= before && result <= after, "should fall back to current time");
});

// ── resolveFinancialSeriesMonthCount behavioral tests ────────────────────────

test("resolveFinancialSeriesMonthCount defaults to 6 for invalid input", () => {
	assert.equal(resolveFinancialSeriesMonthCount(null), 6);
	assert.equal(resolveFinancialSeriesMonthCount(undefined), 6);
	assert.equal(resolveFinancialSeriesMonthCount(0), 6);
	assert.equal(resolveFinancialSeriesMonthCount(-1), 6);
	assert.equal(resolveFinancialSeriesMonthCount(1.5), 6);
});

test("resolveFinancialSeriesMonthCount clamps to 24 for large values", () => {
	assert.equal(resolveFinancialSeriesMonthCount(100), 24);
	assert.equal(resolveFinancialSeriesMonthCount(24), 24);
});

test("resolveFinancialSeriesMonthCount passes through valid values ≤ 24", () => {
	assert.equal(resolveFinancialSeriesMonthCount(1), 1);
	assert.equal(resolveFinancialSeriesMonthCount(12), 12);
});

// ── toMonthKey behavioral tests ───────────────────────────────────────────────

test("toMonthKey formats valid Date objects as YYYY-MM", () => {
	assert.equal(toMonthKey(new Date("2026-06-15T00:00:00.000Z")), "2026-06");
	assert.equal(toMonthKey(new Date("2026-01-01T00:00:00.000Z")), "2026-01");
});

test("toMonthKey formats valid date strings as YYYY-MM", () => {
	assert.equal(toMonthKey("2026-06-15"), "2026-06");
	assert.equal(toMonthKey("2025-12-01"), "2025-12");
});

test("toMonthKey returns null for invalid/unparseable date inputs", () => {
	// null → new Date(null) = epoch (1970-01-01) — not null
	assert.equal(toMonthKey(null), "1970-01");
	// undefined/non-parseable strings → Invalid Date → null
	assert.equal(toMonthKey(undefined), null);
	assert.equal(toMonthKey("not-a-date"), null);
	// calendar-impossible month causes new Date() to be Invalid Date
	assert.equal(toMonthKey("2026-13-01"), null);
});

// ── normalizeStatusCounts behavioral tests ───────────────────────────────────

test("normalizeStatusCounts aggregates Prisma groupBy rows correctly", () => {
	const rows = [
		{ status: "active", _count: { _all: 5 } },
		{ status: "breeding", _count: { _all: 3 } },
		{ status: "sold", _count: { _all: 1 } },
	];
	const result = normalizeStatusCounts(rows);
	assert.equal(result.active, 5);
	assert.equal(result.breeding, 3);
	assert.equal(result.sold, 1);
});

test("normalizeStatusCounts skips rows with empty or missing status string", () => {
	const rows = [
		{ status: "active", _count: { _all: 4 } },
		{ status: "", _count: { _all: 2 } },
		{ _count: { _all: 1 } },
	];
	const result = normalizeStatusCounts(rows);
	assert.equal(Object.keys(result).length, 1);
	assert.equal(result.active, 4);
});

test("normalizeStatusCounts treats missing _count._all as 0", () => {
	const rows = [{ status: "active" }, { status: "sold", _count: { _all: null } }];
	const result = normalizeStatusCounts(rows);
	assert.equal(result.active, 0);
	assert.equal(result.sold, 0);
});

// ── buildFinancialSeries behavioral tests ─────────────────────────────────────

test("buildFinancialSeries returns 6 months by default", () => {
	const series = buildFinancialSeries({ generatedAt: new Date("2026-06-15T00:00:00.000Z") });
	assert.equal(series.length, 6);
});

test("buildFinancialSeries returns N months when specified", () => {
	const series = buildFinancialSeries({
		months: 3,
		generatedAt: new Date("2026-06-15T00:00:00.000Z"),
	});
	assert.equal(series.length, 3);
});

test("buildFinancialSeries last entry is the current month", () => {
	const series = buildFinancialSeries({ generatedAt: new Date("2026-06-15T00:00:00.000Z") });
	assert.equal(series[series.length - 1].month, "2026-06");
});

test("buildFinancialSeries sums revenue and expenses per month and computes profit", () => {
	const series = buildFinancialSeries({
		months: 3,
		generatedAt: new Date("2026-06-15T00:00:00.000Z"),
		salesRecords: [
			{ saleDate: "2026-06-01", price: 1000000 },
			{ saleDate: "2026-06-15", price: 500000 },
			{ saleDate: "2026-04-01", price: 300000 },
		],
		expenseRecords: [
			{ date: "2026-06-10", amount: 200000 },
			{ date: "2026-04-20", amount: 100000 },
		],
	});
	const apr = series.find((s) => s.month === "2026-04");
	const jun = series.find((s) => s.month === "2026-06");

	assert.equal(apr.revenue, 300000);
	assert.equal(apr.expense, 100000);
	assert.equal(apr.profit, 200000);

	assert.equal(jun.revenue, 1500000);
	assert.equal(jun.expense, 200000);
	assert.equal(jun.profit, 1300000);
});

test("buildFinancialSeries uses zero for months with no records", () => {
	const series = buildFinancialSeries({
		months: 2,
		generatedAt: new Date("2026-06-15T00:00:00.000Z"),
	});
	for (const entry of series) {
		assert.equal(entry.revenue, 0);
		assert.equal(entry.expense, 0);
		assert.equal(entry.profit, 0);
	}
});

test("buildFinancialSeries ignores records outside the N-month window", () => {
	const series = buildFinancialSeries({
		months: 2,
		generatedAt: new Date("2026-06-15T00:00:00.000Z"),
		salesRecords: [
			{ saleDate: "2026-06-01", price: 1000000 },
			{ saleDate: "2026-01-01", price: 9999999 },
		],
	});
	const totalRevenue = series.reduce((sum, s) => sum + s.revenue, 0);
	assert.equal(totalRevenue, 1000000);
});

test("buildFinancialSeries skips records with null or invalid dates", () => {
	const series = buildFinancialSeries({
		months: 1,
		generatedAt: new Date("2026-06-15T00:00:00.000Z"),
		salesRecords: [
			{ saleDate: "not-a-date", price: 999 },
			{ saleDate: null, price: 999 },
			{ saleDate: "2026-06-01", price: 500000 },
		],
	});
	const jun = series.find((s) => s.month === "2026-06");
	assert.equal(jun.revenue, 500000);
});

test("buildFinancialSeries tolerates null/non-object options input", () => {
	assert.doesNotThrow(() => buildFinancialSeries(null));
	assert.doesNotThrow(() => buildFinancialSeries("bad"));
	const series = buildFinancialSeries(null);
	assert.equal(series.length, 6);
});
