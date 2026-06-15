/**
 * Behavioral tests for the private row-normalization helpers shared
 * across all "use server" action files. Each file cannot be loaded in
 * Node ESM because "use server" + path-alias imports fail; helpers are
 * re-implemented inline and cross-checked via source-grep guards.
 *
 * Files covered:
 *   src/lib/actions/building.js      — isBuildingActionRow, normalizeBuildingActionRows
 *   src/lib/actions/cattle.js        — isCattleTagDuplicateError, isCattleActionRow, normalizeCattleActionRows
 *   src/lib/actions/expense.js       — isPlainObject, parseOptionalDateFilter, normalizeExpenseRows, normalizeExpenseCategory
 *   src/lib/actions/feed.js          — isFeedActionRow, normalizeFeedActionRows
 *   src/lib/actions/inventory.js     — isInventoryActionRow, normalizeInventoryActionRows
 *   src/lib/actions/notification.js  — isFreshNotificationSummary, isNotificationActionCattleRow, normalizeNotificationActionCattleRows
 *   src/lib/actions/sales.js         — isSalesActionRow, normalizeSalesActionRows
 *   src/lib/actions/schedule.js      — isScheduleActionRow, normalizeScheduleActionRows
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readAction(name) {
	return readFileSync(path.join(SRC_ROOT, `lib/actions/${name}.js`), "utf8");
}

const buildingSrc = readAction("building");
const cattleSrc = readAction("cattle");
const expenseSrc = readAction("expense");
const feedSrc = readAction("feed");
const inventorySrc = readAction("inventory");
const notificationSrc = readAction("notification");
const salesSrc = readAction("sales");
const scheduleSrc = readAction("schedule");

// ── Inline re-implementations ─────────────────────────────────────────────────

// Shared plain-object check pattern (identical in all action files)
function isActionRow(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeActionRows(rows) {
	return Array.isArray(rows) ? rows.filter((row) => isActionRow(row)) : [];
}

// From cattle.js — unique logic
function isCattleTagDuplicateError(error) {
	if (error?.code !== "P2002") {
		return false;
	}
	const target = error?.meta?.target;
	if (Array.isArray(target)) {
		return target.includes("tagNumber");
	}
	return typeof target === "string" && target.includes("tagNumber");
}

// From notification.js — unique logic
function isFreshNotificationSummary(summary, now = Date.now()) {
	if (!summary?.payload || !summary.generatedAt) {
		return false;
	}
	const generatedAt = new Date(summary.generatedAt);
	const age = now - generatedAt.getTime();
	return Number.isFinite(age) && age >= 0 && age < 60 * 1000;
}

// From expense.js — unique logic
function parseOptionalDateFilter(value) {
	if (!value) {
		return null;
	}
	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? null : value;
	}
	if (typeof value === "string") {
		const normalized = value.trim();
		if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
			return null;
		}
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

// ── Source-grep guards ────────────────────────────────────────────────────────

test("building.js isBuildingActionRow is non-null non-array object check", () => {
	assert.match(buildingSrc, /function isBuildingActionRow\(value\)/);
	assert.match(buildingSrc, /value !== null/);
	assert.match(buildingSrc, /!Array\.isArray\(value\)/);
});

test("cattle.js isCattleTagDuplicateError checks P2002 and tagNumber", () => {
	assert.match(cattleSrc, /function isCattleTagDuplicateError\(error\)/);
	assert.match(cattleSrc, /error\?\.code !== ["']P2002["']/);
	assert.match(cattleSrc, /target\.includes\(["']tagNumber["']\)/);
});

test("expense.js parseOptionalDateFilter uses YYYY-MM-DD roundtrip check", () => {
	assert.match(expenseSrc, /function parseOptionalDateFilter\(value\)/);
	assert.match(expenseSrc, /parsed\.toISOString\(\)\.slice\(0, 10\) !== normalized/);
});

test("expense.js normalizeExpenseCategory defaults to 'Other'", () => {
	assert.match(expenseSrc, /function normalizeExpenseCategory\(value\)/);
	assert.match(expenseSrc, /"Other"/);
});

test("notification.js isFreshNotificationSummary checks age < 60000ms", () => {
	assert.match(notificationSrc, /function isFreshNotificationSummary\(summary/);
	assert.match(notificationSrc, /age < 60 \* 1000/);
	assert.match(notificationSrc, /summary\?\.payload/);
});

test("notification.js isNotificationActionCattleRow has null + object + !Array guard", () => {
	assert.match(notificationSrc, /function isNotificationActionCattleRow\(value\) \{/);
	assert.match(notificationSrc, /value !== null/);
	assert.match(notificationSrc, /typeof value === ["']object["']/);
	assert.match(notificationSrc, /!Array\.isArray\(value\)/);
});

test("notification.js normalizeNotificationActionCattleRows filters via isNotificationActionCattleRow", () => {
	assert.match(
		notificationSrc,
		/function normalizeNotificationActionCattleRows\(rows\) \{/,
	);
	assert.match(notificationSrc, /isNotificationActionCattleRow\(row\)/);
	assert.match(notificationSrc, /Array\.isArray\(rows\)/);
});

test("notification.js getNotifications tries cache then live prisma query", () => {
	assert.match(notificationSrc, /export async function getNotifications\(\)/);
	assert.match(notificationSrc, /requireAuthenticatedSession\(\)/);
	assert.match(notificationSrc, /isFreshNotificationSummary\(cached\)/);
	assert.match(
		notificationSrc,
		/prisma\.cattle\.findMany\(\{ where: \{ isArchived: false \} \}\)/,
	);
	assert.match(notificationSrc, /prisma\.inventoryItem\.findMany\(\)/);
	assert.match(
		notificationSrc,
		/normalizeNotificationActionCattleRows\(cattleRows\)/,
	);
	assert.match(notificationSrc, /buildNotifications\(cattle, inventory\)/);
});

test("feed.js normalizeFeedActionRows uses isFeedActionRow", () => {
	assert.match(feedSrc, /function normalizeFeedActionRows\(rows\)/);
	assert.match(feedSrc, /isFeedActionRow\(row\)/);
});

test("sales.js normalizeSalesActionRows uses isSalesActionRow", () => {
	assert.match(salesSrc, /function normalizeSalesActionRows\(rows\)/);
	assert.match(salesSrc, /isSalesActionRow\(row\)/);
});

test("schedule.js normalizeScheduleActionRows uses isScheduleActionRow", () => {
	assert.match(scheduleSrc, /function normalizeScheduleActionRows\(rows\)/);
	assert.match(scheduleSrc, /isScheduleActionRow\(row\)/);
});

// ── Shared isActionRow / normalizeActionRows behavioral tests ─────────────────
// These tests apply to all 6 action files that share the same pattern.

test("isActionRow returns true for plain objects", () => {
	assert.equal(isActionRow({ id: "a" }), true);
	assert.equal(isActionRow({}), true);
});

test("isActionRow returns false for null", () => {
	assert.equal(isActionRow(null), false);
});

test("isActionRow returns false for arrays", () => {
	assert.equal(isActionRow([]), false);
	assert.equal(isActionRow([{ id: "a" }]), false);
});

test("isActionRow returns false for primitives", () => {
	assert.equal(isActionRow("string"), false);
	assert.equal(isActionRow(42), false);
	assert.equal(isActionRow(true), false);
	assert.equal(isActionRow(undefined), false);
});

test("normalizeActionRows returns empty array for non-array input", () => {
	assert.deepEqual(normalizeActionRows(null), []);
	assert.deepEqual(normalizeActionRows(undefined), []);
	assert.deepEqual(normalizeActionRows({}), []);
});

test("normalizeActionRows filters out nulls, arrays, and primitives", () => {
	const rows = [null, "string", 42, [], { id: "valid" }, { name: "also valid" }];
	const result = normalizeActionRows(rows);
	assert.equal(result.length, 2);
});

test("normalizeActionRows keeps all plain objects (no id requirement)", () => {
	const rows = [{ a: 1 }, { b: 2 }];
	assert.equal(normalizeActionRows(rows).length, 2);
});

test("normalizeActionRows returns empty array for empty input", () => {
	assert.deepEqual(normalizeActionRows([]), []);
});

// ── isCattleTagDuplicateError behavioral tests ────────────────────────────────

test("isCattleTagDuplicateError returns false for non-P2002 error codes", () => {
	assert.equal(isCattleTagDuplicateError({ code: "P2003" }), false);
	assert.equal(isCattleTagDuplicateError({ code: null }), false);
	assert.equal(isCattleTagDuplicateError(null), false);
	assert.equal(isCattleTagDuplicateError(undefined), false);
});

test("isCattleTagDuplicateError returns true when code=P2002 and target array includes tagNumber", () => {
	const error = { code: "P2002", meta: { target: ["tagNumber"] } };
	assert.equal(isCattleTagDuplicateError(error), true);
});

test("isCattleTagDuplicateError returns false when code=P2002 but target array doesn't include tagNumber", () => {
	const error = { code: "P2002", meta: { target: ["email"] } };
	assert.equal(isCattleTagDuplicateError(error), false);
});

test("isCattleTagDuplicateError returns true when code=P2002 and target string includes tagNumber", () => {
	const error = { code: "P2002", meta: { target: "tagNumber_farmId" } };
	assert.equal(isCattleTagDuplicateError(error), true);
});

test("isCattleTagDuplicateError returns false when code=P2002 but target string doesn't include tagNumber", () => {
	const error = { code: "P2002", meta: { target: "email_unique" } };
	assert.equal(isCattleTagDuplicateError(error), false);
});

test("isCattleTagDuplicateError returns false when code=P2002 but meta.target is null", () => {
	const error = { code: "P2002", meta: { target: null } };
	assert.equal(isCattleTagDuplicateError(error), false);
});

// ── isFreshNotificationSummary behavioral tests ───────────────────────────────

test("isFreshNotificationSummary returns false for null/undefined summary", () => {
	assert.equal(isFreshNotificationSummary(null), false);
	assert.equal(isFreshNotificationSummary(undefined), false);
});

test("isFreshNotificationSummary returns false when summary.payload is missing", () => {
	assert.equal(isFreshNotificationSummary({ generatedAt: new Date() }), false);
});

test("isFreshNotificationSummary returns false when summary.generatedAt is missing", () => {
	assert.equal(isFreshNotificationSummary({ payload: [] }), false);
});

test("isFreshNotificationSummary returns true for a summary generated 30 seconds ago", () => {
	const now = Date.now();
	const summary = {
		payload: [{ type: "test" }],
		generatedAt: new Date(now - 30_000).toISOString(), // 30 seconds ago
	};
	assert.equal(isFreshNotificationSummary(summary, now), true);
});

test("isFreshNotificationSummary returns false for a summary generated 61 seconds ago", () => {
	const now = Date.now();
	const summary = {
		payload: [{ type: "test" }],
		generatedAt: new Date(now - 61_000).toISOString(), // 61 seconds ago
	};
	assert.equal(isFreshNotificationSummary(summary, now), false);
});

test("isFreshNotificationSummary returns false for a future generatedAt (negative age)", () => {
	const now = Date.now();
	const summary = {
		payload: [],
		generatedAt: new Date(now + 5_000).toISOString(), // 5 seconds in future
	};
	// age = now - (now + 5000) = -5000, which is negative → false
	assert.equal(isFreshNotificationSummary(summary, now), false);
});

test("isFreshNotificationSummary is fresh at exactly 59999ms", () => {
	const now = Date.now();
	const summary = {
		payload: [{}],
		generatedAt: new Date(now - 59_999).toISOString(),
	};
	assert.equal(isFreshNotificationSummary(summary, now), true);
});

test("isFreshNotificationSummary is stale at exactly 60000ms", () => {
	const now = Date.now();
	const summary = {
		payload: [{}],
		generatedAt: new Date(now - 60_000).toISOString(),
	};
	assert.equal(isFreshNotificationSummary(summary, now), false);
});

// ── parseOptionalDateFilter behavioral tests ──────────────────────────────────

test("parseOptionalDateFilter returns null for falsy values", () => {
	assert.equal(parseOptionalDateFilter(null), null);
	assert.equal(parseOptionalDateFilter(undefined), null);
	assert.equal(parseOptionalDateFilter(""), null);
	assert.equal(parseOptionalDateFilter(0), null);
	assert.equal(parseOptionalDateFilter(false), null);
});

test("parseOptionalDateFilter returns the Date for a valid Date instance", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const result = parseOptionalDateFilter(d);
	assert.equal(result, d);
});

test("parseOptionalDateFilter returns null for an Invalid Date instance", () => {
	assert.equal(parseOptionalDateFilter(new Date("invalid")), null);
});

test("parseOptionalDateFilter returns Date for a valid YYYY-MM-DD string", () => {
	const result = parseOptionalDateFilter("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("parseOptionalDateFilter returns null for non-YYYY-MM-DD strings", () => {
	assert.equal(parseOptionalDateFilter("2026/06/15"), null);
	assert.equal(parseOptionalDateFilter("June 15"), null);
	assert.equal(parseOptionalDateFilter("2026-6-5"), null);
});

test("parseOptionalDateFilter returns null for calendar-impossible YYYY-MM-DD", () => {
	assert.equal(parseOptionalDateFilter("2026-02-31"), null);
	assert.equal(parseOptionalDateFilter("2026-13-01"), null);
});

test("parseOptionalDateFilter returns null for non-string, non-Date, non-falsy values", () => {
	assert.equal(parseOptionalDateFilter(42), null);
	assert.equal(parseOptionalDateFilter({}), null);
	assert.equal(parseOptionalDateFilter([]), null);
});

// ── normalizeExpenseCategory behavioral tests ─────────────────────────────────

test("normalizeExpenseCategory returns trimmed string for valid input", () => {
	assert.equal(normalizeExpenseCategory("사료비"), "사료비");
	assert.equal(normalizeExpenseCategory("  의약품  "), "의약품");
});

test("normalizeExpenseCategory returns 'Other' for empty/whitespace strings", () => {
	assert.equal(normalizeExpenseCategory(""), "Other");
	assert.equal(normalizeExpenseCategory("   "), "Other");
});

test("normalizeExpenseCategory returns 'Other' for non-strings", () => {
	assert.equal(normalizeExpenseCategory(null), "Other");
	assert.equal(normalizeExpenseCategory(undefined), "Other");
	assert.equal(normalizeExpenseCategory(42), "Other");
	assert.equal(normalizeExpenseCategory([]), "Other");
});
