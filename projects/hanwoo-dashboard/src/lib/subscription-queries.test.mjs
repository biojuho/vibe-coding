import assert from "node:assert/strict";
import test from "node:test";

// Pure logic tests for subscription status resolution — no DB required.
// We test the STATUS RESOLUTION RULES by stubbing the DB result, not the
// actual Prisma queries (those are integration territory).

function resolveSubscriptionStatus(sub) {
	if (!sub) return { status: "INACTIVE", daysLeft: null };

	if (sub.status === "ACTIVE") {
		const daysLeft = sub.nextPaymentDate
			? Math.max(0, Math.ceil((new Date(sub.nextPaymentDate) - new Date()) / 86400000))
			: null;
		return { status: "ACTIVE", daysLeft, nextPaymentDate: sub.nextPaymentDate };
	}

	if (sub.status === "TRIAL" && sub.trialEndDate) {
		const daysLeft = Math.ceil((new Date(sub.trialEndDate) - new Date()) / 86400000);
		if (daysLeft > 0) {
			return { status: "TRIAL", daysLeft, trialEndDate: sub.trialEndDate };
		}
		return { status: "INACTIVE", daysLeft: 0 };
	}

	return { status: "INACTIVE", daysLeft: null };
}

function daysFromNow(n) {
	const d = new Date();
	d.setDate(d.getDate() + n);
	return d;
}

test("no subscription record → INACTIVE", () => {
	assert.deepEqual(resolveSubscriptionStatus(null), { status: "INACTIVE", daysLeft: null });
});

test("ACTIVE subscription → status ACTIVE with daysLeft", () => {
	const result = resolveSubscriptionStatus({
		status: "ACTIVE",
		nextPaymentDate: daysFromNow(15),
		trialEndDate: null,
	});
	assert.equal(result.status, "ACTIVE");
	assert.ok(result.daysLeft >= 14 && result.daysLeft <= 15);
});

test("ACTIVE subscription without nextPaymentDate → daysLeft null", () => {
	const result = resolveSubscriptionStatus({ status: "ACTIVE", nextPaymentDate: null });
	assert.equal(result.status, "ACTIVE");
	assert.equal(result.daysLeft, null);
});

test("TRIAL with 14 days remaining → status TRIAL", () => {
	const result = resolveSubscriptionStatus({
		status: "TRIAL",
		trialEndDate: daysFromNow(14),
	});
	assert.equal(result.status, "TRIAL");
	assert.ok(result.daysLeft >= 13 && result.daysLeft <= 14);
});

test("TRIAL with expired trialEndDate → INACTIVE", () => {
	const result = resolveSubscriptionStatus({
		status: "TRIAL",
		trialEndDate: daysFromNow(-1),
	});
	assert.equal(result.status, "INACTIVE");
	assert.equal(result.daysLeft, 0);
});

test("TRIAL without trialEndDate → INACTIVE", () => {
	const result = resolveSubscriptionStatus({ status: "TRIAL", trialEndDate: null });
	assert.equal(result.status, "INACTIVE");
	assert.equal(result.daysLeft, null);
});

test("INACTIVE subscription record → INACTIVE", () => {
	const result = resolveSubscriptionStatus({ status: "INACTIVE", trialEndDate: null });
	assert.equal(result.status, "INACTIVE");
	assert.equal(result.daysLeft, null);
});
