import DashboardClient from "@/components/DashboardClient";
import ErrorBoundary from "@/components/ErrorBoundary";
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
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import {
	getCachedCattleList,
	getCachedDashboardSummary,
	getCachedSalesList,
} from "@/lib/dashboard/cached-queries";

export default async function Page() {
	await requireAuthenticatedSession({ redirectToLogin: true });

	const [
		initialCattlePage,
		initialSalesPage,
		summary,
		notifications,
		feedStandards,
		inventory,
		schedule,
		feedHistory,
		buildings,
		farmSettings,
		expenses,
		marketPrice,
		profitability,
	] = await Promise.all([
		getCachedCattleList({ limit: 50 }),
		getCachedSalesList({ limit: 50 }),
		getCachedDashboardSummary(),
		getNotifications(),
		getFeedStandards(),
		getInventory(),
		getScheduleEvents(),
		getFeedHistory(),
		getBuildings(),
		getFarmSettings(),
		getExpenseRecords(),
		getRealTimeMarketPrice(),
		getProfitabilityData(),
	]);

	return (
		<ErrorBoundary>
			<DashboardClient
				initialCattlePage={initialCattlePage}
				initialSalesPage={initialSalesPage}
				initialSummary={summary}
				initialNotifications={notifications}
				initialFeedStandards={feedStandards}
				initialInventory={inventory}
				initialSchedule={schedule}
				initialFeedHistory={feedHistory}
				initialBuildings={buildings}
				initialFarmSettings={farmSettings}
				initialExpenses={expenses}
				initialMarketPrice={marketPrice}
				initialProfitability={profitability}
			/>
		</ErrorBoundary>
	);
}
