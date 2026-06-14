/**
 * Behavioral tests for private pure helpers in MarketPriceWidget.js:
 *   normalizePricePanelRows  — filters for ARRAY entries (not objects!)
 *   toValidUpdatedAt         — fallback Date for falsy/invalid values
 *   normalizePriceSnapshot   — adds bull/{} and cow/{} defaults
 *
 * getSourcePresentation is already covered in widget-pure-helpers.test.mjs.
 * MarketPriceWidget.js imports React; cannot load in Node ESM.
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
	path.join(SRC_ROOT, "components/widgets/MarketPriceWidget.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function normalizePricePanelRows(rows) {
	return Array.isArray(rows) ? rows.filter((row) => Array.isArray(row)) : [];
}

function toValidUpdatedAt(value, fallback = new Date()) {
	if (!value) {
		return fallback;
	}

	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? fallback : date;
}

function normalizePriceSnapshot(data) {
	return data
		? {
				...data,
				bull: data.bull ?? {},
				cow: data.cow ?? {},
			}
		: data;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("MarketPriceWidget.js normalizePricePanelRows filters for array rows", () => {
	assert.match(src, /function normalizePricePanelRows\(rows\)/);
	assert.match(src, /rows\.filter\(\(row\) => Array\.isArray\(row\)\)/);
});

test("MarketPriceWidget.js toValidUpdatedAt uses fallback for falsy/invalid", () => {
	assert.match(src, /function toValidUpdatedAt\(value, fallback = new Date\(\)\)/);
	assert.match(src, /if \(!value\)/);
	assert.match(src, /Number\.isNaN\(date\.getTime\(\)\) \? fallback : date/);
});

test("MarketPriceWidget.js normalizePriceSnapshot defaults bull and cow to {}", () => {
	assert.match(src, /function normalizePriceSnapshot\(data\)/);
	assert.match(src, /bull: data\.bull \?\? \{\}/);
	assert.match(src, /cow: data\.cow \?\? \{\}/);
});

// ── normalizePricePanelRows behavioral tests ──────────────────────────────────

test("normalizePricePanelRows returns empty array for non-array input", () => {
	assert.deepEqual(normalizePricePanelRows(null), []);
	assert.deepEqual(normalizePricePanelRows(undefined), []);
	assert.deepEqual(normalizePricePanelRows({}), []);
});

test("normalizePricePanelRows keeps ARRAY entries, not object entries", () => {
	// Unlike other normalizers — this is unique: keeps sub-arrays
	const rows = [
		["1++ 등급", 25000],
		["1+ 등급", 22000],
		{ grade: "1 등급", value: 20000 }, // object — filtered out
		null,
		"string",
		42,
	];
	const result = normalizePricePanelRows(rows);
	assert.equal(result.length, 2);
	assert.deepEqual(result[0], ["1++ 등급", 25000]);
	assert.deepEqual(result[1], ["1+ 등급", 22000]);
});

test("normalizePricePanelRows returns empty array for all-non-array entries", () => {
	assert.deepEqual(normalizePricePanelRows([{}, null, "string"]), []);
});

test("normalizePricePanelRows returns empty array for empty input array", () => {
	assert.deepEqual(normalizePricePanelRows([]), []);
});

// ── toValidUpdatedAt behavioral tests ─────────────────────────────────────────

test("toValidUpdatedAt returns fallback for null/undefined/0/false (falsy)", () => {
	const fallback = new Date("2026-06-01T00:00:00.000Z");
	assert.equal(toValidUpdatedAt(null, fallback), fallback);
	assert.equal(toValidUpdatedAt(undefined, fallback), fallback);
	assert.equal(toValidUpdatedAt(0, fallback), fallback);
	assert.equal(toValidUpdatedAt("", fallback), fallback);
	assert.equal(toValidUpdatedAt(false, fallback), fallback);
});

test("toValidUpdatedAt returns fallback for invalid date string", () => {
	const fallback = new Date("2026-06-01T00:00:00.000Z");
	const result = toValidUpdatedAt("not-a-date", fallback);
	assert.equal(result, fallback);
});

test("toValidUpdatedAt returns fallback for invalid Date instance", () => {
	const fallback = new Date("2026-06-01T00:00:00.000Z");
	const result = toValidUpdatedAt(new Date("invalid"), fallback);
	assert.equal(result, fallback);
});

test("toValidUpdatedAt returns a Date for valid date string", () => {
	const fallback = new Date("2026-01-01T00:00:00.000Z");
	const result = toValidUpdatedAt("2026-06-15T12:00:00.000Z", fallback);
	assert.ok(result instanceof Date);
	assert.notEqual(result, fallback);
});

test("toValidUpdatedAt returns a Date for valid Date instance", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const fallback = new Date("2026-01-01T00:00:00.000Z");
	const result = toValidUpdatedAt(d, fallback);
	assert.ok(result instanceof Date);
	assert.equal(result.getTime(), d.getTime());
});

test("toValidUpdatedAt does not mutate Date input", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const original = d.getTime();
	const fallback = new Date();
	toValidUpdatedAt(d, fallback);
	assert.equal(d.getTime(), original);
});

// ── normalizePriceSnapshot behavioral tests ───────────────────────────────────

test("normalizePriceSnapshot returns data as-is for null/undefined/falsy", () => {
	// The implementation returns `data` for falsy input (not {})
	assert.equal(normalizePriceSnapshot(null), null);
	assert.equal(normalizePriceSnapshot(undefined), undefined);
	assert.equal(normalizePriceSnapshot(false), false);
	assert.equal(normalizePriceSnapshot(0), 0);
});

test("normalizePriceSnapshot spreads data and defaults bull/cow to {}", () => {
	const data = { source: "kape-live", issueDateKey: "2026-06-15" };
	const result = normalizePriceSnapshot(data);
	assert.equal(result.source, "kape-live");
	assert.equal(result.issueDateKey, "2026-06-15");
	assert.deepEqual(result.bull, {});
	assert.deepEqual(result.cow, {});
});

test("normalizePriceSnapshot preserves existing bull data", () => {
	const bullData = { grade1pp: 9500000 };
	const data = { bull: bullData, cow: null };
	const result = normalizePriceSnapshot(data);
	assert.equal(result.bull, bullData);
});

test("normalizePriceSnapshot uses {} for null bull/cow", () => {
	const data = { bull: null, cow: null };
	const result = normalizePriceSnapshot(data);
	assert.deepEqual(result.bull, {});
	assert.deepEqual(result.cow, {});
});

test("normalizePriceSnapshot preserves existing cow data", () => {
	const cowData = { grade1pp: 8000000 };
	const data = { bull: undefined, cow: cowData };
	const result = normalizePriceSnapshot(data);
	assert.deepEqual(result.bull, {});
	assert.equal(result.cow, cowData);
});
