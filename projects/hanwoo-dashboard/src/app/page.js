import DashboardClient from '@/components/DashboardClient';
import {
  getCattleList,
  getFeedStandards,
  getInventory,
  getScheduleEvents,
  getFeedHistory,
  getBuildings,
  getFarmSettings,
  getExpenseRecords,
  getRealTimeMarketPrice,
  getSalesRecords,
} from '@/lib/actions';
import { buildDashboardSummaryPayload } from '@/lib/dashboard/summary-service';
import { requireAuthenticatedSession } from '@/lib/auth-guard';
import prisma from '@/lib/db';

// Force dynamic because we are fetching data from DB that changes
export const dynamic = 'force-dynamic';

export default async function Page() {
  await requireAuthenticatedSession({ redirectToLogin: true });

  const [
    cattleRegistry,
    salesLedger,
    summary,
    feedStandards,
    inventory,
    schedule,
    feedHistory,
    buildings,
    farmSettings,
    expenses,
    marketPrice,
  ] = await Promise.all([
    getCattleList(),
    getSalesRecords(),
    buildDashboardSummaryPayload({ client: prisma }),
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
        initialCattleRegistry={cattleRegistry}
        initialSalesLedger={salesLedger}
        initialSummary={summary}
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
