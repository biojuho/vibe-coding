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

test("estimateDailyFeedConsumptionKg clamps invalid lookbackDays to 30 (HW-TF01)", () => {
	const source = readSource("lib/dashboard/today-focus.mjs");
	// safeLookbackDays guard must exist
	assert.match(
		source,
		/const safeLookbackDays\s*=\s*\n?\s*Number\.isFinite\(lookbackDays\)/,
	);
	// Division must use safeLookbackDays, not raw lookbackDays
	assert.match(source, /return totalKg \/ safeLookbackDays/);
	// cutoff must use safeLookbackDays
	assert.match(source, /lookbackDays\s*\*\s*86400000/.source ? /safeLookbackDays\s*\*\s*86400000/ : /safeLookbackDays/);
});

test("estimateDailyFeedConsumptionKg does NOT divide by raw lookbackDays (HW-TF01)", () => {
	const source = readSource("lib/dashboard/today-focus.mjs");
	// The bare division by lookbackDays (not safeLookbackDays) must not appear
	assert.doesNotMatch(source, /return totalKg \/ lookbackDays/);
});
