import assert from "node:assert/strict";
import test from "node:test";

import {
	addDays,
	buildCustomerKey,
	buildOrderId,
	normalizePaymentKey,
	normalizePaymentOrderId,
	parseCustomerKeyFromOrderId,
	PREMIUM_SUBSCRIPTION,
	TRIAL_DAYS,
} from "./subscription.js";

// ── PREMIUM_SUBSCRIPTION constants ────────────────────────────────────────────

test("PREMIUM_SUBSCRIPTION.amount is 9900 (KRW)", () => {
	assert.equal(PREMIUM_SUBSCRIPTION.amount, 9900);
});

test("TRIAL_DAYS is 14", () => {
	assert.equal(TRIAL_DAYS, 14);
});

// ── buildCustomerKey ──────────────────────────────────────────────────────────

test("buildCustomerKey prefixes userId with 'user_'", () => {
	assert.equal(buildCustomerKey("abc123"), "user_abc123");
});

test("buildCustomerKey is deterministic for the same userId", () => {
	assert.equal(buildCustomerKey("x"), buildCustomerKey("x"));
});

// ── buildOrderId ──────────────────────────────────────────────────────────────

test("buildOrderId includes the prefix 'sub_' and the customerKey", () => {
	const orderId = buildOrderId("user_abc", 1716700000000);
	assert.ok(orderId.startsWith("sub_user_abc_"), `got: ${orderId}`);
});

test("buildOrderId is unique for different timestamps", () => {
	const a = buildOrderId("user_abc", 1000);
	const b = buildOrderId("user_abc", 2000);
	assert.notEqual(a, b);
});

// ── normalizePaymentOrderId ───────────────────────────────────────────────────

test("normalizePaymentOrderId accepts valid alphanumeric-dash-underscore IDs", () => {
	assert.equal(normalizePaymentOrderId("sub_user_abc_1716700000000"), "sub_user_abc_1716700000000");
	assert.equal(normalizePaymentOrderId("abc123"), "abc123");
	// 6-char minimum: A-B_CD is 6 chars (valid)
	assert.equal(normalizePaymentOrderId("A-B_CD"), "A-B_CD");
});

test("normalizePaymentOrderId trims whitespace before validation", () => {
	assert.equal(normalizePaymentOrderId("  abc123  "), "abc123");
});

test("normalizePaymentOrderId returns empty string for IDs shorter than 6 chars", () => {
	assert.equal(normalizePaymentOrderId("ab"), "");
	assert.equal(normalizePaymentOrderId(""), "");
});

test("normalizePaymentOrderId returns empty string for IDs longer than 64 chars", () => {
	const long = "a".repeat(65);
	assert.equal(normalizePaymentOrderId(long), "");
});

test("normalizePaymentOrderId returns empty string for non-string inputs", () => {
	assert.equal(normalizePaymentOrderId(null), "");
	assert.equal(normalizePaymentOrderId(undefined), "");
	assert.equal(normalizePaymentOrderId(12345), "");
});

test("normalizePaymentOrderId rejects IDs with special characters (spaces, @, etc.)", () => {
	assert.equal(normalizePaymentOrderId("bad id!"), "");
	assert.equal(normalizePaymentOrderId("bad@id"), "");
});

// ── normalizePaymentKey ───────────────────────────────────────────────────────

test("normalizePaymentKey accepts valid payment key strings", () => {
	const key = "paymentKey_abc123";
	assert.equal(normalizePaymentKey(key), key);
});

test("normalizePaymentKey returns empty string for empty or whitespace-only input", () => {
	assert.equal(normalizePaymentKey(""), "");
	assert.equal(normalizePaymentKey("   "), "");
	assert.equal(normalizePaymentKey(null), "");
});

test("normalizePaymentKey rejects keys containing whitespace", () => {
	assert.equal(normalizePaymentKey("key with space"), "");
	assert.equal(normalizePaymentKey("key\twith\ttab"), "");
});

test("normalizePaymentKey returns empty string for keys over 200 chars", () => {
	const long = "k".repeat(201);
	assert.equal(normalizePaymentKey(long), "");
});

// ── parseCustomerKeyFromOrderId ───────────────────────────────────────────────

test("parseCustomerKeyFromOrderId extracts customerKey from a valid orderId", () => {
	const orderId = buildOrderId("user_abc123", 1716700000000);
	const parsed = parseCustomerKeyFromOrderId(orderId);
	assert.equal(parsed, "user_abc123");
});

test("parseCustomerKeyFromOrderId returns null for malformed orderIds", () => {
	assert.equal(parseCustomerKeyFromOrderId("not-an-order-id"), null);
	assert.equal(parseCustomerKeyFromOrderId(""), null);
	assert.equal(parseCustomerKeyFromOrderId(null), null);
});

test("parseCustomerKeyFromOrderId round-trips with buildOrderId + buildCustomerKey", () => {
	const userId = "user-999";
	const customerKey = buildCustomerKey(userId);
	const orderId = buildOrderId(customerKey, 1716700000000);
	assert.equal(parseCustomerKeyFromOrderId(orderId), customerKey);
});

// ── addDays ───────────────────────────────────────────────────────────────────

test("addDays adds the specified number of days to a Date", () => {
	const base = new Date("2026-01-01T00:00:00Z");
	const result = addDays(base, 14);
	assert.equal(result.toISOString().slice(0, 10), "2026-01-15");
});

test("addDays does not mutate the original Date", () => {
	const base = new Date("2026-01-01T00:00:00Z");
	addDays(base, 7);
	assert.equal(base.toISOString().slice(0, 10), "2026-01-01");
});

test("addDays returns a valid date when days=0", () => {
	const base = new Date("2026-06-01");
	const result = addDays(base, 0);
	assert.equal(result.toISOString().slice(0, 10), "2026-06-01");
});

test("addDays accepts timestamp numbers as base date", () => {
	const ts = new Date("2026-01-01T00:00:00Z").getTime();
	const result = addDays(ts, 1);
	assert.equal(result.toISOString().slice(0, 10), "2026-01-02");
});
