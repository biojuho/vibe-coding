/**
 * Behavioral tests for isFreshNotificationSummary in actions/notification.js.
 *
 * The file uses "use server" and imports from path aliases, so it can't be
 * loaded in Node ESM. The function is re-implemented inline and cross-checked
 * via source-grep so production code and tests cannot silently diverge.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(
	path.join(SRC_ROOT, "lib/actions/notification.js"),
	"utf8",
);

// ── Inline re-implementation ───────────────────────────────────────────────────

const NOTIFICATION_FRESH_TTL_MS = 60 * 1000; // 1 minute

function isFreshNotificationSummary(summary, now = Date.now()) {
	if (!summary?.payload || !summary.generatedAt) {
		return false;
	}
	const generatedAt = new Date(summary.generatedAt);
	const age = now - generatedAt.getTime();
	return Number.isFinite(age) && age >= 0 && age < NOTIFICATION_FRESH_TTL_MS;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("notification.js isFreshNotificationSummary guards against missing payload/generatedAt", () => {
	assert.match(src, /function isFreshNotificationSummary\(summary, now = Date\.now\(\)\)/);
	assert.match(src, /if \(!summary\?\.payload \|\| !summary\.generatedAt\)/);
});

test("notification.js isFreshNotificationSummary uses Number.isFinite age guard", () => {
	assert.match(src, /const age = now - generatedAt\.getTime\(\);/);
	assert.match(src, /return Number\.isFinite\(age\) && age >= 0 && age < 60 \* 1000;/);
});

// ── isFreshNotificationSummary behavioral tests ───────────────────────────────

// Reference "now" for deterministic testing
const NOW_MS = new Date("2026-06-15T12:00:00.000Z").getTime();

test("isFreshNotificationSummary returns false for null summary", () => {
	assert.equal(isFreshNotificationSummary(null, NOW_MS), false);
});

test("isFreshNotificationSummary returns false for undefined summary", () => {
	assert.equal(isFreshNotificationSummary(undefined, NOW_MS), false);
});

test("isFreshNotificationSummary returns false for summary missing payload", () => {
	assert.equal(
		isFreshNotificationSummary(
			{ generatedAt: new Date(NOW_MS - 1000).toISOString() },
			NOW_MS,
		),
		false,
	);
});

test("isFreshNotificationSummary returns false for summary missing generatedAt", () => {
	assert.equal(
		isFreshNotificationSummary({ payload: [] }, NOW_MS),
		false,
	);
});

test("isFreshNotificationSummary returns true for summary generated 1 second ago", () => {
	const generatedAt = new Date(NOW_MS - 1000).toISOString();
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt }, NOW_MS),
		true,
	);
});

test("isFreshNotificationSummary returns true for summary generated 59 seconds ago (just inside TTL)", () => {
	const generatedAt = new Date(NOW_MS - 59000).toISOString();
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt }, NOW_MS),
		true,
	);
});

test("isFreshNotificationSummary returns false for summary at exactly 60 seconds (TTL boundary)", () => {
	const generatedAt = new Date(NOW_MS - 60000).toISOString();
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt }, NOW_MS),
		false,
	);
});

test("isFreshNotificationSummary returns false for summary generated 5 minutes ago", () => {
	const generatedAt = new Date(NOW_MS - 5 * 60 * 1000).toISOString();
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt }, NOW_MS),
		false,
	);
});

test("isFreshNotificationSummary returns false for future generatedAt (age < 0)", () => {
	const generatedAt = new Date(NOW_MS + 5000).toISOString();
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt }, NOW_MS),
		false,
	);
});

test("isFreshNotificationSummary returns false for invalid generatedAt string (NaN age)", () => {
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt: "not-a-date" }, NOW_MS),
		false,
	);
});

test("isFreshNotificationSummary treats non-empty payload array as truthy", () => {
	const generatedAt = new Date(NOW_MS - 5000).toISOString();
	const notifications = [{ id: "estrus-1", type: "estrus" }];
	assert.equal(
		isFreshNotificationSummary({ payload: notifications, generatedAt }, NOW_MS),
		true,
	);
});

test("isFreshNotificationSummary treats empty array payload as truthy (array is always truthy in JS)", () => {
	const generatedAt = new Date(NOW_MS - 5000).toISOString();
	assert.equal(
		isFreshNotificationSummary({ payload: [], generatedAt }, NOW_MS),
		true,
	);
});
