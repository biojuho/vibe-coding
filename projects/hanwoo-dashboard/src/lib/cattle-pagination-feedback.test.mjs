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

test('cattle pagination failures surface Korean retry feedback', () => {
  const hookSource = readSource('lib/hooks/useCattlePagination.js');
  const dashboardSource = readSource('components/DashboardClient.js');

  assert.match(hookSource, /CATTLE_PAGINATION_TIMEOUT_MESSAGE/);
  assert.match(hookSource, /CATTLE_PAGINATION_ERROR_MESSAGE/);
  assert.match(hookSource, /setLoadError\(CATTLE_PAGINATION_TIMEOUT_MESSAGE\)/);
  assert.match(hookSource, /setLoadError\(CATTLE_PAGINATION_ERROR_MESSAGE\)/);
  assert.match(hookSource, /const loadInFlightRef = useRef\(false\);/);
  assert.match(hookSource, /if \(loadInFlightRef\.current \|\| isLoading \|\| !hasMore\) return;/);
  assert.match(hookSource, /loadInFlightRef\.current = true;/);
  assert.match(hookSource, /loadInFlightRef\.current = false;\s+if \(abortRef\.current === controller\)/);
  assert.match(hookSource, /loadMore, loadError/);
  assert.match(dashboardSource, /cattlePagination\.loadError/);
  assert.match(dashboardSource, /const cattleLoadMoreLabel = cattlePagination\.isLoading \? '개체 목록을 불러오는 중입니다' : '개체 더 보기';/);
  assert.match(dashboardSource, /aria-busy=\{cattlePagination\.isLoading\}/);
  assert.match(dashboardSource, /aria-label=\{cattleLoadMoreLabel\}/);
  assert.match(dashboardSource, /title=\{cattleLoadMoreLabel\}/);
  assert.match(dashboardSource, /role="status"/);
  assert.match(dashboardSource, /aria-live="polite"/);
  assert.match(dashboardSource, /개체 더 보기/);
  assert.doesNotMatch(hookSource, /setLoadError\(error\.message\)/);
});
