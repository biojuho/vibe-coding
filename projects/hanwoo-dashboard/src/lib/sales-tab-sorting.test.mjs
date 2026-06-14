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

test("sales tab keeps malformed sale dates at the end of recent records", () => {
	const source = readSource("components/tabs/SalesTab.js");

	assert.match(source, /function getSaleDateTime\(value\) \{/);
	assert.match(
		source,
		/return Number\.isNaN\(date\.getTime\(\)\)\s*\?\s*Number\.NEGATIVE_INFINITY\s*:\s*date\.getTime\(\)/,
	);
	// Sort must use NaN-safe comparator (HW-S01: two invalid dates → NaN diff → stable 0)
	assert.match(
		source,
		/getSaleDateTime\(\s*second\.saleDate\s*\)\s*-\s*getSaleDateTime\(\s*first\.saleDate\s*\)/,
	);
	assert.match(source, /Number\.isNaN\(diff\)\s*\?\s*0\s*:\s*diff/);
	assert.doesNotMatch(
		source,
		/new Date\(second\.saleDate\) - new Date\(first\.saleDate\)/,
	);
});

test("sales tab NaN sort guard: both dates invalid keeps stable order", () => {
	// Verify the guard pattern is present (structural, since we can't import JSX)
	const source = readSource("components/tabs/SalesTab.js");
	assert.match(
		source,
		/const diff\s*=\s*getSaleDateTime\(\s*second\.saleDate\s*\)\s*-\s*getSaleDateTime\(\s*first\.saleDate\s*\)/,
	);
	assert.match(source, /return Number\.isNaN\(diff\)\s*\?\s*0\s*:\s*diff/);
});
