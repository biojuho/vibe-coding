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

test("dashboard calving submit avoids raw invalid Date toISOString calls", () => {
	const source = readSource("components/DashboardClient.js");

	assert.match(source, /function toStrictIsoDateOrNull\(value\) \{/);
	assert.match(source, /const normalized = value\.trim\(\);/);
	assert.match(
		source,
		/if \(!\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/\.test\(normalized\)\) \{/,
	);
	assert.match(source, /date\.toISOString\(\)\.slice\(0, 10\) !== normalized/);
	assert.match(
		source,
		/const birthDate = toStrictIsoDateOrNull\(calvingDate\);/,
	);
	assert.match(
		source,
		/if \(!birthDate\) \{\s+showError\('[^']*'\);\s+return false;\s+\}/,
	);
	assert.match(source, /birthDate,/);
	assert.doesNotMatch(
		source,
		/birthDate: new Date\(calvingDate\)\.toISOString\(\)/,
	);
});
