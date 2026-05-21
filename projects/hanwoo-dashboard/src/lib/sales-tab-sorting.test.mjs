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

test('sales tab keeps malformed sale dates at the end of recent records', () => {
  const source = readSource('components/tabs/SalesTab.js');

  assert.match(source, /function getSaleDateTime\(value\) \{/);
  assert.match(source, /return Number\.isNaN\(date\.getTime\(\)\) \? Number\.NEGATIVE_INFINITY : date\.getTime\(\);/);
  assert.match(
    source,
    /sort\(\(first, second\) => getSaleDateTime\(second\.saleDate\) - getSaleDateTime\(first\.saleDate\)\)/,
  );
  assert.doesNotMatch(source, /new Date\(second\.saleDate\) - new Date\(first\.saleDate\)/);
});
