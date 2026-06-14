import { auth } from "@/auth";
import DashboardClient from "@/components/DashboardClient";
import ErrorBoundary from "@/components/ErrorBoundary";
import LandingPage from "@/components/LandingPage";
import { getSubscriptionStatus } from "@/lib/subscription-queries";
import {
	getBuildings,
	getExpenseRecords,
	getFarmSettings,
	getFeedHistory,
	getFeedStandards,
	getInventory,
	getNotifications,
	getProfitabilityData,
	getRealTimeMarketPrice,
	getScheduleEvents,
} from "@/lib/actions";
import {
	getCachedCattleList,
	getCachedDashboardSummary,
	getCachedSalesList,
} from "@/lib/dashboard/cached-queries";
import {
	buildDashboardInitialDataFallback,
	buildDashboardInitialDataLoadStatus,
} from "@/lib/dashboard/initial-data-fallback.mjs";

export const metadata = {
	title: "대시보드 · Joolife 한우",
	description: "한우 농장 관리 대시보드 — 개체 관리, 수익성 분석, AI 인사이트를 한 곳에서.",
};

const INITIAL_PAGE_LIMIT = 50;

const INITIAL_DATA_LOADERS = [
	{
		key: "initialCattlePage",
		sectionId: "cattle",
		load: () => getCachedCattleList({ limit: INITIAL_PAGE_LIMIT }),
	},
	{
		key: "initialSalesPage",
		sectionId: "sales",
		load: () => getCachedSalesList({ limit: INITIAL_PAGE_LIMIT }),
	},
	{
		key: "summary",
		sectionId: "summary",
		load: () => getCachedDashboardSummary(),
	},
	{
		key: "notifications",
		sectionId: "notifications",
		load: () => getNotifications(),
	},
	{
		key: "feedStandards",
		sectionId: "feedStandards",
		load: () => getFeedStandards(),
	},
	{
		key: "inventory",
		sectionId: "inventory",
		load: () => getInventory(),
	},
	{
		key: "schedule",
		sectionId: "schedule",
		load: () => getScheduleEvents(),
	},
	{
		key: "feedHistory",
		sectionId: "feedHistory",
		load: () => getFeedHistory(),
	},
	{
		key: "buildings",
		sectionId: "buildings",
		load: () => getBuildings(),
	},
	{
		key: "farmSettings",
		sectionId: "farmSettings",
		load: () => getFarmSettings(),
	},
	{
		key: "expenses",
		sectionId: "expenses",
		load: () => getExpenseRecords(),
	},
	{
		key: "marketPrice",
		sectionId: "marketPrice",
		load: () => getRealTimeMarketPrice(),
	},
	{
		key: "profitability",
		sectionId: "profitability",
		load: () => getProfitabilityData(),
	},
];

function isNextControlFlowError(error) {
	const digest = typeof error?.digest === "string" ? error.digest : "";
	return digest.startsWith("NEXT_REDIRECT") || digest.startsWith("NEXT_NOT_FOUND");
}

function logInitialDataLoadFailure(sectionId, error) {
	const errorName =
		typeof error?.name === "string" && error.name.length > 0
			? error.name
			: "Error";
	const errorMessage =
		typeof error?.message === "string" && error.message.length > 0
			? error.message
			: "initial data unavailable";

	console.warn(
		`[hanwoo-dashboard] degraded initial ${sectionId} data load: ${errorName}: ${errorMessage}`,
	);
}

async function loadInitialDataSection(loader) {
	try {
		return {
			key: loader.key,
			sectionId: loader.sectionId,
			ok: true,
			value: await loader.load(),
		};
	} catch (error) {
		if (isNextControlFlowError(error)) {
			throw error;
		}

		logInitialDataLoadFailure(loader.sectionId, error);
		return {
			key: loader.key,
			sectionId: loader.sectionId,
			ok: false,
			value: buildDashboardInitialDataFallback(loader.sectionId, {
				limit: INITIAL_PAGE_LIMIT,
			}),
		};
	}
}

export async function loadDashboardInitialData() {
	const results = await Promise.all(INITIAL_DATA_LOADERS.map(loadInitialDataSection));
	const data = Object.fromEntries(
		results.map((result) => [result.key, result.value]),
	);

	return {
		...data,
		initialDataLoadStatus: buildDashboardInitialDataLoadStatus(results),
	};
}

export default async function Page() {
	let session = null;
	try {
		session = await auth();
	} catch {
		// DB unreachable — show landing page
	}

	if (!session?.user?.id) {
		return <LandingPage />;
	}

	const [initialData, subscriptionStatus] = await Promise.all([
		loadDashboardInitialData(),
		getSubscriptionStatus(session.user.id).catch(() => ({ status: "INACTIVE", daysLeft: null })),
	]);

	return (
		<ErrorBoundary>
			<DashboardClient
				initialCattlePage={initialData.initialCattlePage}
				initialSalesPage={initialData.initialSalesPage}
				initialSummary={initialData.summary}
				initialNotifications={initialData.notifications}
				initialFeedStandards={initialData.feedStandards}
				initialInventory={initialData.inventory}
				initialSchedule={initialData.schedule}
				initialFeedHistory={initialData.feedHistory}
				initialBuildings={initialData.buildings}
				initialFarmSettings={initialData.farmSettings}
				initialExpenses={initialData.expenses}
				initialMarketPrice={initialData.marketPrice}
				initialProfitability={initialData.profitability}
				initialDataLoadStatus={initialData.initialDataLoadStatus}
				subscriptionStatus={subscriptionStatus}
			/>
		</ErrorBoundary>
	);
}
