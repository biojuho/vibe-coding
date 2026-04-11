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
import { getCattleListPage, getSalesListPage } from '@/lib/dashboard/list-queries';
import { buildDashboardSummaryPayload } from '@/lib/dashboard/summary-service';
import { requireAuthenticatedSession } from '@/lib/auth-guard';
import prisma from '@/lib/db';

// Force dynamic because we are fetching data from DB that changes
export const dynamic = 'force-dynamic';

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
    getCattleListPage({ limit: 50 }),
    getSalesListPage({ limit: 50 }),
    buildDashboardSummaryPayload({ client: prisma }),
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
