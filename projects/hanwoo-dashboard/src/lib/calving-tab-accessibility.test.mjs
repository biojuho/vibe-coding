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

test('calving tab form fields expose explicit labels and invalid states', () => {
  const source = readSource('components/tabs/CalvingTab.js');

  assert.match(source, /<span className="section-header-icon" aria-hidden="true">🐮<\/span>/);
  assert.match(source, /<label htmlFor="calving-date"/);
  assert.match(source, /id="calving-date"\s+type="date"/);
  assert.match(source, /aria-invalid=\{Boolean\(errors\.calvingDate\)\}/);
  assert.match(source, /<label htmlFor="calf-gender"/);
  assert.match(source, /id="calf-gender"\s+\{\.\.\.register\('calfGender'\)\}/);
  assert.match(source, /aria-invalid=\{Boolean\(errors\.calfGender\)\}/);
});
