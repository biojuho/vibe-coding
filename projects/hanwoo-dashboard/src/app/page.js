import DashboardClient from '@/components/DashboardClient';
import {
  getFeedStandards,
  getInventory,
  getScheduleEvents,
  getFeedHistory,
  getBuildings,
  getFarmSettings,
  getExpenseRecords,
  getRealTimeMarketPrice,
  getNotifications,
} from '@/lib/actions';
import {
  getCachedDashboardSummary,
  getCachedCattleList,
  getCachedSalesList,
} from '@/lib/dashboard/cached-queries';
import { requireAuthenticatedSession } from '@/lib/auth-guard';

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
  ]);

  return (
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
    />
  );
}

