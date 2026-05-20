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

test('operational create forms stay open when async submit handlers fail', () => {
  const expectations = [
    {
      file: 'components/tabs/SalesTab.js',
      submit: 'submitSale',
      handler: 'onCreateSale',
    },
    {
      file: 'components/tabs/InventoryTab.js',
      submit: 'submitNewItem',
      handler: 'onAddItem',
    },
    {
      file: 'components/tabs/ScheduleTab.js',
      submit: 'submitSchedule',
      handler: 'onCreateEvent',
    },
    {
      file: 'components/tabs/SettingsTab.js',
      submit: 'submitBuilding',
      handler: 'onCreateBuilding',
    },
  ];

  for (const item of expectations) {
    const source = readSource(item.file);
    assert.match(source, new RegExp(`const ${item.submit} = async \\(values\\) => \\{`));
    assert.match(source, new RegExp(`const saved = await ${item.handler}\\(values\\);`));
    assert.match(source, /if \(!saved\) \{\s+return;\s+\}/);
  }
});

test('cattle edit form delegates close behavior to the async update handler', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /<CattleForm cattle=\{selectedCow\} buildings=\{buildings\} onSubmit=\{handleUpdateCattle\}/);
  assert.match(source, /const result = await updateCattle\(updated\.id, updated\);/);
  assert.match(source, /if \(result\.success\) \{[\s\S]*?setIsEditing\(false\);/);
  assert.doesNotMatch(source, /onSubmit=\{\(updated\) => \{ handleUpdateCattle\(updated\); setIsEditing\(false\); \}\}/);
});

test('feed record form preserves input when async save fails', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /const submitFeedRecord = async \(values\) => \{/);
  assert.match(source, /const recorded = await onRecordFeed\(\{\s+\.\.\.values,\s+buildingId: selectedBuilding,\s+\}\);/);
  assert.match(source, /if \(!recorded\) \{\s+return;\s+\}/);
  assert.match(source, /reset\(\{\s+\.\.\.createFeedRecordValues\(\),\s+date: values\.date,\s+\}\);/);
});

test('feed record form waits for async saves before re-enabling submit', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
  assert.match(source, /setIsSaving\(true\);/);
  assert.match(source, /await onRecordFeed\(\{/);
  assert.match(source, /finally \{\s+setIsSaving\(false\);/);
  assert.match(source, /type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}/);
});

test('feed building filter chips expose selected state and Korean labels', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /function FilterChip\(\{ active, children, onClick, label, disabled = false \}\)/);
  assert.match(source, /disabled=\{disabled\}/);
  assert.match(source, /aria-pressed=\{active\}/);
  assert.match(source, /aria-label=\{label\}/);
  assert.match(source, /label="전체 축사 급여 보기"/);
  assert.match(source, /label=\{`\$\{building\.name\} 급여 보기`\}/);
});

test('feed record form fields expose labels and validation state', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /<PremiumLabel htmlFor="feed-date">/);
  assert.match(source, /id="feed-date"[\s\S]*?aria-invalid=\{Boolean\(errors\.date\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="feed-note">/);
  assert.match(source, /id="feed-note"[\s\S]*?aria-invalid=\{Boolean\(errors\.note\)\}/);
  assert.match(source, /const fieldId = `feed-\$\{inputProps\.name\}`;/);
  assert.match(source, /<PremiumLabel htmlFor=\{fieldId\}>/);
  assert.match(source, /id=\{fieldId\}[\s\S]*?aria-invalid=\{Boolean\(error\)\}/);
});

test('feed record form validation messages are announced with their controls', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /id="feed-date"[\s\S]*?aria-describedby=\{errors\.date \? "feed-date-error" : undefined\}/);
  assert.match(source, /id="feed-date-error" role="alert"[\s\S]*?\{errors\.date\.message\}/);
  assert.match(source, /id="feed-note"[\s\S]*?aria-describedby=\{errors\.note \? "feed-note-error" : undefined\}/);
  assert.match(source, /id="feed-note-error" role="alert"[\s\S]*?\{errors\.note\.message\}/);
  assert.match(source, /const errorId = `\$\{fieldId\}-error`;/);
  assert.match(source, /aria-describedby=\{error \? errorId : undefined\}/);
  assert.match(source, /<div id=\{errorId\} role="alert" style=\{errorTextStyle\}>\{error\}<\/div>/);
});

test('inventory quantity edit preserves input when async save fails', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /const handleUpdate = async \(id\) => \{/);
  assert.match(source, /const saved = await onUpdateQuantity\(id, editQty\);/);
  assert.match(source, /if \(!saved\) \{\s+return;\s+\}/);
  assert.match(source, /setEditId\(null\);\s+setEditQty\(''\);/);
});

test('inventory quantity edit controls use Korean task labels', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 수정`\}/);
  assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 저장`\}/);
  assert.match(source, />\s*저장\s*<\/PremiumButton>/);
  assert.doesNotMatch(source, />\s*OK\s*<\/PremiumButton>/);
});
