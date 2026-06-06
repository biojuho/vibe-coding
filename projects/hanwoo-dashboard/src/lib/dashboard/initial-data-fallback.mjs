const DEFAULT_PAGE_LIMIT = 50;
const DEFAULT_FARM_ID = "default";

export const DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE =
	"저장소 연결이 불안정해 빈 대시보드로 먼저 열었습니다. 새로고침하면 최신 농장 데이터를 다시 불러옵니다.";

const SECTION_LABELS = new Map([
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
]);

function normalizeSectionId(sectionId) {
	return typeof sectionId === "string" && sectionId.trim().length > 0
		? sectionId.trim()
		: "unknown";
}

function toDateKey(value) {
	return [
		value.getFullYear(),
		String(value.getMonth() + 1).padStart(2, "0"),
		String(value.getDate()).padStart(2, "0"),
	].join("-");
}

function buildEmptyPage(limit = DEFAULT_PAGE_LIMIT) {
	return {
		items: [],
		pageInfo: {
			hasMore: false,
			nextCursor: null,
			limit,
			returnedCount: 0,
		},
	};
}

function buildEmptySummary(now = new Date()) {
	const generatedAt =
		now instanceof Date && !Number.isNaN(now.getTime()) ? now : new Date();
	const monthStart = new Date(
		generatedAt.getFullYear(),
		generatedAt.getMonth(),
		1,
	);

	return {
		farmId: DEFAULT_FARM_ID,
		generatedAt: generatedAt.toISOString(),
		headcount: {
			totalActive: 0,
			byStatus: {},
			averageWeight: 0,
		},
		monthlyRollup: {
			monthStart: toDateKey(monthStart),
			salesCount: 0,
			salesTotal: 0,
			expenseTotal: 0,
			profitTotal: 0,
		},
		financialSeries: [],
		buildingCount: 0,
		buildingOccupancy: [],
		farmSettings: null,
	};
}

function buildEmptyFarmSettings() {
	return {
		id: DEFAULT_FARM_ID,
		name: "Joolife 한우 농장",
		location: "",
		latitude: null,
		longitude: null,
	};
}

function buildEmptyProfitability() {
	return {
		data: null,
		error: "INITIAL_DATA_UNAVAILABLE",
		meta: {
			source: "initial-data-fallback",
		},
	};
}

export function getDashboardInitialDataSectionLabel(sectionId) {
	const normalized = normalizeSectionId(sectionId);
	return SECTION_LABELS.get(normalized) ?? normalized;
}

export function buildDashboardInitialDataFallback(sectionId, options = {}) {
	const normalized = normalizeSectionId(sectionId);
	const limit =
		Number.isSafeInteger(options.limit) && options.limit > 0
			? options.limit
			: DEFAULT_PAGE_LIMIT;

	if (normalized === "cattle" || normalized === "sales") {
		return buildEmptyPage(limit);
	}

	if (normalized === "summary") {
		return buildEmptySummary(options.now);
	}

	if (normalized === "farmSettings") {
		return buildEmptyFarmSettings();
	}

	if (normalized === "marketPrice") {
		return null;
	}

	if (normalized === "profitability") {
		return buildEmptyProfitability();
	}

	return [];
}

export function normalizeDashboardInitialDataLoadStatus(status) {
	if (!status || typeof status !== "object" || Array.isArray(status)) {
		return {
			degraded: false,
			failedSections: [],
			failedSectionLabels: [],
			message: "",
		};
	}

	const failedSections = Array.isArray(status.failedSections)
		? status.failedSections
				.map(normalizeSectionId)
				.filter((sectionId) => sectionId !== "unknown")
		: [];
	const uniqueFailedSections = [...new Set(failedSections)];
	const degraded = status.degraded === true || uniqueFailedSections.length > 0;

	return {
		degraded,
		failedSections: uniqueFailedSections,
		failedSectionLabels: uniqueFailedSections.map(
			getDashboardInitialDataSectionLabel,
		),
		message: degraded
			? typeof status.message === "string" && status.message.trim().length > 0
				? status.message.trim()
				: DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE
			: "",
	};
}

export function buildDashboardInitialDataLoadStatus(results) {
	const failedSections = Array.isArray(results)
		? results
				.filter((result) => result?.ok === false)
				.map((result) => normalizeSectionId(result.sectionId))
				.filter((sectionId) => sectionId !== "unknown")
		: [];

	return normalizeDashboardInitialDataLoadStatus({
		degraded: failedSections.length > 0,
		failedSections,
		message: DASHBOARD_INITIAL_DATA_DEGRADED_MESSAGE,
	});
}
