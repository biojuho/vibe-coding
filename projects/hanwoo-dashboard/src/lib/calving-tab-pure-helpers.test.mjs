/**
 * Behavioral tests for private pure helpers in CalvingTab.js:
 *   getPregnancyDateTime    — null → POSITIVE_INFINITY, invalid → POSITIVE_INFINITY
 *   normalizeCalvingCattle  — array filter requiring id != null
 *   normalizeCalvingBuildings — array filter (plain objects, no id requirement)
 *   normalizeCalvingTabOptions — object guard
 *
 * CalvingTab.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/tabs/CalvingTab.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function getPregnancyDateTime(value) {
	if (value == null) return Number.POSITIVE_INFINITY;
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime())
		? Number.POSITIVE_INFINITY
		: date.getTime();
}

function normalizeCalvingCattle(cattle) {
	return Array.isArray(cattle)
		? cattle.filter(
				(row) =>
					row && typeof row === "object" && !Array.isArray(row) && row.id != null,
			)
		: [];
}

function normalizeCalvingBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings.filter(
				(building) =>
					building && typeof building === "object" && !Array.isArray(building),
			)
		: [];
}

function normalizeCalvingTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("CalvingTab.js getPregnancyDateTime null guard returns POSITIVE_INFINITY", () => {
	assert.match(src, /function getPregnancyDateTime\(value\)/);
	assert.match(src, /if \(value == null\) return Number\.POSITIVE_INFINITY/);
	assert.match(src, /Number\.isNaN\(date\.getTime\(\)\)\s*\?\s*Number\.POSITIVE_INFINITY/);
});

test("CalvingTab.js normalizeCalvingCattle requires id != null", () => {
	assert.match(src, /function normalizeCalvingCattle\(cattle\)/);
	assert.match(src, /row\.id != null/);
});

test("CalvingTab.js normalizeCalvingBuildings has no id requirement", () => {
	assert.match(src, /function normalizeCalvingBuildings\(buildings\)/);
	// Unlike normalizeCalvingCattle, no id requirement
	assert.doesNotMatch(src, /function normalizeCalvingBuildings[\s\S]*?building\.id != null/);
});

// ── getPregnancyDateTime behavioral tests ─────────────────────────────────────

test("getPregnancyDateTime returns POSITIVE_INFINITY for null", () => {
	assert.equal(getPregnancyDateTime(null), Number.POSITIVE_INFINITY);
});

test("getPregnancyDateTime returns POSITIVE_INFINITY for undefined", () => {
	assert.equal(getPregnancyDateTime(undefined), Number.POSITIVE_INFINITY);
});

test("getPregnancyDateTime returns POSITIVE_INFINITY for invalid date strings", () => {
	assert.equal(getPregnancyDateTime("not-a-date"), Number.POSITIVE_INFINITY);
	assert.equal(getPregnancyDateTime("abc"), Number.POSITIVE_INFINITY);
});

test("getPregnancyDateTime returns POSITIVE_INFINITY for invalid Date instance", () => {
	assert.equal(getPregnancyDateTime(new Date("invalid")), Number.POSITIVE_INFINITY);
});

test("getPregnancyDateTime returns numeric timestamp for valid date string", () => {
	const result = getPregnancyDateTime("2026-06-15");
	assert.ok(typeof result === "number" && Number.isFinite(result));
});

test("getPregnancyDateTime returns numeric timestamp for valid Date instance", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	assert.equal(getPregnancyDateTime(d), d.getTime());
});

test("getPregnancyDateTime does not mutate Date input", () => {
	const d = new Date("2026-06-15T12:00:00.000Z");
	const original = d.getTime();
	getPregnancyDateTime(d);
	assert.equal(d.getTime(), original);
});

test("getPregnancyDateTime sorts earliest pregnancies first (smaller timestamps)", () => {
	// Null/invalid → POSITIVE_INFINITY sorts LAST (not first like NEGATIVE_INFINITY)
	const records = [
		{ pregnancyDate: "2026-04-15" },
		{ pregnancyDate: null },
		{ pregnancyDate: "2026-06-01" },
		{ pregnancyDate: "invalid" },
	];
	// ascending sort: earliest pregnancy first, null/invalid sorts to the end
	const sorted = [...records].sort(
		(a, b) => getPregnancyDateTime(a.pregnancyDate) - getPregnancyDateTime(b.pregnancyDate),
	);
	assert.equal(sorted[0].pregnancyDate, "2026-04-15");
	assert.equal(sorted[1].pregnancyDate, "2026-06-01");
	// null and invalid → POSITIVE_INFINITY → sort last
	const lastTwoDates = new Set([sorted[2].pregnancyDate, sorted[3].pregnancyDate]);
	assert.ok(lastTwoDates.has(null));
	assert.ok(lastTwoDates.has("invalid"));
});

test("getPregnancyDateTime treats null differently from 0 (null is not epoch)", () => {
	// null guard fires before new Date(null) which would return epoch (0)
	assert.equal(getPregnancyDateTime(null), Number.POSITIVE_INFINITY);
	// Epoch (0) is a valid date, returns 0
	assert.equal(getPregnancyDateTime(0), 0);
});

// ── normalizeCalvingCattle behavioral tests ───────────────────────────────────

test("normalizeCalvingCattle returns empty array for non-array input", () => {
	assert.deepEqual(normalizeCalvingCattle(null), []);
	assert.deepEqual(normalizeCalvingCattle(undefined), []);
	assert.deepEqual(normalizeCalvingCattle({}), []);
});

test("normalizeCalvingCattle requires id != null", () => {
	const cattle = [
		{ id: "c1", name: "소1" },
		{ id: null, name: "소2" },
		{ id: undefined, name: "소3" },
		{ name: "소4" },
	];
	const result = normalizeCalvingCattle(cattle);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "c1");
});

test("normalizeCalvingCattle keeps id:0 (loose != null)", () => {
	const cattle = [{ id: 0, name: "소" }];
	assert.equal(normalizeCalvingCattle(cattle).length, 1);
});

test("normalizeCalvingCattle filters null, primitives, and arrays", () => {
	const cattle = [null, "string", 42, [], { id: "c1" }];
	assert.equal(normalizeCalvingCattle(cattle).length, 1);
});

// ── normalizeCalvingBuildings behavioral tests ────────────────────────────────

test("normalizeCalvingBuildings returns empty array for non-array input", () => {
	assert.deepEqual(normalizeCalvingBuildings(null), []);
	assert.deepEqual(normalizeCalvingBuildings(undefined), []);
});

test("normalizeCalvingBuildings does NOT require id (unlike normalizeCalvingCattle)", () => {
	const buildings = [{ name: "축사A" }, { name: "축사B" }];
	const result = normalizeCalvingBuildings(buildings);
	assert.equal(result.length, 2);
});

test("normalizeCalvingBuildings filters null, primitives, and arrays", () => {
	const buildings = [null, "string", 42, [], { id: "b1" }];
	assert.equal(normalizeCalvingBuildings(buildings).length, 1);
});

// ── normalizeCalvingTabOptions behavioral tests ───────────────────────────────

test("normalizeCalvingTabOptions returns input for valid object", () => {
	const obj = { cattle: [], buildings: [] };
	assert.equal(normalizeCalvingTabOptions(obj), obj);
});

test("normalizeCalvingTabOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeCalvingTabOptions(null), {});
	assert.deepEqual(normalizeCalvingTabOptions(undefined), {});
	assert.deepEqual(normalizeCalvingTabOptions([]), {});
});
