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

	assert.match(hookSource, /function normalizePaginationParams\(params\) \{/);
	assert.match(
		hookSource,
		/params && typeof params === "object" && !Array\.isArray\(params\)/,
	);
	assert.match(
		hookSource,
		/const safeExtraParams = normalizePaginationParams\(extraParams\);/,
	);
	assert.match(hookSource, /export function useCursorPagination\(options = \{\}\) \{/);
	assert.match(
		hookSource,
		/const \{\s+endpoint,\s+initialItems = \[\],\s+initialPageInfo = null,\s+\} = normalizePaginationParams\(options\);/,
	);
	assert.doesNotMatch(
		hookSource,
		/export function useCursorPagination\(\{\s+endpoint,\s+initialItems = \[\],\s+initialPageInfo = null,\s+\} = \{\}\)/,
	);
	assert.match(
		hookSource,
		/Object\.entries\(safeExtraParams\)/,
	);
	assert.match(hookSource, /function normalizePaginationItems\(items\) \{/);
	assert.match(
		hookSource,
		/Array\.isArray\(items\)[\s\S]*?\? items\.filter\([\s\S]*?\(item\) => item && typeof item === ["']object["'] && !Array\.isArray\(item\)[\s\S]*?\)[\s\S]*?: \[\]/,
	);
	assert.match(
		hookSource,
		/useState\(\s*\(\s*\)\s*=>\s*normalizePaginationItems\(\s*initialItems\s*\),?\s*\)/,
	);
	assert.match(
		hookSource,
		/const \{ items: newItems, pageInfo: newPageInfo \} = json\.data \?\? \{\};/,
	);
	assert.match(
		hookSource,
		/const safeNewItems = normalizePaginationItems\(newItems\);/,
	);
	assert.match(
		hookSource,
		/setItems\(\s*\(\s*prev\s*\)\s*=>\s*\[\s*\.\.\.\s*normalizePaginationItems\(\s*prev\s*\),\s*\.\.\.\s*safeNewItems,?\s*\]\s*\)/,
	);
	assert.doesNotMatch(hookSource, /Object\.entries\(extraParams\)/);
	assert.doesNotMatch(hookSource, /useState\(initialItems\)/);
	assert.doesNotMatch(hookSource, /setItems\(\(prev\) => \[\.\.\.prev, \.\.\.newItems\]\)/);
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
