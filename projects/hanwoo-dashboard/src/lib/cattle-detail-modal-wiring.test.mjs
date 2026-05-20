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

test('cattle form and detail icon-only navigation controls have Korean labels', () => {
  const formSource = readSource('components/forms/CattleForm.js');
  const detailSource = readSource('components/forms/CattleDetailModal.js');

  assert.match(formSource, /aria-label="개체 목록으로 돌아가기"/);
  assert.match(formSource, /title="개체 목록으로 돌아가기"/);
  assert.match(formSource, /role="dialog"/);
  assert.match(formSource, /aria-modal="true"/);
  assert.match(formSource, /aria-labelledby="cattle-form-title"/);
  assert.match(formSource, /id="cattle-form-title"/);
  assert.match(detailSource, /aria-label="개체 상세 닫기"/);
  assert.match(detailSource, /title="개체 상세 닫기"/);
  assert.match(detailSource, /role="dialog"/);
  assert.match(detailSource, /aria-modal="true"/);
  assert.match(detailSource, /aria-labelledby="cattle-detail-title"/);
  assert.match(detailSource, /id="cattle-detail-title"/);
  assert.doesNotMatch(formSource, /aria-label="Back"/);
  assert.doesNotMatch(detailSource, /aria-label="Close"/);
});
