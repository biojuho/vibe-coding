import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
	enqueue,
	getDeadLetterQueue,
	getQueue,
	queueSize,
	setDeadLetterQueue,
	setQueue,
} from "./offlineQueue.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

function withBrowserStorage(callback) {
	const originalWindow = globalThis.window;
	const originalLocalStorage = globalThis.localStorage;
	const store = new Map();
	const localStorage = {
		getItem: (key) => (store.has(key) ? store.get(key) : null),
		removeItem: (key) => {
			store.delete(key);
		},
		setItem: (key, value) => {
			store.set(key, String(value));
		},
	};

	globalThis.window = {};
	globalThis.localStorage = localStorage;

	try {
		return callback({ store });
	} finally {
		if (typeof originalWindow === "undefined") {
			delete globalThis.window;
		} else {
			globalThis.window = originalWindow;
		}

		if (typeof originalLocalStorage === "undefined") {
			delete globalThis.localStorage;
		} else {
			globalThis.localStorage = originalLocalStorage;
		}
	}
}

test("offline queue persistence tolerates restricted browser storage", () => {
	const source = readSource("lib/offlineQueue.js");

	assert.match(source, /function persistQueueList\(key, queue\) \{/);
	assert.match(
		source,
		/try \{\s+if \(!Array\.isArray\(queue\) \|\| queue\.length === 0\) \{\s+localStorage\.removeItem\(key\);\s+return;\s+\}\s+localStorage\.setItem\(key, JSON\.stringify\(queue\)\);\s+\} catch \{/,
	);
	assert.match(
		source,
		/Best-effort persistence: restricted storage should not break the UI flow\./,
	);
});

test("offline queue clearing tolerates restricted browser storage", () => {
	const source = readSource("lib/offlineQueue.js");

	assert.match(
		source,
		/export function clearQueue\(\) \{\s+if \(typeof window === "undefined"\) return;\s+try \{\s+localStorage\.removeItem\(QUEUE_KEY\);\s+\} catch \{\}\s+\}/,
	);
	assert.match(
		source,
		/export function clearDeadLetterQueue\(\) \{\s+if \(typeof window === "undefined"\) return;\s+try \{\s+localStorage\.removeItem\(DEAD_LETTER_KEY\);\s+\} catch \{\}\s+\}/,
	);
});

test("offline queue rewrites non-finite persisted timestamps", () => {
	withBrowserStorage(({ store }) => {
		const before = Date.now();
		store.set(
			"joolife-offline-queue",
			'[{"id":"queued-1","action":"createCattle","timestamp":1e999}]',
		);

		const [item] = getQueue();

		assert.equal(item.id, "queued-1");
		assert.equal(item.action, "createCattle");
		assert.equal(Number.isFinite(item.timestamp), true);
		assert.ok(item.timestamp >= before);
		assert.doesNotMatch(store.get("joolife-offline-queue"), /1e999/);
	});
});

test("enqueue adds an item and queueSize reflects the count", () => {
	withBrowserStorage(() => {
		// Start from empty
		setQueue([]);
		assert.equal(queueSize(), 0);

		enqueue("createCattle", { name: "테스트" });
		assert.equal(queueSize(), 1);

		enqueue("updateCattle", { id: "c-1", weight: 400 });
		assert.equal(queueSize(), 2);

		const queue = getQueue();
		assert.equal(queue[0].action, "createCattle");
		assert.deepEqual(queue[0].args, { name: "테스트" });
	});
});

test("getQueue returns [] for corrupted JSON in storage", () => {
	withBrowserStorage(({ store }) => {
		store.set("joolife-offline-queue", "not-valid-json{{");
		const queue = getQueue();
		assert.deepEqual(queue, []);
	});
});

test("getDeadLetterQueue returns [] when no dead letters exist", () => {
	withBrowserStorage(() => {
		setDeadLetterQueue([]);
		const dead = getDeadLetterQueue();
		assert.deepEqual(dead, []);
	});
});

test("setDeadLetterQueue persists items and getDeadLetterQueue reads them back", () => {
	withBrowserStorage(() => {
		const items = [
			{ id: "d-1", action: "createCattle", args: {}, timestamp: Date.now(), retryCount: 3 },
		];
		setDeadLetterQueue(items);
		const dead = getDeadLetterQueue();
		assert.equal(dead.length, 1);
		assert.equal(dead[0].action, "createCattle");
	});
});
