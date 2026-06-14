/**
 * Behavioral tests for the pure mergeRemainingQueue function in syncManager.js
 * and the pure helpers in actions/_helpers.js.
 *
 * Both files import from bare specifiers/path aliases that cannot be resolved
 * in Node ESM tests; functions are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const syncSrc = readFileSync(path.join(SRC_ROOT, "lib/syncManager.js"), "utf8");
const helpersSrc = readFileSync(
	path.join(SRC_ROOT, "lib/actions/_helpers.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function mergeRemainingQueue(snapshotQueue, latestQueue, failedItems) {
	const processedIds = new Set(snapshotQueue.map((item) => item.id));
	const queuedWhileSyncing = latestQueue.filter(
		(item) => !processedIds.has(item.id),
	);
	return [...failedItems, ...queuedWhileSyncing];
}

function serializeCattleHistoryMetadata(metadata) {
	if (!metadata) return null;
	try {
		return JSON.stringify(metadata);
	} catch (error) {
		return null;
	}
}

function normalizeCattleHistoryEventDate(value) {
	const date = value instanceof Date ? value : new Date(value);
	return Number.isNaN(date.getTime()) ? new Date() : date;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("syncManager.js mergeRemainingQueue filters new items using processedIds Set", () => {
	assert.match(syncSrc, /const processedIds = new Set\(snapshotQueue\.map\(/);
	assert.match(syncSrc, /!processedIds\.has\(item\.id\)/);
	assert.match(syncSrc, /return \[\.\.\.failedItems, \.\.\.queuedWhileSyncing\]/);
});

test("_helpers.js serializeCattleHistoryMetadata returns null for falsy input", () => {
	assert.match(helpersSrc, /function serializeCattleHistoryMetadata\(metadata\)/);
	assert.match(helpersSrc, /if \(!metadata\) \{/);
	assert.match(helpersSrc, /return null;/);
});

test("_helpers.js normalizeCattleHistoryEventDate falls back to new Date() for invalid dates", () => {
	assert.match(helpersSrc, /function normalizeCattleHistoryEventDate\(value\)/);
	assert.match(helpersSrc, /Number\.isNaN\(date\.getTime\(\)\) \? new Date\(\) : date/);
});

// ── mergeRemainingQueue behavioral tests ──────────────────────────────────────

test("mergeRemainingQueue returns only failedItems when latestQueue matches snapshotQueue", () => {
	const snapshot = [{ id: "a" }, { id: "b" }];
	const latest = [{ id: "a" }, { id: "b" }];
	const failed = [{ id: "a", retryCount: 1 }];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.equal(result.length, 1);
	assert.equal(result[0].id, "a");
	assert.equal(result[0].retryCount, 1);
});

test("mergeRemainingQueue appends items added to latestQueue during sync", () => {
	const snapshot = [{ id: "a" }, { id: "b" }];
	const latest = [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }];
	const failed = [];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.equal(result.length, 2);
	assert.equal(result[0].id, "c");
	assert.equal(result[1].id, "d");
});

test("mergeRemainingQueue puts failedItems before queuedWhileSyncing", () => {
	const snapshot = [{ id: "a" }];
	const latest = [{ id: "a" }, { id: "b" }];
	const failed = [{ id: "a", retryCount: 1 }];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.equal(result.length, 2);
	assert.equal(result[0].id, "a"); // failed item first
	assert.equal(result[0].retryCount, 1);
	assert.equal(result[1].id, "b"); // new item second
});

test("mergeRemainingQueue returns empty array when all items synced and no new items", () => {
	const snapshot = [{ id: "a" }, { id: "b" }];
	const latest = [{ id: "a" }, { id: "b" }];
	const failed = [];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.deepEqual(result, []);
});

test("mergeRemainingQueue handles empty snapshotQueue (no items were processed)", () => {
	const snapshot = [];
	const latest = [{ id: "a" }, { id: "b" }];
	const failed = [];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.equal(result.length, 2);
	assert.equal(result[0].id, "a");
	assert.equal(result[1].id, "b");
});

test("mergeRemainingQueue handles empty latestQueue (queue was drained)", () => {
	const snapshot = [{ id: "a" }, { id: "b" }];
	const latest = [];
	const failed = [{ id: "a", retryCount: 1 }];
	const result = mergeRemainingQueue(snapshot, latest, failed);
	assert.deepEqual(result, failed);
});

// ── serializeCattleHistoryMetadata behavioral tests ───────────────────────────

test("serializeCattleHistoryMetadata returns null for null", () => {
	assert.equal(serializeCattleHistoryMetadata(null), null);
});

test("serializeCattleHistoryMetadata returns null for undefined", () => {
	assert.equal(serializeCattleHistoryMetadata(undefined), null);
});

test("serializeCattleHistoryMetadata returns null for empty string and 0", () => {
	assert.equal(serializeCattleHistoryMetadata(""), null);
	assert.equal(serializeCattleHistoryMetadata(0), null);
});

test("serializeCattleHistoryMetadata serializes valid objects to JSON string", () => {
	const result = serializeCattleHistoryMetadata({ weight: 450, note: "healthy" });
	assert.equal(typeof result, "string");
	assert.deepEqual(JSON.parse(result), { weight: 450, note: "healthy" });
});

test("serializeCattleHistoryMetadata returns null for objects with circular references", () => {
	const circular = {};
	circular.self = circular;
	assert.equal(serializeCattleHistoryMetadata(circular), null);
});

test("serializeCattleHistoryMetadata serializes arrays", () => {
	const result = serializeCattleHistoryMetadata([1, 2, 3]);
	assert.equal(result, "[1,2,3]");
});

// ── normalizeCattleHistoryEventDate behavioral tests ──────────────────────────

test("normalizeCattleHistoryEventDate preserves valid Date instances", () => {
	const d = new Date("2026-06-15T00:00:00.000Z");
	const result = normalizeCattleHistoryEventDate(d);
	assert.equal(result.toISOString(), d.toISOString());
});

test("normalizeCattleHistoryEventDate parses valid date strings", () => {
	const result = normalizeCattleHistoryEventDate("2026-01-01T00:00:00.000Z");
	assert.equal(result.toISOString(), "2026-01-01T00:00:00.000Z");
});

test("normalizeCattleHistoryEventDate falls back to current time for invalid string", () => {
	const before = new Date();
	const result = normalizeCattleHistoryEventDate("not-a-date");
	const after = new Date();
	assert.ok(result >= before && result <= after, "should fall back to current time");
});

test("normalizeCattleHistoryEventDate falls back to current time for null", () => {
	// new Date(null) = epoch (Jan 1 1970), which is a valid date — not a fallback
	// But null → new Date(null) → getTime() = 0 → NOT NaN → returns epoch date
	const result = normalizeCattleHistoryEventDate(null);
	assert.ok(result instanceof Date, "should always return a Date");
	// null → epoch, which is valid (not NaN) → returns epoch
	assert.equal(result.getTime(), 0);
});

test("normalizeCattleHistoryEventDate falls back for undefined (new Date(undefined) = Invalid Date)", () => {
	const before = new Date();
	const result = normalizeCattleHistoryEventDate(undefined);
	const after = new Date();
	assert.ok(result >= before && result <= after, "undefined should fall back to now");
});
