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
