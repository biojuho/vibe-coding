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

test('dashboard local date sorting keeps malformed dates at the end', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /function getSortableDateTime\(value\) \{/);
  assert.match(source, /return Number\.isNaN\(date\.getTime\(\)\) \? null : date\.getTime\(\);/);
  assert.match(source, /if \(leftTime === null\) return 1;/);
  assert.match(source, /if \(rightTime === null\) return -1;/);
  assert.match(source, /return leftTime - rightTime;/);
  assert.match(source, /return rightTime - leftTime;/);
  assert.doesNotMatch(source, /new Date\(left\[key\]\) - new Date\(right\[key\]\)/);
  assert.doesNotMatch(source, /new Date\(right\[key\]\) - new Date\(left\[key\]\)/);
});
