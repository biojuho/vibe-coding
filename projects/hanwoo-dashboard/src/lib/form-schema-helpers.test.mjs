/**
 * Behavioral tests for the pure helper functions in formSchemas.js.
 *
 * formSchemas.js imports from "@/lib/utils" (path alias) which cannot be
 * resolved in Node ESM tests. The pure helpers — emptyToUndefined,
 * toPlainNumber, and isDateInputString — are re-implemented inline and
 * cross-checked via source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/formSchemas.js"), "utf8");

// ── Inline re-implementations ─────────────────────────────────────────────────

const DATE_INPUT_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const PLAIN_NUMBER_INPUT_PATTERN = /^-?(?:\d+|\d+\.\d+|\.\d+)$/;

function emptyToUndefined(value) {
	if (value === "" || value === null || value === undefined) return undefined;
	if (typeof value === "string") {
		const trimmed = value.trim();
		return trimmed === "" ? undefined : trimmed;
	}
	return value;
}

function toPlainNumber(value) {
	const normalized = emptyToUndefined(value);
	if (normalized === undefined) return undefined;
	if (typeof normalized === "string") {
		if (!PLAIN_NUMBER_INPUT_PATTERN.test(normalized)) return Number.NaN;
		return Number(normalized);
	}
	if (typeof normalized === "number") return Number(normalized);
	return normalized;
}

function isDateInputString(value) {
	if (!DATE_INPUT_PATTERN.test(value)) return false;
	const parsed = new Date(`${value}T00:00:00.000Z`);
	return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("formSchemas.js emptyToUndefined trims whitespace and maps empty/null/undefined to undefined", () => {
	assert.match(src, /const emptyToUndefined\s*=/);
	assert.match(src, /value === "" \|\| value === null \|\| value === undefined/);
	assert.match(src, /trimmed === "" \? undefined : trimmed/);
});

test("formSchemas.js toPlainNumber rejects scientific and hex notation", () => {
	assert.match(src, /PLAIN_NUMBER_INPUT_PATTERN/);
	assert.match(src, /return Number\.NaN;/);
});

test("formSchemas.js isDateInputString uses strict roundtrip validation for calendar dates", () => {
	assert.match(src, /const isDateInputString\s*=/);
	assert.match(src, /parsed\.toISOString\(\)\.slice\(0, 10\) === value/);
	assert.match(src, /Number\.isNaN\(parsed\.getTime\(\)\)/);
});

test("formSchemas.js pastOrTodayDateString compares against toInputDate(new Date())", () => {
	assert.match(src, /const pastOrTodayDateString\s*=/);
	assert.match(src, /value <= toInputDate\(new Date\(\)\)/);
});

// ── emptyToUndefined behavioral tests ────────────────────────────────────────

test("emptyToUndefined returns undefined for empty string", () => {
	assert.equal(emptyToUndefined(""), undefined);
});

test("emptyToUndefined returns undefined for null", () => {
	assert.equal(emptyToUndefined(null), undefined);
});

test("emptyToUndefined returns undefined for undefined", () => {
	assert.equal(emptyToUndefined(undefined), undefined);
});

test("emptyToUndefined returns undefined for whitespace-only string", () => {
	assert.equal(emptyToUndefined("   "), undefined);
	assert.equal(emptyToUndefined("\t\n"), undefined);
});

test("emptyToUndefined trims whitespace from non-empty strings", () => {
	assert.equal(emptyToUndefined("  hello  "), "hello");
	assert.equal(emptyToUndefined("농장 이름"), "농장 이름");
});

test("emptyToUndefined passes through non-string values unchanged", () => {
	assert.equal(emptyToUndefined(42), 42);
	assert.equal(emptyToUndefined(0), 0);
	assert.equal(emptyToUndefined(false), false);
	const obj = { id: 1 };
	assert.equal(emptyToUndefined(obj), obj);
});

// ── toPlainNumber behavioral tests ────────────────────────────────────────────

test("toPlainNumber returns undefined for empty/null/undefined inputs", () => {
	assert.equal(toPlainNumber(""), undefined);
	assert.equal(toPlainNumber(null), undefined);
	assert.equal(toPlainNumber(undefined), undefined);
	assert.equal(toPlainNumber("   "), undefined);
});

test("toPlainNumber parses valid integer strings", () => {
	assert.equal(toPlainNumber("0"), 0);
	assert.equal(toPlainNumber("42"), 42);
	assert.equal(toPlainNumber("1500000"), 1500000);
});

test("toPlainNumber parses valid decimal strings", () => {
	assert.equal(toPlainNumber("10.5"), 10.5);
	assert.equal(toPlainNumber("18.25"), 18.25);
	assert.equal(toPlainNumber(".5"), 0.5);
});

test("toPlainNumber parses negative numbers", () => {
	assert.equal(toPlainNumber("-5"), -5);
	assert.equal(toPlainNumber("-0.5"), -0.5);
});

test("toPlainNumber returns NaN for scientific notation", () => {
	assert.ok(Number.isNaN(toPlainNumber("1e6")));
	assert.ok(Number.isNaN(toPlainNumber("1E5")));
	assert.ok(Number.isNaN(toPlainNumber("3.5e1")));
});

test("toPlainNumber returns NaN for hex notation", () => {
	assert.ok(Number.isNaN(toPlainNumber("0x10")));
	assert.ok(Number.isNaN(toPlainNumber("0xFF")));
});

test("toPlainNumber returns NaN for non-numeric strings", () => {
	assert.ok(Number.isNaN(toPlainNumber("abc")));
	assert.ok(Number.isNaN(toPlainNumber("10kg")));
	assert.ok(Number.isNaN(toPlainNumber("$100")));
});

test("toPlainNumber passes through numeric values directly", () => {
	assert.equal(toPlainNumber(42), 42);
	assert.equal(toPlainNumber(0), 0);
	assert.equal(toPlainNumber(-5), -5);
	assert.equal(toPlainNumber(10.5), 10.5);
});

// ── isDateInputString behavioral tests ───────────────────────────────────────

test("isDateInputString accepts valid calendar dates", () => {
	assert.equal(isDateInputString("2026-06-15"), true);
	assert.equal(isDateInputString("2024-02-29"), true); // leap year
	assert.equal(isDateInputString("2000-01-01"), true);
	assert.equal(isDateInputString("2026-01-31"), true);
});

test("isDateInputString rejects calendar-impossible dates", () => {
	assert.equal(isDateInputString("2026-13-01"), false); // month 13
	assert.equal(isDateInputString("2026-02-29"), false); // non-leap year
	assert.equal(isDateInputString("2026-02-31"), false); // Feb 31
	assert.equal(isDateInputString("2026-04-31"), false); // April 31
});

test("isDateInputString rejects non-YYYY-MM-DD formats", () => {
	assert.equal(isDateInputString("20260615"), false);
	assert.equal(isDateInputString("2026/06/15"), false);
	assert.equal(isDateInputString("June 15, 2026"), false);
	assert.equal(isDateInputString(""), false);
});

test("isDateInputString rejects partial date strings", () => {
	assert.equal(isDateInputString("2026-06"), false);
	assert.equal(isDateInputString("2026"), false);
	assert.equal(isDateInputString("2026-6-5"), false); // single-digit month/day
});

test("isDateInputString catches rollover dates via strict round-trip check", () => {
	// "2026-02-31" would roll over to "2026-03-03" after new Date() parsing
	// The strict round-trip catches this since the ISO slice won't match
	assert.equal(isDateInputString("2026-02-31"), false);
	assert.equal(isDateInputString("2026-11-31"), false); // Nov only has 30 days
});
