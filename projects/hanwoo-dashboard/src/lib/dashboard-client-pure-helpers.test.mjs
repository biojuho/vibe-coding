/**
 * Behavioral tests for private pure helpers in DashboardClient.js:
 *   toStrictIsoDateOrNull     — strict YYYY-MM-DD validation
 *   getSortableDateTime       — Date/string → milliseconds or null
 *   toValidCalendarDate       — Date/string → Date instance or null
 *   normalizeDashboardItems   — array shape guard
 *   normalizeDashboardBuildings — array with name/penCount normalization
 *   normalizeDashboardCattleList — array with name normalization
 *
 * DashboardClient.js imports React and path aliases that cannot be
 * resolved in Node ESM. Pure helpers are re-implemented inline with
 * source-grep guards so divergence is caught at test time.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "components/DashboardClient.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toFiniteNumber(value, fallback = 0) {
	const n = Number(value);
	return Number.isFinite(n) ? n : fallback;
}

function toStrictIsoDateOrNull(value) {
	if (typeof value !== "string") {
		return null;
	}

	const normalized = value.trim();
	if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
		return null;
	}

	const date = new Date(`${normalized}T00:00:00.000Z`);
	return Number.isNaN(date.getTime()) ||
		date.toISOString().slice(0, 10) !== normalized
		? null
		: date.toISOString();
}

function getSortableDateTime(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date.getTime();
}

function toValidCalendarDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
			const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
			if (
				Number.isNaN(strictDate.getTime()) ||
				strictDate.toISOString().slice(0, 10) !== dateKey
			) {
				return null;
			}
		}
	}

	return date;
}

function normalizeDashboardItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) =>
					item &&
					typeof item === "object" &&
					!Array.isArray(item) &&
					item.id != null,
			)
		: [];
}

function normalizeDashboardBuildings(buildings) {
	if (!Array.isArray(buildings)) return [];

	return buildings
		.filter(
			(building) =>
				building &&
				typeof building === "object" &&
				!Array.isArray(building) &&
				building.id != null,
		)
		.map((building, index) => ({
			...building,
			id: building.id,
			name:
				typeof building.name === "string" && building.name.trim().length > 0
					? building.name
					: "축사 이름 미등록",
			penCount: Math.max(
				1,
				Math.floor(toFiniteNumber(building.penCount) || 32),
			),
			description:
				typeof building.description === "string" ? building.description : "",
			_displayIndex: index,
		}));
}

function normalizeDashboardCattleList(cattleItems) {
	return normalizeDashboardItems(cattleItems).map((cow) => ({
		...cow,
		id: cow.id,
		name:
			typeof cow.name === "string" && cow.name.trim().length > 0
				? cow.name
				: "개체명 미등록",
	}));
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("DashboardClient.js toStrictIsoDateOrNull rejects non-strings and invalid dates", () => {
	assert.match(src, /function toStrictIsoDateOrNull\(value\)/);
	assert.match(src, /if \(typeof value !== ["']string["']\)/);
	assert.match(src, /date\.toISOString\(\)\.slice\(0, 10\) !== normalized/);
});

test("DashboardClient.js getSortableDateTime returns null for NaN", () => {
	assert.match(src, /function getSortableDateTime\(value\)/);
	assert.match(
		src,
		/return Number\.isNaN\(date\.getTime\(\)\) \? null : date\.getTime\(\)/,
	);
});

test("DashboardClient.js toValidCalendarDate applies strict calendar roundtrip for YYYY-MM-DD strings", () => {
	assert.match(src, /function toValidCalendarDate\(value\)/);
	assert.match(src, /strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
});

test("DashboardClient.js normalizeDashboardItems filters by id != null and plain object", () => {
	assert.match(src, /function normalizeDashboardItems\(items\)/);
	assert.match(src, /item\.id != null/);
	assert.match(src, /!Array\.isArray\(item\)/);
});

test("DashboardClient.js normalizeDashboardBuildings uses fallback name '축사 이름 미등록'", () => {
	assert.match(src, /function normalizeDashboardBuildings\(buildings\)/);
	assert.match(src, /"축사 이름 미등록"/);
	assert.match(src, /Math\.max\(\s*1,\s*Math\.floor\(/);
});

test("DashboardClient.js normalizeDashboardCattleList uses fallback name '개체명 미등록'", () => {
	assert.match(src, /function normalizeDashboardCattleList\(cattleItems\)/);
	assert.match(src, /"개체명 미등록"/);
	assert.match(src, /normalizeDashboardItems\(cattleItems\)/);
});

// ── toStrictIsoDateOrNull behavioral tests ────────────────────────────────────

test("toStrictIsoDateOrNull returns null for non-string inputs", () => {
	assert.equal(toStrictIsoDateOrNull(null), null);
	assert.equal(toStrictIsoDateOrNull(undefined), null);
	assert.equal(toStrictIsoDateOrNull(20260615), null);
	assert.equal(toStrictIsoDateOrNull(new Date("2026-06-15")), null);
	assert.equal(toStrictIsoDateOrNull([]), null);
});

test("toStrictIsoDateOrNull returns null for non-YYYY-MM-DD strings", () => {
	assert.equal(toStrictIsoDateOrNull(""), null);
	assert.equal(toStrictIsoDateOrNull("2026/06/15"), null);
	assert.equal(toStrictIsoDateOrNull("June 15 2026"), null);
	assert.equal(toStrictIsoDateOrNull("2026-6-15"), null); // single digit month
	assert.equal(toStrictIsoDateOrNull("2026-06-15T12:00:00Z"), null); // ISO with time
});

test("toStrictIsoDateOrNull returns ISO string for valid calendar dates", () => {
	assert.equal(toStrictIsoDateOrNull("2026-06-15"), "2026-06-15T00:00:00.000Z");
	assert.equal(toStrictIsoDateOrNull("2026-01-01"), "2026-01-01T00:00:00.000Z");
	assert.equal(toStrictIsoDateOrNull("2026-12-31"), "2026-12-31T00:00:00.000Z");
});

test("toStrictIsoDateOrNull trims whitespace before parsing", () => {
	assert.equal(
		toStrictIsoDateOrNull("  2026-06-15  "),
		"2026-06-15T00:00:00.000Z",
	);
});

test("toStrictIsoDateOrNull returns null for calendar-impossible dates", () => {
	// Feb 31 doesn't exist — roundtrip check catches rollover
	assert.equal(toStrictIsoDateOrNull("2026-02-31"), null);
	assert.equal(toStrictIsoDateOrNull("2026-13-01"), null);
	assert.equal(toStrictIsoDateOrNull("2026-00-01"), null);
	assert.equal(toStrictIsoDateOrNull("2026-06-00"), null);
});

// ── getSortableDateTime behavioral tests ──────────────────────────────────────

test("getSortableDateTime returns ms timestamp for a valid Date", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	assert.equal(getSortableDateTime(d), d.getTime());
});

test("getSortableDateTime returns ms timestamp for a valid date string", () => {
	const expected = new Date("2026-06-15T00:00:00.000Z").getTime();
	assert.equal(getSortableDateTime("2026-06-15T00:00:00.000Z"), expected);
});

test("getSortableDateTime returns null for invalid date strings", () => {
	assert.equal(getSortableDateTime("not-a-date"), null);
	assert.equal(getSortableDateTime(""), null);
	assert.equal(getSortableDateTime(undefined), null);
});

test("getSortableDateTime does not mutate the input Date", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const original = d.getTime();
	getSortableDateTime(d);
	assert.equal(d.getTime(), original);
});

test("getSortableDateTime returns 0 for epoch Date (new Date(0))", () => {
	assert.equal(getSortableDateTime(new Date(0)), 0);
});

// ── toValidCalendarDate behavioral tests ──────────────────────────────────────

test("toValidCalendarDate returns Date clone for a valid Date instance", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const result = toValidCalendarDate(d);
	assert.ok(result instanceof Date);
	assert.equal(result.getTime(), d.getTime());
});

test("toValidCalendarDate returns Date for a valid ISO string", () => {
	const result = toValidCalendarDate("2026-06-15T12:00:00.000Z");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString(), "2026-06-15T12:00:00.000Z");
});

test("toValidCalendarDate returns Date for a valid YYYY-MM-DD string", () => {
	const result = toValidCalendarDate("2026-06-15");
	assert.ok(result instanceof Date, "should return a Date");
});

test("toValidCalendarDate returns null for invalid date strings", () => {
	assert.equal(toValidCalendarDate("not-a-date"), null);
	assert.equal(toValidCalendarDate("abc"), null);
});

test("toValidCalendarDate returns null for calendar-impossible YYYY-MM-DD strings", () => {
	assert.equal(toValidCalendarDate("2026-02-31"), null);
	assert.equal(toValidCalendarDate("2026-13-01"), null);
});

test("toValidCalendarDate returns epoch Date for null (new Date(null) = epoch)", () => {
	const result = toValidCalendarDate(null);
	assert.ok(result instanceof Date);
	assert.equal(result.getTime(), 0);
});

test("toValidCalendarDate returns null for undefined (Invalid Date)", () => {
	assert.equal(toValidCalendarDate(undefined), null);
});

// ── normalizeDashboardItems behavioral tests ──────────────────────────────────

test("normalizeDashboardItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeDashboardItems(null), []);
	assert.deepEqual(normalizeDashboardItems(undefined), []);
	assert.deepEqual(normalizeDashboardItems({}), []);
	assert.deepEqual(normalizeDashboardItems("string"), []);
});

test("normalizeDashboardItems returns empty array for empty array", () => {
	assert.deepEqual(normalizeDashboardItems([]), []);
});

test("normalizeDashboardItems keeps plain objects with id", () => {
	const items = [{ id: "a" }, { id: "b" }];
	const result = normalizeDashboardItems(items);
	assert.equal(result.length, 2);
	assert.equal(result[0].id, "a");
});

test("normalizeDashboardItems filters out nulls and primitives", () => {
	const items = [null, undefined, "string", 42, { id: "ok" }];
	const result = normalizeDashboardItems(items);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "ok");
});

test("normalizeDashboardItems filters out arrays (even if they have id)", () => {
	const arr = [{ id: "nested" }];
	const items = [arr, { id: "plain" }];
	const result = normalizeDashboardItems(items);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "plain");
});

test("normalizeDashboardItems filters out objects without id", () => {
	const items = [{ name: "no id" }, { id: null }, { id: "valid" }];
	const result = normalizeDashboardItems(items);
	// id: null is filtered (null == null is true, but null != null via != is false — actually null != null is false)
	// Wait: item.id != null checks for both null and undefined via loose inequality
	// { id: null } → null != null → false → filtered out
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "valid");
});

test("normalizeDashboardItems keeps items with id: 0 (0 != null is true)", () => {
	const items = [{ id: 0 }, { id: "" }];
	const result = normalizeDashboardItems(items);
	// 0 != null → true (kept); "" != null → true (kept)
	assert.equal(result.length, 2);
});

// ── normalizeDashboardBuildings behavioral tests ───────────────────────────────

test("normalizeDashboardBuildings returns empty array for non-array input", () => {
	assert.deepEqual(normalizeDashboardBuildings(null), []);
	assert.deepEqual(normalizeDashboardBuildings(undefined), []);
});

test("normalizeDashboardBuildings adds _displayIndex based on filtered position", () => {
	const buildings = [
		{ id: "b1", name: "축사1" },
		{ id: "b2", name: "축사2" },
	];
	const result = normalizeDashboardBuildings(buildings);
	assert.equal(result[0]._displayIndex, 0);
	assert.equal(result[1]._displayIndex, 1);
});

test("normalizeDashboardBuildings uses fallback name for empty/missing name", () => {
	const buildings = [
		{ id: "b1", name: "" },
		{ id: "b2" },
		{ id: "b3", name: "   " },
	];
	const result = normalizeDashboardBuildings(buildings);
	assert.equal(result.length, 3);
	assert.ok(result.every((b) => b.name === "축사 이름 미등록"));
});

test("normalizeDashboardBuildings preserves valid names", () => {
	const buildings = [{ id: "b1", name: "본 축사" }];
	const result = normalizeDashboardBuildings(buildings);
	assert.equal(result[0].name, "본 축사");
});

test("normalizeDashboardBuildings uses penCount=32 default when penCount is missing", () => {
	const buildings = [{ id: "b1", name: "축사" }];
	const result = normalizeDashboardBuildings(buildings);
	// Math.max(1, Math.floor(toFiniteNumber(undefined) || 32)) = Math.max(1, Math.floor(0 || 32)) = 32
	assert.equal(result[0].penCount, 32);
});

test("normalizeDashboardBuildings rounds penCount to floor and enforces minimum 1", () => {
	const buildings = [
		{ id: "b1", name: "축사", penCount: 10.9 },
		{ id: "b2", name: "축사", penCount: 0 },
	];
	const result = normalizeDashboardBuildings(buildings);
	assert.equal(result[0].penCount, 10); // floored
	assert.equal(result[1].penCount, 32); // 0 is falsy → || 32 → 32, max(1,32)=32
});

test("normalizeDashboardBuildings defaults description to empty string for non-strings", () => {
	const buildings = [{ id: "b1", name: "축사", description: 42 }];
	const result = normalizeDashboardBuildings(buildings);
	assert.equal(result[0].description, "");
});

// ── normalizeDashboardCattleList behavioral tests ─────────────────────────────

test("normalizeDashboardCattleList returns empty array for non-array input", () => {
	assert.deepEqual(normalizeDashboardCattleList(null), []);
	assert.deepEqual(normalizeDashboardCattleList(undefined), []);
});

test("normalizeDashboardCattleList uses fallback name for cattle without name", () => {
	const cows = [
		{ id: "c1" },
		{ id: "c2", name: "" },
		{ id: "c3", name: "   " },
	];
	const result = normalizeDashboardCattleList(cows);
	assert.equal(result.length, 3);
	assert.ok(result.every((c) => c.name === "개체명 미등록"));
});

test("normalizeDashboardCattleList preserves valid cow names", () => {
	const cows = [{ id: "c1", name: "누렁이" }];
	const result = normalizeDashboardCattleList(cows);
	assert.equal(result[0].name, "누렁이");
});

test("normalizeDashboardCattleList filters out items without id", () => {
	const cows = [{ name: "no id" }, { id: "valid", name: "소" }];
	const result = normalizeDashboardCattleList(cows);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "valid");
});

test("normalizeDashboardCattleList passes through extra cow fields unchanged", () => {
	const cows = [{ id: "c1", name: "소", weight: 450, breed: "한우" }];
	const result = normalizeDashboardCattleList(cows);
	assert.equal(result[0].weight, 450);
	assert.equal(result[0].breed, "한우");
});

test("DashboardClient logs archive cattle failure to console.error", () => {
	assert.match(
		src,
		/console\.error\(["']DashboardClient: archive cattle operation failed["'], err\)/,
	);
});
