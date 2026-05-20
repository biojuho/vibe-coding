import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, '..');

function readSource(relativePath) {
  return readFileSync(path.join(SRC_ROOT, relativePath), 'utf8');
}

test('sales pagination failures surface Korean retry feedback', () => {
  const hookSource = readSource('lib/hooks/useSalesPagination.js');
  const tabSource = readSource('components/tabs/SalesTab.js');

  assert.match(hookSource, /SALES_PAGINATION_TIMEOUT_MESSAGE/);
  assert.match(hookSource, /SALES_PAGINATION_ERROR_MESSAGE/);
  assert.match(hookSource, /setLoadError\(SALES_PAGINATION_TIMEOUT_MESSAGE\)/);
  assert.match(hookSource, /setLoadError\(SALES_PAGINATION_ERROR_MESSAGE\)/);
  assert.match(hookSource, /const loadInFlightRef = useRef\(false\);/);
  assert.match(hookSource, /if \(loadInFlightRef\.current \|\| isLoading \|\| !hasMore\) return;/);
  assert.match(hookSource, /loadInFlightRef\.current = true;/);
  assert.match(hookSource, /loadInFlightRef\.current = false;\s+if \(abortRef\.current === controller\)/);
  assert.match(hookSource, /loadMore, loadError/);
  assert.match(tabSource, /salesPagination\.loadError/);
  assert.match(tabSource, /aria-busy=\{salesPagination\.isLoading\}/);
  assert.match(tabSource, /role="status"/);
  assert.match(tabSource, /aria-live="polite"/);
  assert.doesNotMatch(hookSource, /setLoadError\(error\.message\)/);
  assert.doesNotMatch(tabSource, /salesPagination\.error\.message/);
});
