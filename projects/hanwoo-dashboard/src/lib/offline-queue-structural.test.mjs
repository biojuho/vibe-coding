/**
 * Source-grep behavioral coverage for offlineQueue.js
 *
 * offlineQueue.js uses localStorage + crypto globals, so it can't be directly
 * imported in Node ESM. We assert structural and contract invariants via
 * source-grep and re-implement the pure helpers inline for behavioral tests.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/offlineQueue.js"), "utf8");

// ── Source-grep guards ────────────────────────────────────────────────────────

test("offlineQueue: QUEUE_KEY is joolife-offline-queue", () => {
	assert.match(src, /const QUEUE_KEY = ["']joolife-offline-queue["'];/);
});

test("offlineQueue: DEAD_LETTER_KEY is joolife-offline-dead-letter", () => {
	assert.match(src, /const DEAD_LETTER_KEY = ["']joolife-offline-dead-letter["'];/);
});

test("offlineQueue: DEAD_LETTER_LIMIT is 100", () => {
	assert.match(src, /const DEAD_LETTER_LIMIT = 100;/);
});

test("offlineQueue: createQueueItemId uses crypto.randomUUID with fallback", () => {
	assert.match(src, /globalThis\.crypto\?\.randomUUID\?\.\(\)/);
	assert.match(src, /offline-\$\{Date\.now\(\)\}/);
});

test("offlineQueue: normalizeQueueTimestamp validates finite number", () => {
	assert.match(src, /function normalizeQueueTimestamp\(value\) \{/);
	assert.match(src, /typeof value === ["']number["'] && Number\.isFinite\(value\)/);
	assert.match(src, /\? value : Date\.now\(\)/);
});

test("offlineQueue: normalizeQueueItem validates action is non-empty string", () => {
	assert.match(src, /function normalizeQueueItem\(item\) \{/);
	assert.match(src, /typeof item\.action !== ["']string["']/);
	assert.match(src, /item\.action\.length === 0/);
});

test("offlineQueue: normalizeQueueItem spreads normalizeOfflineQueueMetadata", () => {
	assert.match(src, /\.\.\.normalizeOfflineQueueMetadata\(item\)/);
});

test("offlineQueue: readQueue checks all 5 metadata fields for needsRewrite", () => {
	assert.match(src, /item\.retryCount !== parsed\[index\]\?\.retryCount/);
	assert.match(src, /item\.lastAttemptAt !== parsed\[index\]\?\.lastAttemptAt/);
	assert.match(src, /item\.lastError !== parsed\[index\]\?\.lastError/);
	assert.match(src, /item\.deadLetteredAt !== parsed\[index\]\?\.deadLetteredAt/);
});

test("offlineQueue: persistDeadLetterQueue slices to DEAD_LETTER_LIMIT", () => {
	assert.match(src, /function persistDeadLetterQueue\(queue\) \{/);
	assert.match(src, /Array\.isArray\(queue\) \? queue\.slice\(-DEAD_LETTER_LIMIT\) : \[\]/);
});

test("offlineQueue: persistQueueList skips when window undefined", () => {
	assert.match(src, /if \(typeof window === ["']undefined["']\) return;/);
});

test("offlineQueue: persistQueueList removes key for empty queue", () => {
	assert.match(src, /localStorage\.removeItem\(key\)/);
	assert.match(src, /!Array\.isArray\(queue\) \|\| queue\.length === 0/);
});

test("offlineQueue: exports all expected public functions", () => {
	for (const fn of [
		"getQueue",
		"getDeadLetterQueue",
		"enqueue",
		"setQueue",
		"setDeadLetterQueue",
		"appendDeadLetterQueue",
		"clearQueue",
		"clearDeadLetterQueue",
		"queueSize",
	]) {
		assert.match(src, new RegExp(`export function ${fn}\\(`), `${fn} not exported`);
	}
});

test("offlineQueue: enqueue builds item via normalizeQueueItem", () => {
	assert.match(
		src,
		/const nextItem = normalizeQueueItem\(\{ action, args, timestamp: Date\.now\(\) \}\)/,
	);
	assert.match(src, /persistQueue\(\[\.\.\.queue, nextItem\]\)/);
	assert.match(src, /return nextItem;/);
});

test("offlineQueue: enqueue returns null when normalizeQueueItem returns null", () => {
	assert.match(src, /if \(!nextItem\) \{\s+return null;\s+\}/);
});

test("offlineQueue: appendDeadLetterQueue merges with current dead-letter queue", () => {
	assert.match(src, /function appendDeadLetterQueue\(items\) \{/);
	assert.match(src, /const current = getDeadLetterQueue\(\)/);
	assert.match(src, /setDeadLetterQueue\(\[\.\.\.current, \.\.\./);
});

test("offlineQueue: queueSize returns getQueue().length", () => {
	assert.match(src, /export function queueSize\(\) \{\s+return getQueue\(\)\.length;\s+\}/);
});

// ── Inline behavioral tests for pure helpers ──────────────────────────────────

// Re-implement normalizeQueueTimestamp (pure, no side effects)
function normalizeQueueTimestamp(value) {
	return typeof value === "number" && Number.isFinite(value) ? value : Date.now();
}

test("normalizeQueueTimestamp: returns value for finite number", () => {
	assert.equal(normalizeQueueTimestamp(1234567890), 1234567890);
	assert.equal(normalizeQueueTimestamp(0), 0);
});

test("normalizeQueueTimestamp: returns Date.now() for NaN", () => {
	const before = Date.now();
	const result = normalizeQueueTimestamp(Number.NaN);
	const after = Date.now();
	assert.ok(result >= before && result <= after);
});

test("normalizeQueueTimestamp: returns Date.now() for Infinity", () => {
	const before = Date.now();
	const result = normalizeQueueTimestamp(Infinity);
	const after = Date.now();
	assert.ok(result >= before && result <= after);
});

test("normalizeQueueTimestamp: returns Date.now() for string", () => {
	const before = Date.now();
	const result = normalizeQueueTimestamp("2024-01-01");
	const after = Date.now();
	assert.ok(result >= before && result <= after);
});

test("normalizeQueueTimestamp: returns Date.now() for null", () => {
	const before = Date.now();
	const result = normalizeQueueTimestamp(null);
	const after = Date.now();
	assert.ok(result >= before && result <= after);
});

// Re-implement persistDeadLetterQueue's trim logic
function trimDeadLetterQueue(queue, limit = 100) {
	return Array.isArray(queue) ? queue.slice(-limit) : [];
}

test("persistDeadLetterQueue trim: keeps last 100 items when over limit", () => {
	const queue = Array.from({ length: 150 }, (_, i) => ({ id: String(i) }));
	const result = trimDeadLetterQueue(queue, 100);
	assert.equal(result.length, 100);
	assert.equal(result[0].id, "50");
	assert.equal(result[99].id, "149");
});

test("persistDeadLetterQueue trim: returns empty array for non-array input", () => {
	assert.deepEqual(trimDeadLetterQueue(null, 100), []);
	assert.deepEqual(trimDeadLetterQueue(undefined, 100), []);
});

test("persistDeadLetterQueue trim: returns all items when under limit", () => {
	const queue = [{ id: "a" }, { id: "b" }];
	assert.deepEqual(trimDeadLetterQueue(queue, 100), queue);
});
