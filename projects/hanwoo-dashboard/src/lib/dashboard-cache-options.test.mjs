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

test("dashboard cache key helpers ignore array filter fields", () => {
	const source = readSource("lib/dashboard/cache.js");

	assert.match(source, /function normalizeObject\(value\) \{/);
	assert.match(
		source,
		/value && typeof value === "object" && !Array\.isArray\(value\)/,
	);
	assert.match(source, /\} = normalizeObject\(filters\);/);
	assert.doesNotMatch(
		source,
		/return value && typeof value === "object" \? value : \{\};/,
	);
});
