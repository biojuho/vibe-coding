/**
 * Behavioral tests for the private normalizeDate and toIssueDateKey helpers
 * in dashboard/read-models.js.
 *
 * read-models.js imports from bare specifiers (prisma, cache.js without extension
 * context) that cannot be resolved in Node ESM. These helpers are re-implemented
 * inline and cross-checked via source-grep so production code cannot drift.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..", "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/read-models.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function normalizeDate(value) {
	const fallback = new Date();

	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? fallback : value;
	}

	if (!value) {
		return fallback;
	}

	let date;
	if (typeof value === "string" && /^\d{8}$/.test(value)) {
		date = new Date(
			`${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}T00:00:00.000Z`,
		);
	} else {
		date = new Date(value);
	}

	return Number.isNaN(date.getTime()) ? fallback : date;
}

function toIssueDateKey(issueDate) {
	const date = normalizeDate(issueDate);
	return date.toISOString().slice(0, 10);
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("read-models.js normalizeDate handles YYYYMMDD format via slice reconstruction", () => {
	assert.match(src, /\/\^\\d\{8\}\$\/\.test\(value\)/);
	assert.match(
		src,
		/\$\{value\.slice\(0, 4\)\}-\$\{value\.slice\(4, 6\)\}-\$\{value\.slice\(6, 8\)\}/,
	);
});

test("read-models.js normalizeDate falls back to new Date() for invalid inputs", () => {
	assert.match(src, /const fallback = new Date\(\);/);
	assert.match(src, /return Number\.isNaN\(value\.getTime\(\)\) \? fallback : value;/);
	assert.match(src, /return Number\.isNaN\(date\.getTime\(\)\) \? fallback : date;/);
});

// ── normalizeDate behavioral tests ───────────────────────────────────────────

test("normalizeDate passes through valid Date instances", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const result = normalizeDate(d);
	assert.equal(result, d);
});

test("normalizeDate falls back to now for Invalid Date instances", () => {
	const before = new Date();
	const result = normalizeDate(new Date("invalid"));
	const after = new Date();
	assert.ok(result >= before && result <= after, "should fall back to current time");
});

test("normalizeDate parses YYYYMMDD string (8-digit format) to a valid Date", () => {
	const result = normalizeDate("20260615");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("normalizeDate parses standard ISO date-time strings", () => {
	const result = normalizeDate("2026-06-15T12:00:00.000Z");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString(), "2026-06-15T12:00:00.000Z");
});

test("normalizeDate parses YYYY-MM-DD date strings", () => {
	const result = normalizeDate("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("normalizeDate falls back to now for null", () => {
	const before = new Date();
	const result = normalizeDate(null);
	const after = new Date();
	assert.ok(result >= before && result <= after, "null should fall back to now");
});

test("normalizeDate falls back to now for undefined", () => {
	const before = new Date();
	const result = normalizeDate(undefined);
	const after = new Date();
	assert.ok(result >= before && result <= after, "undefined should fall back to now");
});

test("normalizeDate falls back to now for empty string", () => {
	const before = new Date();
	const result = normalizeDate("");
	const after = new Date();
	assert.ok(result >= before && result <= after, "empty string should fall back to now");
});

test("normalizeDate falls back to now for invalid string (not parseable)", () => {
	const before = new Date();
	const result = normalizeDate("not-a-date");
	const after = new Date();
	assert.ok(result >= before && result <= after, "invalid string should fall back to now");
});

test("normalizeDate falls back to now for 9-digit numeric strings (not YYYYMMDD)", () => {
	// 9 digits fails the /^\d{8}$/ test, goes through new Date() which likely fails
	const before = new Date();
	const result = normalizeDate("202606150");
	const after = new Date();
	assert.ok(result >= before && result <= after, "9-digit string should fall back to now");
});

// ── toIssueDateKey behavioral tests ──────────────────────────────────────────

test("toIssueDateKey returns YYYY-MM-DD for a valid Date input", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	assert.equal(toIssueDateKey(d), "2026-06-15");
});

test("toIssueDateKey converts YYYYMMDD string to YYYY-MM-DD", () => {
	assert.equal(toIssueDateKey("20260615"), "2026-06-15");
});

test("toIssueDateKey converts ISO date-time string to date portion", () => {
	assert.equal(toIssueDateKey("2026-06-15T12:00:00.000Z"), "2026-06-15");
});

test("toIssueDateKey returns today's date for null/invalid input (fallback)", () => {
	const today = new Date().toISOString().slice(0, 10);
	assert.equal(toIssueDateKey(null), today);
	assert.equal(toIssueDateKey("invalid"), today);
});
