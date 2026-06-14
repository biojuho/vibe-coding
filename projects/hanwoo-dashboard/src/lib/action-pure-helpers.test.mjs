/**
 * Behavioral tests for private pure helpers in server action files.
 *
 * These files use "use server" + path aliases that can't load in Node ESM.
 * Pure helpers are re-implemented inline and pinned via source-grep so
 * production code and tests cannot silently diverge.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const expenseSrc = readFileSync(path.join(SRC_ROOT, "lib/actions/expense.js"), "utf8");
const cattleSrc = readFileSync(path.join(SRC_ROOT, "lib/actions/cattle.js"), "utf8");

// ── Inline re-implementations ─────────────────────────────────────────────────

function parseOptionalDateFilter(value) {
	if (!value) return null;

	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? null : value;
	}

	if (typeof value === "string") {
		const normalized = value.trim();
		if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) return null;
		const parsed = new Date(`${normalized}T00:00:00.000Z`);
		return Number.isNaN(parsed.getTime()) ||
			parsed.toISOString().slice(0, 10) !== normalized
			? null
			: parsed;
	}

	return null;
}

function normalizeExpenseCategory(value) {
	return typeof value === "string" && value.trim() ? value.trim() : "Other";
}

function isCattleTagDuplicateError(error) {
	if (error?.code !== "P2002") return false;
	const target = error?.meta?.target;
	if (Array.isArray(target)) return target.includes("tagNumber");
	return typeof target === "string" && target.includes("tagNumber");
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("expense.js parseOptionalDateFilter uses strict roundtrip date guard", () => {
	assert.match(expenseSrc, /function parseOptionalDateFilter\(value\)/);
	assert.match(expenseSrc, /parsed\.toISOString\(\)\.slice\(0, 10\) !== normalized/);
	assert.match(expenseSrc, /Number\.isNaN\(parsed\.getTime\(\)\)/);
});

test("expense.js normalizeExpenseCategory defaults to 'Other' for blank input", () => {
	assert.match(expenseSrc, /function normalizeExpenseCategory\(value\)/);
	assert.match(expenseSrc, /typeof value === "string" && value\.trim\(\)/);
	assert.match(expenseSrc, /: "Other"/);
});

test("cattle.js isCattleTagDuplicateError checks P2002 code and array/string target", () => {
	assert.match(cattleSrc, /function isCattleTagDuplicateError\(error\)/);
	assert.match(cattleSrc, /error\?\.code !== "P2002"/);
	assert.match(cattleSrc, /Array\.isArray\(target\)/);
	assert.match(cattleSrc, /target\.includes\("tagNumber"\)/);
});

// ── parseOptionalDateFilter behavioral tests ──────────────────────────────────

test("parseOptionalDateFilter returns null for falsy values", () => {
	assert.equal(parseOptionalDateFilter(null), null);
	assert.equal(parseOptionalDateFilter(undefined), null);
	assert.equal(parseOptionalDateFilter(""), null);
	assert.equal(parseOptionalDateFilter(0), null);
	assert.equal(parseOptionalDateFilter(false), null);
});

test("parseOptionalDateFilter passes through valid Date instances", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const result = parseOptionalDateFilter(d);
	assert.equal(result, d);
});

test("parseOptionalDateFilter returns null for NaN Date instances", () => {
	assert.equal(parseOptionalDateFilter(new Date("invalid")), null);
});

test("parseOptionalDateFilter returns a Date for valid YYYY-MM-DD strings", () => {
	const result = parseOptionalDateFilter("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("parseOptionalDateFilter returns null for non-YYYY-MM-DD string formats", () => {
	assert.equal(parseOptionalDateFilter("20260615"), null);
	assert.equal(parseOptionalDateFilter("2026/06/15"), null);
	assert.equal(parseOptionalDateFilter("June 15 2026"), null);
	assert.equal(parseOptionalDateFilter("2026-6-5"), null);
});

test("parseOptionalDateFilter returns null for calendar-impossible dates", () => {
	assert.equal(parseOptionalDateFilter("2026-13-01"), null);
	assert.equal(parseOptionalDateFilter("2026-02-31"), null);
	assert.equal(parseOptionalDateFilter("2026-04-31"), null);
});

test("parseOptionalDateFilter returns null for non-falsy non-date non-string values", () => {
	assert.equal(parseOptionalDateFilter(42), null);
	assert.equal(parseOptionalDateFilter({ date: "2026-06-15" }), null);
	assert.equal(parseOptionalDateFilter([2026, 6, 15]), null);
});

// ── normalizeExpenseCategory behavioral tests ─────────────────────────────────

test("normalizeExpenseCategory returns trimmed string for valid category", () => {
	assert.equal(normalizeExpenseCategory("사료비"), "사료비");
	assert.equal(normalizeExpenseCategory("  사료비  "), "사료비");
	assert.equal(normalizeExpenseCategory("Feed"), "Feed");
});

test("normalizeExpenseCategory returns 'Other' for empty string", () => {
	assert.equal(normalizeExpenseCategory(""), "Other");
});

test("normalizeExpenseCategory returns 'Other' for whitespace-only string", () => {
	assert.equal(normalizeExpenseCategory("   "), "Other");
	assert.equal(normalizeExpenseCategory("\t"), "Other");
});

test("normalizeExpenseCategory returns 'Other' for null, undefined, and non-strings", () => {
	assert.equal(normalizeExpenseCategory(null), "Other");
	assert.equal(normalizeExpenseCategory(undefined), "Other");
	assert.equal(normalizeExpenseCategory(42), "Other");
	assert.equal(normalizeExpenseCategory([]), "Other");
});

// ── isCattleTagDuplicateError behavioral tests ────────────────────────────────

test("isCattleTagDuplicateError returns false for non-P2002 codes", () => {
	assert.equal(isCattleTagDuplicateError({ code: "P2000" }), false);
	assert.equal(isCattleTagDuplicateError({ code: "P2003", meta: { target: "tagNumber" } }), false);
	assert.equal(isCattleTagDuplicateError({ code: "P1000" }), false);
});

test("isCattleTagDuplicateError returns false for null/undefined input", () => {
	assert.equal(isCattleTagDuplicateError(null), false);
	assert.equal(isCattleTagDuplicateError(undefined), false);
	assert.equal(isCattleTagDuplicateError({}), false);
});

test("isCattleTagDuplicateError returns true for P2002 with array target including tagNumber", () => {
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: ["tagNumber"] } }),
		true,
	);
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: ["userId", "tagNumber"] } }),
		true,
	);
});

test("isCattleTagDuplicateError returns false for P2002 with array target NOT including tagNumber", () => {
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: ["userId"] } }),
		false,
	);
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: [] } }),
		false,
	);
});

test("isCattleTagDuplicateError returns true for P2002 with string target including tagNumber", () => {
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: "tagNumber" } }),
		true,
	);
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: "Cattle_tagNumber_key" } }),
		true,
	);
});

test("isCattleTagDuplicateError returns false for P2002 with string target NOT including tagNumber", () => {
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: "userId" } }),
		false,
	);
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: "" } }),
		false,
	);
});

test("isCattleTagDuplicateError returns false for P2002 when target is null or a number", () => {
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: null } }),
		false,
	);
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: { target: 42 } }),
		false,
	);
	assert.equal(
		isCattleTagDuplicateError({ code: "P2002", meta: null }),
		false,
	);
});
