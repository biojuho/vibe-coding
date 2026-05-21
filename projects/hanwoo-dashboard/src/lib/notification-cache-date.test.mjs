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

test('notification action ignores malformed cached generatedAt values', () => {
  const source = readSource('lib/actions/notification.js');

  assert.match(source, /function isFreshNotificationSummary\(summary, now = Date\.now\(\)\)/);
  assert.match(source, /const generatedAt = new Date\(summary\.generatedAt\);/);
  assert.match(source, /const age = now - generatedAt\.getTime\(\);/);
  assert.match(source, /return Number\.isFinite\(age\) && age >= 0 && age < 60 \* 1000;/);
  assert.match(source, /if \(isFreshNotificationSummary\(cached\)\) \{\s+return cached\.payload;/);
  assert.doesNotMatch(source, /Date\.now\(\) - new Date\(cached\.generatedAt\)\.getTime\(\)/);
  assert.doesNotMatch(source, /if \(age < 60 \* 1000\)/);
});
