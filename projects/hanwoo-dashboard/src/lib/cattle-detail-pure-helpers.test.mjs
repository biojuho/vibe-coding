/**
 * Behavioral tests for private pure helpers in CattleDetailModal.js:
 *   toStrictInputDate       — strict YYYY-MM-DD → Date or null
 *   normalizeDetailBuildings — array with id/name normalization
 *
 * CattleDetailModal.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/forms/CattleDetailModal.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toStrictInputDate(value) {
	if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
		return null;
	}
	const date = new Date(`${value}T00:00:00.000Z`);
	return Number.isNaN(date.getTime()) ||
		date.toISOString().slice(0, 10) !== value
		? null
		: date;
}

function normalizeDetailBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings
				.filter((building) => building && typeof building === "object")
				.map((building, index) => ({
					...building,
					id: building.id ?? `detail-building-${index}`,
					name:
						typeof building.name === "string" && building.name.trim()
							? building.name
							: "축사 이름 미등록",
				}))
		: [];
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("CattleDetailModal.js toStrictInputDate uses roundtrip date check", () => {
	assert.match(src, /function toStrictInputDate\(value\)/);
	assert.match(src, /date\.toISOString\(\)\.slice\(0, 10\) !== value/);
	assert.match(src, /\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/\.test\(value\)/);
});

test("CattleDetailModal.js normalizeDetailBuildings uses fallback id and name", () => {
	assert.match(src, /function normalizeDetailBuildings\(buildings\)/);
	assert.match(src, /building\.id \?\? `detail-building-\$\{index\}`/);
	assert.match(src, /"축사 이름 미등록"/);
});

// ── toStrictInputDate behavioral tests ────────────────────────────────────────

test("toStrictInputDate returns null for non-string input", () => {
	assert.equal(toStrictInputDate(null), null);
	assert.equal(toStrictInputDate(undefined), null);
	assert.equal(toStrictInputDate(20260615), null);
	assert.equal(toStrictInputDate(new Date()), null);
});

test("toStrictInputDate returns null for strings not matching YYYY-MM-DD", () => {
	assert.equal(toStrictInputDate(""), null);
	assert.equal(toStrictInputDate("2026/06/15"), null);
	assert.equal(toStrictInputDate("2026-6-15"), null);
	assert.equal(toStrictInputDate("2026-06-15T00:00:00Z"), null);
});

test("toStrictInputDate returns a Date for valid calendar dates", () => {
	const result = toStrictInputDate("2026-06-15");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-15");
});

test("toStrictInputDate returns null for calendar-impossible dates", () => {
	assert.equal(toStrictInputDate("2026-02-31"), null);
	assert.equal(toStrictInputDate("2026-13-01"), null);
	assert.equal(toStrictInputDate("2026-00-01"), null);
	assert.equal(toStrictInputDate("2026-06-00"), null);
});

test("toStrictInputDate does NOT trim whitespace (rejects padded strings)", () => {
	// No trim — regex fails on " 2026-06-15 "
	assert.equal(toStrictInputDate(" 2026-06-15 "), null);
});

test("toStrictInputDate returns Date at UTC midnight for valid date", () => {
	const result = toStrictInputDate("2026-01-01");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString(), "2026-01-01T00:00:00.000Z");
});

// ── normalizeDetailBuildings behavioral tests ─────────────────────────────────

test("normalizeDetailBuildings returns empty array for non-array input", () => {
	assert.deepEqual(normalizeDetailBuildings(null), []);
	assert.deepEqual(normalizeDetailBuildings(undefined), []);
	assert.deepEqual(normalizeDetailBuildings("string"), []);
	assert.deepEqual(normalizeDetailBuildings({}), []);
});

test("normalizeDetailBuildings filters out nulls and primitives", () => {
	const buildings = [null, "string", 42, { id: "b1", name: "축사" }];
	const result = normalizeDetailBuildings(buildings);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "b1");
});

test("normalizeDetailBuildings preserves existing id when present", () => {
	const buildings = [{ id: "existing-id", name: "축사" }];
	const result = normalizeDetailBuildings(buildings);
	assert.equal(result[0].id, "existing-id");
});

test("normalizeDetailBuildings generates fallback id when id is missing", () => {
	const buildings = [{ name: "축사" }, { name: "축사2" }];
	const result = normalizeDetailBuildings(buildings);
	assert.equal(result[0].id, "detail-building-0");
	assert.equal(result[1].id, "detail-building-1");
});

test("normalizeDetailBuildings uses fallback id for null id", () => {
	const buildings = [{ id: null, name: "축사" }];
	const result = normalizeDetailBuildings(buildings);
	assert.equal(result[0].id, "detail-building-0");
});

test("normalizeDetailBuildings preserves valid names", () => {
	const buildings = [{ id: "b1", name: "본 축사" }];
	const result = normalizeDetailBuildings(buildings);
	assert.equal(result[0].name, "본 축사");
});

test("normalizeDetailBuildings uses fallback name for empty or whitespace name", () => {
	const buildings = [
		{ id: "b1", name: "" },
		{ id: "b2", name: "   " },
		{ id: "b3" },
	];
	const result = normalizeDetailBuildings(buildings);
	assert.ok(result.every((b) => b.name === "축사 이름 미등록"));
});

test("normalizeDetailBuildings uses fallback name for non-string name", () => {
	const buildings = [{ id: "b1", name: 42 }, { id: "b2", name: null }];
	const result = normalizeDetailBuildings(buildings);
	assert.ok(result.every((b) => b.name === "축사 이름 미등록"));
});

test("normalizeDetailBuildings passes through other building fields", () => {
	const buildings = [{ id: "b1", name: "축사", penCount: 10, location: "동쪽" }];
	const result = normalizeDetailBuildings(buildings);
	assert.equal(result[0].penCount, 10);
	assert.equal(result[0].location, "동쪽");
});

test("normalizeDetailBuildings includes arrays as buildings if they are objects", () => {
	// Note: the filter checks `typeof building === "object"` — arrays pass typeof object
	// but they're truthy and typeof "object" — so arrays ARE kept (unlike normalizeDashboardBuildings)
	const arr = [];
	arr.id = "array-id";
	arr.name = "배열";
	const buildings = [arr];
	const result = normalizeDetailBuildings(buildings);
	// Arrays pass the filter since there's no !Array.isArray check here
	assert.equal(result.length, 1);
});
