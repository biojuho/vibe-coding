import assert from "node:assert/strict";
import test from "node:test";

import { clientIpFromHeaders, SlidingWindowRateLimiter } from "./rate-limit.ts";

test("SlidingWindowRateLimiter allows up to the limit then blocks", () => {
	const now = 1_000_000;
	const limiter = new SlidingWindowRateLimiter({
		limit: 3,
		windowMs: 1000,
		now: () => now,
	});

	assert.equal(limiter.check("ip").allowed, true);
	assert.equal(limiter.check("ip").allowed, true);
	const third = limiter.check("ip");
	assert.equal(third.allowed, true);
	assert.equal(third.remaining, 0);

	const blocked = limiter.check("ip");
	assert.equal(blocked.allowed, false);
	assert.ok(blocked.retryAfterSec >= 1);
});

test("window slides so old hits expire", () => {
	let now = 0;
	const limiter = new SlidingWindowRateLimiter({
		limit: 2,
		windowMs: 1000,
		now: () => now,
	});
	assert.equal(limiter.check("ip").allowed, true);
	assert.equal(limiter.check("ip").allowed, true);
	assert.equal(limiter.check("ip").allowed, false);

	now += 1001; // slide past the window
	assert.equal(limiter.check("ip").allowed, true, "expired hits free budget");
});

test("reset clears a key's budget", () => {
	const now = 0;
	const limiter = new SlidingWindowRateLimiter({
		limit: 1,
		windowMs: 1000,
		now: () => now,
	});
	assert.equal(limiter.check("ip").allowed, true);
	assert.equal(limiter.check("ip").allowed, false);
	limiter.reset("ip");
	assert.equal(limiter.check("ip").allowed, true);
});

test("keys are isolated", () => {
	const now = 0;
	const limiter = new SlidingWindowRateLimiter({
		limit: 1,
		windowMs: 1000,
		now: () => now,
	});
	assert.equal(limiter.check("a").allowed, true);
	assert.equal(limiter.check("b").allowed, true, "different ip unaffected");
});

test("clientIpFromHeaders prefers x-forwarded-for first hop", () => {
	assert.equal(
		clientIpFromHeaders(new Headers({ "x-forwarded-for": "1.1.1.1, 2.2.2.2" })),
		"1.1.1.1",
	);
	assert.equal(
		clientIpFromHeaders(new Headers({ "x-real-ip": "3.3.3.3" })),
		"3.3.3.3",
	);
	assert.equal(clientIpFromHeaders(new Headers()), "unknown");
});
