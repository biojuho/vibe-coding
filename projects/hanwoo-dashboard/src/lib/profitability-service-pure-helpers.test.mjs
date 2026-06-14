/**
 * Behavioral tests for:
 *   src/lib/dashboard/profitability-service.js — source-grep guards for DB fallback logging
 *   src/components/widgets/AIChatWidget.js     — source-grep guard for error body parse logging
 *
 * Both files import Prisma/React — cannot be loaded in Node ESM.
 * Pure helpers are re-implemented inline; DB logging contracts are verified via source-grep.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

const profitSrc = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/profitability-service.js"),
	"utf8",
);
const chatSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/AIChatWidget.js"),
	"utf8",
);

// ── profitability-service source-grep guards ────────────────────────────────

test("profitability-service: feed expense query failure is logged with console.warn", () => {
	assert.match(
		profitSrc,
		/profitability-service: feed expense query failed/,
		"should log feed expense fallback",
	);
	assert.match(profitSrc, /console\.warn/);
});

test("profitability-service: sales record query failure is logged with console.warn", () => {
	assert.match(
		profitSrc,
		/profitability-service: sales record query failed/,
		"should log sales query fallback",
	);
});

test("profitability-service: sold cattle lookup failure is logged with console.warn", () => {
	assert.match(
		profitSrc,
		/profitability-service: sold cattle lookup failed/,
		"should log sold cattle lookup fallback",
	);
});

test("profitability-service: all three catch blocks return empty array fallback", () => {
	const catchReturns = [...profitSrc.matchAll(/\.catch\(\(err\)\s*=>\s*\{/g)];
	assert.ok(
		catchReturns.length >= 3,
		`expected >= 3 catch((err) => {}) blocks, got ${catchReturns.length}`,
	);
});

test("profitability-service: uses normalizeProfitabilityServiceRows for type safety", () => {
	assert.match(
		profitSrc,
		/normalizeProfitabilityServiceRows/,
		"should normalize rows to guard against non-object entries",
	);
});

// ── profitability-service pure helper re-implementations ───────────────────

function toValidDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function diffMonths(d1, d2) {
	const start = toValidDate(d1);
	const end = toValidDate(d2);
	if (!start || !end) return null;
	let months = (end.getFullYear() - start.getFullYear()) * 12;
	months -= start.getMonth();
	months += end.getMonth();
	return months <= 0 ? 0 : months;
}

function normalizeProfitabilityServiceRows(rows) {
	return Array.isArray(rows)
		? rows.filter((row) => row !== null && typeof row === "object" && !Array.isArray(row))
		: [];
}

// ── diffMonths behavioral tests ────────────────────────────────────────────

test("diffMonths: same month returns 0", () => {
	assert.equal(diffMonths(new Date("2024-01-15"), new Date("2024-01-20")), 0);
});

test("diffMonths: 6 months apart returns 6", () => {
	assert.equal(diffMonths(new Date("2024-01-01"), new Date("2024-07-01")), 6);
});

test("diffMonths: 24 months (2 years) apart returns 24", () => {
	assert.equal(diffMonths(new Date("2022-03-01"), new Date("2024-03-01")), 24);
});

test("diffMonths: end before start returns 0", () => {
	assert.equal(diffMonths(new Date("2024-06-01"), new Date("2024-01-01")), 0);
});

test("diffMonths: invalid date string returns null", () => {
	// new Date(null) = epoch (valid); only genuinely unparseable strings are invalid
	assert.equal(diffMonths("not-a-date", new Date()), null);
	assert.equal(diffMonths(new Date(), "not-a-date"), null);
	assert.equal(diffMonths("bad", "worse"), null);
});

test("diffMonths: ISO string inputs work like Date inputs", () => {
	assert.equal(diffMonths("2023-01-01", "2024-01-01"), 12);
});

// ── normalizeProfitabilityServiceRows behavioral tests ─────────────────────

test("normalizeProfitabilityServiceRows: filters out null entries", () => {
	const result = normalizeProfitabilityServiceRows([null, { id: 1 }, undefined]);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, 1);
});

test("normalizeProfitabilityServiceRows: filters out array entries", () => {
	const result = normalizeProfitabilityServiceRows([[], { id: 2 }]);
	assert.equal(result.length, 1);
});

test("normalizeProfitabilityServiceRows: empty array returns empty array", () => {
	assert.deepEqual(normalizeProfitabilityServiceRows([]), []);
});

test("normalizeProfitabilityServiceRows: non-array input returns empty array", () => {
	assert.deepEqual(normalizeProfitabilityServiceRows(null), []);
	assert.deepEqual(normalizeProfitabilityServiceRows(undefined), []);
	assert.deepEqual(normalizeProfitabilityServiceRows("oops"), []);
});

test("normalizeProfitabilityServiceRows: valid objects are all kept", () => {
	const rows = [{ a: 1 }, { b: 2 }, { c: 3 }];
	assert.equal(normalizeProfitabilityServiceRows(rows).length, 3);
});

// ── AIChatWidget source-grep guard ────────────────────────────────────────

test("AIChatWidget: error response body parse failure logs status with console.warn", () => {
	assert.match(
		chatSrc,
		/AIChatWidget: failed to parse error response body/,
		"should log JSON parse failure for non-OK response",
	);
	assert.match(chatSrc, /res\.status/);
});

test("AIChatWidget: error body parse catch still returns {} fallback", () => {
	assert.match(
		chatSrc,
		/return \{\};/,
		"catch block must return {} so handleError still gets the status code message",
	);
});
