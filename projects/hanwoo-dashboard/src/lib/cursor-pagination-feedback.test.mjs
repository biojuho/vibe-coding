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

test("shared cursor pagination preserves timeout protection when scheduling fails", () => {
	const hookSource = readSource("lib/hooks/useCursorPagination.js");

	assert.match(hookSource, /let didTimeout = false;/);
	assert.match(hookSource, /let timeoutId = null;/);
	assert.match(
		hookSource,
		/try \{\s+timeoutId = window\.setTimeout\(\(\) => \{\s+didTimeout = true;\s+controller\.abort\(\);/,
	);
	assert.match(
		hookSource,
		/console\.error\(`Failed to schedule load-more timeout at \$\{endpoint\}:`, error\);\s+didTimeout = true;\s+controller\.abort\(\);/,
	);
	assert.match(
		hookSource,
		/if \(timeoutId !== null\) \{\s+try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.match(hookSource, /if \(didTimeout && mountedRef\.current\)/);
	assert.doesNotMatch(hookSource, /const timeoutId = window\.setTimeout/);
	assert.doesNotMatch(hookSource, /finally \{\s+window\.clearTimeout\(timeoutId\);/);
});
