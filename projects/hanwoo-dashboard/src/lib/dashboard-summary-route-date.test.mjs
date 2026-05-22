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

test("dashboard summary route safely degrades malformed snapshot meta dates", () => {
	const source = readSource("app/api/dashboard/summary/route.js");

	assert.match(
		source,
		/function toMetaDate\(value, fallback = new Date\(\)\) \{/,
	);
	assert.match(
		source,
		/return Number\.isNaN\(date\.getTime\(\)\) \? fallback : date;/,
	);
	assert.match(
		source,
		/const generatedAt = toMetaDate\(snapshot\.generatedAt, fallback\);/,
	);
	assert.match(
		source,
		/const staleAt = toMetaDate\(snapshot\.staleAt, fallback\);/,
	);
	assert.match(
		source,
		/if \(!snapshot \|\| toMetaDate\(snapshot\.staleAt\) <= new Date\(\)\) \{/,
	);
	assert.doesNotMatch(
		source,
		/const generatedAt = new Date\(snapshot\.generatedAt\);/,
	);
	assert.doesNotMatch(source, /const staleAt = new Date\(snapshot\.staleAt\);/);
	assert.doesNotMatch(
		source,
		/if \(!snapshot \|\| new Date\(snapshot\.staleAt\) <= new Date\(\)\) \{/,
	);
});
