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

test('feedback toasts expose live-region semantics and Korean dismiss labels', () => {
  const source = readSource('components/feedback/FeedbackProvider.js');

  assert.match(source, /const isUrgent = toast\.variant === 'error' \|\| toast\.variant === 'warning'/);
  assert.match(source, /role=\{isUrgent \? 'alert' : 'status'\}/);
  assert.match(source, /aria-live=\{isUrgent \? 'assertive' : 'polite'\}/);
  assert.match(source, /aria-atomic="true"/);
  assert.match(source, /aria-label=\{`\$\{toast\.title\} 알림 닫기`\}/);
  assert.match(source, /aria-hidden="true"/);
  assert.doesNotMatch(source, /aria-label="Close"/);
});
