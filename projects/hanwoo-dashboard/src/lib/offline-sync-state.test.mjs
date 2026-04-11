import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createFailedQueueItemState,
  isPermanentOfflineQueueFailure,
  MAX_OFFLINE_SYNC_RETRIES,
  normalizeOfflineQueueMetadata,
} from './offline-sync-state.mjs';

test('normalizeOfflineQueueMetadata preserves persisted retry fields', () => {
  const result = normalizeOfflineQueueMetadata({
    retryCount: 2,
    lastAttemptAt: 1234,
    lastError: 'network timeout',
    deadLetteredAt: 5678,
  });

  assert.deepEqual(result, {
    retryCount: 2,
    lastAttemptAt: 1234,
    lastError: 'network timeout',
    deadLetteredAt: 5678,
  });
});

test('createFailedQueueItemState keeps retryable failures in the live queue before the cap', () => {
  const result = createFailedQueueItemState(
    { id: 'queue-1', retryCount: 1 },
    { errorMessage: 'network timeout', attemptedAt: 2000 },
  );

  assert.equal(result.disposition, 'retry');
  assert.equal(result.item.retryCount, 2);
  assert.equal(result.item.lastAttemptAt, 2000);
  assert.equal(result.item.lastError, 'network timeout');
  assert.equal(result.item.deadLetteredAt, null);
});

test('createFailedQueueItemState dead-letters items that hit the retry cap', () => {
  const result = createFailedQueueItemState(
    { id: 'queue-2', retryCount: MAX_OFFLINE_SYNC_RETRIES - 1 },
    { errorMessage: 'network timeout', attemptedAt: 3000 },
  );

  assert.equal(result.disposition, 'dead-letter');
  assert.equal(result.item.retryCount, MAX_OFFLINE_SYNC_RETRIES);
  assert.equal(result.item.deadLetteredAt, 3000);
});

test('isPermanentOfflineQueueFailure catches validation-style failures', () => {
  assert.equal(isPermanentOfflineQueueFailure('Validation failed: tagNumber is required.'), true);
  assert.equal(isPermanentOfflineQueueFailure('Request timed out while syncing.'), false);
});

test('createFailedQueueItemState can dead-letter permanent failures immediately', () => {
  const result = createFailedQueueItemState(
    { id: 'queue-3', retryCount: 0 },
    {
      errorMessage: 'Validation failed: invalid payload.',
      attemptedAt: 4000,
      permanent: true,
    },
  );

  assert.equal(result.disposition, 'dead-letter');
  assert.equal(result.item.retryCount, 1);
  assert.equal(result.item.deadLetteredAt, 4000);
});
