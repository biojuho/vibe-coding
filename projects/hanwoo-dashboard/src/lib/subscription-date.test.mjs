import assert from "node:assert/strict";
import test from "node:test";

import {
	addDays,
	buildCustomerKey,
	buildOrderId,
	normalizePaymentKey,
	normalizePaymentOrderId,
	parseCustomerKeyFromOrderId,
} from "./subscription.js";

test("addDays returns a valid date for valid subscription renewal inputs", () => {
	const nextPaymentDate = addDays(new Date("2026-05-21T00:00:00.000Z"), 30);

	assert.equal(nextPaymentDate.toISOString(), "2026-06-20T00:00:00.000Z");
});

test("addDays falls back safely for malformed subscription renewal inputs", () => {
	const nextPaymentDate = addDays("not-a-date", "not-a-day-count");

	assert.ok(nextPaymentDate instanceof Date);
	assert.equal(Number.isFinite(nextPaymentDate.getTime()), true);
});

test("payment redirect identifiers follow Toss callback limits", () => {
	const customerKey = buildCustomerKey("ck_test_123");
	const orderId = buildOrderId(customerKey, 1799999999999);
	const paymentKey = "pay_" + "a".repeat(196);

	assert.equal(normalizePaymentOrderId(` ${orderId} `), orderId);
	assert.equal(parseCustomerKeyFromOrderId(orderId), customerKey);
	assert.equal(normalizePaymentKey(` ${paymentKey} `), paymentKey);

	assert.equal(normalizePaymentOrderId("abc12"), "");
	assert.equal(normalizePaymentOrderId("a".repeat(65)), "");
	assert.equal(normalizePaymentOrderId("order with space"), "");
	assert.equal(parseCustomerKeyFromOrderId("sub_bad/order_1799999999999"), null);
	assert.equal(normalizePaymentKey(""), "");
	assert.equal(normalizePaymentKey("p".repeat(201)), "");
	assert.equal(normalizePaymentKey("payment key with spaces"), "");
});
