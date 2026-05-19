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

test('shared empty state component exposes an action button without custom dependencies', () => {
  const source = readSource('components/ui/empty-state.js');

  assert.match(source, /export default function EmptyState/);
  assert.match(source, /PremiumButton/);
  assert.match(source, /disabled=\{disabled\}/);
  assert.match(source, /onClick=\{onAction\}/);
});

test('operational tabs use action-oriented empty states', () => {
  const expectations = [
    {
      file: 'components/tabs/InventoryTab.js',
      icon: 'PackagePlus',
      title: '등록된 재고가 없습니다',
      action: '재고 등록',
      handler: 'setIsAdding(true)',
    },
    {
      file: 'components/tabs/SalesTab.js',
      icon: 'ReceiptText',
      title: '출하 내역이 없습니다',
      action: '매출 기록',
      handler: 'setIsAdding(true)',
    },
    {
      file: 'components/tabs/ScheduleTab.js',
      icon: 'CalendarPlus',
      title: '예정된 일정이 없습니다',
      action: '일정 추가',
      handler: 'setIsAdding(true)',
    },
  ];

  for (const item of expectations) {
    const source = readSource(item.file);
    assert.match(source, /EmptyState/);
    assert.match(source, new RegExp(`icon=\\{${item.icon}\\}`));
    assert.match(source, new RegExp(`title="${item.title}"`));
    assert.match(source, new RegExp(item.action));
    assert.match(source, new RegExp(item.handler.replace(/[()]/g, '\\$&')));
  }
});
