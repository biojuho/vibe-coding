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

test("dashboard list query parsers normalize malformed search params", () => {
	const source = readSource("lib/dashboard/list-queries.js");

	assert.match(source, /function getSearchParam\(searchParams, key\) \{/);
	assert.match(
		source,
		/return typeof searchParams\?\.get === "function" \? searchParams\.get\(key\) : null;/,
	);
	assert.match(
		source,
		/parsePenNumber\(getSearchParam\(searchParams, "penNumber"\)\)/,
	);
	assert.match(
		source,
		/parseDateParam\(getSearchParam\(searchParams, "from"\), "from"\)/,
	);
	assert.doesNotMatch(source, /searchParams\.get\("/);
});

test("dashboard list page inputs are normalized before destructuring", () => {
	const source = readSource("lib/dashboard/list-queries.js");

	assert.match(source, /function normalizeObject\(value\) \{/);
	assert.match(
		source,
		/value && typeof value === "object" && !Array\.isArray\(value\)/,
	);
	assert.match(source, /\} = normalizeObject\(input\);/);
	assert.doesNotMatch(source, /\} = input;/);
});
