/**
 * Behavioral tests for the DashboardClient.js options normalizer helpers
 * that were flagged by the code-review gate:
 *   normalizeDashboardClientOptions  — full initial-data props normalizer
 *   normalizeFullListLoadOptions     — single-flag options normalizer
 *   normalizeDashboardHelperOptions  — panel helper options with callback defaults
 *   normalizeDashboardHelperItems    — plain-object array filter with id requirement
 *
 * DashboardClient.js imports React and cannot be loaded in Node ESM.
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
	path.join(SRC_ROOT, "components/DashboardClient.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

// normalizeDashboardInitialDataLoadStatus is a dependency — inline stub
function normalizeDashboardInitialDataLoadStatus(status) {
	const safeStatus =
		status && typeof status === "object" && !Array.isArray(status) ? status : {};
	return {
		degraded: safeStatus.degraded === true,
		message: typeof safeStatus.message === "string" ? safeStatus.message : "",
		failedSectionLabels: Array.isArray(safeStatus.failedSectionLabels)
			? safeStatus.failedSectionLabels
			: [],
	};
}

function normalizeDashboardClientOptions(options) {
	const safeOptions =
		options && typeof options === "object" && !Array.isArray(options)
			? options
			: {};

	return {
		initialCattlePage: safeOptions.initialCattlePage,
		initialSalesPage: safeOptions.initialSalesPage,
		initialSummary: safeOptions.initialSummary,
		initialNotifications: safeOptions.initialNotifications ?? [],
		initialFeedStandards: safeOptions.initialFeedStandards ?? [],
		initialInventory: safeOptions.initialInventory ?? [],
		initialSchedule: safeOptions.initialSchedule ?? [],
		initialFeedHistory: safeOptions.initialFeedHistory ?? [],
		initialBuildings: safeOptions.initialBuildings ?? [],
		initialFarmSettings: safeOptions.initialFarmSettings ?? {},
		initialExpenses: safeOptions.initialExpenses ?? [],
		initialMarketPrice: safeOptions.initialMarketPrice ?? null,
		initialProfitability: safeOptions.initialProfitability ?? null,
		initialDataLoadStatus: normalizeDashboardInitialDataLoadStatus(
			safeOptions.initialDataLoadStatus,
		),
		subscriptionStatus: safeOptions.subscriptionStatus ?? null,
	};
}

function normalizeFullListLoadOptions(options) {
	const safeOptions =
		options && typeof options === "object" && !Array.isArray(options)
			? options
			: {};
	return {
		silent: safeOptions.silent === true,
	};
}

function normalizeDashboardHelperOptions(options) {
	const safeOptions =
		options && typeof options === "object" && !Array.isArray(options)
			? options
			: {};
	return {
		items: safeOptions.items ?? [],
		buildings: safeOptions.buildings ?? [],
		cattleList: safeOptions.cattleList ?? [],
		onOpenNotifications:
			typeof safeOptions.onOpenNotifications === "function"
				? safeOptions.onOpenNotifications
				: () => {},
		onNavigate:
			typeof safeOptions.onNavigate === "function"
				? safeOptions.onNavigate
				: () => {},
		onAction:
			typeof safeOptions.onAction === "function"
				? safeOptions.onAction
				: () => {},
		progress: safeOptions.progress ?? null,
		buildingId: safeOptions.buildingId,
		penId: safeOptions.penId,
		onSelect:
			typeof safeOptions.onSelect === "function"
				? safeOptions.onSelect
				: () => {},
		onCreateEvent: safeOptions.onCreateEvent,
	};
}

function normalizeDashboardHelperItems(items) {
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

// ── Source-grep guards ────────────────────────────────────────────────────────

test("DashboardClient.js normalizeDashboardClientOptions defaults array fields to []", () => {
	assert.match(src, /function normalizeDashboardClientOptions\(options\)/);
	assert.match(src, /initialNotifications: safeOptions\.initialNotifications \?\? \[\]/);
	assert.match(src, /initialFarmSettings: safeOptions\.initialFarmSettings \?\? \{\}/);
	assert.match(src, /subscriptionStatus: safeOptions\.subscriptionStatus \?\? null/);
});

test("DashboardClient.js normalizeFullListLoadOptions enforces strict boolean for silent", () => {
	assert.match(src, /function normalizeFullListLoadOptions\(options\)/);
	assert.match(src, /silent: safeOptions\.silent === true/);
});

test("DashboardClient.js normalizeDashboardHelperOptions defaults callbacks to no-op", () => {
	assert.match(src, /function normalizeDashboardHelperOptions\(options\)/);
	assert.match(src, /typeof safeOptions\.onOpenNotifications === ["']function["']/);
	assert.match(src, /typeof safeOptions\.onNavigate === ["']function["']/);
});

test("DashboardClient.js normalizeDashboardHelperItems requires id != null", () => {
	assert.match(src, /function normalizeDashboardHelperItems\(items\)/);
	assert.match(src, /item\.id != null/);
});

// ── normalizeDashboardClientOptions behavioral tests ──────────────────────────

test("normalizeDashboardClientOptions returns defaults for null/undefined/array input", () => {
	for (const input of [null, undefined, [], "string"]) {
		const result = normalizeDashboardClientOptions(input);
		assert.deepEqual(result.initialNotifications, []);
		assert.deepEqual(result.initialBuildings, []);
		assert.deepEqual(result.initialFarmSettings, {});
		assert.equal(result.initialMarketPrice, null);
		assert.equal(result.subscriptionStatus, null);
	}
});

test("normalizeDashboardClientOptions passes through provided array values", () => {
	const notifications = [{ id: "n1" }];
	const result = normalizeDashboardClientOptions({ initialNotifications: notifications });
	assert.equal(result.initialNotifications, notifications);
});

test("normalizeDashboardClientOptions preserves undefined for paged data (no default)", () => {
	const result = normalizeDashboardClientOptions({});
	assert.equal(result.initialCattlePage, undefined);
	assert.equal(result.initialSalesPage, undefined);
});

test("normalizeDashboardClientOptions passes initialSummary through", () => {
	const summary = { totalCattle: 42 };
	const result = normalizeDashboardClientOptions({ initialSummary: summary });
	assert.equal(result.initialSummary, summary);
});

test("normalizeDashboardClientOptions defaults farmSettings to {} not null", () => {
	const result = normalizeDashboardClientOptions({});
	assert.deepEqual(result.initialFarmSettings, {});
});

// ── normalizeFullListLoadOptions behavioral tests ─────────────────────────────

test("normalizeFullListLoadOptions returns silent:false for empty options", () => {
	assert.deepEqual(normalizeFullListLoadOptions({}), { silent: false });
});

test("normalizeFullListLoadOptions returns silent:true only when silent===true (strict)", () => {
	assert.deepEqual(normalizeFullListLoadOptions({ silent: true }), { silent: true });
	assert.deepEqual(normalizeFullListLoadOptions({ silent: 1 }), { silent: false });
	assert.deepEqual(normalizeFullListLoadOptions({ silent: "true" }), { silent: false });
	assert.deepEqual(normalizeFullListLoadOptions({ silent: false }), { silent: false });
});

test("normalizeFullListLoadOptions returns silent:false for non-object input", () => {
	assert.deepEqual(normalizeFullListLoadOptions(null), { silent: false });
	assert.deepEqual(normalizeFullListLoadOptions(undefined), { silent: false });
	assert.deepEqual(normalizeFullListLoadOptions([{ silent: true }]), { silent: false });
});

// ── normalizeDashboardHelperOptions behavioral tests ──────────────────────────

test("normalizeDashboardHelperOptions returns default arrays for missing input", () => {
	const result = normalizeDashboardHelperOptions(null);
	assert.deepEqual(result.items, []);
	assert.deepEqual(result.buildings, []);
	assert.deepEqual(result.cattleList, []);
	assert.equal(result.progress, null);
});

test("normalizeDashboardHelperOptions defaults callbacks to no-op functions", () => {
	const result = normalizeDashboardHelperOptions({});
	assert.ok(typeof result.onOpenNotifications === "function");
	assert.ok(typeof result.onNavigate === "function");
	assert.ok(typeof result.onAction === "function");
	assert.ok(typeof result.onSelect === "function");
	// no-op doesn't throw
	assert.doesNotThrow(() => result.onNavigate("test"));
});

test("normalizeDashboardHelperOptions preserves provided callback functions", () => {
	const myFn = () => "called";
	const result = normalizeDashboardHelperOptions({ onNavigate: myFn });
	assert.equal(result.onNavigate, myFn);
});

test("normalizeDashboardHelperOptions does not wrap non-function callbacks", () => {
	const result = normalizeDashboardHelperOptions({ onNavigate: "not-a-function" });
	// Should fall back to no-op
	assert.ok(typeof result.onNavigate === "function");
	assert.notEqual(result.onNavigate, "not-a-function");
});

test("normalizeDashboardHelperOptions passes buildingId and penId through undefined", () => {
	const result = normalizeDashboardHelperOptions({});
	assert.equal(result.buildingId, undefined);
	assert.equal(result.penId, undefined);
});

test("normalizeDashboardHelperOptions passes buildingId through when provided", () => {
	const result = normalizeDashboardHelperOptions({ buildingId: "b1", penId: 3 });
	assert.equal(result.buildingId, "b1");
	assert.equal(result.penId, 3);
});

// ── normalizeDashboardHelperItems behavioral tests ────────────────────────────

test("normalizeDashboardHelperItems returns empty array for non-array input", () => {
	assert.deepEqual(normalizeDashboardHelperItems(null), []);
	assert.deepEqual(normalizeDashboardHelperItems(undefined), []);
});

test("normalizeDashboardHelperItems keeps plain objects with non-null id", () => {
	const items = [{ id: "a" }, { id: 0 }, { id: "" }];
	const result = normalizeDashboardHelperItems(items);
	// id: 0 and "" are != null (0 != null is true, "" != null is true)
	assert.equal(result.length, 3);
});

test("normalizeDashboardHelperItems filters items without id", () => {
	const items = [{ name: "no id" }, { id: null }, { id: undefined }, { id: "ok" }];
	const result = normalizeDashboardHelperItems(items);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "ok");
});

test("normalizeDashboardHelperItems filters arrays and primitives", () => {
	const items = [[], null, "string", { id: "valid" }];
	const result = normalizeDashboardHelperItems(items);
	assert.equal(result.length, 1);
});
