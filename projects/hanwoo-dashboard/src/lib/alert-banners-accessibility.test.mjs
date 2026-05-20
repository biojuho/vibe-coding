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

test('alert banner decorative calving icon is hidden from assistive tech', () => {
  const source = readSource('components/widgets/AlertBanners.js');

  assert.match(source, /<span aria-hidden="true" style=\{\{ fontSize: '18px' \}\} className="animate-bounce">/);
});
