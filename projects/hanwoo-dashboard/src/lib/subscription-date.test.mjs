import assert from "node:assert/strict";
import test from "node:test";

import { addDays } from "./subscription.js";

test("addDays returns a valid date for valid subscription renewal inputs", () => {
	const nextPaymentDate = addDays(new Date("2026-05-21T00:00:00.000Z"), 30);

	assert.equal(nextPaymentDate.toISOString(), "2026-06-20T00:00:00.000Z");
});

test("addDays falls back safely for malformed subscription renewal inputs", () => {
	const nextPaymentDate = addDays("not-a-date", "not-a-day-count");

	assert.ok(nextPaymentDate instanceof Date);
	assert.equal(Number.isFinite(nextPaymentDate.getTime()), true);
});
