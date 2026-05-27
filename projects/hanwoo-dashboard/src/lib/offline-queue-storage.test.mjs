import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
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
