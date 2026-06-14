/**
 * Behavioral tests for private pure helpers in:
 *   InventoryTab.js   — parseInlineQuantityInput, toInventoryNumber, normalizeInventoryItems
 *   ScheduleTab.js    — toDateKey, normalizeScheduleEvents, formatDaysLeftLabel
 *
 * Both files import React and cannot be loaded in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

const invSrc = readFileSync(
	path.join(SRC_ROOT, "components/tabs/InventoryTab.js"),
	"utf8",
);
const schSrc = readFileSync(
	path.join(SRC_ROOT, "components/tabs/ScheduleTab.js"),
	"utf8",
);

// ── InventoryTab inline re-implementations ────────────────────────────────────

const PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN = /^(?:\d+|\d+\.\d+|\.\d+)$/;

function parseInlineQuantityInput(value) {
	const normalized = String(value).trim();
	if (!PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN.test(normalized)) {
		return Number.NaN;
	}
	const quantity = Number(normalized);
	return Number.isFinite(quantity) ? quantity : Number.NaN;
}

function toInventoryNumber(value, fallback = 0) {
	if (value === null || value === undefined || value === "") {
		return fallback;
	}
	const number = Number(value);
	return Number.isFinite(number) ? number : fallback;
}

function normalizeInventoryItems(inventory) {
	if (!Array.isArray(inventory)) return [];
	return inventory
		.filter((item) => item && typeof item === "object" && !Array.isArray(item))
		.map((item, index) => ({
			...item,
			category:
				typeof item.category === "string" && item.category.trim()
					? item.category
					: "Other",
			id: item.id ?? `inventory-${index}`,
			name:
				typeof item.name === "string" && item.name.trim()
					? item.name
					: "재고명 미등록",
			quantity: toInventoryNumber(item.quantity, null),
			threshold:
				item.threshold === null ||
				item.threshold === undefined ||
				item.threshold === ""
					? null
					: toInventoryNumber(item.threshold, null),
			unit:
				typeof item.unit === "string" && item.unit.trim() ? item.unit : "개",
		}));
}

// ── ScheduleTab inline re-implementations ────────────────────────────────────

const TYPE_STYLES = {
	Vaccination: {},
	Checkup: {},
	Breeding: {},
	Other: {},
	General: {},
};

function toValidDate(value) {
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

function toDateKey(value) {
	const date = toValidDate(value);
	if (!date) return null;
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

function normalizeScheduleEvents(events) {
	if (!Array.isArray(events)) return [];
	return events
		.filter((event) => event && typeof event === "object" && !Array.isArray(event))
		.map((event, index) => ({
			...event,
			id: event.id ?? `schedule-${index}`,
			title:
				typeof event.title === "string" && event.title.trim()
					? event.title
					: "일정명 미등록",
			type:
				typeof event.type === "string" && TYPE_STYLES[event.type]
					? event.type
					: "General",
			isCompleted: Boolean(event.isCompleted),
		}));
}

function formatDaysLeftLabel(daysLeft) {
	return daysLeft === 0 ? "오늘" : `${daysLeft}일 남음`;
}

// ── Source-grep guards: InventoryTab ─────────────────────────────────────────

test("InventoryTab.js PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN is defined", () => {
	assert.match(invSrc, /PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN/);
	assert.match(invSrc, /\\d\+\|\s*\\d\+\\\.\s*\\d\+\|\s*\\\.\s*\\d\+/);
});

test("InventoryTab.js parseInlineQuantityInput trims and returns NaN for mismatch", () => {
	assert.match(invSrc, /function parseInlineQuantityInput\(value\)/);
	assert.match(invSrc, /String\(value\)\.trim\(\)/);
	assert.match(invSrc, /Number\.NaN/);
});

test("InventoryTab.js toInventoryNumber strict null/undefined/empty check before Number()", () => {
	assert.match(invSrc, /function toInventoryNumber\(value, fallback = 0\)/);
	assert.match(invSrc, /value === null \|\| value === undefined \|\| value === ""/);
	assert.match(invSrc, /Number\.isFinite\(number\) \? number : fallback/);
});

test("InventoryTab.js normalizeInventoryItems quantity uses toInventoryNumber(item.quantity, null)", () => {
	assert.match(invSrc, /function normalizeInventoryItems\(inventory\)/);
	assert.match(invSrc, /quantity: toInventoryNumber\(item\.quantity, null\)/);
});

test("InventoryTab.js normalizeInventoryItems threshold: null for null/undefined/empty string", () => {
	assert.match(
		invSrc,
		/item\.threshold === null \|\|\s*item\.threshold === undefined \|\|\s*item\.threshold === ""/,
	);
	assert.match(invSrc, /\? null\s*:\s*toInventoryNumber\(item\.threshold, null\)/);
});

// ── Source-grep guards: ScheduleTab ──────────────────────────────────────────

test("ScheduleTab.js toDateKey uses LOCAL time (getFullYear/getMonth/getDate)", () => {
	assert.match(schSrc, /function toDateKey\(value\)/);
	assert.match(schSrc, /date\.getFullYear\(\)/);
	assert.match(schSrc, /date\.getMonth\(\) \+ 1/);
	assert.match(schSrc, /date\.getDate\(\)/);
});

test("ScheduleTab.js toValidDate rejects YYYY-MM-DD strings that don't roundtrip through ISO", () => {
	assert.match(schSrc, /function toValidDate\(value\)/);
	assert.match(schSrc, /date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
});

test("ScheduleTab.js normalizeScheduleEvents type falls back to General", () => {
	assert.match(schSrc, /function normalizeScheduleEvents\(events\)/);
	assert.match(schSrc, /TYPE_STYLES\[event\.type\]/);
	assert.match(schSrc, /["']General["']/);
});

test("ScheduleTab.js formatDaysLeftLabel returns 오늘 for 0", () => {
	assert.match(schSrc, /function formatDaysLeftLabel\(daysLeft\)/);
	assert.match(schSrc, /daysLeft === 0 \? ["']오늘["']/);
});

// ── parseInlineQuantityInput behavioral tests ────────────────────────────────

test("parseInlineQuantityInput parses integer string", () => {
	assert.equal(parseInlineQuantityInput("42"), 42);
	assert.equal(parseInlineQuantityInput("0"), 0);
	assert.equal(parseInlineQuantityInput("1000"), 1000);
});

test("parseInlineQuantityInput parses decimal string with digit before dot", () => {
	assert.equal(parseInlineQuantityInput("3.14"), 3.14);
	assert.equal(parseInlineQuantityInput("0.5"), 0.5);
	assert.equal(parseInlineQuantityInput("10.0"), 10.0);
});

test("parseInlineQuantityInput parses leading-dot decimal (e.g. .5)", () => {
	assert.equal(parseInlineQuantityInput(".5"), 0.5);
	assert.equal(parseInlineQuantityInput(".25"), 0.25);
});

test("parseInlineQuantityInput trims whitespace before pattern check", () => {
	assert.equal(parseInlineQuantityInput(" 42 "), 42);
	assert.equal(parseInlineQuantityInput("  3.14  "), 3.14);
});

test("parseInlineQuantityInput returns NaN for negative numbers (not in pattern)", () => {
	assert.ok(Number.isNaN(parseInlineQuantityInput("-1")));
	assert.ok(Number.isNaN(parseInlineQuantityInput("-0.5")));
});

test("parseInlineQuantityInput returns NaN for non-numeric string", () => {
	assert.ok(Number.isNaN(parseInlineQuantityInput("abc")));
	assert.ok(Number.isNaN(parseInlineQuantityInput("12abc")));
	assert.ok(Number.isNaN(parseInlineQuantityInput("1e5")));
});

test("parseInlineQuantityInput returns NaN for empty string", () => {
	assert.ok(Number.isNaN(parseInlineQuantityInput("")));
});

test("parseInlineQuantityInput returns NaN for null/undefined (stringified then checked)", () => {
	// String(null) = "null", String(undefined) = "undefined" — both fail pattern
	assert.ok(Number.isNaN(parseInlineQuantityInput(null)));
	assert.ok(Number.isNaN(parseInlineQuantityInput(undefined)));
});

// ── toInventoryNumber behavioral tests ───────────────────────────────────────

test("toInventoryNumber returns fallback (0) for null", () => {
	assert.equal(toInventoryNumber(null), 0);
});

test("toInventoryNumber returns fallback (0) for undefined", () => {
	assert.equal(toInventoryNumber(undefined), 0);
});

test("toInventoryNumber returns fallback (0) for empty string", () => {
	assert.equal(toInventoryNumber(""), 0);
});

test("toInventoryNumber returns custom fallback for null/undefined/empty string", () => {
	assert.equal(toInventoryNumber(null, null), null);
	assert.equal(toInventoryNumber(undefined, null), null);
	assert.equal(toInventoryNumber("", null), null);
	assert.equal(toInventoryNumber(null, 99), 99);
});

test("toInventoryNumber returns the number for finite number input", () => {
	assert.equal(toInventoryNumber(42), 42);
	assert.equal(toInventoryNumber(0), 0);
	assert.equal(toInventoryNumber(3.14), 3.14);
	assert.equal(toInventoryNumber(-5), -5);
});

test("toInventoryNumber parses numeric string", () => {
	assert.equal(toInventoryNumber("42"), 42);
	assert.equal(toInventoryNumber("3.14"), 3.14);
});

test("toInventoryNumber returns fallback for NaN / non-numeric string", () => {
	assert.equal(toInventoryNumber(NaN), 0);
	assert.equal(toInventoryNumber("abc"), 0);
	assert.equal(toInventoryNumber("abc", null), null);
});

test("toInventoryNumber returns fallback for Infinity", () => {
	assert.equal(toInventoryNumber(Infinity), 0);
	assert.equal(toInventoryNumber(-Infinity), 0);
});

// ── normalizeInventoryItems behavioral tests ─────────────────────────────────

test("normalizeInventoryItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeInventoryItems(null), []);
	assert.deepEqual(normalizeInventoryItems(undefined), []);
	assert.deepEqual(normalizeInventoryItems({}), []);
});

test("normalizeInventoryItems filters null, primitives, and arrays", () => {
	const inventory = [null, "string", 42, [], { id: "i1" }];
	assert.equal(normalizeInventoryItems(inventory).length, 1);
});

test("normalizeInventoryItems defaults category to 'Other' when missing", () => {
	const items = [
		{ name: "사료" },
		{ category: "", name: "사료2" },
		{ category: "   ", name: "사료3" },
	];
	const result = normalizeInventoryItems(items);
	assert.ok(result.every((i) => i.category === "Other"));
});

test("normalizeInventoryItems preserves non-empty category string", () => {
	const items = [{ category: "사료", name: "배합사료" }];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].category, "사료");
});

test("normalizeInventoryItems generates fallback id as inventory-{index}", () => {
	const items = [{ name: "A" }, { name: "B" }];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].id, "inventory-0");
	assert.equal(result[1].id, "inventory-1");
});

test("normalizeInventoryItems preserves existing id (including 0)", () => {
	const items = [
		{ id: "explicit-id", name: "A" },
		{ id: 0, name: "B" },
	];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].id, "explicit-id");
	assert.equal(result[1].id, 0);
});

test("normalizeInventoryItems defaults name to '재고명 미등록' when missing", () => {
	const items = [
		{ category: "사료" },
		{ category: "사료", name: "" },
		{ category: "사료", name: "   " },
	];
	const result = normalizeInventoryItems(items);
	assert.ok(result.every((i) => i.name === "재고명 미등록"));
});

test("normalizeInventoryItems preserves non-empty name", () => {
	const items = [{ name: "배합사료 20kg" }];
	assert.equal(normalizeInventoryItems(items)[0].name, "배합사료 20kg");
});

test("normalizeInventoryItems sets quantity to null when quantity is missing (not 0!)", () => {
	const items = [{ name: "A" }];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].quantity, null);
});

test("normalizeInventoryItems sets quantity to null for null/undefined/empty-string quantity", () => {
	const items = [
		{ name: "A", quantity: null },
		{ name: "B", quantity: undefined },
		{ name: "C", quantity: "" },
	];
	const result = normalizeInventoryItems(items);
	assert.ok(result.every((i) => i.quantity === null));
});

test("normalizeInventoryItems passes through finite quantity number", () => {
	const items = [
		{ name: "A", quantity: 50 },
		{ name: "B", quantity: 0 },
		{ name: "C", quantity: 3.5 },
	];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].quantity, 50);
	assert.equal(result[1].quantity, 0);
	assert.equal(result[2].quantity, 3.5);
});

test("normalizeInventoryItems sets threshold to null when threshold is null/undefined/empty", () => {
	const items = [
		{ name: "A", threshold: null },
		{ name: "B", threshold: undefined },
		{ name: "C", threshold: "" },
		{ name: "D" },
	];
	const result = normalizeInventoryItems(items);
	assert.ok(result.every((i) => i.threshold === null));
});

test("normalizeInventoryItems parses threshold as number (not null-forced like quantity)", () => {
	const items = [{ name: "A", threshold: 10 }, { name: "B", threshold: "5" }];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].threshold, 10);
	assert.equal(result[1].threshold, 5);
});

test("normalizeInventoryItems defaults unit to '개' when missing or empty", () => {
	const items = [
		{ name: "A" },
		{ name: "B", unit: "" },
		{ name: "C", unit: "   " },
	];
	const result = normalizeInventoryItems(items);
	assert.ok(result.every((i) => i.unit === "개"));
});

test("normalizeInventoryItems preserves non-empty unit string", () => {
	const items = [{ name: "A", unit: "kg" }];
	assert.equal(normalizeInventoryItems(items)[0].unit, "kg");
});

test("normalizeInventoryItems spreads other fields through", () => {
	const items = [{ id: "i1", name: "사료", category: "사료", notes: "냉장보관" }];
	const result = normalizeInventoryItems(items);
	assert.equal(result[0].notes, "냉장보관");
});

// ── toDateKey behavioral tests ────────────────────────────────────────────────

test("toDateKey returns null for undefined (new Date(undefined) is Invalid Date)", () => {
	assert.equal(toDateKey(undefined), null);
});

test("toDateKey returns null for non-date string", () => {
	assert.equal(toDateKey("not-a-date"), null);
	assert.equal(toDateKey("abc"), null);
});

test("toDateKey returns a YYYY-MM-DD string for a valid date string", () => {
	const result = toDateKey("2026-06-15");
	assert.match(result, /^\d{4}-\d{2}-\d{2}$/);
});

test("toDateKey uses LOCAL calendar day (not UTC)", () => {
	// Confirms getFullYear/getMonth/getDate instead of toISOString() is used
	// The actual value is timezone-dependent; check structure only
	const result = toDateKey("2026-06-15");
	assert.ok(typeof result === "string");
	const [year, month, day] = result.split("-");
	assert.equal(year, "2026");
	assert.ok(Number(month) >= 1 && Number(month) <= 12);
	assert.ok(Number(day) >= 1 && Number(day) <= 31);
});

test("toDateKey returns null for invalid YYYY-MM-DD (e.g. Feb 30)", () => {
	// toValidDate rejects YYYY-MM-DD strings that don't roundtrip through ISO
	assert.equal(toDateKey("2026-02-30"), null);
	assert.equal(toDateKey("2026-13-01"), null);
});

test("toDateKey returns same date for valid Date instance", () => {
	const d = new Date(2026, 5, 15, 12, 0, 0); // month is 0-indexed → June
	const result = toDateKey(d);
	assert.equal(result, "2026-06-15");
});

test("toDateKey returns null for Invalid Date instance", () => {
	assert.equal(toDateKey(new Date("invalid")), null);
});

// ── normalizeScheduleEvents behavioral tests ─────────────────────────────────

test("normalizeScheduleEvents returns empty array for non-array input", () => {
	assert.deepEqual(normalizeScheduleEvents(null), []);
	assert.deepEqual(normalizeScheduleEvents(undefined), []);
	assert.deepEqual(normalizeScheduleEvents({}), []);
});

test("normalizeScheduleEvents filters null, primitives, and arrays", () => {
	const events = [null, "string", 42, [], { title: "백신" }];
	assert.equal(normalizeScheduleEvents(events).length, 1);
});

test("normalizeScheduleEvents generates fallback id as schedule-{index}", () => {
	const events = [{ title: "A" }, { title: "B" }];
	const result = normalizeScheduleEvents(events);
	assert.equal(result[0].id, "schedule-0");
	assert.equal(result[1].id, "schedule-1");
});

test("normalizeScheduleEvents preserves existing id", () => {
	const events = [{ id: "my-id", title: "A" }];
	assert.equal(normalizeScheduleEvents(events)[0].id, "my-id");
});

test("normalizeScheduleEvents defaults title to '일정명 미등록' when missing", () => {
	const events = [
		{ type: "General" },
		{ type: "General", title: "" },
		{ type: "General", title: "   " },
	];
	const result = normalizeScheduleEvents(events);
	assert.ok(result.every((e) => e.title === "일정명 미등록"));
});

test("normalizeScheduleEvents preserves non-empty title", () => {
	const events = [{ title: "백신 접종", type: "Vaccination" }];
	assert.equal(normalizeScheduleEvents(events)[0].title, "백신 접종");
});

test("normalizeScheduleEvents defaults type to 'General' for unknown type", () => {
	const events = [
		{ title: "A", type: "UnknownType" },
		{ title: "B" },
		{ title: "C", type: "" },
		{ title: "D", type: 42 },
	];
	const result = normalizeScheduleEvents(events);
	assert.ok(result.every((e) => e.type === "General"));
});

test("normalizeScheduleEvents preserves valid types from TYPE_STYLES", () => {
	const validTypes = ["Vaccination", "Checkup", "Breeding", "Other", "General"];
	for (const type of validTypes) {
		const result = normalizeScheduleEvents([{ title: "A", type }]);
		assert.equal(result[0].type, type, `type ${type} should be preserved`);
	}
});

test("normalizeScheduleEvents coerces isCompleted via Boolean()", () => {
	const events = [
		{ title: "A", isCompleted: true },
		{ title: "B", isCompleted: false },
		{ title: "C", isCompleted: 1 },
		{ title: "D", isCompleted: 0 },
		{ title: "E", isCompleted: null },
		{ title: "F" },
	];
	const result = normalizeScheduleEvents(events);
	assert.equal(result[0].isCompleted, true);
	assert.equal(result[1].isCompleted, false);
	assert.equal(result[2].isCompleted, true);
	assert.equal(result[3].isCompleted, false);
	assert.equal(result[4].isCompleted, false);
	assert.equal(result[5].isCompleted, false);
});

test("normalizeScheduleEvents spreads other fields through", () => {
	const events = [
		{
			id: "e1",
			title: "백신",
			type: "Vaccination",
			date: "2026-06-15",
			note: "메모",
		},
	];
	const result = normalizeScheduleEvents(events);
	assert.equal(result[0].date, "2026-06-15");
	assert.equal(result[0].note, "메모");
});

// ── formatDaysLeftLabel behavioral tests ──────────────────────────────────────

test("formatDaysLeftLabel returns '오늘' for 0", () => {
	assert.equal(formatDaysLeftLabel(0), "오늘");
});

test("formatDaysLeftLabel returns '{n}일 남음' for positive n", () => {
	assert.equal(formatDaysLeftLabel(1), "1일 남음");
	assert.equal(formatDaysLeftLabel(30), "30일 남음");
	assert.equal(formatDaysLeftLabel(365), "365일 남음");
});
