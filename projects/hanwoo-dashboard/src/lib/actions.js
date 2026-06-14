/**
 * Server Actions barrel — re-exports from domain-specific modules.
 *
 * Each sub-file under ./actions/ carries its own 'use server' directive
 * and handles authentication via requireAuthenticatedSession().
 *
 * Import contract unchanged: `import { getCattleList } from '@/lib/actions'`
 */

export {
	createBuilding,
	deleteBuilding,
	getBuildings,
} from "./actions/building";
export {
	createCattle,
	deleteCattle,
	getArchivedCattle,
	getCattleHistory,
	getCattleList,
	recordCalving,
	updateCattle,
} from "./actions/cattle";
export {
	createExpenseRecord,
	getExpenseAggregation,
	getExpenseRecords,
} from "./actions/expense";
export {
	getFarmSettings,
	updateFarmSettings,
} from "./actions/farm-settings";
export {
	getFeedHistory,
	getFeedStandards,
	recordFeed,
} from "./actions/feed";
export {
	addInventoryItem,
	getInventory,
	updateInventoryQuantity,
} from "./actions/inventory";
export { getRealTimeMarketPrice } from "./actions/market";
export { getNotifications } from "./actions/notification";
export {
	createSalesRecord,
	getSalesRecords,
} from "./actions/sales";
export {
	createScheduleEvent,
	getScheduleEvents,
	toggleEventCompletion,
} from "./actions/schedule";

export {
	deleteAccount,
	getProfitabilityData,
	getRawData,
	getSystemDiagnostics,
	lookupCattleTag,
} from "./actions/system";
