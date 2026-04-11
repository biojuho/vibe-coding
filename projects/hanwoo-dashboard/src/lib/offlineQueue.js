import { normalizeOfflineQueueMetadata } from './offline-sync-state.mjs';

const QUEUE_KEY = 'joolife-offline-queue';
const DEAD_LETTER_KEY = 'joolife-offline-dead-letter';
const DEAD_LETTER_LIMIT = 100;

function createQueueItemId() {
  return globalThis.crypto?.randomUUID?.() ?? `offline-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeQueueItem(item) {
  if (!item || typeof item !== 'object' || typeof item.action !== 'string' || item.action.length === 0) {
    return null;
  }

  return {
    id: typeof item.id === 'string' && item.id.length > 0 ? item.id : createQueueItemId(),
    action: item.action,
    args: item.args,
    timestamp: typeof item.timestamp === 'number' ? item.timestamp : Date.now(),
    ...normalizeOfflineQueueMetadata(item),
  };
}

function persistQueueList(key, queue) {
  if (typeof window === 'undefined') return;

  if (!Array.isArray(queue) || queue.length === 0) {
    localStorage.removeItem(key);
    return;
  }

  localStorage.setItem(key, JSON.stringify(queue));
}

function persistQueue(queue) {
  persistQueueList(QUEUE_KEY, queue);
}

function persistDeadLetterQueue(queue) {
  const trimmed = Array.isArray(queue) ? queue.slice(-DEAD_LETTER_LIMIT) : [];
  persistQueueList(DEAD_LETTER_KEY, trimmed);
}

function readQueue(key) {
  if (typeof window === 'undefined') return [];

  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }

    const normalized = parsed.map(normalizeQueueItem).filter(Boolean);
    const needsRewrite =
      normalized.length !== parsed.length
      || normalized.some(
        (item, index) =>
          item.id !== parsed[index]?.id
          || item.timestamp !== parsed[index]?.timestamp
          || item.retryCount !== parsed[index]?.retryCount
          || item.lastAttemptAt !== parsed[index]?.lastAttemptAt
          || item.lastError !== parsed[index]?.lastError
          || item.deadLetteredAt !== parsed[index]?.deadLetteredAt,
      );

    if (needsRewrite) {
      if (key === DEAD_LETTER_KEY) {
        persistDeadLetterQueue(normalized);
      } else {
        persistQueue(normalized);
      }
    }

    return normalized;
  } catch {
    return [];
  }
}

export function getQueue() {
  return readQueue(QUEUE_KEY);
}

export function getDeadLetterQueue() {
  return readQueue(DEAD_LETTER_KEY);
}

export function enqueue(action, args) {
  const queue = getQueue();
  const nextItem = normalizeQueueItem({ action, args, timestamp: Date.now() });
  if (!nextItem) {
    return null;
  }

  persistQueue([...queue, nextItem]);
  return nextItem;
}

export function setQueue(queue) {
  if (typeof window === 'undefined') return;

  try {
    const normalized = Array.isArray(queue) ? queue.map(normalizeQueueItem).filter(Boolean) : [];
    persistQueue(normalized);
  } catch {
    // Best-effort persistence: keep the current queue if serialization fails.
  }
}

export function setDeadLetterQueue(queue) {
  if (typeof window === 'undefined') return;

  try {
    const normalized = Array.isArray(queue) ? queue.map(normalizeQueueItem).filter(Boolean) : [];
    persistDeadLetterQueue(normalized);
  } catch {
    // Best-effort persistence: keep the current dead-letter queue if serialization fails.
  }
}

export function appendDeadLetterQueue(items) {
  const current = getDeadLetterQueue();
  setDeadLetterQueue([...current, ...(Array.isArray(items) ? items : [])]);
}

export function clearQueue() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(QUEUE_KEY);
}

export function clearDeadLetterQueue() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(DEAD_LETTER_KEY);
}

export function queueSize() {
  return getQueue().length;
}
