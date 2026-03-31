import DashboardClient from '@/components/DashboardClient';
import { getCattleList, getSalesRecords, getFeedStandards, getInventory, getScheduleEvents, getFeedHistory, getBuildings, getFarmSettings, getExpenseRecords } from '@/lib/actions';

// Force dynamic because we are fetching data from DB that changes
export const dynamic = 'force-dynamic';

export default async function Page() {
  const cattle = await getCattleList();
  const sales = await getSalesRecords();
  const feedStandards = await getFeedStandards();
  const inventory = await getInventory();
  const schedule = await getScheduleEvents();
  const feedHistory = await getFeedHistory();
  const buildings = await getBuildings();
  const farmSettings = await getFarmSettings();
  const expenses = await getExpenseRecords();

  return (
    <DashboardClient
        initialCattle={cattle}
        initialSales={sales}
        initialFeedStandards={feedStandards}
        initialInventory={inventory}
        initialSchedule={schedule}
        initialFeedHistory={feedHistory}
        initialBuildings={buildings}
        initialFarmSettings={farmSettings}
        initialExpenses={expenses}
    />
  );
}
