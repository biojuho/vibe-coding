import { getQueue, clearQueue } from './offlineQueue';
import {
  createCattle, updateCattle, deleteCattle,
  recordCalving,
  createSalesRecord, recordFeed,
  addInventoryItem, updateInventoryQuantity,
  createScheduleEvent, toggleEventCompletion,
  createBuilding, deleteBuilding,
  updateFarmSettings, createExpenseRecord
} from './actions';

const ACTION_MAP = {
  createCattle,
  updateCattle: (args) => updateCattle(args[0], args[1]),
  deleteCattle,
  recordCalving,
  createSalesRecord,
  recordFeed,
  addInventoryItem,
  updateInventoryQuantity: (args) => updateInventoryQuantity(args[0], args[1]),
  createScheduleEvent,
  toggleEventCompletion: (args) => toggleEventCompletion(args[0], args[1]),
  createBuilding,
  deleteBuilding,
  updateFarmSettings,
  createExpenseRecord,
};

export async function syncOfflineQueue() {
  const queue = getQueue();
  if (queue.length === 0) return { synced: 0, failed: 0 };

  let synced = 0;
  let failed = 0;

  for (const item of queue) {
    const handler = ACTION_MAP[item.action];
    if (!handler) {
      failed++;
      continue;
    }
    try {
      const args = Array.isArray(item.args) ? item.args : [item.args];
      const result = typeof handler === 'function' && Array.isArray(item.args) && item.args.length > 1
        ? await handler(item.args)
        : await handler(...args);
      if (result?.success === false) {
        failed++;
      } else {
        synced++;
      }
    } catch {
      failed++;
    }
  }

  clearQueue();
  return { synced, failed };
}
