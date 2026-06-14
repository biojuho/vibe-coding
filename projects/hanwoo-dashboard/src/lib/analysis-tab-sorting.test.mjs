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

test("AnalysisTab recentGradedSales sort uses NaN-safe comparator (HW-A01)", () => {
	const source = readSource("components/tabs/AnalysisTab.js");
	// The diff variable pattern
	assert.match(
		source,
		/new Date\(\s*b\.saleDate\s*\)\.getTime\(\)\s*-\s*new Date\(\s*a\.saleDate\s*\)\.getTime\(\)/,
	);
	// Guard must be present
	assert.match(source, /Number\.isNaN\(diff\)\s*\?\s*0\s*:\s*diff/);
});

test("AnalysisTab: doesNotMatch bare Date subtraction without NaN guard", () => {
	const source = readSource("components/tabs/AnalysisTab.js");
	// Old pattern: arrow directly returning unguarded subtraction
	assert.doesNotMatch(
		source,
		/=>\s*new Date\(b\.saleDate\)\s*-\s*new Date\(a\.saleDate\)/,
	);
});
