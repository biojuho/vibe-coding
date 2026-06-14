/**
 * Behavioral tests for private pure helpers in:
 *   src/lib/cattle-csv-export.mjs — normalizeCattleCsvRows, formatCsvDate, formatCsvCell
 *   src/lib/market-price-state.mjs — parseStrictDateKey, toValidDate, toIssueDateKey,
 *                                     toDisplayDate, normalizePriceSide
 *
 * These helpers are not exported; they are re-implemented inline with
 * source-grep guards to catch divergence.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const csvSrc = readFileSync(
	path.join(SRC_ROOT, "lib/cattle-csv-export.mjs"),
	"utf8",
);
const marketSrc = readFileSync(
	path.join(SRC_ROOT, "lib/market-price-state.mjs"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

// From cattle-csv-export.mjs
function normalizeCattleCsvRows(cattleList) {
	return Array.isArray(cattleList)
		? cattleList.filter(
				(cattle) =>
					cattle && typeof cattle === "object" && !Array.isArray(cattle),
			)
		: [];
}

function formatCsvDate(value) {
	if (!value) {
		return "";
	}
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("ko-KR");
}

const FORMULA_PREFIX_RE = /^[=+\-@]/;

function formatCsvCell(value) {
	const text = String(value ?? "");
	const safe = FORMULA_PREFIX_RE.test(text) ? `'${text}` : text;
	if (!/[",\r\n]/.test(safe)) {
		return safe;
	}
	return `"${safe.replace(/"/g, '""')}"`;
}

// From market-price-state.mjs
function parseStrictDateKey(value) {
	const parsed = new Date(`${value}T00:00:00.000Z`);
	return Number.isFinite(parsed.getTime()) &&
		parsed.toISOString().slice(0, 10) === value
		? parsed
		: null;
}

function toValidDate(value) {
	if (value instanceof Date && Number.isFinite(value.getTime())) {
		return value;
	}
	if (typeof value === "string" && /^\d{8}$/.test(value)) {
		const normalized = `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
		return parseStrictDateKey(normalized);
	}
	if (typeof value === "string" && /^\d{4}\.\d{2}\.\d{2}$/.test(value)) {
		return parseStrictDateKey(value.replace(/\./g, "-"));
	}
	if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
		return parseStrictDateKey(value);
	}
	if (!value) {
		return null;
	}
	const parsed = new Date(value);
	return Number.isFinite(parsed.getTime()) ? parsed : null;
}

function toIssueDateKey(value, fallbackNow) {
	const date = toValidDate(value) ?? fallbackNow;
	return date.toISOString().slice(0, 10);
}

function toDisplayDate(issueDateKey) {
	return issueDateKey.replace(/-/g, ".");
}

function normalizePriceSide(side) {
	if (!side || typeof side !== "object" || Array.isArray(side)) {
		return null;
	}
	const normalized = {
		grade1pp: Number(side.grade1pp),
		grade1p: Number(side.grade1p),
		grade1: Number(side.grade1),
	};
	if (
		Object.values(normalized).some(
			(value) => !Number.isFinite(value) || value <= 0,
		)
	) {
		return null;
	}
	return normalized;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("cattle-csv-export.mjs formatCsvCell prefixes formula characters and quotes commas", () => {
	assert.match(csvSrc, /function formatCsvCell\(value\)/);
	assert.match(csvSrc, /FORMULA_PREFIX_RE\.test\(text\)/);
	assert.ok(csvSrc.includes('safe.replace(/"/g, \'""\')')  , 'formatCsvCell should escape double-quotes');
});

test("cattle-csv-export.mjs normalizeCattleCsvRows filters plain objects only", () => {
	assert.match(csvSrc, /function normalizeCattleCsvRows\(cattleList\)/);
	assert.match(csvSrc, /!Array\.isArray\(cattle\)/);
});

test("market-price-state.mjs toValidDate handles 8-digit and YYYY.MM.DD formats", () => {
	assert.match(marketSrc, /function toValidDate\(value\)/);
	assert.match(marketSrc, /\/\^\\d\{8\}\$\//);
	assert.match(marketSrc, /\/\^\\d\{4\}\\\.\\d\{2\}\\\.\\d\{2\}\$\//);
});

test("market-price-state.mjs normalizePriceSide rejects missing or non-positive grades", () => {
	assert.match(marketSrc, /function normalizePriceSide\(side\)/);
	assert.match(marketSrc, /!Number\.isFinite\(value\) \|\| value <= 0/);
	assert.match(marketSrc, /grade1pp/);
});

// ── normalizeCattleCsvRows behavioral tests ───────────────────────────────────

test("normalizeCattleCsvRows returns empty array for non-array input", () => {
	assert.deepEqual(normalizeCattleCsvRows(null), []);
	assert.deepEqual(normalizeCattleCsvRows(undefined), []);
	assert.deepEqual(normalizeCattleCsvRows({}), []);
});

test("normalizeCattleCsvRows filters nulls, arrays, and primitives", () => {
	const rows = [null, "string", 42, [], { id: "ok" }];
	assert.equal(normalizeCattleCsvRows(rows).length, 1);
});

test("normalizeCattleCsvRows keeps plain objects regardless of id", () => {
	const rows = [{ name: "소" }, { name: "누렁이", id: "c1" }];
	assert.equal(normalizeCattleCsvRows(rows).length, 2);
});

// ── formatCsvDate behavioral tests ────────────────────────────────────────────

test("formatCsvDate returns empty string for null, undefined, 0, false", () => {
	assert.equal(formatCsvDate(null), "");
	assert.equal(formatCsvDate(undefined), "");
	assert.equal(formatCsvDate(0), "");
	assert.equal(formatCsvDate(false), "");
});

test("formatCsvDate returns empty string for invalid date string", () => {
	assert.equal(formatCsvDate("not-a-date"), "");
});

test("formatCsvDate returns a Korean locale date string for a valid Date", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = formatCsvDate(d);
	assert.ok(typeof result === "string" && result.length > 0, `should be non-empty, got: ${result}`);
});

test("formatCsvDate accepts a valid date string and formats it", () => {
	const result = formatCsvDate("2026-06-15T12:00:00.000Z");
	assert.ok(typeof result === "string" && result.length > 0);
});

test("formatCsvDate does not mutate Date input", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const original = d.getTime();
	formatCsvDate(d);
	assert.equal(d.getTime(), original);
});

// ── formatCsvCell behavioral tests ────────────────────────────────────────────

test("formatCsvCell returns plain string for safe text", () => {
	assert.equal(formatCsvCell("Hello World"), "Hello World");
	assert.equal(formatCsvCell("한우 농가"), "한우 농가");
});

test("formatCsvCell converts null/undefined to empty string", () => {
	assert.equal(formatCsvCell(null), "");
	assert.equal(formatCsvCell(undefined), "");
});

test("formatCsvCell prefixes = to prevent formula injection", () => {
	assert.equal(formatCsvCell("=SUM(A1)"), "'=SUM(A1)");
});

test("formatCsvCell prefixes + to prevent formula injection", () => {
	assert.equal(formatCsvCell("+cmd"), "'+cmd");
});

test("formatCsvCell prefixes - to prevent formula injection", () => {
	assert.equal(formatCsvCell("-1+1"), "'-1+1");
});

test("formatCsvCell prefixes @ to prevent formula injection", () => {
	assert.equal(formatCsvCell("@SUM"), "'@SUM");
});

test("formatCsvCell wraps text with comma in double quotes", () => {
	const result = formatCsvCell("Smith, John");
	assert.equal(result, '"Smith, John"');
});

test("formatCsvCell wraps text with double-quote and escapes internal quotes", () => {
	const result = formatCsvCell('He said "hello"');
	assert.equal(result, '"He said ""hello"""');
});

test("formatCsvCell wraps text with newline in double quotes", () => {
	const result = formatCsvCell("line1\nline2");
	assert.ok(result.startsWith('"'));
	assert.ok(result.endsWith('"'));
});

test("formatCsvCell converts numbers to their string representation", () => {
	assert.equal(formatCsvCell(42), "42");
	assert.equal(formatCsvCell(3.14), "3.14");
});

// ── parseStrictDateKey behavioral tests ──────────────────────────────────────

test("parseStrictDateKey returns Date for valid YYYY-MM-DD", () => {
	const result = parseStrictDateKey("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("parseStrictDateKey returns null for calendar-impossible dates", () => {
	assert.equal(parseStrictDateKey("2026-02-31"), null);
	assert.equal(parseStrictDateKey("2026-13-01"), null);
});

// ── toValidDate behavioral tests ──────────────────────────────────────────────

test("toValidDate returns the same Date for a valid Date instance", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	assert.equal(toValidDate(d), d);
});

test("toValidDate returns null for invalid Date instance", () => {
	assert.equal(toValidDate(new Date("invalid")), null);
});

test("toValidDate parses 8-digit YYYYMMDD string", () => {
	const result = toValidDate("20260615");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("toValidDate parses YYYY.MM.DD dotted string", () => {
	const result = toValidDate("2026.06.15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("toValidDate parses YYYY-MM-DD ISO date string", () => {
	const result = toValidDate("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("toValidDate returns null for null/undefined/0/false (falsy)", () => {
	assert.equal(toValidDate(null), null);
	assert.equal(toValidDate(undefined), null);
	assert.equal(toValidDate(0), null);
	assert.equal(toValidDate(false), null);
	assert.equal(toValidDate(""), null);
});

test("toValidDate returns null for YYYYMMDD that rolls over (calendar impossible)", () => {
	assert.equal(toValidDate("20260231"), null); // Feb 31
});

// ── toIssueDateKey behavioral tests ───────────────────────────────────────────

test("toIssueDateKey returns YYYY-MM-DD string from a valid Date", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const fallback = new Date("2026-01-01T00:00:00.000Z");
	assert.equal(toIssueDateKey(d, fallback), "2026-06-15");
});

test("toIssueDateKey falls back to fallbackNow for invalid value", () => {
	const fallback = new Date("2026-06-01T00:00:00.000Z");
	assert.equal(toIssueDateKey(null, fallback), "2026-06-01");
});

// ── toDisplayDate behavioral tests ────────────────────────────────────────────

test("toDisplayDate converts YYYY-MM-DD to YYYY.MM.DD", () => {
	assert.equal(toDisplayDate("2026-06-15"), "2026.06.15");
	assert.equal(toDisplayDate("2026-01-01"), "2026.01.01");
});

// ── normalizePriceSide behavioral tests ───────────────────────────────────────

test("normalizePriceSide returns null for null/undefined/primitive", () => {
	assert.equal(normalizePriceSide(null), null);
	assert.equal(normalizePriceSide(undefined), null);
	assert.equal(normalizePriceSide("string"), null);
	assert.equal(normalizePriceSide(42), null);
});

test("normalizePriceSide returns null for arrays", () => {
	assert.equal(normalizePriceSide([]), null);
});

test("normalizePriceSide returns null when any grade value is missing", () => {
	assert.equal(normalizePriceSide({ grade1pp: 9500000, grade1p: 8000000 }), null);
});

test("normalizePriceSide returns null when any grade value is zero or negative", () => {
	assert.equal(normalizePriceSide({ grade1pp: 0, grade1p: 8000000, grade1: 7000000 }), null);
	assert.equal(normalizePriceSide({ grade1pp: -1, grade1p: 8000000, grade1: 7000000 }), null);
});

test("normalizePriceSide returns normalized object for all-positive grades", () => {
	const result = normalizePriceSide({
		grade1pp: 9500000,
		grade1p: 8500000,
		grade1: 7500000,
	});
	assert.ok(result !== null);
	assert.equal(result.grade1pp, 9500000);
	assert.equal(result.grade1p, 8500000);
	assert.equal(result.grade1, 7500000);
});

test("normalizePriceSide coerces string numbers to Number", () => {
	const result = normalizePriceSide({
		grade1pp: "9500000",
		grade1p: "8500000",
		grade1: "7500000",
	});
	assert.ok(result !== null);
	assert.equal(result.grade1pp, 9500000);
});

test("normalizePriceSide returns null when a grade is NaN (e.g. non-numeric string)", () => {
	assert.equal(
		normalizePriceSide({ grade1pp: "abc", grade1p: 8500000, grade1: 7500000 }),
		null,
	);
});
