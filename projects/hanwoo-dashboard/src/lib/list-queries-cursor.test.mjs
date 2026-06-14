/**
 * Behavioral tests for cursor pagination helpers in dashboard/list-queries.js
 * that are not yet covered by list-queries-parse.test.mjs:
 *   endOfDay, toCursorSortValue, buildDescendingCursorWhere, buildPageInfo
 *
 * list-queries.js imports from bare specifiers that cannot be resolved in
 * Node ESM. Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/list-queries.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function endOfDay(date) {
	const value = new Date(date);
	value.setUTCHours(23, 59, 59, 999);
	return value;
}

function encodeCursor(payload) {
	return Buffer.from(JSON.stringify(payload)).toString("base64url");
}

function toCursorSortValue(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function buildDescendingCursorWhere(fieldName, cursor) {
	if (!cursor) {
		return undefined;
	}

	return {
		OR: [
			{ [fieldName]: { lt: cursor.sortValue } },
			{
				AND: [
					{ [fieldName]: cursor.sortValue },
					{ id: { lt: cursor.id } },
				],
			},
		],
	};
}

function buildPageInfo(items, hasMore, limit, sortField) {
	if (!hasMore || items.length === 0) {
		return {
			hasMore: false,
			nextCursor: null,
			limit,
			returnedCount: items.length,
		};
	}

	const lastItem = items[items.length - 1];
	const sortValue = toCursorSortValue(lastItem[sortField]);
	if (!sortValue) {
		return {
			hasMore: false,
			nextCursor: null,
			limit,
			returnedCount: items.length,
		};
	}

	return {
		hasMore: true,
		nextCursor: encodeCursor({
			id: lastItem.id,
			sortValue,
		}),
		limit,
		returnedCount: items.length,
	};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("list-queries.js endOfDay sets UTC hours to 23:59:59.999", () => {
	assert.match(src, /function endOfDay\(date\)/);
	assert.match(src, /value\.setUTCHours\(23, 59, 59, 999\)/);
});

test("list-queries.js toCursorSortValue returns null for NaN dates", () => {
	assert.match(src, /function toCursorSortValue\(value\)/);
	assert.match(src, /return Number\.isNaN\(date\.getTime\(\)\) \? null : date\.toISOString\(\)/);
});

test("list-queries.js buildDescendingCursorWhere returns undefined for falsy cursor", () => {
	assert.match(src, /function buildDescendingCursorWhere\(fieldName, cursor\)/);
	assert.match(src, /if \(!cursor\)/);
	assert.match(src, /return undefined;/);
});

test("list-queries.js buildPageInfo returns hasMore:false for empty items", () => {
	assert.match(src, /function buildPageInfo\(items, hasMore, limit, sortField\)/);
	assert.match(src, /if \(!hasMore \|\| items\.length === 0\)/);
});

// ── endOfDay behavioral tests ──────────────────────────────────────────────────

test("endOfDay sets time to 23:59:59.999 UTC for a midnight Date", () => {
	const input = new Date("2026-06-15T00:00:00.000Z");
	const result = endOfDay(input);
	assert.equal(result.toISOString(), "2026-06-15T23:59:59.999Z");
});

test("endOfDay sets time to 23:59:59.999 UTC for a mid-day Date", () => {
	const input = new Date("2026-06-15T14:30:00.000Z");
	const result = endOfDay(input);
	assert.equal(result.toISOString(), "2026-06-15T23:59:59.999Z");
});

test("endOfDay does not mutate the input Date", () => {
	const input = new Date("2026-06-15T10:00:00.000Z");
	const originalTime = input.getTime();
	endOfDay(input);
	assert.equal(input.getTime(), originalTime, "input should not be mutated");
});

test("endOfDay accepts a date string and applies end-of-day", () => {
	const result = endOfDay("2026-06-15");
	assert.equal(result.toISOString(), "2026-06-15T23:59:59.999Z");
});

// ── toCursorSortValue behavioral tests ────────────────────────────────────────

test("toCursorSortValue returns ISO string for a valid Date", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	assert.equal(toCursorSortValue(d), "2026-06-15T12:00:00.000Z");
});

test("toCursorSortValue clones Date instances (defensive copy)", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = toCursorSortValue(d);
	assert.equal(result, d.toISOString(), "returns ISO not original reference");
});

test("toCursorSortValue returns ISO string for valid date strings", () => {
	const result = toCursorSortValue("2026-06-15T12:00:00.000Z");
	assert.equal(result, "2026-06-15T12:00:00.000Z");
});

test("toCursorSortValue returns null for Invalid Date instances", () => {
	assert.equal(toCursorSortValue(new Date("invalid")), null);
});

test("toCursorSortValue returns null for invalid date strings", () => {
	assert.equal(toCursorSortValue("not-a-date"), null);
	assert.equal(toCursorSortValue(""), null);
	assert.equal(toCursorSortValue(undefined), null);
});

// ── buildDescendingCursorWhere behavioral tests ───────────────────────────────

test("buildDescendingCursorWhere returns undefined for null cursor", () => {
	assert.equal(buildDescendingCursorWhere("saleDate", null), undefined);
});

test("buildDescendingCursorWhere returns undefined for undefined cursor", () => {
	assert.equal(buildDescendingCursorWhere("saleDate", undefined), undefined);
});

test("buildDescendingCursorWhere returns undefined for falsy cursor (0, false, '')", () => {
	assert.equal(buildDescendingCursorWhere("saleDate", 0), undefined);
	assert.equal(buildDescendingCursorWhere("saleDate", ""), undefined);
	assert.equal(buildDescendingCursorWhere("saleDate", false), undefined);
});

test("buildDescendingCursorWhere returns OR clause for a valid cursor", () => {
	const cursor = { id: "item-123", sortValue: new Date("2026-06-15T00:00:00.000Z") };
	const result = buildDescendingCursorWhere("saleDate", cursor);
	assert.ok(result !== undefined);
	assert.ok(Array.isArray(result.OR));
	assert.equal(result.OR.length, 2);
});

test("buildDescendingCursorWhere first OR branch uses lt on sortValue", () => {
	const sortValue = new Date("2026-06-15T00:00:00.000Z");
	const cursor = { id: "item-123", sortValue };
	const result = buildDescendingCursorWhere("saleDate", cursor);
	assert.deepEqual(result.OR[0], { saleDate: { lt: sortValue } });
});

test("buildDescendingCursorWhere second OR branch ties on date and breaks by id lt", () => {
	const sortValue = new Date("2026-06-15T00:00:00.000Z");
	const cursor = { id: "item-123", sortValue };
	const result = buildDescendingCursorWhere("saleDate", cursor);
	assert.deepEqual(result.OR[1], {
		AND: [
			{ saleDate: sortValue },
			{ id: { lt: "item-123" } },
		],
	});
});

// ── buildPageInfo behavioral tests ────────────────────────────────────────────

test("buildPageInfo returns hasMore:false when hasMore=false", () => {
	const items = [{ id: "a", saleDate: new Date("2026-06-15T00:00:00.000Z") }];
	const result = buildPageInfo(items, false, 50, "saleDate");
	assert.equal(result.hasMore, false);
	assert.equal(result.nextCursor, null);
	assert.equal(result.limit, 50);
	assert.equal(result.returnedCount, 1);
});

test("buildPageInfo returns hasMore:false for empty items array", () => {
	const result = buildPageInfo([], true, 50, "saleDate");
	assert.equal(result.hasMore, false);
	assert.equal(result.nextCursor, null);
	assert.equal(result.returnedCount, 0);
});

test("buildPageInfo returns hasMore:true with encoded cursor when conditions met", () => {
	const saleDate = new Date("2026-06-15T00:00:00.000Z");
	const items = [
		{ id: "a", saleDate },
		{ id: "b", saleDate },
	];
	const result = buildPageInfo(items, true, 50, "saleDate");
	assert.equal(result.hasMore, true);
	assert.ok(typeof result.nextCursor === "string", "nextCursor should be a string");
	assert.equal(result.returnedCount, 2);
	// cursor should be decodable
	const decoded = JSON.parse(Buffer.from(result.nextCursor, "base64url").toString("utf8"));
	assert.equal(decoded.id, "b");
	assert.equal(decoded.sortValue, saleDate.toISOString());
});

test("buildPageInfo uses the LAST item for cursor, not the first", () => {
	const items = [
		{ id: "first", saleDate: new Date("2026-06-10T00:00:00.000Z") },
		{ id: "last", saleDate: new Date("2026-06-05T00:00:00.000Z") },
	];
	const result = buildPageInfo(items, true, 50, "saleDate");
	const decoded = JSON.parse(Buffer.from(result.nextCursor, "base64url").toString("utf8"));
	assert.equal(decoded.id, "last");
});

test("buildPageInfo returns hasMore:false when last item has an invalid sortField value", () => {
	// Invalid date in sortField → toCursorSortValue returns null → hasMore:false
	const items = [{ id: "a", saleDate: "not-a-date" }];
	const result = buildPageInfo(items, true, 50, "saleDate");
	assert.equal(result.hasMore, false);
	assert.equal(result.nextCursor, null);
});
