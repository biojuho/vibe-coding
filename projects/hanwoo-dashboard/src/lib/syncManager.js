import { appendDeadLetterQueue, getQueue, setQueue } from './offlineQueue';
import {
  createFailedQueueItemState,
  isPermanentOfflineQueueFailure,
} from './offline-sync-state.mjs';
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
  createCattle: (args) => createCattle(args[0]),
  updateCattle: (args) => updateCattle(args[0], args[1]),
  deleteCattle: (args) => deleteCattle(args[0]),
  recordCalving: (args) => recordCalving(args[0]),
  createSalesRecord: (args) => createSalesRecord(args[0]),
  recordFeed: (args) => recordFeed(args[0]),
  addInventoryItem: (args) => addInventoryItem(args[0]),
  updateInventoryQuantity: (args) => updateInventoryQuantity(args[0], args[1]),
  createScheduleEvent: (args) => createScheduleEvent(args[0]),
  toggleEventCompletion: (args) => toggleEventCompletion(args[0], args[1]),
  createBuilding: (args) => createBuilding(args[0]),
  deleteBuilding: (args) => deleteBuilding(args[0]),
  updateFarmSettings: (args) => updateFarmSettings(args[0]),
  createExpenseRecord: (args) => createExpenseRecord(args[0]),
};

let activeSyncPromise = null;

function mergeRemainingQueue(snapshotQueue, latestQueue, failedItems) {
  const processedIds = new Set(snapshotQueue.map((item) => item.id));
  const queuedWhileSyncing = latestQueue.filter((item) => !processedIds.has(item.id));
  return [...failedItems, ...queuedWhileSyncing];
}

async function syncOfflineQueueInternal() {
  const queueSnapshot = getQueue();
  if (queueSnapshot.length === 0) return { synced: 0, failed: 0, deadLettered: 0 };

  let synced = 0;
  const failedItems = [];
  const deadLetterItems = [];

  for (const item of queueSnapshot) {
    const handler = ACTION_MAP[item.action];
    if (!handler) {
      const failureState = createFailedQueueItemState(item, {
        errorMessage: `No offline sync handler is registered for action "${item.action}".`,
        permanent: true,
      });
      deadLetterItems.push(failureState.item);
      continue;
    }

    try {
      const args = Array.isArray(item.args) ? item.args : [item.args];
      const result = await handler(args);
      if (result?.success === false) {
        const errorMessage =
          typeof result?.message === 'string' && result.message.length > 0
            ? result.message
            : `Offline sync action "${item.action}" returned an unsuccessful result.`;
        const failureState = createFailedQueueItemState(item, {
          errorMessage,
          permanent: isPermanentOfflineQueueFailure(errorMessage),
        });
        if (failureState.disposition === 'dead-letter') {
          deadLetterItems.push(failureState.item);
        } else {
          failedItems.push(failureState.item);
        }
      } else {
        synced++;
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error && error.message
          ? error.message
          : `Offline sync action "${item.action}" threw an unknown error.`;
      const failureState = createFailedQueueItemState(item, {
        errorMessage,
        permanent: isPermanentOfflineQueueFailure(errorMessage),
      });
      if (failureState.disposition === 'dead-letter') {
        deadLetterItems.push(failureState.item);
      } else {
        failedItems.push(failureState.item);
      }
    }
  }

  const latestQueue = getQueue();
  const nextQueue = mergeRemainingQueue(queueSnapshot, latestQueue, failedItems);
  setQueue(nextQueue);
  if (deadLetterItems.length > 0) {
    appendDeadLetterQueue(deadLetterItems);
  }

  return {
    synced,
    failed: failedItems.length + deadLetterItems.length,
    deadLettered: deadLetterItems.length,
  };
}

export async function syncOfflineQueue() {
  if (activeSyncPromise) {
    return activeSyncPromise.then((result) => ({ ...result, reused: true }));
  }

  activeSyncPromise = (async () => {
    try {
      return await syncOfflineQueueInternal();
    } finally {
      activeSyncPromise = null;
    }
  })();

  const result = await activeSyncPromise;
  return { ...result, reused: false };
}
