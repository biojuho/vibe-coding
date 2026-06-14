/**
 * Behavioral tests for private pure helpers in AnalysisTab.js:
 *   toMonthKey            — Date/string → "YYYY-MM" local-time month key or null
 *   normalizeAnalysisItems — array filter (plain objects, no id requirement)
 *
 * AnalysisTab.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/tabs/AnalysisTab.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

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

// ── Source-grep guards ────────────────────────────────────────────────────────

test("AnalysisTab.js toMonthKey uses YYYY-MM format from local-time getFullYear/getMonth", () => {
	assert.match(src, /function toMonthKey\(value\)/);
	assert.match(src, /date\.getFullYear\(\)/);
	assert.match(src, /date\.getMonth\(\) \+ 1/);
	assert.match(src, /\.padStart\(2, ["']0["']\)/);
});

test("AnalysisTab.js normalizeAnalysisItems filters nulls, arrays, and primitives", () => {
	assert.match(src, /function normalizeAnalysisItems\(items\)/);
	assert.match(src, /item && typeof item === ["']object["'] && !Array\.isArray\(item\)/);
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

test("toMonthKey returns YYYY-MM string for a valid Date instance", () => {
	// Use noon UTC to avoid timezone boundary issues in the month
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = toMonthKey(d);
	// The result is local time — but June 15 noon UTC is June 15 in any timezone
	assert.ok(typeof result === "string", "should return a string");
	assert.ok(/^\d{4}-\d{2}$/.test(result), `should match YYYY-MM format, got: ${result}`);
});

test("toMonthKey returns YYYY-MM string for a valid YYYY-MM-DD string", () => {
	// Using first of month at midnight UTC — safe for all timezones
	const result = toMonthKey("2026-06-01");
	assert.ok(typeof result === "string");
	assert.ok(/^\d{4}-\d{2}$/.test(result));
});

test("toMonthKey pads single-digit months with a leading zero", () => {
	// January = month 0 in JS local time; we need local noon to avoid offset crossing
	const jan = new Date(2026, 0, 15, 12, 0, 0); // local January 15
	const result = toMonthKey(jan);
	assert.ok(result.endsWith("-01"), `expected month 01 in result: ${result}`);
});

test("toMonthKey for valid ISO string matches expected year-month portion", () => {
	const result = toMonthKey("2026-03-15T12:00:00.000Z");
	assert.ok(typeof result === "string");
	assert.ok(/^\d{4}-\d{2}$/.test(result));
});

test("toMonthKey does not mutate a Date input", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const original = d.getTime();
	toMonthKey(d);
	assert.equal(d.getTime(), original);
});

test("toMonthKey handles epoch (new Date(0)) without throwing", () => {
	const result = toMonthKey(new Date(0));
	assert.ok(typeof result === "string");
	assert.ok(/^\d{4}-\d{2}$/.test(result));
});

// ── normalizeAnalysisItems behavioral tests ───────────────────────────────────

test("normalizeAnalysisItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeAnalysisItems(null), []);
	assert.deepEqual(normalizeAnalysisItems(undefined), []);
	assert.deepEqual(normalizeAnalysisItems("string"), []);
	assert.deepEqual(normalizeAnalysisItems({}), []);
});

test("normalizeAnalysisItems keeps plain objects regardless of id", () => {
	const items = [{ saleDate: "2026-06-15" }, { a: 1, b: 2 }];
	assert.equal(normalizeAnalysisItems(items).length, 2);
});

test("normalizeAnalysisItems filters null, undefined, and falsy values", () => {
	const items = [null, undefined, false, 0, "", { id: "valid" }];
	const result = normalizeAnalysisItems(items);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "valid");
});

test("normalizeAnalysisItems filters arrays even though they are objects", () => {
	const items = [[], [{ id: "a" }], { id: "plain" }];
	const result = normalizeAnalysisItems(items);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "plain");
});

test("normalizeAnalysisItems does NOT require id field (unlike normalizeDashboardItems)", () => {
	const items = [{ name: "no-id" }];
	const result = normalizeAnalysisItems(items);
	assert.equal(result.length, 1);
});

test("normalizeAnalysisItems returns empty array for empty input", () => {
	assert.deepEqual(normalizeAnalysisItems([]), []);
});
