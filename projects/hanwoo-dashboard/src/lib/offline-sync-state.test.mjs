import assert from "node:assert/strict";
import test from "node:test";

import {
	createFailedQueueItemState,
	isPermanentOfflineQueueFailure,
	MAX_OFFLINE_SYNC_RETRIES,
	normalizeOfflineQueueMetadata,
} from "./offline-sync-state.mjs";

test("normalizeOfflineQueueMetadata preserves persisted retry fields", () => {
	const result = normalizeOfflineQueueMetadata({
		retryCount: 2,
		lastAttemptAt: 1234,
		lastError: "network timeout",
		deadLetteredAt: 5678,
	});

	assert.deepEqual(result, {
		retryCount: 2,
		lastAttemptAt: 1234,
		lastError: "network timeout",
		deadLetteredAt: 5678,
	});
});

test("normalizeOfflineQueueMetadata ignores malformed queue items", () => {
	const result = normalizeOfflineQueueMetadata(null);

	assert.deepEqual(result, {
		retryCount: 0,
		lastAttemptAt: null,
		lastError: null,
		deadLetteredAt: null,
	});
});

test("createFailedQueueItemState keeps retryable failures in the live queue before the cap", () => {
	const result = createFailedQueueItemState(
		{ id: "queue-1", retryCount: 1 },
		{ errorMessage: "network timeout", attemptedAt: 2000 },
	);

	assert.equal(result.disposition, "retry");
	assert.equal(result.item.retryCount, 2);
	assert.equal(result.item.lastAttemptAt, 2000);
	assert.equal(result.item.lastError, "network timeout");
	assert.equal(result.item.deadLetteredAt, null);
});

test("createFailedQueueItemState ignores malformed item and options input", () => {
	const result = createFailedQueueItemState(null, null);

	assert.equal(result.disposition, "retry");
	assert.equal(result.item.retryCount, 1);
	assert.equal(result.item.lastError, null);
	assert.equal(result.item.deadLetteredAt, null);
	assert.equal(typeof result.item.lastAttemptAt, "number");
});

test("offline queue failure state ignores array item and option fields", () => {
	const item = [];
	item.retryCount = 2;
	const options = [];
	options.errorMessage = "array error should be ignored";
	options.attemptedAt = 1234;
	options.permanent = true;

	const metadata = normalizeOfflineQueueMetadata(item);
	const result = createFailedQueueItemState(item, options);

	assert.deepEqual(metadata, {
		retryCount: 0,
		lastAttemptAt: null,
		lastError: null,
		deadLetteredAt: null,
	});
	assert.equal(result.disposition, "retry");
	assert.equal(result.item.retryCount, 1);
	assert.equal(result.item.lastError, null);
	assert.equal(result.item.deadLetteredAt, null);
	assert.notEqual(result.item.lastAttemptAt, 1234);
});

test("createFailedQueueItemState dead-letters items that hit the retry cap", () => {
	const result = createFailedQueueItemState(
		{ id: "queue-2", retryCount: MAX_OFFLINE_SYNC_RETRIES - 1 },
		{ errorMessage: "network timeout", attemptedAt: 3000 },
	);

	assert.equal(result.disposition, "dead-letter");
	assert.equal(result.item.retryCount, MAX_OFFLINE_SYNC_RETRIES);
	assert.equal(result.item.deadLetteredAt, 3000);
});

test("isPermanentOfflineQueueFailure catches validation-style failures", () => {
	assert.equal(
		isPermanentOfflineQueueFailure("Validation failed: tagNumber is required."),
		true,
	);
	assert.equal(
		isPermanentOfflineQueueFailure("Request timed out while syncing."),
		false,
	);
});

test("createFailedQueueItemState can dead-letter permanent failures immediately", () => {
	const result = createFailedQueueItemState(
		{ id: "queue-3", retryCount: 0 },
		{
			errorMessage: "Validation failed: invalid payload.",
			attemptedAt: 4000,
			permanent: true,
		},
	);

	assert.equal(result.disposition, "dead-letter");
	assert.equal(result.item.retryCount, 1);
	assert.equal(result.item.deadLetteredAt, 4000);
});

test("isPermanentOfflineQueueFailure catches Korean permanent failure messages", () => {
	assert.equal(isPermanentOfflineQueueFailure("유효하지 않은 이표번호입니다"), true);
	assert.equal(isPermanentOfflineQueueFailure("필수 항목이 빠졌습니다"), true);
	assert.equal(isPermanentOfflineQueueFailure("개체를 찾을 수 없습니다"), true);
	assert.equal(isPermanentOfflineQueueFailure("존재하지 않는 농장입니다"), true);
});

test("isPermanentOfflineQueueFailure returns false for non-string and empty inputs", () => {
	assert.equal(isPermanentOfflineQueueFailure(null), false);
	assert.equal(isPermanentOfflineQueueFailure(undefined), false);
	assert.equal(isPermanentOfflineQueueFailure(""), false);
	assert.equal(isPermanentOfflineQueueFailure("   "), false);
	assert.equal(isPermanentOfflineQueueFailure(42), false);
});

test("createFailedQueueItemState respects custom maxRetries option", () => {
	const result = createFailedQueueItemState(
		{ id: "queue-4", retryCount: 1 },
		{ errorMessage: "timeout", attemptedAt: 5000, maxRetries: 2 },
	);
	assert.equal(result.disposition, "dead-letter");
	assert.equal(result.item.retryCount, 2);
	assert.equal(result.item.deadLetteredAt, 5000);
});

test("normalizeOfflineQueueMetadata treats negative retryCount as 0", () => {
	const result = normalizeOfflineQueueMetadata({ retryCount: -1, lastAttemptAt: 1000 });
	assert.equal(result.retryCount, 0);
	assert.equal(result.lastAttemptAt, 1000);
});

test("normalizeOfflineQueueMetadata treats float retryCount as 0", () => {
	const result = normalizeOfflineQueueMetadata({ retryCount: 1.5 });
	assert.equal(result.retryCount, 0);
});
