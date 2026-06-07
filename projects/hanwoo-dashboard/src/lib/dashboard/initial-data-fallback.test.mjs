import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
	DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE,
	buildDashboardInitialDataFallback,
	buildDashboardInitialDataLoadStatus,
	normalizeDashboardInitialDataLoadStatus,
} from "./initial-data-fallback.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "../..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("dashboard initial data fallbacks preserve serializable client shapes", () => {
	const cattlePage = buildDashboardInitialDataFallback("cattle", {
		limit: 25,
	});
	const salesPage = buildDashboardInitialDataFallback("sales");
	const summary = buildDashboardInitialDataFallback("summary", {
		now: new Date("2026-06-15T12:30:00.000Z"),
	});
	const farmSettings = buildDashboardInitialDataFallback("farmSettings");
	const profitability = buildDashboardInitialDataFallback("profitability");

	assert.deepEqual(cattlePage, {
		items: [],
		pageInfo: {
			hasMore: false,
			nextCursor: null,
			limit: 25,
			returnedCount: 0,
		},
	});
	assert.equal(salesPage.pageInfo.limit, 50);
	assert.equal(summary.farmId, "default");
	assert.equal(summary.monthlyRollup.monthStart, "2026-06-01");
	assert.deepEqual(summary.headcount, {
		totalActive: 0,
		byStatus: {},
		averageWeight: 0,
	});
	assert.deepEqual(summary.financialSeries, []);
	assert.equal(farmSettings.name, "Joolife 한우 농장");
	assert.equal(farmSettings.latitude, null);
	assert.equal(buildDashboardInitialDataFallback("marketPrice"), null);
	assert.deepEqual(profitability, {
		data: null,
		error: "INITIAL_DATA_UNAVAILABLE",
		meta: {
			source: "initial-data-fallback",
		},
	});
	assert.deepEqual(buildDashboardInitialDataFallback("notifications"), []);
});

test("dashboard initial data status deduplicates failed sections", () => {
	const status = buildDashboardInitialDataLoadStatus([
		{ sectionId: "cattle", ok: false },
		{ sectionId: "cattle", ok: false },
		{ sectionId: "summary", ok: true },
		{ sectionId: "profitability", ok: false },
	]);

	assert.equal(status.degraded, true);
	assert.deepEqual(status.failedSections, ["cattle", "profitability"]);
	assert.deepEqual(status.failedSectionLabels, ["개체", "수익성"]);
	assert.equal(status.message, DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE);
	assert.deepEqual(normalizeDashboardInitialDataLoadStatus(null), {
		degraded: false,
		failedSections: [],
		failedSectionLabels: [],
		message: "",
	});
});

test("home route degrades initial data failures instead of crashing the shell", () => {
	const pageSource = readSource("app/page.js");
	const dashboardClientSource = readSource("components/DashboardClient.js");
	const globalCssSource = readSource("app/globals.css");
	const readFallbackSources = [
		"lib/actions/inventory.js",
		"lib/actions/expense.js",
		"lib/actions/feed.js",
		"lib/actions/building.js",
		"lib/actions/schedule.js",
		"lib/actions/notification.js",
		"lib/actions/market.js",
		"lib/dashboard/profitability-service.js",
	].map(readSource);
	const readFallbackSource = readFallbackSources.join("\n");

	assert.match(pageSource, /async function loadInitialDataSection\(loader\)/);
	assert.match(pageSource, /isNextControlFlowError\(error\)/);
	assert.match(pageSource, /buildDashboardInitialDataFallback/);
	assert.match(pageSource, /buildDashboardInitialDataLoadStatus\(results\)/);
	assert.match(
		pageSource,
		/initialDataLoadStatus=\{initialData\.initialDataLoadStatus\}/,
	);
	assert.doesNotMatch(
		pageSource,
		/await Promise\.all\(\[\s*getCachedCattleList/,
	);

	assert.match(dashboardClientSource, /function InitialDataStatusBanner/);
	assert.match(
		dashboardClientSource,
		/normalizeDashboardInitialDataLoadStatus/,
	);
	assert.match(dashboardClientSource, /aria-label="저장소 연결 저하"/);
	assert.match(dashboardClientSource, /role="status"/);
	assert.match(dashboardClientSource, /router\.refresh\(\)/);
	assert.match(
		dashboardClientSource,
		/className="min-h-11 w-full border-amber-500\/40 bg-white\/70 text-amber-950 hover:bg-amber-100 dark:bg-amber-900\/30 dark:text-amber-100 sm:w-auto"/,
	);
	assert.match(
		dashboardClientSource,
		/mb-7 flex flex-col gap-4 pt-2 pb-1 sm:flex-row/,
	);
	assert.match(
		dashboardClientSource,
		/flex w-full flex-wrap justify-end gap-2\.5/,
	);
	assert.match(
		dashboardClientSource,
		/const isInitialCattleDataDegraded =\s+initialDataLoadStatus\.failedSections\.includes\("cattle"\);/,
	);
	assert.match(
		dashboardClientSource,
		/const isInitialSalesDataDegraded =\s+initialDataLoadStatus\.failedSections\.includes\("sales"\);/,
	);
	assert.match(
		dashboardClientSource,
		/const shouldSkipFieldModeCattlePreload =\s+isInitialCattleDataDegraded;/,
	);
	assert.match(
		dashboardClientSource,
		/const \[allCattleRegistry, setAllCattleRegistry\] = useState\(\(\) =>\s+isInitialCattleDataDegraded \? \[\] : null,/,
	);
	assert.match(
		dashboardClientSource,
		/const \[allSalesLedger, setAllSalesLedger\] = useState\(\(\) =>\s+isInitialSalesDataDegraded \? \[\] : null,/,
	);
	assert.match(
		dashboardClientSource,
		/shouldSkipFieldModeCattlePreload \? null : ensureAllCattleLoaded/,
	);
	assert.match(
		globalCssSource,
		/grid-template-columns: repeat\(8, minmax\(0, 1fr\)\)/,
	);
	assert.match(globalCssSource, /\.tab-item \{[\s\S]*?min-width: 0;/);
	assert.doesNotMatch(
		readFallbackSource,
		/console\.error\(["'](?:Failed to fetch inventory|Failed to fetch expenses|Failed to fetch feed standards|Failed to fetch feed history|Failed to fetch buildings|Failed to fetch schedule|Failed to get notifications|Market price cache read failed|수익성 추정 오류)/,
	);
	assert.match(readFallbackSource, /Degraded inventory fetch/);
	assert.match(readFallbackSource, /Degraded expenses fetch/);
	assert.match(readFallbackSource, /Degraded feed standards fetch/);
	assert.match(readFallbackSource, /Degraded feed history fetch/);
	assert.match(readFallbackSource, /Degraded buildings fetch/);
	assert.match(readFallbackSource, /Degraded schedule fetch/);
	assert.match(readFallbackSource, /Degraded notifications fetch/);
	assert.match(readFallbackSource, /Market price cache read degraded/);
	assert.match(readFallbackSource, /Degraded profitability estimate/);
});
