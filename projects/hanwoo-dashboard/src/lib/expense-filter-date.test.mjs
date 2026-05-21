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

test('expense filters ignore malformed optional date values before querying', () => {
  const source = readSource('lib/actions/expense.js');

  assert.match(source, /function parseOptionalDateFilter\(value\)/);
  assert.match(source, /if \(!\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/\.test\(normalized\)\) \{/);
  assert.match(source, /const parsed = new Date\(`\$\{normalized\}T00:00:00\.000Z`\);/);
  assert.match(source, /parsed\.toISOString\(\)\.slice\(0, 10\) !== normalized/);
  assert.match(source, /const fromDate = parseOptionalDateFilter\(filters\.fromDate\);/);
  assert.match(source, /const toDate = parseOptionalDateFilter\(filters\.toDate\);/);
  assert.match(source, /if \(fromDate\) where\.date\.gte = fromDate;/);
  assert.match(source, /if \(toDate\) where\.date\.lte = toDate;/);
  assert.doesNotMatch(source, /where\.date\.gte = new Date\(filters\.fromDate\)/);
  assert.doesNotMatch(source, /where\.date\.lte = new Date\(filters\.toDate\)/);
});
