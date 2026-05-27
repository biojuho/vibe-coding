import assert from "node:assert/strict";
import test from "node:test";
import { enqueueJob, getQueue, getQueueEvents } from "./queue.js";

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

test("BullMQ helpers ignore malformed options before configuration checks", async () => {
	await withoutRedisConfiguration(async () => {
		assert.throws(
			() => getQueue("dashboard.cache.warm", null),
			/REDIS_URL \(or BULLMQ_REDIS_URL\) is required/,
		);
		assert.throws(
			() => getQueueEvents("dashboard.cache.warm", null),
			/REDIS_URL \(or BULLMQ_REDIS_URL\) is required/,
		);
		await assert.rejects(
			() => enqueueJob("dashboard.cache.warm", { farmId: "farm-1" }, null),
			/REDIS_URL \(or BULLMQ_REDIS_URL\) is required/,
		);
	});
});
