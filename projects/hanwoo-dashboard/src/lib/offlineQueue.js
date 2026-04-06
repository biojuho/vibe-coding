const QUEUE_KEY = 'joolife-offline-queue';

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
  };
}

function persistQueue(queue) {
  if (typeof window === 'undefined') return;

  if (!Array.isArray(queue) || queue.length === 0) {
    localStorage.removeItem(QUEUE_KEY);
    return;
  }

  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export function getQueue() {
  if (typeof window === 'undefined') return [];

  try {
    const raw = localStorage.getItem(QUEUE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }

    const normalized = parsed.map(normalizeQueueItem).filter(Boolean);
    const needsRewrite =
      normalized.length !== parsed.length
      || normalized.some((item, index) => item.id !== parsed[index]?.id || item.timestamp !== parsed[index]?.timestamp);

    if (needsRewrite) {
      persistQueue(normalized);
    }

    return normalized;
  } catch {
    return [];
  }
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

export function clearQueue() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(QUEUE_KEY);
}

export function queueSize() {
  return getQueue().length;
}
