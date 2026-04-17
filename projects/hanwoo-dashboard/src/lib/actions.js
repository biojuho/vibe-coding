/**
 * Server Actions barrel — re-exports from domain-specific modules.
 *
 * Each sub-file under ./actions/ carries its own 'use server' directive
 * and handles authentication via requireAuthenticatedSession().
 *
 * Import contract unchanged: `import { getCattleList } from '@/lib/actions'`
 */

export {
  getCattleList,
  getArchivedCattle,
  createCattle,
  updateCattle,
  recordCalving,
  deleteCattle,
  getCattleHistory,
} from './actions/cattle';

export {
  getSalesRecords,
  createSalesRecord,
} from './actions/sales';

export {
  getFeedStandards,
  recordFeed,
  getFeedHistory,
} from './actions/feed';

export {
  getInventory,
  addInventoryItem,
  updateInventoryQuantity,
} from './actions/inventory';

export {
  getScheduleEvents,
  createScheduleEvent,
  toggleEventCompletion,
} from './actions/schedule';

export {
  getBuildings,
  createBuilding,
  deleteBuilding,
} from './actions/building';

export {
  getFarmSettings,
  updateFarmSettings,
} from './actions/farm-settings';

export {
  getRealTimeMarketPrice,
} from './actions/market';

export {
  getNotifications,
} from './actions/notification';

export {
  getExpenseRecords,
  createExpenseRecord,
  getExpenseAggregation,
} from './actions/expense';

export {
  getSystemDiagnostics,
  getRawData,
  lookupCattleTag,
  getProfitabilityData,
} from './actions/system';
