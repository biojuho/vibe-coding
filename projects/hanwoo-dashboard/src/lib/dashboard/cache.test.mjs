import assert from "node:assert/strict";
import test from "node:test";
import {
	buildCattleListKey,
	buildSalesListKey,
	deleteCachedKeys,
	deleteCachedKeysByPrefixes,
} from "./cache.js";

function withoutRedisConfiguration(callback) {
	const originalRedisUrl = process.env.REDIS_URL;
	const originalBullmqRedisUrl = process.env.BULLMQ_REDIS_URL;

	delete process.env.REDIS_URL;
	delete process.env.BULLMQ_REDIS_URL;

	try {
		return callback();
	} finally {
		if (typeof originalRedisUrl === "undefined") {
			delete process.env.REDIS_URL;
		} else {
			process.env.REDIS_URL = originalRedisUrl;
		}

		if (typeof originalBullmqRedisUrl === "undefined") {
			delete process.env.BULLMQ_REDIS_URL;
		} else {
			process.env.BULLMQ_REDIS_URL = originalBullmqRedisUrl;
		}
	}
}

test("dashboard list cache keys tolerate malformed filter objects", () => {
	assert.equal(
		buildCattleListKey(null),
		"dashboard:cattle:list:v1:default:all:all:all:all:50",
	);
	assert.equal(
		buildSalesListKey(null),
		"dashboard:sales:v1:default:all:all:start:50",
	);
});

test("dashboard cache delete helpers tolerate malformed key lists", async () => {
	await withoutRedisConfiguration(async () => {
		assert.equal(await deleteCachedKeys(null), 0);
		assert.equal(await deleteCachedKeysByPrefixes(null), 0);
	});
});
