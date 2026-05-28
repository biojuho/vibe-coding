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

test("cattle pagination failures surface Korean retry feedback", () => {
	const hookSource = readSource("lib/hooks/useCattlePagination.js");
	const dashboardSource = readSource("components/DashboardClient.js");

	assert.match(hookSource, /CATTLE_PAGINATION_TIMEOUT_MESSAGE/);
	assert.match(hookSource, /CATTLE_PAGINATION_ERROR_MESSAGE/);
	assert.match(hookSource, /function normalizePaginationParams\(params\) \{/);
	assert.match(
		hookSource,
		/params && typeof params === "object" && !Array\.isArray\(params\)/,
	);
	assert.match(hookSource, /export function useCattlePagination\(options = \{\}\) \{/);
	assert.match(
		hookSource,
		/const \{ initialItems = \[\], initialPageInfo = null \} =\s+normalizePaginationParams\(options\);/,
	);
	assert.doesNotMatch(
		hookSource,
		/export function useCattlePagination\(\{\s+initialItems = \[\],\s+initialPageInfo = null,\s+\} = \{\}\)/,
	);
	assert.match(
		hookSource,
		/async \(params = \{\}\) => \{\s+const \{ buildingId, penNumber, status \} =\s+normalizePaginationParams\(params\);/,
	);
	assert.doesNotMatch(
		hookSource,
		/async \(\{ buildingId, penNumber, status \} = \{\}\) =>/,
	);
	assert.match(hookSource, /setLoadError\(CATTLE_PAGINATION_TIMEOUT_MESSAGE\)/);
	assert.match(hookSource, /setLoadError\(CATTLE_PAGINATION_ERROR_MESSAGE\)/);
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
		/console\.error\("Failed to schedule cattle pagination timeout:", error\);/,
	);
	assert.match(
		hookSource,
		/console\.error\("Failed to schedule cattle pagination timeout:", error\);\s+didTimeout = true;\s+controller\.abort\(\);/,
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
	assert.match(dashboardSource, /cattlePagination\.loadError/);
	assert.match(
		dashboardSource,
		/const cattleLoadMoreLabel = cattlePagination\.isLoading\s*\?\s*["']개체 목록을 불러오는 중입니다["']\s*:\s*["']이전 개체 더 보기["']/,
	);
	assert.match(dashboardSource, /aria-busy=\{cattlePagination\.isLoading\}/);
	assert.match(dashboardSource, /aria-label=\{cattleLoadMoreLabel\}/);
	assert.match(dashboardSource, /title=\{cattleLoadMoreLabel\}/);
	assert.match(dashboardSource, /role="status"/);
	assert.match(dashboardSource, /aria-live="polite"/);
	assert.match(dashboardSource, /aria-atomic="true"/);
	assert.match(dashboardSource, /이전 개체 더 보기/);
	assert.doesNotMatch(hookSource, /setLoadError\(error\.message\)/);
});

test("cattle pagination normalizes malformed page item payloads", () => {
	const hookSource = readSource("lib/hooks/useCattlePagination.js");

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
