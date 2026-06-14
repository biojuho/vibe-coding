/**
 * Behavioral tests for private pure helpers in SettingsTab.js:
 *   normalizeSettingsBuildings   — filter + map (id required, penCount coerced to 0)
 *   normalizeSettingsTabOptions  — object guard, defaults to {}
 *   normalizeSettingsWidgetRegistry — array filter for plain objects
 *   normalizeSettingsWidgetVisible  — object guard, defaults to {}
 *
 * SettingsTab.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/tabs/SettingsTab.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function normalizeSettingsBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings
				.filter(
					(building) =>
						building &&
						typeof building === "object" &&
						!Array.isArray(building) &&
						building.id != null,
				)
				.map((building) => ({
					...building,
					name:
						typeof building.name === "string" && building.name.trim()
							? building.name
							: "축사 이름 미등록",
					penCount: Number.isFinite(Number(building.penCount))
						? Number(building.penCount)
						: 0,
				}))
		: [];
}

function normalizeSettingsTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeSettingsWidgetRegistry(widgets) {
	return Array.isArray(widgets)
		? widgets.filter(
				(widget) => widget && typeof widget === "object" && !Array.isArray(widget),
			)
		: [];
}

function normalizeSettingsWidgetVisible(widgetVisible) {
	return widgetVisible &&
		typeof widgetVisible === "object" &&
		!Array.isArray(widgetVisible)
		? widgetVisible
		: {};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("SettingsTab.js normalizeSettingsBuildings requires id != null and coerces penCount", () => {
	assert.match(src, /function normalizeSettingsBuildings\(buildings\)/);
	assert.match(src, /building\.id != null/);
	assert.match(src, /Number\.isFinite\(Number\(building\.penCount\)\)/);
	assert.match(src, /"축사 이름 미등록"/);
});

test("SettingsTab.js normalizeSettingsTabOptions returns input or empty object", () => {
	assert.match(src, /function normalizeSettingsTabOptions\(options\)/);
	assert.match(src, /typeof options === ["']object["'] && !Array\.isArray\(options\)/);
});

test("SettingsTab.js normalizeSettingsWidgetRegistry filters plain objects", () => {
	assert.match(src, /function normalizeSettingsWidgetRegistry\(widgets\)/);
	assert.match(src, /!Array\.isArray\(widget\)/);
});

test("SettingsTab.js normalizeSettingsWidgetVisible returns input or empty object", () => {
	assert.match(src, /function normalizeSettingsWidgetVisible\(widgetVisible\)/);
	assert.match(src, /typeof widgetVisible === ["']object["']/);
	assert.match(src, /!Array\.isArray\(widgetVisible\)/);
});

// ── normalizeSettingsBuildings behavioral tests ───────────────────────────────

test("normalizeSettingsBuildings returns empty array for non-array input", () => {
	assert.deepEqual(normalizeSettingsBuildings(null), []);
	assert.deepEqual(normalizeSettingsBuildings(undefined), []);
	assert.deepEqual(normalizeSettingsBuildings({}), []);
	assert.deepEqual(normalizeSettingsBuildings("string"), []);
});

test("normalizeSettingsBuildings filters buildings without id", () => {
	const buildings = [
		{ name: "축사A" },
		{ id: null, name: "축사B" },
		{ id: undefined, name: "축사C" },
		{ id: "b1", name: "축사D" },
	];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "b1");
});

test("normalizeSettingsBuildings keeps id:0 (loose equality != null)", () => {
	const buildings = [{ id: 0, name: "축사" }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result.length, 1);
});

test("normalizeSettingsBuildings filters arrays and null entries", () => {
	const buildings = [null, [], "string", { id: "ok", name: "정상 축사" }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "ok");
});

test("normalizeSettingsBuildings preserves valid name", () => {
	const buildings = [{ id: "b1", name: "본 축사" }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result[0].name, "본 축사");
});

test("normalizeSettingsBuildings uses fallback name for empty string", () => {
	const buildings = [{ id: "b1", name: "" }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result[0].name, "축사 이름 미등록");
});

test("normalizeSettingsBuildings uses fallback name for whitespace-only string", () => {
	const buildings = [{ id: "b1", name: "   " }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result[0].name, "축사 이름 미등록");
});

test("normalizeSettingsBuildings uses fallback name for non-string name", () => {
	const buildings = [
		{ id: "b1", name: 42 },
		{ id: "b2", name: null },
		{ id: "b3" },
	];
	const result = normalizeSettingsBuildings(buildings);
	assert.ok(result.every((b) => b.name === "축사 이름 미등록"));
});

test("normalizeSettingsBuildings coerces numeric string penCount", () => {
	const buildings = [{ id: "b1", name: "축사", penCount: "10" }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result[0].penCount, 10);
});

test("normalizeSettingsBuildings defaults penCount to 0 for invalid value", () => {
	const buildings = [
		{ id: "b1", name: "축사A", penCount: "abc" },
		{ id: "b2", name: "축사B", penCount: null },
		{ id: "b3", name: "축사C" },
	];
	const result = normalizeSettingsBuildings(buildings);
	assert.ok(result.every((b) => b.penCount === 0));
});

test("normalizeSettingsBuildings passes through numeric penCount directly", () => {
	const buildings = [{ id: "b1", name: "축사", penCount: 32 }];
	const result = normalizeSettingsBuildings(buildings);
	assert.equal(result[0].penCount, 32);
});

test("normalizeSettingsBuildings spreads other fields through", () => {
	const buildings = [{ id: "b1", name: "축사", pens: ["p1", "p2"], location: "동쪽" }];
	const result = normalizeSettingsBuildings(buildings);
	assert.deepEqual(result[0].pens, ["p1", "p2"]);
	assert.equal(result[0].location, "동쪽");
});

// ── normalizeSettingsTabOptions behavioral tests ──────────────────────────────

test("normalizeSettingsTabOptions returns original object for valid input", () => {
	const obj = { buildings: [], widgets: [] };
	assert.equal(normalizeSettingsTabOptions(obj), obj);
});

test("normalizeSettingsTabOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeSettingsTabOptions(null), {});
	assert.deepEqual(normalizeSettingsTabOptions(undefined), {});
	assert.deepEqual(normalizeSettingsTabOptions([]), {});
	assert.deepEqual(normalizeSettingsTabOptions("string"), {});
});

// ── normalizeSettingsWidgetRegistry behavioral tests ─────────────────────────

test("normalizeSettingsWidgetRegistry returns empty array for non-array input", () => {
	assert.deepEqual(normalizeSettingsWidgetRegistry(null), []);
	assert.deepEqual(normalizeSettingsWidgetRegistry(undefined), []);
	assert.deepEqual(normalizeSettingsWidgetRegistry({}), []);
});

test("normalizeSettingsWidgetRegistry keeps plain objects regardless of id", () => {
	const widgets = [{ id: "w1" }, { name: "widget-no-id" }];
	const result = normalizeSettingsWidgetRegistry(widgets);
	assert.equal(result.length, 2);
});

test("normalizeSettingsWidgetRegistry filters arrays, null, and primitives", () => {
	const widgets = [null, "string", [], 42, { id: "ok" }];
	const result = normalizeSettingsWidgetRegistry(widgets);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "ok");
});

// ── normalizeSettingsWidgetVisible behavioral tests ───────────────────────────

test("normalizeSettingsWidgetVisible returns original object for valid input", () => {
	const obj = { AIChatWidget: true, MarketPriceWidget: false };
	assert.equal(normalizeSettingsWidgetVisible(obj), obj);
});

test("normalizeSettingsWidgetVisible returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeSettingsWidgetVisible(null), {});
	assert.deepEqual(normalizeSettingsWidgetVisible(undefined), {});
	assert.deepEqual(normalizeSettingsWidgetVisible([]), {});
	assert.deepEqual(normalizeSettingsWidgetVisible("string"), {});
});

test("normalizeSettingsWidgetVisible accepts empty object", () => {
	assert.deepEqual(normalizeSettingsWidgetVisible({}), {});
});
