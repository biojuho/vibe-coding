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

test("sales pagination failures surface Korean retry feedback", () => {
	const hookSource = readSource("lib/hooks/useSalesPagination.js");
	const tabSource = readSource("components/tabs/SalesTab.js");

	assert.match(hookSource, /SALES_PAGINATION_TIMEOUT_MESSAGE/);
	assert.match(hookSource, /SALES_PAGINATION_ERROR_MESSAGE/);
	assert.match(hookSource, /이전 판매 기록을 불러오는 데 시간이 오래 걸리고 있습니다/);
	assert.match(hookSource, /이전 판매 기록을 불러오지 못했습니다/);
	assert.doesNotMatch(hookSource, /이전 매출 기록/);
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
		/console\.error\("Failed to schedule sales pagination timeout:", error\);/,
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
	assert.match(tabSource, /salesPagination\.loadError/);
	assert.match(
		tabSource,
		/const loadMoreLabel = salesPagination\?\.isLoading\s*\?\s*["']이전 판매 기록 불러오는 중["']\s*:\s*["']이전 판매 기록 더 보기["']/,
	);
	assert.match(tabSource, /aria-busy=\{salesPagination\.isLoading\}/);
	assert.match(tabSource, /aria-label=\{loadMoreLabel\}/);
	assert.match(tabSource, /title=\{loadMoreLabel\}/);
	assert.match(
		tabSource,
		/salesPagination\.isLoading\s*\?\s*["']이전 판매 기록 불러오는 중\.\.\.["']\s*:\s*["']이전 판매 기록 더 보기["']/,
	);
	assert.match(tabSource, /role="status"/);
	assert.match(tabSource, /aria-live="polite"/);
	assert.match(tabSource, /aria-atomic="true"/);
	assert.doesNotMatch(hookSource, /setLoadError\(error\.message\)/);
	assert.doesNotMatch(tabSource, /salesPagination\.error\.message/);
});

test("sales pagination normalizes malformed page item payloads", () => {
	const hookSource = readSource("lib/hooks/useSalesPagination.js");

	assert.match(hookSource, /function normalizePaginationItems\(items\) \{/);
	assert.match(
		hookSource,
		/Array\.isArray\(items\)\s*\?\s*items\.filter\(\s*\(item\)\s*=>\s*item\s*&&\s*typeof\s*item\s*===\s*["']object["']\s*\)\s*:\s*\[\]/,
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
