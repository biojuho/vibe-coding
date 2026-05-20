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
  assert.match(hookSource, /loadMore, loadError/);
  assert.match(dashboardSource, /cattlePagination\.loadError/);
  assert.match(dashboardSource, /role="status"/);
  assert.match(dashboardSource, /개체 더 보기/);
  assert.doesNotMatch(hookSource, /setLoadError\(error\.message\)/);
});
