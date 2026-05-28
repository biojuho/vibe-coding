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

test("home cache invalidation normalizes malformed options before access", () => {
	const source = readSource("lib/actions/_helpers.js");

	assert.match(source, /function normalizeObject\(value\) \{/);
	assert.match(
		source,
		/value && typeof value === "object" && !Array\.isArray\(value\)/,
	);
	assert.match(source, /const safeOptions = normalizeObject\(options\);/);
	assert.match(source, /\.\.\.safeOptions,/);
	assert.match(source, /if \(safeOptions\.cattleListPages\) \{/);
	assert.match(source, /if \(safeOptions\.salesListPages\) \{/);
	assert.doesNotMatch(source, /\.\.\.options,/);
	assert.doesNotMatch(source, /if \(options\.cattleListPages\) \{/);
	assert.doesNotMatch(source, /if \(options\.salesListPages\) \{/);
});
