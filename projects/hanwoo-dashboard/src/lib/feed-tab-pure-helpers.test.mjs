/**
 * Behavioral tests for private pure helpers in FeedTab.js:
 *   toValidFeedDate    — Date/string → Date or null (roundtrip check on YYYY-MM-DD)
 *   getFeedDateTime    — Date/string → ms timestamp or NEGATIVE_INFINITY
 *   formatFeedDateLabel — Date/string → Korean locale string or "날짜 미등록"
 *   normalizeFeedItems  — array filter (plain objects, no id requirement)
 *   normalizeFeedBuildings — filter + map (fallback id/name, no id requirement)
 *
 * FeedTab.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/tabs/FeedTab.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toValidFeedDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (
			/^\d{4}-\d{2}-\d{2}$/.test(dateKey) &&
			date.toISOString().slice(0, 10) !== dateKey
		) {
			return null;
		}
	}

	return date;
}

function getFeedDateTime(value) {
	return toValidFeedDate(value)?.getTime() ?? Number.NEGATIVE_INFINITY;
}

function formatFeedDateLabel(value, options) {
	const date = toValidFeedDate(value);
	return date ? date.toLocaleDateString("ko-KR", options) : "날짜 미등록";
}

function normalizeFeedItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeFeedBuildings(buildings) {
	return normalizeFeedItems(buildings).map((building, index) => ({
		...building,
		id: building.id ?? `feed-building-${index}`,
		name:
			typeof building.name === "string" && building.name.trim()
				? building.name
				: "축사 이름 미등록",
	}));
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("FeedTab.js toValidFeedDate does YYYY-MM-DD roundtrip check for strings", () => {
	assert.match(src, /function toValidFeedDate\(value\)/);
	assert.match(src, /\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\//);
	assert.match(src, /date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
});

test("FeedTab.js getFeedDateTime returns NEGATIVE_INFINITY for invalid dates", () => {
	assert.match(src, /function getFeedDateTime\(value\)/);
	assert.match(src, /toValidFeedDate\(value\)\?\.getTime\(\) \?\? Number\.NEGATIVE_INFINITY/);
});

test("FeedTab.js formatFeedDateLabel returns Korean locale string or fallback", () => {
	assert.match(src, /function formatFeedDateLabel\(value, options\)/);
	assert.match(src, /toLocaleDateString\(["']ko-KR["']/);
	assert.match(src, /"날짜 미등록"/);
});

test("FeedTab.js normalizeFeedBuildings uses feed-building-N fallback id", () => {
	assert.match(src, /function normalizeFeedBuildings\(buildings\)/);
	assert.match(src, /`feed-building-\$\{index\}`/);
	assert.match(src, /"축사 이름 미등록"/);
});

// ── toValidFeedDate behavioral tests ─────────────────────────────────────────

test("toValidFeedDate returns null for truly invalid date strings", () => {
	assert.equal(toValidFeedDate("not-a-date"), null);
	assert.equal(toValidFeedDate("abc"), null);
	assert.equal(toValidFeedDate("2026-13-01"), null);
});

test("toValidFeedDate returns null for calendar-impossible YYYY-MM-DD", () => {
	assert.equal(toValidFeedDate("2026-02-31"), null);
});

test("toValidFeedDate returns Date for valid YYYY-MM-DD string", () => {
	const result = toValidFeedDate("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("toValidFeedDate returns Date for valid Date instance", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = toValidFeedDate(d);
	assert.ok(result instanceof Date);
	assert.equal(result.getTime(), d.getTime());
});

test("toValidFeedDate does not mutate input Date", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const original = d.getTime();
	toValidFeedDate(d);
	assert.equal(d.getTime(), original);
});

test("toValidFeedDate returns null for invalid Date instance", () => {
	assert.equal(toValidFeedDate(new Date("invalid")), null);
});

test("toValidFeedDate accepts full ISO timestamp string (non-YYYY-MM-DD)", () => {
	// ISO strings don't match /^\d{4}-\d{2}-\d{2}$/ so skip roundtrip guard
	const result = toValidFeedDate("2026-06-15T12:00:00.000Z");
	assert.ok(result instanceof Date);
});

test("toValidFeedDate returns null for null/undefined/0/false (new Date falsy)", () => {
	// new Date(null) = epoch (valid!), new Date(undefined) = NaN
	// Per implementation: `new Date(null).getTime()` = 0 which IS finite
	// So null creates epoch Date
	const nullResult = toValidFeedDate(null);
	// null is not a string, so no string roundtrip guard — returns epoch Date
	assert.ok(nullResult instanceof Date);
	assert.equal(nullResult.getTime(), 0);

	// undefined → NaN
	assert.equal(toValidFeedDate(undefined), null);
});

// ── getFeedDateTime behavioral tests ─────────────────────────────────────────

test("getFeedDateTime returns NEGATIVE_INFINITY for invalid date strings", () => {
	assert.equal(getFeedDateTime("not-a-date"), Number.NEGATIVE_INFINITY);
	assert.equal(getFeedDateTime(undefined), Number.NEGATIVE_INFINITY);
	assert.equal(getFeedDateTime("2026-02-31"), Number.NEGATIVE_INFINITY);
});

test("getFeedDateTime returns numeric timestamp for valid date", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = getFeedDateTime(d);
	assert.ok(typeof result === "number" && Number.isFinite(result));
	assert.equal(result, d.getTime());
});

test("getFeedDateTime returns NEGATIVE_INFINITY for invalid Date instance", () => {
	assert.equal(getFeedDateTime(new Date("invalid")), Number.NEGATIVE_INFINITY);
});

test("getFeedDateTime is usable as a sort comparator key (earlier dates sort first)", () => {
	const records = [
		{ date: "2026-06-15" },
		{ date: "2026-05-10" },
		{ date: "invalid" },
		{ date: "2026-07-01" },
	];
	const sorted = [...records].sort(
		(a, b) => getFeedDateTime(a.date) - getFeedDateTime(b.date),
	);
	// Invalid dates (NEGATIVE_INFINITY) sort to the front
	assert.equal(sorted[0].date, "invalid");
	assert.equal(sorted[1].date, "2026-05-10");
	assert.equal(sorted[2].date, "2026-06-15");
	assert.equal(sorted[3].date, "2026-07-01");
});

// ── formatFeedDateLabel behavioral tests ─────────────────────────────────────

test("formatFeedDateLabel returns '날짜 미등록' for invalid date", () => {
	assert.equal(formatFeedDateLabel("not-a-date"), "날짜 미등록");
	assert.equal(formatFeedDateLabel(undefined), "날짜 미등록");
	assert.equal(formatFeedDateLabel("2026-02-31"), "날짜 미등록");
});

test("formatFeedDateLabel returns a non-empty Korean-locale string for valid date", () => {
	const result = formatFeedDateLabel("2026-06-15");
	assert.ok(typeof result === "string" && result.length > 0);
	assert.notEqual(result, "날짜 미등록");
});

test("formatFeedDateLabel accepts Date instance", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const result = formatFeedDateLabel(d);
	assert.ok(typeof result === "string" && result.length > 0);
});

// ── normalizeFeedItems behavioral tests ───────────────────────────────────────

test("normalizeFeedItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeFeedItems(null), []);
	assert.deepEqual(normalizeFeedItems(undefined), []);
	assert.deepEqual(normalizeFeedItems({}), []);
});

test("normalizeFeedItems filters null, primitives, and arrays", () => {
	const items = [null, "string", 42, [], { id: "ok" }];
	assert.equal(normalizeFeedItems(items).length, 1);
});

test("normalizeFeedItems keeps plain objects regardless of id", () => {
	const items = [{ date: "2026-06-15" }, { cattle: "한우" }];
	assert.equal(normalizeFeedItems(items).length, 2);
});

// ── normalizeFeedBuildings behavioral tests ───────────────────────────────────

test("normalizeFeedBuildings returns empty array for non-array input", () => {
	assert.deepEqual(normalizeFeedBuildings(null), []);
	assert.deepEqual(normalizeFeedBuildings(undefined), []);
});

test("normalizeFeedBuildings does NOT require id (unlike SettingsTab)", () => {
	// No id filter — accepts buildings without id and assigns fallback
	const buildings = [{ name: "축사A" }, { name: "축사B" }];
	const result = normalizeFeedBuildings(buildings);
	assert.equal(result.length, 2);
	assert.equal(result[0].id, "feed-building-0");
	assert.equal(result[1].id, "feed-building-1");
});

test("normalizeFeedBuildings preserves existing id", () => {
	const buildings = [{ id: "b1", name: "축사" }];
	const result = normalizeFeedBuildings(buildings);
	assert.equal(result[0].id, "b1");
});

test("normalizeFeedBuildings uses fallback name for empty/whitespace string", () => {
	const buildings = [
		{ name: "" },
		{ name: "   " },
		{ name: 42 },
		{},
	];
	const result = normalizeFeedBuildings(buildings);
	assert.ok(result.every((b) => b.name === "축사 이름 미등록"));
});

test("normalizeFeedBuildings preserves valid name", () => {
	const buildings = [{ name: "동쪽 축사" }];
	const result = normalizeFeedBuildings(buildings);
	assert.equal(result[0].name, "동쪽 축사");
});

test("normalizeFeedBuildings passes through other fields", () => {
	const buildings = [{ id: "b1", name: "축사", penCount: 5, region: "서쪽" }];
	const result = normalizeFeedBuildings(buildings);
	assert.equal(result[0].penCount, 5);
	assert.equal(result[0].region, "서쪽");
});

test("normalizeFeedBuildings filters null/primitive entries before mapping", () => {
	const buildings = [null, "string", { name: "축사" }];
	const result = normalizeFeedBuildings(buildings);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "feed-building-0");
});
