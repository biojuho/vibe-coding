/**
 * Behavioral tests for private pure helpers in the AI API routes:
 *   src/app/api/ai/chat/route.js
 *   src/app/api/ai/insight/route.js
 *
 * Both files import from Next.js, @google/generative-ai, and path aliases
 * that cannot be resolved in Node ESM. Pure helpers are re-implemented
 * inline and cross-checked via source-grep.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const chatSrc = readFileSync(
	path.join(SRC_ROOT, "app/api/ai/chat/route.js"),
	"utf8",
);
const insightSrc = readFileSync(
	path.join(SRC_ROOT, "app/api/ai/insight/route.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

// From @/lib/utils (re-implemented to avoid path alias)
function toFiniteNumber(value, fallback = 0) {
	const amount = Number(value);
	return Number.isFinite(amount) ? amount : fallback;
}

// From chat/route.js
function formatSaleDateForContext(value) {
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) {
		return "출하일 미등록";
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (
			/^\d{4}-\d{2}-\d{2}$/.test(dateKey) &&
			date.toISOString().slice(0, 10) !== dateKey
		) {
			return "출하일 미등록";
		}
	}

	return date.toISOString().slice(0, 10);
}

function isFarmContextRow(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeFarmContextRows(rows) {
	return Array.isArray(rows) ? rows.filter((row) => isFarmContextRow(row)) : [];
}

function normalizeStatusCountLabel(value) {
	return typeof value === "string" && value.trim() ? value.trim() : "상태 미등록";
}

function normalizeStatusCountValue(value) {
	if (isFarmContextRow(value._count)) {
		return toFiniteNumber(value._count._all);
	}
	return toFiniteNumber(value._count);
}

// From insight/route.js
class InsightTimeoutError extends Error {
	constructor(timeoutMs) {
		super(`AI insight generation timed out after ${timeoutMs}ms.`);
		this.name = "InsightTimeoutError";
		this.timeoutMs = timeoutMs;
	}
}

function normalizeInsightRequestBody(body) {
	return body && typeof body === "object" && !Array.isArray(body) ? body : {};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("chat/route.js formatSaleDateForContext uses roundtrip date guard", () => {
	assert.match(chatSrc, /function formatSaleDateForContext\(value\)/);
	assert.match(chatSrc, /date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
	assert.match(chatSrc, /return "출하일 미등록"/);
});

test("chat/route.js isFarmContextRow checks non-null non-array object", () => {
	assert.match(chatSrc, /function isFarmContextRow\(value\)/);
	assert.match(chatSrc, /value !== null/);
	assert.match(chatSrc, /!Array\.isArray\(value\)/);
});

test("chat/route.js normalizeStatusCountLabel falls back to Korean default", () => {
	assert.match(chatSrc, /function normalizeStatusCountLabel\(value\)/);
	assert.match(chatSrc, /"상태 미등록"/);
});

test("insight/route.js InsightTimeoutError has name and timeoutMs properties", () => {
	assert.match(insightSrc, /class InsightTimeoutError extends Error/);
	assert.match(insightSrc, /this\.name = ["']InsightTimeoutError["']/);
	assert.match(insightSrc, /this\.timeoutMs = timeoutMs/);
});

// ── formatSaleDateForContext behavioral tests ─────────────────────────────────

test("formatSaleDateForContext returns YYYY-MM-DD for a valid Date object", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	assert.equal(formatSaleDateForContext(d), "2026-06-15");
});

test("formatSaleDateForContext returns YYYY-MM-DD for a valid ISO string", () => {
	assert.equal(formatSaleDateForContext("2026-06-15T12:00:00.000Z"), "2026-06-15");
});

test("formatSaleDateForContext returns YYYY-MM-DD for a valid YYYY-MM-DD string", () => {
	assert.equal(formatSaleDateForContext("2026-06-15"), "2026-06-15");
});

test("formatSaleDateForContext returns '출하일 미등록' for an invalid date string", () => {
	assert.equal(formatSaleDateForContext("not-a-date"), "출하일 미등록");
	assert.equal(formatSaleDateForContext("abc"), "출하일 미등록");
});

test("formatSaleDateForContext returns '출하일 미등록' for calendar-impossible YYYY-MM-DD strings", () => {
	// Feb 31 rolls over to Mar 3 — roundtrip check catches this
	assert.equal(formatSaleDateForContext("2026-02-31"), "출하일 미등록");
	assert.equal(formatSaleDateForContext("2026-13-01"), "출하일 미등록");
});

test("formatSaleDateForContext returns epoch string for null (new Date(null) = epoch)", () => {
	// new Date(null) = Jan 1 1970, valid date — typeof null !== 'string', no string branch
	assert.equal(formatSaleDateForContext(null), "1970-01-01");
});

test("formatSaleDateForContext returns '출하일 미등록' for undefined (Invalid Date)", () => {
	assert.equal(formatSaleDateForContext(undefined), "출하일 미등록");
});

// ── isFarmContextRow behavioral tests ─────────────────────────────────────────

test("isFarmContextRow returns true for plain objects", () => {
	assert.equal(isFarmContextRow({ status: "비육우", _count: 5 }), true);
	assert.equal(isFarmContextRow({}), true);
});

test("isFarmContextRow returns false for null", () => {
	assert.equal(isFarmContextRow(null), false);
});

test("isFarmContextRow returns false for arrays", () => {
	assert.equal(isFarmContextRow([]), false);
	assert.equal(isFarmContextRow([{ id: 1 }]), false);
});

test("isFarmContextRow returns false for primitives", () => {
	assert.equal(isFarmContextRow("string"), false);
	assert.equal(isFarmContextRow(42), false);
	assert.equal(isFarmContextRow(true), false);
	assert.equal(isFarmContextRow(undefined), false);
});

// ── normalizeFarmContextRows behavioral tests ──────────────────────────────────

test("normalizeFarmContextRows keeps only plain object rows", () => {
	const rows = [
		{ status: "비육우", _count: 5 },
		null,
		"bad",
		{ status: "송아지", _count: 2 },
		[],
	];
	const result = normalizeFarmContextRows(rows);
	assert.equal(result.length, 2);
	assert.equal(result[0].status, "비육우");
	assert.equal(result[1].status, "송아지");
});

test("normalizeFarmContextRows returns empty array for non-array input", () => {
	assert.deepEqual(normalizeFarmContextRows(null), []);
	assert.deepEqual(normalizeFarmContextRows(undefined), []);
	assert.deepEqual(normalizeFarmContextRows({}), []);
	assert.deepEqual(normalizeFarmContextRows("string"), []);
});

test("normalizeFarmContextRows returns empty array for empty array input", () => {
	assert.deepEqual(normalizeFarmContextRows([]), []);
});

// ── normalizeStatusCountLabel behavioral tests ────────────────────────────────

test("normalizeStatusCountLabel trims and returns non-empty strings", () => {
	assert.equal(normalizeStatusCountLabel("비육우"), "비육우");
	assert.equal(normalizeStatusCountLabel("  비육우  "), "비육우");
});

test("normalizeStatusCountLabel returns '상태 미등록' for empty/whitespace strings", () => {
	assert.equal(normalizeStatusCountLabel(""), "상태 미등록");
	assert.equal(normalizeStatusCountLabel("   "), "상태 미등록");
	assert.equal(normalizeStatusCountLabel("\t"), "상태 미등록");
});

test("normalizeStatusCountLabel returns '상태 미등록' for non-strings", () => {
	assert.equal(normalizeStatusCountLabel(null), "상태 미등록");
	assert.equal(normalizeStatusCountLabel(undefined), "상태 미등록");
	assert.equal(normalizeStatusCountLabel(42), "상태 미등록");
	assert.equal(normalizeStatusCountLabel([]), "상태 미등록");
});

// ── normalizeStatusCountValue behavioral tests ────────────────────────────────

test("normalizeStatusCountValue extracts _count when it's a number", () => {
	assert.equal(normalizeStatusCountValue({ _count: 5 }), 5);
	assert.equal(normalizeStatusCountValue({ _count: 0 }), 0);
});

test("normalizeStatusCountValue extracts _count._all when _count is an object", () => {
	// Prisma groupBy with _count: true returns { _count: { _all: N } }
	assert.equal(normalizeStatusCountValue({ _count: { _all: 3 } }), 3);
	assert.equal(normalizeStatusCountValue({ _count: { _all: 0 } }), 0);
});

test("normalizeStatusCountValue returns 0 (fallback) for non-finite _count values", () => {
	assert.equal(normalizeStatusCountValue({ _count: null }), 0);
	assert.equal(normalizeStatusCountValue({ _count: "five" }), 0);
	assert.equal(normalizeStatusCountValue({ _count: undefined }), 0);
});

test("normalizeStatusCountValue returns 0 for missing _count._all in object branch", () => {
	assert.equal(normalizeStatusCountValue({ _count: { _all: null } }), 0);
	assert.equal(normalizeStatusCountValue({ _count: {} }), 0);
});

// ── InsightTimeoutError behavioral tests ──────────────────────────────────────

test("InsightTimeoutError has name='InsightTimeoutError'", () => {
	const err = new InsightTimeoutError(10000);
	assert.equal(err.name, "InsightTimeoutError");
});

test("InsightTimeoutError message includes the timeout value", () => {
	const err = new InsightTimeoutError(10000);
	assert.ok(err.message.includes("10000ms"), `message: ${err.message}`);
});

test("InsightTimeoutError stores timeoutMs on the instance", () => {
	const err = new InsightTimeoutError(5000);
	assert.equal(err.timeoutMs, 5000);
});

test("InsightTimeoutError is an instance of Error", () => {
	assert.ok(new InsightTimeoutError(10000) instanceof Error);
});

// ── normalizeInsightRequestBody behavioral tests ───────────────────────────────

test("normalizeInsightRequestBody passes through plain objects", () => {
	const body = { forceFresh: true, farmId: "default" };
	const result = normalizeInsightRequestBody(body);
	assert.equal(result, body);
});

test("normalizeInsightRequestBody returns empty object for null/undefined", () => {
	assert.deepEqual(normalizeInsightRequestBody(null), {});
	assert.deepEqual(normalizeInsightRequestBody(undefined), {});
});

test("normalizeInsightRequestBody returns empty object for arrays", () => {
	assert.deepEqual(normalizeInsightRequestBody([{ key: "val" }]), {});
});

test("normalizeInsightRequestBody returns empty object for primitives", () => {
	assert.deepEqual(normalizeInsightRequestBody("string"), {});
	assert.deepEqual(normalizeInsightRequestBody(42), {});
});
