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

test("dashboard read models normalize malformed market issue dates before keying cache rows", () => {
	const source = readSource("lib/dashboard/read-models.js");

	assert.match(source, /const fallback = new Date\(\);/);
	assert.match(
		source,
		/return Number\.isNaN\(value\.getTime\(\)\) \? fallback : value;/,
	);
	assert.match(
		source,
		/return Number\.isNaN\(date\.getTime\(\)\) \? fallback : date;/,
	);
	assert.match(source, /const date = normalizeDate\(issueDate\);/);
	assert.match(source, /return date\.toISOString\(\)\.slice\(0, 10\);/);
	assert.doesNotMatch(source, /return new Date\(value\);\s*\}/);
});

test("dashboard read models ignore array option fields before cache checks", () => {
	const source = readSource("lib/dashboard/read-models.js");

	assert.match(source, /function normalizeObject\(value\) \{/);
	assert.match(
		source,
		/value && typeof value === "object" && !Array\.isArray\(value\)/,
	);
	assert.match(source, /const safeOptions = normalizeObject\(options\);/);
	assert.match(source, /const safeInput = normalizeObject\(input\);/);
});
