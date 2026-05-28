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

test("sales pagination failures surface retry feedback through guarded controls", () => {
	const hookSource = readSource("lib/hooks/useSalesPagination.js");
	const tabSource = readSource("components/tabs/SalesTab.js");

	assert.match(hookSource, /SALES_PAGINATION_TIMEOUT_MESSAGE/);
	assert.match(hookSource, /SALES_PAGINATION_ERROR_MESSAGE/);
	assert.match(hookSource, /function normalizePaginationParams\(params\) \{/);
	assert.match(
		hookSource,
		/params && typeof params === "object" && !Array\.isArray\(params\)/,
	);
	assert.match(hookSource, /export function useSalesPagination\(options = \{\}\) \{/);
	assert.match(
		hookSource,
		/const \{ initialItems = \[\], initialPageInfo = null \} =\s+normalizePaginationParams\(options\);/,
	);
	assert.doesNotMatch(
		hookSource,
		/export function useSalesPagination\(\{\s+initialItems = \[\],\s+initialPageInfo = null,\s+\} = \{\}\)/,
	);
	assert.match(
		hookSource,
		/async \(params = \{\}\) => \{\s+const \{ from, to \} = normalizePaginationParams\(params\);/,
	);
	assert.doesNotMatch(hookSource, /async \(\{ from, to \} = \{\}\) =>/);
	assert.match(hookSource, /setLoadError\(SALES_PAGINATION_TIMEOUT_MESSAGE\)/);
	assert.match(hookSource, /setLoadError\(SALES_PAGINATION_ERROR_MESSAGE\)/);
	assert.match(hookSource, /const loadInFlightRef = useRef\(false\);/);
	assert.match(
		hookSource,
		/if \(loadInFlightRef\.current \|\| isLoading \|\| !hasMore\) return;/,
	);
	assert.match(hookSource, /loadInFlightRef\.current = true;/);
	assert.match(hookSource, /let timeoutId = null;/);
	assert.match(
		hookSource,
		/try \{\s+timeoutId = window\.setTimeout\(\(\) => \{\s+didTimeout = true;\s+controller\.abort\(\);/,
	);
	assert.match(
		hookSource,
		/console\.error\("Failed to schedule sales pagination timeout:", error\);\s+didTimeout = true;\s+controller\.abort\(\);/,
	);
	assert.match(
		hookSource,
		/if \(timeoutId !== null\) \{\s+try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.match(
		hookSource,
		/loadInFlightRef\.current = false;\s+if \(abortRef\.current === controller\)/,
	);
	assert.doesNotMatch(hookSource, /const timeoutId = window\.setTimeout/);
	assert.doesNotMatch(hookSource, /finally \{\s+window\.clearTimeout\(timeoutId\);/);
	assert.match(hookSource, /loadMore, loadError/);

	assert.match(tabSource, /function normalizeSalesPaginationOptions\(pagination\) \{/);
	assert.match(
		tabSource,
		/pagination && typeof pagination === "object" && !Array\.isArray\(pagination\)/,
	);
	assert.match(
		tabSource,
		/const safeSalesPagination = normalizeSalesPaginationOptions\(salesPagination\);/,
	);
	assert.match(
		tabSource,
		/const handleLoadMoreSales =\s+typeof safeSalesPagination\.loadMore === "function"\s+\? safeSalesPagination\.loadMore\s+: \(\) => \{\};/,
	);
	assert.match(tabSource, /const loadMoreLabel = safeSalesPagination\.isLoading\s*\?/);
	assert.match(tabSource, /safeSalesPagination\.hasMore/);
	assert.match(tabSource, /onClick=\{handleLoadMoreSales\}/);
	assert.match(tabSource, /disabled=\{safeSalesPagination\.isLoading\}/);
	assert.match(tabSource, /aria-busy=\{safeSalesPagination\.isLoading\}/);
	assert.match(tabSource, /aria-label=\{loadMoreLabel\}/);
	assert.match(tabSource, /title=\{loadMoreLabel\}/);
	assert.match(tabSource, /safeSalesPagination\.loadError/);
	assert.match(tabSource, /role="status"/);
	assert.match(tabSource, /aria-live="polite"/);
	assert.match(tabSource, /aria-atomic="true"/);
	assert.doesNotMatch(hookSource, /setLoadError\(error\.message\)/);
	assert.doesNotMatch(tabSource, /salesPagination\.error\.message/);
	assert.doesNotMatch(tabSource, /onClick=\{\(\) => salesPagination\.loadMore\(\)\}/);
});

test("sales pagination normalizes malformed page item payloads", () => {
	const hookSource = readSource("lib/hooks/useSalesPagination.js");

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
	assert.doesNotMatch(hookSource, /useState\(initialItems\)/);
	assert.doesNotMatch(
		hookSource,
		/setItems\(\(prev\) => \[\.\.\.prev, \.\.\.newItems\]\)/,
	);
});
