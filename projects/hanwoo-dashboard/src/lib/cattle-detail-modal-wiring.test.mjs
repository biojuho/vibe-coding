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

test('cattle detail shows a real calving due date from pregnancy date', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.match(source, /getCalvingDate/);
  assert.match(source, /label="분만 예정일" value=\{cattle\.pregnancyDate \? formatDate\(getCalvingDate\(cattle\.pregnancyDate\)\) : "-"\}/);
  assert.doesNotMatch(source, /계산중/);
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
  assert.match(formSource, /<label htmlFor="cattle-name"/);
  assert.match(formSource, /id="cattle-name"/);
  assert.match(formSource, /<label htmlFor="cattle-tag-number"/);
  assert.match(formSource, /id="cattle-tag-number"/);
  assert.match(formSource, /<label htmlFor="cattle-building"/);
  assert.match(formSource, /id="cattle-building"[^>]*aria-invalid=\{Boolean\(errors\.buildingId\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-pen-number"/);
  assert.match(formSource, /id="cattle-pen-number"[^>]*aria-invalid=\{Boolean\(errors\.penNumber\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-gender"/);
  assert.match(formSource, /id="cattle-gender"[^>]*aria-invalid=\{Boolean\(errors\.gender\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-status"/);
  assert.match(formSource, /id="cattle-status"[^>]*aria-invalid=\{Boolean\(errors\.status\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-birth-date"/);
  assert.match(formSource, /id="cattle-birth-date"[^>]*aria-invalid=\{Boolean\(errors\.birthDate\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-weight"/);
  assert.match(formSource, /id="cattle-weight"[^>]*aria-invalid=\{Boolean\(errors\.weight\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-purchase-price"/);
  assert.match(formSource, /id="cattle-purchase-price"[\s\S]*?aria-invalid=\{Boolean\(errors\.purchasePrice\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-purchase-date"/);
  assert.match(formSource, /id="cattle-purchase-date"[^>]*aria-invalid=\{Boolean\(errors\.purchaseDate\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-genetic-father"/);
  assert.match(formSource, /id="cattle-genetic-father"[\s\S]*?aria-invalid=\{Boolean\(errors\.geneticInfo\?\.father\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-genetic-mother"/);
  assert.match(formSource, /id="cattle-genetic-mother"[\s\S]*?aria-invalid=\{Boolean\(errors\.geneticInfo\?\.mother\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-memo"/);
  assert.match(formSource, /id="cattle-memo"[\s\S]*?aria-invalid=\{Boolean\(errors\.memo\)\}/);
  assert.match(detailSource, /aria-label="개체 상세 닫기"/);
  assert.match(detailSource, /title="개체 상세 닫기"/);
  assert.match(detailSource, /type="button"\s+onClick=\{onClose\}/);
  assert.match(detailSource, /aria-label=\{`\$\{cattle\.name\} 개체 정보 수정`\}/);
  assert.match(detailSource, /title="개체 정보 수정"/);
  assert.match(detailSource, /type="button"\s+onClick=\{onEdit\}/);
  assert.match(detailSource, /aria-label=\{`\$\{cattle\.name\} 개체 보관 처리`\}/);
  assert.match(detailSource, /title="개체 보관 처리"/);
  assert.match(detailSource, /> 보관<\/button>/);
  assert.match(detailSource, /type="button"\s+onClick=\{onDelete\}/);
  assert.match(detailSource, /role="dialog"/);
  assert.match(detailSource, /aria-modal="true"/);
  assert.match(detailSource, /aria-labelledby="cattle-detail-title"/);
  assert.match(detailSource, /id="cattle-detail-title"/);
  assert.doesNotMatch(formSource, /aria-label="Back"/);
  assert.doesNotMatch(detailSource, /aria-label="Close"/);
});

test('cattle detail decorative icons are hidden from assistive tech', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.match(source, /<span aria-hidden="true" style=\{\{fontSize:"18px",lineHeight:1\}\}>\{icon\}<\/span> \{title\}/);
  assert.match(source, /<div aria-hidden="true" style=\{\{/);
});
