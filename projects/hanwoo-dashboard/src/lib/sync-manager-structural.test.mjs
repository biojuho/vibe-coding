/**
 * Source-grep behavioral coverage for syncManager.js
 *
 * syncManager.js imports server actions and offlineQueue — cannot be directly
 * loaded in Node ESM. We assert the critical structural/behavioral contracts
 * via source-grep and re-implement pure helpers inline.
 *
 * Key invariants (CLAUDE.md minefield):
 *   - offlineQueue deadLetter key preserved
 *   - mergeRemainingQueue prevents re-queuing items being processed
 *   - activeSyncPromise deduplicates concurrent calls
 *   - Unsupported action → permanent dead-letter immediately
 *   - Exception during action → retry (non-permanent)
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/syncManager.js"), "utf8");

// ── Source-grep guards ────────────────────────────────────────────────────────

test("syncManager: ACTION_MAP covers all 14 supported offline actions", () => {
	const actions = [
		"createCattle",
		"updateCattle",
		"deleteCattle",
		"recordCalving",
		"createSalesRecord",
		"recordFeed",
		"addInventoryItem",
		"updateInventoryQuantity",
		"createScheduleEvent",
		"toggleEventCompletion",
		"createBuilding",
		"deleteBuilding",
		"updateFarmSettings",
		"createExpenseRecord",
	];
	for (const action of actions) {
		assert.match(src, new RegExp(`${action}:`), `ACTION_MAP missing: ${action}`);
	}
});

test("syncManager: unsupported action is dead-lettered with permanent=true", () => {
	assert.match(src, /if \(!handler\) \{/);
	assert.match(src, /permanent: true/);
	assert.match(src, /deadLetterItems\.push\(failureState\.item\)/);
});

test("syncManager: result.success === false triggers failure path", () => {
	assert.match(src, /result\?\.success === false/);
	assert.match(src, /isPermanentOfflineQueueFailure\(errorMessage\)/);
});

test("syncManager: disposition='dead-letter' routes to deadLetterItems", () => {
	assert.match(src, /failureState\.disposition === ["']dead-letter["']/);
});

test("syncManager: exception path uses OFFLINE_SYNC_RETRY_ERROR_MESSAGE", () => {
	assert.match(src, /const OFFLINE_SYNC_RETRY_ERROR_MESSAGE =/);
	assert.match(src, /\} catch \{/);
	assert.match(src, /const errorMessage = OFFLINE_SYNC_RETRY_ERROR_MESSAGE;/);
});

test("syncManager: mergeRemainingQueue deduplicates using processedIds Set", () => {
	assert.match(src, /function mergeRemainingQueue\(snapshotQueue, latestQueue, failedItems\) \{/);
	assert.match(src, /const processedIds = new Set\(snapshotQueue\.map\(\(item\) => item\.id\)\)/);
	assert.match(src, /\.filter\(\s*\(item\) => !processedIds\.has\(item\.id\)/);
	assert.match(src, /return \[\.\.\.failedItems, \.\.\.queuedWhileSyncing\]/);
});

test("syncManager: activeSyncPromise deduplicates concurrent syncOfflineQueue calls", () => {
	assert.match(src, /let activeSyncPromise = null;/);
	assert.match(src, /if \(activeSyncPromise\) \{/);
	assert.match(src, /activeSyncPromise\.then\(\(result\) => \(\{ \.\.\.result, reused: true \}\)\)/);
	assert.match(src, /reused: false/);
});

test("syncManager: activeSyncPromise is always reset to null in finally", () => {
	assert.match(src, /\} finally \{\s+activeSyncPromise = null;\s+\}/);
});

test("syncManager: deadLetterItems go through appendDeadLetterQueue", () => {
	assert.match(src, /appendDeadLetterQueue\(deadLetterItems\)/);
	assert.match(src, /if \(deadLetterItems\.length > 0\) \{/);
});

test("syncManager: return value shape has synced, failed, deadLettered keys", () => {
	assert.match(src, /return \{\s*synced,\s*failed:/);
	assert.match(src, /deadLettered: deadLetterItems\.length/);
});

test("syncManager: empty queue returns early with 0s", () => {
	assert.match(
		src,
		/if \(queueSnapshot\.length === 0\)\s+return \{ synced: 0, failed: 0, deadLettered: 0 \}/,
	);
});

test("syncManager: args normalized to array before calling handler", () => {
	assert.match(src, /const args = Array\.isArray\(item\.args\) \? item\.args : \[item\.args\]/);
	assert.match(src, /const result = await handler\(args\)/);
});

test("syncManager: uses 3 error message constants with Korean text", () => {
	assert.match(src, /오프라인 요청을 동기화하지 못했습니다/);
	assert.match(src, /지원하지 않는 오프라인 작업입니다/);
	assert.match(src, /오프라인 작업을 서버에 반영하지 못했습니다/);
});

test("syncManager: exports syncOfflineQueue as the only public function", () => {
	assert.match(src, /export async function syncOfflineQueue\(\) \{/);
	const exportCount = (src.match(/^export /gm) ?? []).length;
	assert.equal(exportCount, 1, "syncManager should have exactly 1 export");
});

// ── Inline behavioral test for mergeRemainingQueue ────────────────────────────

function mergeRemainingQueue(snapshotQueue, latestQueue, failedItems) {
	const processedIds = new Set(snapshotQueue.map((item) => item.id));
	const queuedWhileSyncing = latestQueue.filter(
		(item) => !processedIds.has(item.id),
	);
	return [...failedItems, ...queuedWhileSyncing];
}

test("mergeRemainingQueue: excludes snapshot IDs from latestQueue", () => {
	const snapshot = [{ id: "a" }, { id: "b" }];
	const latest = [{ id: "a" }, { id: "b" }, { id: "c" }];
	const failed = [{ id: "a-retry" }];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.deepEqual(
		result.map((i) => i.id),
		["a-retry", "c"],
	);
});

test("mergeRemainingQueue: puts failedItems first (retry before new)", () => {
	const snapshot = [{ id: "x" }];
	const latest = [{ id: "x" }, { id: "new" }];
	const failed = [{ id: "x-fail" }];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.equal(result[0].id, "x-fail");
	assert.equal(result[1].id, "new");
});

test("mergeRemainingQueue: returns just failedItems when no new enqueues", () => {
	const snapshot = [{ id: "a" }];
	const latest = [{ id: "a" }];
	const failed = [{ id: "a-fail" }];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.deepEqual(result.map((i) => i.id), ["a-fail"]);
});

test("mergeRemainingQueue: returns empty array when nothing failed and nothing new", () => {
	const snapshot = [{ id: "a" }];
	const latest = [{ id: "a" }];
	const result = mergeRemainingQueue(snapshot, latest, []);
	assert.deepEqual(result, []);
});

test("mergeRemainingQueue: includes all new items when snapshot is empty", () => {
	const result = mergeRemainingQueue([], [{ id: "x" }, { id: "y" }], []);
	assert.deepEqual(result.map((i) => i.id), ["x", "y"]);
});
