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

test('primary data-entry submit buttons show pending copy while saving', () => {
  const expectations = [
    ['components/forms/CattleForm.js', /\{isSaving \? '저장 중\.\.\.' : '저장하기'\}/],
    ['components/tabs/CalvingTab.js', /\{isSaving \? '분만 기록 저장 중\.\.\.' : '분만 완료 및 송아지 등록'\}/],
    ['components/tabs/ScheduleTab.js', /\{isSaving \? '일정 등록 중\.\.\.' : '일정 등록하기'\}/],
    ['components/tabs/FeedTab.js', /\{isSaving \? '급여 기록 저장 중\.\.\.' : '급여 기록 저장하기'\}/],
    ['components/tabs/InventoryTab.js', /\{isSaving \? '재고 등록 중\.\.\.' : '등록하기'\}/],
    ['components/tabs/SalesTab.js', /\{isSaving \? '판매 기록 등록 중\.\.\.' : '등록하기'\}/],
  ];

  for (const [relativePath, pattern] of expectations) {
    const source = readSource(relativePath);

    assert.match(source, pattern, `${relativePath} should expose pending submit copy`);
  }
});
