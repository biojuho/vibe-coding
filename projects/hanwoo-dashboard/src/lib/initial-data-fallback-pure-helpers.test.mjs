/**
 * Behavioral tests for initial-data-fallback.mjs
 *
 * All exports are pure (no external dependencies), so we import directly.
 * Private helpers (normalizeSectionId, toDateKey, buildEmpty*) are exercised
 * indirectly via public API, with source-grep guards for structural invariants.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
	DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE,
	buildDashboardInitialDataFallback,
	buildDashboardInitialDataLoadStatus,
	getDashboardInitialDataSectionLabel,
	normalizeDashboardInitialDataLoadStatus,
} from "../lib/dashboard/initial-data-fallback.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/dashboard/initial-data-fallback.mjs"),
	"utf8",
);

// ── Source-grep guards ────────────────────────────────────────────────────────

test("initial-data-fallback: SECTION_LABELS covers all 13 Korean labels", () => {
	assert.match(src, /const SECTION_LABELS = new Map\(\[/);
	assert.match(src, /"cattle"/);
	assert.match(src, /"sales"/);
	assert.match(src, /"summary"/);
	assert.match(src, /"notifications"/);
	assert.match(src, /"feedStandards"/);
	assert.match(src, /"inventory"/);
	assert.match(src, /"schedule"/);
	assert.match(src, /"feedHistory"/);
	assert.match(src, /"buildings"/);
	assert.match(src, /"farmSettings"/);
	assert.match(src, /"expenses"/);
	assert.match(src, /"marketPrice"/);
	assert.match(src, /"profitability"/);
});

test("initial-data-fallback: normalizeSectionId trims whitespace, falls back to 'unknown'", () => {
	assert.match(src, /function normalizeSectionId\(sectionId\) \{/);
	assert.match(src, /sectionId\.trim\(\)\.length > 0/);
	assert.match(src, /["']unknown["']/);
});

test("initial-data-fallback: buildEmptyPage uses DEFAULT_PAGE_LIMIT", () => {
	assert.match(src, /const DEFAULT_PAGE_LIMIT = 50;/);
	assert.match(src, /function buildEmptyPage\(limit = DEFAULT_PAGE_LIMIT\) \{/);
	assert.match(src, /hasMore: false/);
	assert.match(src, /nextCursor: null/);
	assert.match(src, /returnedCount: 0/);
});

test("initial-data-fallback: buildEmptySummary guards invalid now with new Date()", () => {
	assert.match(src, /function buildEmptySummary\(now = new Date\(\)\) \{/);
	assert.match(
		src,
		/now instanceof Date && !Number\.isNaN\(now\.getTime\(\)\) \? now : new Date\(\)/,
	);
});

test("initial-data-fallback: buildEmptyProfitability returns INITIAL_DATA_UNAVAILABLE error", () => {
	assert.match(src, /function buildEmptyProfitability\(\) \{/);
	assert.match(src, /["']INITIAL_DATA_UNAVAILABLE["']/);
	assert.match(src, /["']initial-data-fallback["']/);
});

// ── DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE ───────────────────────────────────

test("DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE is a non-empty string", () => {
	assert.ok(typeof DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE === "string");
	assert.ok(DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE.length > 0);
});

// ── getDashboardInitialDataSectionLabel ───────────────────────────────────────

test("getDashboardInitialDataSectionLabel returns Korean label for known sections", () => {
	const pairs = [
		["cattle", "개체"],
		["sales", "매출"],
		["summary", "요약"],
		["notifications", "알림"],
		["feedStandards", "사료 기준"],
		["inventory", "재고"],
		["schedule", "일정"],
		["feedHistory", "급여 기록"],
		["buildings", "축사"],
		["farmSettings", "농장 설정"],
		["expenses", "비용"],
		["marketPrice", "시세"],
		["profitability", "수익성"],
	];
	for (const [id, expected] of pairs) {
		assert.equal(getDashboardInitialDataSectionLabel(id), expected, `label for "${id}"`);
	}
});

test("getDashboardInitialDataSectionLabel returns sectionId for unknown sections", () => {
	assert.equal(getDashboardInitialDataSectionLabel("widget_xyz"), "widget_xyz");
});

test("getDashboardInitialDataSectionLabel returns 'unknown' for empty string", () => {
	assert.equal(getDashboardInitialDataSectionLabel(""), "unknown");
	assert.equal(getDashboardInitialDataSectionLabel("   "), "unknown");
});

test("getDashboardInitialDataSectionLabel returns 'unknown' for non-string input", () => {
	assert.equal(getDashboardInitialDataSectionLabel(null), "unknown");
	assert.equal(getDashboardInitialDataSectionLabel(undefined), "unknown");
	assert.equal(getDashboardInitialDataSectionLabel(42), "unknown");
});

// ── buildDashboardInitialDataFallback ────────────────────────────────────────

test("buildDashboardInitialDataFallback returns empty page for 'cattle'", () => {
	const result = buildDashboardInitialDataFallback("cattle");
	assert.deepEqual(result.items, []);
	assert.equal(result.pageInfo.hasMore, false);
	assert.equal(result.pageInfo.nextCursor, null);
	assert.equal(result.pageInfo.limit, 50);
	assert.equal(result.pageInfo.returnedCount, 0);
});

test("buildDashboardInitialDataFallback returns empty page for 'sales'", () => {
	const result = buildDashboardInitialDataFallback("sales");
	assert.deepEqual(result.items, []);
	assert.equal(result.pageInfo.hasMore, false);
});

test("buildDashboardInitialDataFallback respects custom limit for 'cattle'", () => {
	const result = buildDashboardInitialDataFallback("cattle", { limit: 20 });
	assert.equal(result.pageInfo.limit, 20);
});

test("buildDashboardInitialDataFallback ignores non-integer limit", () => {
	const result = buildDashboardInitialDataFallback("cattle", { limit: "bad" });
	assert.equal(result.pageInfo.limit, 50); // falls back to default
});

test("buildDashboardInitialDataFallback returns summary object for 'summary'", () => {
	const now = new Date("2024-06-15");
	const result = buildDashboardInitialDataFallback("summary", { now });
	assert.equal(result.farmId, "default");
	assert.equal(result.headcount.totalActive, 0);
	assert.deepEqual(result.headcount.byStatus, {});
	assert.equal(result.monthlyRollup.salesCount, 0);
	assert.deepEqual(result.financialSeries, []);
	assert.equal(result.buildingCount, 0);
});

test("buildDashboardInitialDataFallback summary uses current month start as monthStart", () => {
	const now = new Date("2024-06-15");
	const result = buildDashboardInitialDataFallback("summary", { now });
	assert.equal(result.monthlyRollup.monthStart, "2024-06-01");
});

test("buildDashboardInitialDataFallback returns farmSettings object for 'farmSettings'", () => {
	const result = buildDashboardInitialDataFallback("farmSettings");
	assert.equal(result.id, "default");
	assert.ok(typeof result.name === "string");
	assert.equal(result.latitude, null);
	assert.equal(result.longitude, null);
});

test("buildDashboardInitialDataFallback returns null for 'marketPrice'", () => {
	const result = buildDashboardInitialDataFallback("marketPrice");
	assert.equal(result, null);
});

test("buildDashboardInitialDataFallback returns profitability error object for 'profitability'", () => {
	const result = buildDashboardInitialDataFallback("profitability");
	assert.equal(result.data, null);
	assert.equal(result.error, "INITIAL_DATA_UNAVAILABLE");
	assert.equal(result.meta.source, "initial-data-fallback");
});

test("buildDashboardInitialDataFallback returns [] for unknown sectionId", () => {
	const result = buildDashboardInitialDataFallback("unknown_section");
	assert.deepEqual(result, []);
});

test("buildDashboardInitialDataFallback returns [] for known sections not matching specific branches", () => {
	// 'notifications', 'inventory', 'schedule', etc. all return []
	for (const section of ["notifications", "inventory", "schedule", "feedHistory", "buildings"]) {
		const result = buildDashboardInitialDataFallback(section);
		assert.deepEqual(result, [], `section "${section}" should return []`);
	}
});

// ── normalizeDashboardInitialDataLoadStatus ──────────────────────────────────

test("normalizeDashboardInitialDataLoadStatus returns non-degraded baseline for null input", () => {
	const result = normalizeDashboardInitialDataLoadStatus(null);
	assert.equal(result.degraded, false);
	assert.deepEqual(result.failedSections, []);
	assert.deepEqual(result.failedSectionLabels, []);
	assert.equal(result.message, "");
});

test("normalizeDashboardInitialDataLoadStatus returns non-degraded baseline for non-object", () => {
	for (const input of [undefined, [], "string", 42]) {
		const result = normalizeDashboardInitialDataLoadStatus(input);
		assert.equal(result.degraded, false);
		assert.deepEqual(result.failedSections, []);
	}
});

test("normalizeDashboardInitialDataLoadStatus degraded=true when degraded flag is set", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: true,
		failedSections: [],
		message: "custom message",
	});
	assert.equal(result.degraded, true);
	assert.equal(result.message, "custom message");
});

test("normalizeDashboardInitialDataLoadStatus degraded=true when failedSections non-empty", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: false,
		failedSections: ["cattle"],
		message: "",
	});
	assert.equal(result.degraded, true);
	assert.deepEqual(result.failedSections, ["cattle"]);
});

test("normalizeDashboardInitialDataLoadStatus deduplicates failedSections", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: true,
		failedSections: ["cattle", "cattle", "sales"],
	});
	assert.equal(result.failedSections.length, 2);
	assert.ok(result.failedSections.includes("cattle"));
	assert.ok(result.failedSections.includes("sales"));
});

test("normalizeDashboardInitialDataLoadStatus filters out empty-string sectionIds", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: true,
		failedSections: ["", "  ", "cattle"],
	});
	assert.deepEqual(result.failedSections, ["cattle"]);
});

test("normalizeDashboardInitialDataLoadStatus builds failedSectionLabels in Korean", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: true,
		failedSections: ["cattle", "sales"],
	});
	assert.ok(result.failedSectionLabels.includes("개체"));
	assert.ok(result.failedSectionLabels.includes("매출"));
});

test("normalizeDashboardInitialDataLoadStatus uses default message when no custom message", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: true,
		failedSections: ["cattle"],
		message: "",
	});
	assert.equal(result.message, DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE);
});

test("normalizeDashboardInitialDataLoadStatus message is empty when not degraded", () => {
	const result = normalizeDashboardInitialDataLoadStatus({
		degraded: false,
		failedSections: [],
	});
	assert.equal(result.message, "");
});

// ── buildDashboardInitialDataLoadStatus ──────────────────────────────────────

test("buildDashboardInitialDataLoadStatus returns non-degraded for all-success results", () => {
	const results = [
		{ ok: true, sectionId: "cattle" },
		{ ok: true, sectionId: "sales" },
	];
	const status = buildDashboardInitialDataLoadStatus(results);
	assert.equal(status.degraded, false);
	assert.deepEqual(status.failedSections, []);
});

test("buildDashboardInitialDataLoadStatus is degraded when any result has ok=false", () => {
	const results = [
		{ ok: true, sectionId: "cattle" },
		{ ok: false, sectionId: "sales" },
	];
	const status = buildDashboardInitialDataLoadStatus(results);
	assert.equal(status.degraded, true);
	assert.deepEqual(status.failedSections, ["sales"]);
	assert.ok(status.failedSectionLabels.includes("매출"));
});

test("buildDashboardInitialDataLoadStatus handles empty results array", () => {
	const status = buildDashboardInitialDataLoadStatus([]);
	assert.equal(status.degraded, false);
});

test("buildDashboardInitialDataLoadStatus handles non-array input", () => {
	const status = buildDashboardInitialDataLoadStatus(null);
	assert.equal(status.degraded, false);
	assert.deepEqual(status.failedSections, []);
});

test("buildDashboardInitialDataLoadStatus uses DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE", () => {
	const results = [{ ok: false, sectionId: "cattle" }];
	const status = buildDashboardInitialDataLoadStatus(results);
	assert.equal(status.message, DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE);
});
