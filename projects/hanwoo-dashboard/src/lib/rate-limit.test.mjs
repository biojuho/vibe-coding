import assert from "node:assert/strict";
import test from "node:test";

const MODULE_PATH = new URL("./rate-limit.mjs", import.meta.url).href;

async function freshModule() {
	const rand = Math.random().toString(36).slice(2);
	return import(`${MODULE_PATH}?t=${rand}`);
}

test("checkRateLimit allows first request and tracks remaining", async () => {
	const { checkRateLimit } = await freshModule();
	const result = checkRateLimit("test-ip-1", { maxRequests: 3, windowMs: 60000 });
	assert.equal(result.allowed, true);
	assert.equal(result.remaining, 2);
});

test("checkRateLimit blocks after maxRequests exceeded", async () => {
	const { checkRateLimit } = await freshModule();
	const key = "test-ip-2";
	const opts = { maxRequests: 3, windowMs: 60000 };
	checkRateLimit(key, opts);
	checkRateLimit(key, opts);
	checkRateLimit(key, opts);
	const blocked = checkRateLimit(key, opts);
	assert.equal(blocked.allowed, false);
	assert.equal(blocked.remaining, 0);
	assert.ok(typeof blocked.retryAfterSeconds === "number" && blocked.retryAfterSeconds > 0);
});

test("checkRateLimit uses separate buckets per key", async () => {
	const { checkRateLimit } = await freshModule();
	const opts = { maxRequests: 2, windowMs: 60000 };
	checkRateLimit("key-a", opts);
	checkRateLimit("key-a", opts);
	const blockedA = checkRateLimit("key-a", opts);
	assert.equal(blockedA.allowed, false);

	const allowedB = checkRateLimit("key-b", opts);
	assert.equal(allowedB.allowed, true);
});

test("checkRateLimit resets after window expires", async () => {
	const { checkRateLimit } = await freshModule();
	const key = "test-ip-reset";
	const opts = { maxRequests: 1, windowMs: 1 };
	checkRateLimit(key, opts);
	const blocked = checkRateLimit(key, opts);
	assert.equal(blocked.allowed, false);
	await new Promise((resolve) => setTimeout(resolve, 10));
	const allowed = checkRateLimit(key, opts);
	assert.equal(allowed.allowed, true);
});

test("checkRateLimit: last allowed call has remaining=0 (still allowed)", async () => {
	const { checkRateLimit } = await freshModule();
	const key = "test-boundary";
	const opts = { maxRequests: 3, windowMs: 60000 };
	checkRateLimit(key, opts); // remaining=2
	checkRateLimit(key, opts); // remaining=1
	const last = checkRateLimit(key, opts); // remaining=0, still allowed
	assert.equal(last.allowed, true);
	assert.equal(last.remaining, 0);
	// next call is the first denied one
	const denied = checkRateLimit(key, opts);
	assert.equal(denied.allowed, false);
	assert.equal(denied.remaining, 0);
});

test("checkRateLimit: denied calls are idempotent (count does not keep incrementing)", async () => {
	const { checkRateLimit } = await freshModule();
	const key = "test-idempotent";
	const opts = { maxRequests: 2, windowMs: 60000 };
	checkRateLimit(key, opts);
	checkRateLimit(key, opts);
	// all further calls should be denied with the same retryAfterSeconds (not growing)
	const d1 = checkRateLimit(key, opts);
	const d2 = checkRateLimit(key, opts);
	assert.equal(d1.allowed, false);
	assert.equal(d2.allowed, false);
	// retryAfterSeconds should decrease or stay equal (never grow beyond the original window)
	assert.ok(d2.retryAfterSeconds <= d1.retryAfterSeconds + 1);
});

test("checkRateLimit: default maxRequests=5 (no options)", async () => {
	const { checkRateLimit } = await freshModule();
	const key = "test-defaults";
	// 5 allowed
	for (let i = 0; i < 5; i++) {
		assert.equal(checkRateLimit(key).allowed, true);
	}
	// 6th denied
	assert.equal(checkRateLimit(key).allowed, false);
});

test("checkRateLimit: retryAfterSeconds is at most ceil(windowMs/1000)", async () => {
	const { checkRateLimit } = await freshModule();
	const key = "test-retry";
	const windowMs = 5000;
	checkRateLimit(key, { maxRequests: 1, windowMs });
	const denied = checkRateLimit(key, { maxRequests: 1, windowMs });
	assert.ok(denied.retryAfterSeconds <= Math.ceil(windowMs / 1000));
});
