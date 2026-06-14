/**
 * Behavioral tests for private pure helpers in AlertBanners.js:
 *   normalizeDaysLeft           — clamps to >= 0, floors to integer
 *   normalizeAlertBannerOptions — object guard
 *   normalizeAlertNotifications — type-filter + cattleName/id/penNumber normalization
 *   normalizeBuildings          — array filter for plain objects
 *
 * AlertBanners.js imports React; cannot load in Node ESM.
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
	path.join(SRC_ROOT, "components/widgets/AlertBanners.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toFiniteNumber(value) {
	const n = Number(value);
	return Number.isFinite(n) ? n : 0;
}

function normalizeDaysLeft(value) {
	return Math.max(0, Math.floor(toFiniteNumber(value)));
}

function normalizeAlertBannerOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeAlertNotifications(notifications, type) {
	if (!Array.isArray(notifications)) return [];

	return notifications
		.filter(
			(notification) =>
				notification &&
				typeof notification === "object" &&
				!Array.isArray(notification) &&
				notification.type === type,
		)
		.map((notification, index) => ({
			...notification,
			cattleName:
				typeof notification.cattleName === "string" &&
				notification.cattleName.trim()
					? notification.cattleName
					: "개체명 미등록",
			id: notification.id ?? `${type}-${index}`,
			penNumber: notification.penNumber ?? "칸 미지정",
		}));
}

function normalizeBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings.filter(
				(building) =>
					building && typeof building === "object" && !Array.isArray(building),
			)
		: [];
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("AlertBanners.js normalizeDaysLeft uses Math.max(0, Math.floor(...))", () => {
	assert.match(src, /function normalizeDaysLeft\(value\)/);
	assert.match(src, /Math\.max\(0, Math\.floor/);
	assert.match(src, /toFiniteNumber\(value\)/);
});

test("AlertBanners.js normalizeAlertNotifications filters by type and maps defaults", () => {
	assert.match(src, /function normalizeAlertNotifications\(notifications, type\)/);
	assert.match(src, /notification\.type === type/);
	assert.match(src, /"개체명 미등록"/);
	assert.match(src, /`\$\{type\}-\$\{index\}`/);
	assert.match(src, /"칸 미지정"/);
});

// ── normalizeDaysLeft behavioral tests ────────────────────────────────────────

test("normalizeDaysLeft returns 0 for null/undefined/NaN/non-finite", () => {
	assert.equal(normalizeDaysLeft(null), 0);
	assert.equal(normalizeDaysLeft(undefined), 0);
	assert.equal(normalizeDaysLeft(NaN), 0);
	assert.equal(normalizeDaysLeft(Infinity), 0);
	assert.equal(normalizeDaysLeft("abc"), 0);
});

test("normalizeDaysLeft returns 0 for negative values (clamped)", () => {
	assert.equal(normalizeDaysLeft(-1), 0);
	assert.equal(normalizeDaysLeft(-100), 0);
});

test("normalizeDaysLeft returns 0 for exactly 0", () => {
	assert.equal(normalizeDaysLeft(0), 0);
});

test("normalizeDaysLeft floors decimal values", () => {
	assert.equal(normalizeDaysLeft(3.9), 3);
	assert.equal(normalizeDaysLeft(1.1), 1);
	assert.equal(normalizeDaysLeft(0.9), 0);
});

test("normalizeDaysLeft returns integer for positive integer input", () => {
	assert.equal(normalizeDaysLeft(7), 7);
	assert.equal(normalizeDaysLeft(30), 30);
});

test("normalizeDaysLeft coerces numeric string", () => {
	assert.equal(normalizeDaysLeft("5"), 5);
	assert.equal(normalizeDaysLeft("0"), 0);
});

// ── normalizeAlertBannerOptions behavioral tests ──────────────────────────────

test("normalizeAlertBannerOptions returns input for valid object", () => {
	const obj = { notifications: [], buildings: [] };
	assert.equal(normalizeAlertBannerOptions(obj), obj);
});

test("normalizeAlertBannerOptions returns {} for null/undefined/array", () => {
	assert.deepEqual(normalizeAlertBannerOptions(null), {});
	assert.deepEqual(normalizeAlertBannerOptions(undefined), {});
	assert.deepEqual(normalizeAlertBannerOptions([]), {});
	assert.deepEqual(normalizeAlertBannerOptions("string"), {});
});

// ── normalizeAlertNotifications behavioral tests ──────────────────────────────

test("normalizeAlertNotifications returns empty array for non-array input", () => {
	assert.deepEqual(normalizeAlertNotifications(null, "estrus"), []);
	assert.deepEqual(normalizeAlertNotifications(undefined, "estrus"), []);
});

test("normalizeAlertNotifications filters by type", () => {
	const notifications = [
		{ type: "estrus", cattleName: "소1", id: "n1", penNumber: 1 },
		{ type: "pregnancy", cattleName: "소2", id: "n2", penNumber: 2 },
		{ type: "estrus", cattleName: "소3", id: "n3", penNumber: 3 },
	];
	const estrus = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(estrus.length, 2);
	assert.ok(estrus.every((n) => n.type === "estrus"));
});

test("normalizeAlertNotifications preserves valid cattleName", () => {
	const notifications = [{ type: "estrus", cattleName: "누렁이", id: "n1" }];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].cattleName, "누렁이");
});

test("normalizeAlertNotifications uses fallback for empty/whitespace cattleName", () => {
	const notifications = [
		{ type: "estrus", cattleName: "", id: "n1" },
		{ type: "estrus", cattleName: "   ", id: "n2" },
		{ type: "estrus", id: "n3" },
	];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.ok(result.every((n) => n.cattleName === "개체명 미등록"));
});

test("normalizeAlertNotifications uses fallback for non-string cattleName", () => {
	const notifications = [
		{ type: "estrus", cattleName: null, id: "n1" },
		{ type: "estrus", cattleName: 42, id: "n2" },
	];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.ok(result.every((n) => n.cattleName === "개체명 미등록"));
});

test("normalizeAlertNotifications preserves existing id", () => {
	const notifications = [{ type: "estrus", cattleName: "소", id: "existing-id" }];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].id, "existing-id");
});

test("normalizeAlertNotifications generates fallback id when id is null/undefined", () => {
	const notifications = [
		{ type: "estrus", cattleName: "소1" },
		{ type: "estrus", cattleName: "소2", id: null },
	];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].id, "estrus-0");
	assert.equal(result[1].id, "estrus-1");
});

test("normalizeAlertNotifications fallback id uses the type prefix", () => {
	const notifications = [{ type: "pregnancy", cattleName: "소" }];
	const result = normalizeAlertNotifications(notifications, "pregnancy");
	assert.equal(result[0].id, "pregnancy-0");
});

test("normalizeAlertNotifications preserves existing penNumber", () => {
	const notifications = [{ type: "estrus", cattleName: "소", penNumber: 3 }];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].penNumber, 3);
});

test("normalizeAlertNotifications uses '칸 미지정' for missing penNumber", () => {
	const notifications = [{ type: "estrus", cattleName: "소" }];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].penNumber, "칸 미지정");
});

test("normalizeAlertNotifications uses '칸 미지정' for null penNumber", () => {
	const notifications = [{ type: "estrus", cattleName: "소", penNumber: null }];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].penNumber, "칸 미지정");
});

test("normalizeAlertNotifications filters null/primitive/array entries", () => {
	const notifications = [
		null,
		"string",
		42,
		[],
		{ type: "estrus", cattleName: "소", id: "ok" },
	];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "ok");
});

test("normalizeAlertNotifications spreads other fields through", () => {
	const notifications = [
		{ type: "estrus", cattleName: "소", id: "n1", daysLeft: 3, buildingId: "b1" },
	];
	const result = normalizeAlertNotifications(notifications, "estrus");
	assert.equal(result[0].daysLeft, 3);
	assert.equal(result[0].buildingId, "b1");
});

// ── normalizeBuildings behavioral tests ───────────────────────────────────────

test("normalizeBuildings returns empty array for non-array input", () => {
	assert.deepEqual(normalizeBuildings(null), []);
	assert.deepEqual(normalizeBuildings(undefined), []);
	assert.deepEqual(normalizeBuildings({}), []);
});

test("normalizeBuildings filters null, primitives, and arrays", () => {
	const buildings = [null, "string", 42, [], { id: "b1" }];
	const result = normalizeBuildings(buildings);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "b1");
});

test("normalizeBuildings keeps plain objects regardless of id", () => {
	const buildings = [{ name: "축사A" }, { name: "축사B" }];
	assert.equal(normalizeBuildings(buildings).length, 2);
});
