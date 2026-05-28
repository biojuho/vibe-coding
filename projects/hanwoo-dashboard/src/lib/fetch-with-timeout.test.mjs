import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { fetchWithTimeout } from "./fetchWithTimeout.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("fetchWithTimeout guards timeout scheduling and cleanup", () => {
	const source = readSource("lib/fetchWithTimeout.js");

	assert.match(source, /function normalizeOptions\(options\) \{/);
	assert.match(
		source,
		/const safeOptions = normalizeOptions\(options\);/,
	);
	assert.match(source, /Number\.isFinite\(safeOptions\.timeoutMs\)/);
	assert.match(source, /const timeoutError = new TimeoutError\(message, timeoutMs\);/);
	assert.match(source, /let timeoutId = null;/);
	assert.match(
		source,
		/try \{\s+timeoutId = setTimeout\(\(\) => controller\.abort\(timeoutError\), timeoutMs\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Failed to schedule fetch timeout:", error\);/,
	);
	assert.match(source, /controller\.abort\(timeoutError\);/);
	assert.match(
		source,
		/if \(timeoutId !== null\) \{\s+try \{\s+clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.doesNotMatch(
		source,
		/const timeoutId = setTimeout\(\(\) => controller\.abort\(timeoutError\), timeoutMs\);/,
	);
	assert.doesNotMatch(source, /finally \{\s+clearTimeout\(timeoutId\);/);
});

test("fetchWithTimeout ignores malformed options input", async () => {
	const originalFetch = globalThis.fetch;
	globalThis.fetch = async (_input, init) => {
		assert.ok(init.signal instanceof AbortSignal);
		return new Response("ok", { status: 200 });
	};

	try {
		const response = await fetchWithTimeout("https://example.test", {}, null);

		assert.equal(response.status, 200);
		assert.equal(await response.text(), "ok");
	} finally {
		globalThis.fetch = originalFetch;
	}
});

test("fetchWithTimeout ignores array option fields", async () => {
	const originalFetch = globalThis.fetch;
	const arrayOptions = [];
	arrayOptions.timeoutMs = 1;
	arrayOptions.errorMessage = "array timeout should be ignored";
	globalThis.fetch = async (_input, init) => {
		assert.ok(init.signal instanceof AbortSignal);
		return new Response("ok", { status: 200 });
	};

	try {
		const response = await fetchWithTimeout(
			"https://example.test",
			{},
			arrayOptions,
		);

		assert.equal(response.status, 200);
		assert.equal(await response.text(), "ok");
	} finally {
		globalThis.fetch = originalFetch;
	}
});
