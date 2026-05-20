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

test('calving tab validation messages are announced with their controls', () => {
  const source = readSource('components/tabs/CalvingTab.js');

  assert.match(source, /aria-describedby=\{errors\.calvingDate \? "calving-date-error" : undefined\}/);
  assert.match(source, /<div id="calving-date-error" role="alert"/);
  assert.match(source, /aria-describedby=\{errors\.calfGender \? "calf-gender-error" : undefined\}/);
  assert.match(source, /<div id="calf-gender-error" role="alert"/);
  assert.match(source, /aria-describedby=\{errors\.calfTagNumber \? "calf-tag-number-error" : undefined\}/);
  assert.match(source, /<div id="calf-tag-number-error" role="alert"/);
});

test('calving form waits for async saves before re-enabling actions', () => {
  const source = readSource('components/tabs/CalvingTab.js');

  assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
  assert.match(source, /setIsSaving\(true\);/);
  assert.match(source, /await onRecordCalving\(\{/);
  assert.match(source, /finally \{\s*setIsSaving\(false\);/);
  assert.match(source, /<button type="submit" disabled=\{isSaving\} aria-busy=\{isSaving\}/);
  assert.match(source, /type="button"\s+onClick=\{closeCalvingForm\}\s+disabled=\{isSaving\}/);
});
