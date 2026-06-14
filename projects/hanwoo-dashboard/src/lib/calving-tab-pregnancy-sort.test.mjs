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

test("CalvingTab getPregnancyDateTime has null guard (HW-C01)", () => {
	const source = readSource("components/tabs/CalvingTab.js");
	// null check must come before Date construction (new Date(null) = epoch)
	assert.match(source, /if\s*\(\s*value\s*==\s*null\s*\)\s*return\s+Number\.POSITIVE_INFINITY/);
});

test("CalvingTab getPregnancyDateTime returns POSITIVE_INFINITY for NaN dates", () => {
	const source = readSource("components/tabs/CalvingTab.js");
	assert.match(source, /Number\.isNaN\(date\.getTime\(\)\)\s*\?\s*Number\.POSITIVE_INFINITY/);
});

test("CalvingTab: doesNotMatch new Date(value) without null guard", () => {
	const source = readSource("components/tabs/CalvingTab.js");
	// Old pattern: immediately constructing Date from value without null check first
	// (null guard must appear before Date construction in getPregnancyDateTime)
	const fnMatch = source.match(/function getPregnancyDateTime\(value\)\s*\{([\s\S]*?)\n\}/);
	assert.ok(fnMatch, "getPregnancyDateTime function must exist");
	const fnBody = fnMatch[1];
	// null check must appear before Date constructor usage
	const nullGuardPos = fnBody.indexOf("if (value == null)");
	const dateCtorPos = fnBody.indexOf("new Date(value)");
	assert.ok(nullGuardPos >= 0, "null guard must exist");
	assert.ok(dateCtorPos >= 0, "Date constructor must exist");
	assert.ok(nullGuardPos < dateCtorPos, "null guard must precede Date construction");
});
