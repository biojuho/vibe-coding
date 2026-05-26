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

test("form default date builders safely fallback through toInputDate", () => {
	const source = readSource("lib/formSchemas.js");

	assert.match(
		source,
		/const toDefaultInputDate = \(\s*date\s*=\s*new Date\(\)\s*\)\s*=>\s*toInputDate\(\s*date\s*\)\s*\|\|\s*toInputDate\(\s*new Date\(\)\s*\);?/,
	);
	assert.match(source, /date: toDefaultInputDate\(date\),/);
	assert.match(source, /date: toDefaultInputDate\(\),/);
	assert.match(source, /calvingDate: toDefaultInputDate\(date\),/);
	assert.doesNotMatch(source, /baseDate\.toISOString\(\)\.split\(["']T["']\)\[0\]/);
	assert.doesNotMatch(
		source,
		/date: new Date\(\)\.toISOString\(\)\.split\(["']T["']\)\[0\]/,
	);
	assert.doesNotMatch(source, /calvingDate: toInputDate\(date\),/);
});
