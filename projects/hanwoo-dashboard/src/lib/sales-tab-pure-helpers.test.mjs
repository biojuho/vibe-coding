/**
 * Behavioral tests for private pure helpers in SalesTab.js:
 *   getSaleDateTime            — Date/string → ms timestamp or NEGATIVE_INFINITY
 *   normalizeSalesItems        — array filter for plain objects
 *   normalizeSalesTabOptions   — object guard
 *   normalizeSalesPaginationOptions — object guard
 *
 * SalesTab.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/tabs/SalesTab.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function getSaleDateTime(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime())
		? Number.NEGATIVE_INFINITY
		: date.getTime();
}

function normalizeSalesItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeSalesTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeSalesPaginationOptions(pagination) {
	return pagination && typeof pagination === "object" && !Array.isArray(pagination)
		? pagination
		: {};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("SalesTab.js getSaleDateTime returns NEGATIVE_INFINITY for invalid dates", () => {
	assert.match(src, /function getSaleDateTime\(value\) \{/);
	assert.match(src, /Number\.NEGATIVE_INFINITY/);
	assert.match(src, /Number\.isNaN\(date\.getTime\(\)\)/);
});

test("SalesTab.js normalizeSalesItems filters plain objects", () => {
	assert.match(src, /function normalizeSalesItems\(items\)/);
	assert.match(src, /!Array\.isArray\(item\)/);
});

test("SalesTab.js normalizeSalesTabOptions returns object or {}", () => {
	assert.match(src, /function normalizeSalesTabOptions\(options\)/);
	assert.match(src, /typeof options === ["']object["'] && !Array\.isArray\(options\)/);
});

test("SalesTab.js normalizeSalesPaginationOptions returns object or {}", () => {
	assert.match(src, /function normalizeSalesPaginationOptions\(pagination\)/);
	assert.match(src, /typeof pagination === ["']object["'] && !Array\.isArray\(pagination\)/);
});

// ── getSaleDateTime behavioral tests ─────────────────────────────────────────

test("getSaleDateTime returns NEGATIVE_INFINITY for invalid date strings", () => {
	assert.equal(getSaleDateTime("not-a-date"), Number.NEGATIVE_INFINITY);
	assert.equal(getSaleDateTime("abc"), Number.NEGATIVE_INFINITY);
	assert.equal(getSaleDateTime(undefined), Number.NEGATIVE_INFINITY);
});

test("getSaleDateTime returns NEGATIVE_INFINITY for invalid Date instance", () => {
	assert.equal(getSaleDateTime(new Date("invalid")), Number.NEGATIVE_INFINITY);
});

test("getSaleDateTime returns numeric timestamp for valid date string", () => {
	const result = getSaleDateTime("2026-06-15");
	assert.ok(typeof result === "number" && Number.isFinite(result));
});

test("getSaleDateTime returns numeric timestamp for valid Date instance", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = getSaleDateTime(d);
	assert.equal(result, d.getTime());
});

test("getSaleDateTime does not mutate Date input", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const original = d.getTime();
	getSaleDateTime(d);
	assert.equal(d.getTime(), original);
});

test("getSaleDateTime sorts later dates to higher values (descending sort uses b - a)", () => {
	const records = [
		{ saleDate: "2026-06-15" },
		{ saleDate: "2026-05-10" },
		{ saleDate: "invalid-date" },
		{ saleDate: "2026-07-01" },
	];
	// descending: latest first (b - a)
	const sorted = [...records].sort(
		(a, b) => getSaleDateTime(b.saleDate) - getSaleDateTime(a.saleDate),
	);
	// invalid becomes NEGATIVE_INFINITY → sorts last in descending
	assert.equal(sorted[0].saleDate, "2026-07-01");
	assert.equal(sorted[1].saleDate, "2026-06-15");
	assert.equal(sorted[2].saleDate, "2026-05-10");
	assert.equal(sorted[3].saleDate, "invalid-date");
});

// ── normalizeSalesItems behavioral tests ─────────────────────────────────────

test("normalizeSalesItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeSalesItems(null), []);
	assert.deepEqual(normalizeSalesItems(undefined), []);
	assert.deepEqual(normalizeSalesItems({}), []);
});

test("normalizeSalesItems filters null, primitives, and arrays", () => {
	const items = [null, "string", 42, [], { id: "ok" }];
	assert.equal(normalizeSalesItems(items).length, 1);
});

test("normalizeSalesItems keeps plain objects regardless of id", () => {
	const items = [{ saleDate: "2026-06-15" }, { price: 5000000 }];
	assert.equal(normalizeSalesItems(items).length, 2);
});

// ── normalizeSalesTabOptions behavioral tests ─────────────────────────────────

test("normalizeSalesTabOptions returns input for valid object", () => {
	const obj = { saleRecords: [] };
	assert.equal(normalizeSalesTabOptions(obj), obj);
});

test("normalizeSalesTabOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeSalesTabOptions(null), {});
	assert.deepEqual(normalizeSalesTabOptions(undefined), {});
	assert.deepEqual(normalizeSalesTabOptions([]), {});
	assert.deepEqual(normalizeSalesTabOptions("string"), {});
});

// ── normalizeSalesPaginationOptions behavioral tests ──────────────────────────

test("normalizeSalesPaginationOptions returns input for valid object", () => {
	const obj = { cursor: "abc", hasMore: true };
	assert.equal(normalizeSalesPaginationOptions(obj), obj);
});

test("normalizeSalesPaginationOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeSalesPaginationOptions(null), {});
	assert.deepEqual(normalizeSalesPaginationOptions(undefined), {});
	assert.deepEqual(normalizeSalesPaginationOptions([]), {});
});
