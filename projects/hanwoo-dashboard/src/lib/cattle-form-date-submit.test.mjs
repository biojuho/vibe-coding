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

test("cattle form submit date conversion avoids raw invalid Date toISOString calls", () => {
	const source = readSource("components/forms/CattleForm.js");

	assert.match(source, /import \{ toInputDate \} from ["']@\/lib\/utils["'];/);
	assert.match(source, /function toIsoDateOrNull\(value\) \{/);
	assert.match(source, /const inputDate = toInputDate\(value\);/);
	assert.match(
		source,
		/return inputDate\s*\?\s*new\s+Date\(\s*`\$\{inputDate\}T00:00:00\.000Z`\s*\)\s*\.toISOString\(\s*\)\s*:\s*null\s*;?/s,
	);
	assert.match(
		source,
		/const birthDate = toIsoDateOrNull\(values\.birthDate\);/,
	);
	assert.match(source, /if \(!birthDate\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/purchaseDate: toIsoDateOrNull\(values\.purchaseDate\),/,
	);
	assert.doesNotMatch(
		source,
		/birthDate: new Date\(values\.birthDate\)\.toISOString\(\)/,
	);
	assert.doesNotMatch(
		source,
		/new Date\(values\.purchaseDate\)\.toISOString\(\)/,
	);
});

test("cattle form OCGK lookup gates birthDate with typeof string check (HW-CF001)", () => {
	const source = readSource("components/forms/CattleForm.js");
	// Must check typeof before calling .replace() on API response birthDate
	assert.match(
		source,
		/typeof data\.birthDate === "string" && data\.birthDate/,
	);
	// Must NOT call .replace() with only a truthiness check
	assert.doesNotMatch(source, /if \(data\.birthDate\) \{\s*const raw = data\.birthDate\.replace/s);
});

test("CattleForm logs cattle tag lookup failure to console.error before showing user error", () => {
	const source = readSource("components/forms/CattleForm.js");
	assert.match(
		source,
		/console\.error\(["']CattleForm: cattle tag lookup failed["'], err\)/,
	);
	assert.match(
		source,
		/} catch \(err\) \{\s+console\.error\(["']CattleForm: cattle tag lookup failed["'], err\)/,
	);
});
