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

test('dashboard list page cursors avoid raw invalid Date toISOString calls', () => {
  const source = readSource('lib/dashboard/list-queries.js');

  assert.match(source, /function toCursorSortValue\(value\) \{/);
  assert.match(source, /return Number\.isNaN\(date\.getTime\(\)\) \? null : date\.toISOString\(\);/);
  assert.match(source, /const sortValue = toCursorSortValue\(lastItem\[sortField\]\);/);
  assert.match(source, /if \(!sortValue\) \{\s+return \{\s+hasMore: false,\s+nextCursor: null,/);
  assert.match(source, /sortValue,/);
  assert.doesNotMatch(source, /sortValue: new Date\(lastItem\[sortField\]\)\.toISOString\(\)/);
});
