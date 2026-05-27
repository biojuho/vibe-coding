import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "../..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("dashboard read-model cache options are normalized before access", () => {
	const source = readSource("lib/dashboard/read-models.js");

	assert.match(source, /function normalizeObject\(value\) \{/);
	assert.match(source, /const safeOptions = normalizeObject\(options\);/);
	assert.match(source, /if \(!safeOptions\.bypassCache\) \{/);
});

test("dashboard cache invalidation normalizes input before reading fields", () => {
	const source = readSource("lib/dashboard/read-models.js");

	assert.match(source, /const safeInput = normalizeObject\(input\);/);
	assert.match(source, /const farmId = safeInput\.farmId \?\? "default";/);
	assert.match(source, /safeInput\.summary \? buildDashboardSummaryKey\(farmId\) : null/);
	assert.match(source, /if \(safeInput\.notifications\) \{/);
});
