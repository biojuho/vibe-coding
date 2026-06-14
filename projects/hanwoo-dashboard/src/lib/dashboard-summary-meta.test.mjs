/**
 * Behavioral tests for toMetaDate and buildMeta in
 * src/app/api/dashboard/summary/route.js.
 *
 * Both functions are module-private (not exported) and the file imports
 * from Next.js / path aliases that can't be resolved in Node ESM. They are
 * re-implemented inline with source-grep guards to catch divergence.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "app/api/dashboard/summary/route.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function toMetaDate(value, fallback = new Date()) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? fallback : date;
}

function buildMeta(snapshot, source) {
	const fallback = new Date();
	const generatedAt = toMetaDate(snapshot.generatedAt, fallback);
	const staleAt = toMetaDate(snapshot.staleAt, fallback);

	return {
		source,
		generatedAt: generatedAt.toISOString(),
		staleAt: staleAt.toISOString(),
		isStale: staleAt <= new Date(),
		ageSeconds: Math.max(
			0,
			Math.floor((Date.now() - generatedAt.getTime()) / 1000),
		),
	};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("route.js toMetaDate copies Date instances via getTime() clone", () => {
	assert.match(
		src,
		/value instanceof Date \? new Date\(value\.getTime\(\)\) : new Date\(value\)/,
	);
	assert.match(src, /return Number\.isNaN\(date\.getTime\(\)\) \? fallback : date;/);
});

test("route.js buildMeta uses Math.max(0,...) for ageSeconds clamping", () => {
	assert.match(src, /Math\.max\(\s*0,/);
	assert.match(src, /Math\.floor\(\(Date\.now\(\) - generatedAt\.getTime\(\)\) \/ 1000\)/);
});

test("route.js buildMeta isStale uses staleAt <= new Date()", () => {
	assert.match(src, /isStale: staleAt <= new Date\(\)/);
});

// ── toMetaDate behavioral tests ───────────────────────────────────────────────

test("toMetaDate copies a valid Date instance (defensive clone)", () => {
	const original = new Date("2026-06-15T12:00:00.000Z");
	const result = toMetaDate(original);
	assert.ok(result instanceof Date);
	assert.equal(result.getTime(), original.getTime());
	assert.ok(result !== original, "should return a clone, not same reference");
});

test("toMetaDate returns fallback for Invalid Date instance", () => {
	const fallback = new Date("2026-06-15T00:00:00.000Z");
	const result = toMetaDate(new Date("invalid"), fallback);
	assert.equal(result, fallback);
});

test("toMetaDate parses a valid ISO date string", () => {
	const result = toMetaDate("2026-06-15T12:00:00.000Z");
	assert.ok(result instanceof Date);
	assert.equal(result.toISOString(), "2026-06-15T12:00:00.000Z");
});

test("toMetaDate returns fallback for an invalid date string", () => {
	const fallback = new Date("2026-01-01T00:00:00.000Z");
	const result = toMetaDate("not-a-date", fallback);
	assert.equal(result, fallback);
});

test("toMetaDate returns fallback for undefined (new Date(undefined) = Invalid Date)", () => {
	const fallback = new Date("2026-06-15T00:00:00.000Z");
	const result = toMetaDate(undefined, fallback);
	assert.equal(result, fallback);
});

test("toMetaDate returns epoch (not fallback) for null — new Date(null) = epoch", () => {
	// new Date(null) = Jan 1 1970 00:00:00 UTC (time = 0), which is NOT NaN
	const fallback = new Date("2026-06-15T00:00:00.000Z");
	const result = toMetaDate(null, fallback);
	assert.ok(result instanceof Date);
	assert.equal(result.getTime(), 0, "null → epoch, not fallback");
});

test("toMetaDate default fallback is near current time", () => {
	const before = new Date();
	const result = toMetaDate("invalid-date");
	const after = new Date();
	assert.ok(result >= before && result <= after, "default fallback should be now");
});

// ── buildMeta behavioral tests ────────────────────────────────────────────────

test("buildMeta returns correct source field", () => {
	const snapshot = {
		generatedAt: new Date(Date.now() - 30000).toISOString(),
		staleAt: new Date(Date.now() + 300000).toISOString(),
	};
	const meta = buildMeta(snapshot, "snapshot");
	assert.equal(meta.source, "snapshot");
});

test("buildMeta generatedAt and staleAt are ISO strings", () => {
	const snapshot = {
		generatedAt: new Date(Date.now() - 30000).toISOString(),
		staleAt: new Date(Date.now() + 300000).toISOString(),
	};
	const meta = buildMeta(snapshot, "rebuilt");
	assert.ok(typeof meta.generatedAt === "string");
	assert.ok(typeof meta.staleAt === "string");
	assert.ok(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(meta.generatedAt));
	assert.ok(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(meta.staleAt));
});

test("buildMeta isStale=true when staleAt is in the past", () => {
	const snapshot = {
		generatedAt: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
		staleAt: new Date(Date.now() - 1800000).toISOString(), // 30 min ago
	};
	const meta = buildMeta(snapshot, "snapshot");
	assert.equal(meta.isStale, true);
});

test("buildMeta isStale=false when staleAt is in the future", () => {
	const snapshot = {
		generatedAt: new Date(Date.now() - 30000).toISOString(), // 30 sec ago
		staleAt: new Date(Date.now() + 3600000).toISOString(), // 1 hour from now
	};
	const meta = buildMeta(snapshot, "snapshot");
	assert.equal(meta.isStale, false);
});

test("buildMeta ageSeconds is approximately correct (within ±3 seconds)", () => {
	const GENERATED_AGE_MS = 60000; // 60 seconds ago
	const snapshot = {
		generatedAt: new Date(Date.now() - GENERATED_AGE_MS).toISOString(),
		staleAt: new Date(Date.now() + 300000).toISOString(),
	};
	const meta = buildMeta(snapshot, "snapshot");
	assert.ok(
		meta.ageSeconds >= 59 && meta.ageSeconds <= 63,
		`ageSeconds=${meta.ageSeconds} should be ~60`,
	);
});

test("buildMeta ageSeconds is 0 for future generatedAt (Math.max clamp)", () => {
	const snapshot = {
		generatedAt: new Date(Date.now() + 10000).toISOString(), // 10 sec in future
		staleAt: new Date(Date.now() + 300000).toISOString(),
	};
	const meta = buildMeta(snapshot, "snapshot");
	assert.equal(meta.ageSeconds, 0, "future generatedAt should clamp to 0");
});

test("buildMeta falls back for invalid snapshot.generatedAt string", () => {
	const snapshot = {
		generatedAt: "bad-date",
		staleAt: new Date(Date.now() + 300000).toISOString(),
	};
	// Should not throw — toMetaDate falls back to new Date()
	const before = new Date();
	const meta = buildMeta(snapshot, "snapshot");
	const after = new Date();
	const generatedAtDate = new Date(meta.generatedAt);
	assert.ok(
		generatedAtDate >= before && generatedAtDate <= after,
		"invalid generatedAt should fall back to now",
	);
	// ageSeconds should be 0 or 1 since fallback is "now"
	assert.ok(meta.ageSeconds <= 2, "ageSeconds should be near 0 when generatedAt falls back to now");
});

test("buildMeta falls back for invalid snapshot.staleAt string", () => {
	const snapshot = {
		generatedAt: new Date(Date.now() - 30000).toISOString(),
		staleAt: "bad-date",
	};
	// Should not throw — toMetaDate falls back to new Date()
	const meta = buildMeta(snapshot, "snapshot");
	// staleAt fallback is "now", so isStale should be true (fallback <= new Date())
	assert.equal(meta.isStale, true, "invalid staleAt falls back to now, making it immediately stale");
});
