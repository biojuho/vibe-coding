/**
 * Behavioral tests for private pure helpers in FieldModeView.js:
 *   createFreshChecklist      — DEFAULT_CHECKLIST with checked: false
 *   normalizeStoredChecklist  — merges saved state back to DEFAULT order
 *   normalizeFieldModeViewOptions — object guard
 *   normalizeFieldModeCattleList  — array filter for plain objects
 *
 * FieldModeView.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/widgets/FieldModeView.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

const DEFAULT_CHECKLIST = [
	{
		id: "feed_check",
		title: "우사 급이통 청소 및 사료 배부 확인",
		icon: "🌾",
		detail: "오전 급여 후 남은 찌꺼기 및 사료 변질 여부",
	},
	{
		id: "bedding_check",
		title: "우방 깔짚(톱밥) 수분 상태 점검",
		icon: "🧹",
		detail: "축사 바닥 톱밥 오염도 측정 및 추가 보충 여부",
	},
	{
		id: "thi_monitor",
		title: "온습도 및 가축 열지수(THI) 모니터링",
		icon: "🌬️",
		detail: "THI 경보 확인 후 환풍기 풍량 및 안개분무 작동",
	},
	{
		id: "health_scan",
		title: "개체 거동 및 활력 관찰 (건강 점검)",
		icon: "🩺",
		detail: "절뚝임, 호흡 급박, 사료 섭취 거부 개체 식별",
	},
	{
		id: "breeding_focus",
		title: "임신/분만 예정우 상태 밀착 관찰",
		icon: "🍼",
		detail: "유방 팽창, 외음부 부종, 진통 개시 징후 점검",
	},
];

function createFreshChecklist() {
	return DEFAULT_CHECKLIST.map((item) => ({ ...item, checked: false }));
}

function normalizeStoredChecklist(value) {
	if (!Array.isArray(value)) {
		return createFreshChecklist();
	}

	const savedById = new Map(
		value
			.filter((item) => item && typeof item === "object" && !Array.isArray(item))
			.map((item) => [item.id, item]),
	);

	return DEFAULT_CHECKLIST.map((item) => ({
		...item,
		checked: Boolean(savedById.get(item.id)?.checked),
	}));
}

function normalizeFieldModeViewOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeFieldModeCattleList(cattleList) {
	return Array.isArray(cattleList)
		? cattleList.filter(
				(cow) => cow && typeof cow === "object" && !Array.isArray(cow),
			)
		: [];
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("FieldModeView.js createFreshChecklist maps DEFAULT_CHECKLIST with checked:false", () => {
	assert.match(src, /function createFreshChecklist\(\)/);
	assert.match(src, /DEFAULT_CHECKLIST\.map\(\(item\) => \(\{ \.\.\.item, checked: false \}\)\)/);
});

test("FieldModeView.js normalizeStoredChecklist builds Map keyed by id", () => {
	assert.match(src, /function normalizeStoredChecklist\(value\)/);
	assert.match(src, /new Map\(/);
	assert.match(src, /\[item\.id, item\]/);
	assert.match(src, /Boolean\(savedById\.get\(item\.id\)\?\.checked\)/);
});

test("FieldModeView.js normalizeStoredChecklist returns createFreshChecklist for non-array", () => {
	assert.match(src, /if \(!Array\.isArray\(value\)\)/);
	assert.match(src, /return createFreshChecklist\(\)/);
});

// ── createFreshChecklist behavioral tests ─────────────────────────────────────

test("createFreshChecklist returns an array with the same length as DEFAULT_CHECKLIST", () => {
	const result = createFreshChecklist();
	assert.equal(result.length, DEFAULT_CHECKLIST.length);
	assert.equal(result.length, 5);
});

test("createFreshChecklist sets checked:false for every item", () => {
	const result = createFreshChecklist();
	assert.ok(result.every((item) => item.checked === false));
});

test("createFreshChecklist preserves other fields from DEFAULT_CHECKLIST", () => {
	const result = createFreshChecklist();
	for (let i = 0; i < DEFAULT_CHECKLIST.length; i += 1) {
		assert.equal(result[i].id, DEFAULT_CHECKLIST[i].id);
		assert.equal(result[i].title, DEFAULT_CHECKLIST[i].title);
		assert.equal(result[i].icon, DEFAULT_CHECKLIST[i].icon);
	}
});

test("createFreshChecklist returns new objects (does not mutate DEFAULT_CHECKLIST)", () => {
	const result = createFreshChecklist();
	// Mutating result should not affect future calls
	result[0].checked = true;
	const result2 = createFreshChecklist();
	assert.equal(result2[0].checked, false);
});

test("createFreshChecklist includes known checklist ids", () => {
	const result = createFreshChecklist();
	const ids = new Set(result.map((item) => item.id));
	assert.ok(ids.has("feed_check"));
	assert.ok(ids.has("bedding_check"));
	assert.ok(ids.has("thi_monitor"));
	assert.ok(ids.has("health_scan"));
	assert.ok(ids.has("breeding_focus"));
});

// ── normalizeStoredChecklist behavioral tests ─────────────────────────────────

test("normalizeStoredChecklist returns fresh checklist for null input", () => {
	const result = normalizeStoredChecklist(null);
	assert.ok(result.every((item) => item.checked === false));
	assert.equal(result.length, DEFAULT_CHECKLIST.length);
});

test("normalizeStoredChecklist returns fresh checklist for non-array input", () => {
	for (const input of [undefined, {}, "string", 42]) {
		const result = normalizeStoredChecklist(input);
		assert.ok(result.every((item) => item.checked === false));
		assert.equal(result.length, DEFAULT_CHECKLIST.length);
	}
});

test("normalizeStoredChecklist restores checked:true for a matching saved item", () => {
	const saved = [{ id: "feed_check", checked: true }];
	const result = normalizeStoredChecklist(saved);
	const feedItem = result.find((item) => item.id === "feed_check");
	assert.equal(feedItem.checked, true);
});

test("normalizeStoredChecklist uses checked:false for items not in saved data", () => {
	// Only feed_check is saved
	const saved = [{ id: "feed_check", checked: true }];
	const result = normalizeStoredChecklist(saved);
	const others = result.filter((item) => item.id !== "feed_check");
	assert.ok(others.every((item) => item.checked === false));
});

test("normalizeStoredChecklist converts falsy checked to false via Boolean()", () => {
	const saved = [
		{ id: "feed_check", checked: 0 },
		{ id: "bedding_check", checked: null },
		{ id: "thi_monitor", checked: "" },
	];
	const result = normalizeStoredChecklist(saved);
	for (const item of result) {
		assert.equal(typeof item.checked, "boolean");
	}
	assert.equal(result.find((i) => i.id === "feed_check").checked, false);
	assert.equal(result.find((i) => i.id === "bedding_check").checked, false);
});

test("normalizeStoredChecklist converts truthy non-boolean checked to true", () => {
	const saved = [
		{ id: "health_scan", checked: 1 },
		{ id: "breeding_focus", checked: "yes" },
	];
	const result = normalizeStoredChecklist(saved);
	assert.equal(result.find((i) => i.id === "health_scan").checked, true);
	assert.equal(result.find((i) => i.id === "breeding_focus").checked, true);
});

test("normalizeStoredChecklist ignores saved items with unknown ids", () => {
	const saved = [
		{ id: "unknown_task", checked: true },
		{ id: "feed_check", checked: true },
	];
	const result = normalizeStoredChecklist(saved);
	assert.equal(result.length, DEFAULT_CHECKLIST.length);
	assert.equal(result.find((i) => i.id === "feed_check").checked, true);
	assert.ok(result.find((i) => i.id === "unknown_task") === undefined);
});

test("normalizeStoredChecklist preserves DEFAULT_CHECKLIST item order", () => {
	// Even if saved array is in different order, result follows DEFAULT_CHECKLIST order
	const saved = [
		{ id: "breeding_focus", checked: true },
		{ id: "feed_check", checked: true },
	];
	const result = normalizeStoredChecklist(saved);
	assert.equal(result[0].id, DEFAULT_CHECKLIST[0].id);
	assert.equal(result[4].id, DEFAULT_CHECKLIST[4].id);
});

test("normalizeStoredChecklist filters null/primitive entries in saved array", () => {
	const saved = [
		null,
		"string",
		42,
		{ id: "feed_check", checked: true },
	];
	const result = normalizeStoredChecklist(saved);
	assert.equal(result.find((i) => i.id === "feed_check").checked, true);
});

test("normalizeStoredChecklist preserves DEFAULT_CHECKLIST field values", () => {
	const saved = [{ id: "feed_check", checked: true }];
	const result = normalizeStoredChecklist(saved);
	const feedItem = result.find((item) => item.id === "feed_check");
	assert.equal(feedItem.title, DEFAULT_CHECKLIST[0].title);
	assert.equal(feedItem.icon, DEFAULT_CHECKLIST[0].icon);
});

// ── normalizeFieldModeViewOptions behavioral tests ────────────────────────────

test("normalizeFieldModeViewOptions returns input for valid object", () => {
	const obj = { cattleList: [] };
	assert.equal(normalizeFieldModeViewOptions(obj), obj);
});

test("normalizeFieldModeViewOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeFieldModeViewOptions(null), {});
	assert.deepEqual(normalizeFieldModeViewOptions(undefined), {});
	assert.deepEqual(normalizeFieldModeViewOptions([]), {});
});

// ── normalizeFieldModeCattleList behavioral tests ─────────────────────────────

test("normalizeFieldModeCattleList returns empty array for non-array input", () => {
	assert.deepEqual(normalizeFieldModeCattleList(null), []);
	assert.deepEqual(normalizeFieldModeCattleList(undefined), []);
	assert.deepEqual(normalizeFieldModeCattleList({}), []);
});

test("normalizeFieldModeCattleList filters null, primitives, and arrays", () => {
	const cattle = [null, "string", 42, [], { id: "c1" }];
	assert.equal(normalizeFieldModeCattleList(cattle).length, 1);
});

test("normalizeFieldModeCattleList keeps plain objects regardless of id", () => {
	const cattle = [{ earTagNumber: "001" }, { earTagNumber: "002" }];
	assert.equal(normalizeFieldModeCattleList(cattle).length, 2);
});
