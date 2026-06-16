import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const SRC_DIR = path.dirname(fileURLToPath(import.meta.url));
const readLib = (name: string) =>
	readFileSync(path.join(SRC_DIR, "lib", name), "utf8");

// KD-PLD001: isDashboardDataPayload must validate inner notebook items so that
// malformed API responses (null title / string source_count) are rejected before
// reaching render code instead of crashing mid-render.
test("isDashboardDataPayload validates notebook item title and source_count", () => {
	const src = readLib("dashboard-payload.ts");
	// Per-item guard: every notebook must have title:string and source_count:number
	assert.match(
		src,
		/typeof nb\.title === "string"/,
		"missing title type-guard in isDashboardDataPayload",
	);
	assert.match(
		src,
		/isNumber\(nb\.source_count\)/,
		"missing source_count number-guard in isDashboardDataPayload",
	);
});

// KD-VW001: filterDashboard must guard nb.title before calling .toLowerCase()
// to avoid a crash when a non-string title comes in despite the type annotation.
test("filterDashboard guards nb.title type before toLowerCase", () => {
	const src = readLib("dashboard-view.ts");
	assert.match(
		src,
		/typeof nb\.title === "string" &&\s+nb\.title\.toLowerCase\(\)/,
		"filterDashboard missing typeof guard before nb.title.toLowerCase()",
	);
});

// KD-VW002: computeLanguageStats must coerce source_count to Number so that a
// string value from the API doesn't produce string concatenation instead of
// numeric addition in the reduce.
test("computeLanguageStats coerces nb.source_count via Number()", () => {
	const src = readLib("dashboard-view.ts");
	assert.match(
		src,
		/Number\(nb\.source_count\)/,
		"computeLanguageStats missing Number() coercion for source_count",
	);
});
