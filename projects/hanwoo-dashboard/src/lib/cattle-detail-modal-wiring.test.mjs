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

test('cattle detail breeding actions use an in-app date form instead of browser prompts', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.doesNotMatch(source, /\bprompt\s*\(/);
  assert.match(source, /activeBreedingAction/);
  assert.match(source, /type="date"/);
  assert.match(source, /handleSaveBreedingRecord/);
  assert.match(source, /onUpdate\(nextCattle/);
  assert.match(source, /successTitle: activeBreedingAction === 'pregnancy'/);
});
