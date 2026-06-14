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

test("FeedTab sort uses NaN-safe comparator (HW-F02)", () => {
	const source = readSource("components/tabs/FeedTab.js");
	// getFeedDateTime fallback is NEGATIVE_INFINITY — two invalid dates → NaN diff
	assert.match(
		source,
		/getFeedDateTime\(\s*first\.date\s*\)\s*-\s*getFeedDateTime\(\s*second\.date\s*\)/,
	);
	// Guard must be present
	assert.match(source, /Number\.isNaN\(diff\)\s*\?\s*0\s*:\s*diff/);
});

test("FeedTab: doesNotMatch unguarded NEGATIVE_INFINITY subtraction in sort", () => {
	const source = readSource("components/tabs/FeedTab.js");
	// Old pattern (no NaN guard) must not exist
	assert.doesNotMatch(
		source,
		/\.sort\(\s*\(\s*first,\s*second\s*\)\s*=>\s*getFeedDateTime/,
	);
});
