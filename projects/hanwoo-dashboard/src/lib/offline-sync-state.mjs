export const MAX_OFFLINE_SYNC_RETRIES = 3;

const PERMANENT_FAILURE_PATTERNS = [
  /validation/i,
  /invalid/i,
  /required/i,
  /missing/i,
  /not found/i,
  /unknown action/i,
  /unsupported/i,
  /유효하지/i,
  /필수/i,
  /찾을 수 없/i,
  /존재하지 않/i,
];

function normalizeTimestamp(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function normalizeRetryCount(value) {
  return Number.isInteger(value) && value > 0 ? value : 0;
}

export function normalizeOfflineQueueMetadata(item = {}) {
  return {
    retryCount: normalizeRetryCount(item.retryCount),
    lastAttemptAt: normalizeTimestamp(item.lastAttemptAt),
    lastError: typeof item.lastError === 'string' && item.lastError.length > 0 ? item.lastError : null,
    deadLetteredAt: normalizeTimestamp(item.deadLetteredAt),
  };
}

export function isPermanentOfflineQueueFailure(message) {
  if (typeof message !== 'string' || message.trim().length === 0) {
    return false;
  }

  return PERMANENT_FAILURE_PATTERNS.some((pattern) => pattern.test(message));
}

export function createFailedQueueItemState(
  item,
  {
    errorMessage = '',
    attemptedAt = Date.now(),
    permanent = false,
    maxRetries = MAX_OFFLINE_SYNC_RETRIES,
  } = {},
) {
  const nextRetryCount = normalizeRetryCount(item?.retryCount) + 1;
  const nextItem = {
    ...item,
    retryCount: nextRetryCount,
    lastAttemptAt: attemptedAt,
    lastError: typeof errorMessage === 'string' && errorMessage.length > 0 ? errorMessage : null,
  };

  if (permanent || nextRetryCount >= maxRetries) {
    return {
      disposition: 'dead-letter',
      item: {
        ...nextItem,
        deadLetteredAt: attemptedAt,
      },
    };
  }

  return {
    disposition: 'retry',
    item: {
      ...nextItem,
      deadLetteredAt: null,
    },
  };
}
