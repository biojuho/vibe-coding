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

test('inventory tab normalizes malformed inventory payloads before rendering', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /function normalizeInventoryItems\(inventory\)/);
  assert.match(source, /if \(!Array\.isArray\(inventory\)\) return \[\]/);
  assert.match(source, /\.filter\(\(item\) => item && typeof item === 'object'\)/);
  assert.match(source, /const safeInventory = normalizeInventoryItems\(inventory\);/);
  assert.match(source, /safeInventory\.map\(\(item\) => \{/);
  assert.match(source, /safeInventory\.length === 0/);
  assert.match(source, /id: item\.id \?\? `inventory-\$\{index\}`/);
  assert.match(source, /'재고명 미등록'/);
  assert.match(source, /unit: typeof item\.unit === 'string' && item\.unit\.trim\(\) \? item\.unit : '개'/);
  assert.doesNotMatch(source, /inventory\.map\(\(item\) => \{/);
  assert.doesNotMatch(source, /inventory\.length === 0/);
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
  assert.match(source, /const saveInFlightRef = useRef\(false\)/);
  assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
  assert.match(source, /saveInFlightRef\.current = true;/);
  assert.match(source, /setIsSaving\(true\);/);
  assert.match(source, /await onRecordFeed\(\{/);
  assert.match(source, /finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/);
  assert.match(source, /const submitButtonLabel = isSaving \? '급여 기록 저장 중' : '급여 기록 저장하기';/);
  assert.match(source, /type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/);
});

test('feed summaries normalize numeric inputs before aggregation', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /import \{ toFiniteNumber \} from '@\/lib\/utils';/);
  assert.match(source, /function toValidFeedDate\(value\) \{/);
  assert.match(source, /const date = value instanceof Date \? new Date\(value\.getTime\(\)\) : new Date\(value\);/);
  assert.match(source, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
  assert.match(source, /date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
  assert.match(source, /return date;/);
  assert.match(source, /function getFeedDateTime\(value\) \{/);
  assert.match(source, /return toValidFeedDate\(value\)\?\.getTime\(\) \?\? Number\.NEGATIVE_INFINITY;/);
  assert.match(source, /function formatFeedDateLabel\(value, options\) \{/);
  assert.match(source, /return date \? date\.toLocaleDateString\('ko-KR', options\) : '날짜 미등록';/);
  assert.match(source, /getFeedDateTime\(first\.date\) - getFeedDateTime\(second\.date\)/);
  assert.match(source, /const key = formatFeedDateLabel\(record\.date, \{ month: 'short', day: 'numeric' \}\);/);
  assert.match(source, /\{formatFeedDateLabel\(record\.date\)\}/);
  assert.match(source, /roughageTotal: \(toFiniteNumber\(standard\.roughageKg\) \* count\)\.toFixed\(1\)/);
  assert.match(source, /concentrateTotal: \(toFiniteNumber\(standard\.concentrateKg\) \* count\)\.toFixed\(1\)/);
  assert.match(source, /sum \+ toFiniteNumber\(value\.roughageTotal\)/);
  assert.match(source, /sum \+ toFiniteNumber\(value\.concentrateTotal\)/);
  assert.match(source, /sum \+ toFiniteNumber\(standardsMap\[row\.status\]\?\.roughageKg\)/);
  assert.match(source, /sum \+ toFiniteNumber\(standardsMap\[row\.status\]\?\.concentrateKg\)/);
  assert.match(source, /grouped\[key\]\.roughage \+= toFiniteNumber\(record\.roughage\);/);
  assert.match(source, /grouped\[key\]\.concentrate \+= toFiniteNumber\(record\.concentrate\);/);
  assert.doesNotMatch(source, /const date = new Date\(value\);/);
  assert.doesNotMatch(source, /new Date\(record\.date\)\.toLocaleDateString/);
  assert.doesNotMatch(source, /new Date\(first\.date\) - new Date\(second\.date\)/);
  assert.doesNotMatch(source, /parseFloat\(value\.roughageTotal\)/);
  assert.doesNotMatch(source, /parseFloat\(value\.concentrateTotal\)/);
  assert.doesNotMatch(source, /standardsMap\[row\.status\]\?\.roughageKg \|\| 0/);
  assert.doesNotMatch(source, /standardsMap\[row\.status\]\?\.concentrateKg \|\| 0/);
});

test('feed tab normalizes malformed payloads before rendering', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /function normalizeFeedItems\(items\) \{/);
  assert.match(source, /return Array\.isArray\(items\) \? items\.filter\(\(item\) => item && typeof item === 'object'\) : \[\];/);
  assert.match(source, /function normalizeFeedBuildings\(buildings\) \{/);
  assert.match(source, /id: building\.id \?\? `feed-building-\$\{index\}`/);
  assert.match(source, /'축사명 미등록'/);
  assert.match(source, /const safeCattle = useMemo\(\(\) => normalizeFeedItems\(cattle\), \[cattle\]\);/);
  assert.match(source, /const safeFeedStandards = useMemo\(\(\) => normalizeFeedItems\(feedStandards\), \[feedStandards\]\);/);
  assert.match(source, /const safeFeedHistory = useMemo\(\(\) => normalizeFeedItems\(feedHistory\), \[feedHistory\]\);/);
  assert.match(source, /const safeBuildings = useMemo\(\(\) => normalizeFeedBuildings\(buildings\), \[buildings\]\);/);
  assert.match(source, /safeFeedStandards\.forEach\(\(standard\) => \{/);
  assert.match(source, /safeCattle\.filter\(\(row\) => row\.status === status\)/);
  assert.match(source, /return safeCattle;/);
  assert.match(source, /\[\.\.\.safeFeedHistory\]\.sort/);
  assert.match(source, /safeBuildings\.map\(\(building\) => \(/);
  assert.match(source, /safeFeedHistory\.slice\(0, 5\)\.map\(\(record, index\) => \(/);
  assert.match(source, /key=\{record\.id \?\? `feed-record-\$\{index\}`\}/);
  assert.doesNotMatch(source, /feedStandards\.forEach\(\(standard\) => \{/);
  assert.doesNotMatch(source, /const count = cattle\.filter/);
  assert.doesNotMatch(source, /return cattle;/);
  assert.doesNotMatch(source, /\[\.\.\.feedHistory\]\.sort/);
  assert.doesNotMatch(source, /buildings\.map\(\(building\) => \(/);
  assert.doesNotMatch(source, /feedHistory\.slice\(0, 5\)\.map/);
});

test('feed building filter chips expose selected state and Korean labels', () => {
  const source = readSource('components/tabs/FeedTab.js');

  assert.match(source, /function FilterChip\(\{ active, children, onClick, label, disabled = false \}\)/);
  assert.match(source, /const actionLabel = disabled \? `\$\{label\} - 급여 기록 저장 중에는 변경할 수 없습니다` : label;/);
  assert.match(source, /disabled=\{disabled\}/);
  assert.match(source, /aria-busy=\{disabled\}/);
  assert.match(source, /aria-pressed=\{active\}/);
  assert.match(source, /aria-label=\{actionLabel\}/);
  assert.match(source, /title=\{actionLabel\}/);
  assert.match(source, /label="전체 축사 급여 보기" disabled=\{isSaving\}/);
  assert.match(source, /label=\{`\$\{building\.name\} 급여 보기`\}[\s\S]*?disabled=\{isSaving\}/);
});

test('feed tab visible copy is readable Korean product copy', () => {
  const source = readSource('components/tabs/FeedTab.js');

  const expectedCopy = [
    '축사를 먼저 선택해 주세요.',
    '급여 기록은 특정 축사 기준으로 저장됩니다.',
    '사료 급여 모니터링',
    '오늘 급여 가이드',
    '조사료 권장량',
    '배합사료 권장량',
    '오늘 급여 기록',
    '기록 날짜',
    '특이사항 메모',
    '사료 상태, 섭취 변화, 축사 메모를 적어 주세요.',
    '급여 기록 저장하기',
    '최근 급여 추이',
    '최근 기록',
    '날짜 미등록',
  ];

  for (const copy of expectedCopy) {
    assert.equal(source.includes(copy), true);
  }

  assert.equal(source.includes('湲됱뿬'), false);
  assert.equal(source.includes('異뺤궗'), false);
  assert.equal(source.includes('議곗궗猷'), false);
  assert.equal(source.includes('諛고빀'), false);
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

  assert.match(source, /id="feed-date"[\s\S]*?aria-describedby=\{errors\.date \? 'feed-date-error' : undefined\}/);
  assert.match(source, /id="feed-date-error" role="alert"[\s\S]*?\{errors\.date\.message\}/);
  assert.match(source, /id="feed-note"[\s\S]*?aria-describedby=\{errors\.note \? 'feed-note-error' : undefined\}/);
  assert.match(source, /id="feed-note-error" role="alert"[\s\S]*?\{errors\.note\.message\}/);
  assert.match(source, /const errorId = `\$\{fieldId\}-error`;/);
  assert.match(source, /aria-describedby=\{error \? errorId : undefined\}/);
  assert.match(source, /<div id=\{errorId\} role="alert" style=\{errorTextStyle\}>\{error\}<\/div>/);
});

test('inventory quantity edit preserves input when async save fails', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /const handleUpdate = async \(id\) => \{/);
  assert.match(source, /const parsedQuantity = parseInlineQuantityInput\(editQty\);/);
  assert.match(source, /const saved = await onUpdateQuantity\(id, parsedQuantity\);/);
  assert.match(source, /if \(!saved\) \{\s+return;\s+\}/);
  assert.match(source, /setEditId\(null\);\s+setEditQty\(''\);/);
});

test('inventory create form waits for async saves before re-enabling submit', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /const saveInFlightRef = useRef\(false\)/);
  assert.match(source, /const submitButtonLabel = isSaving \? '재고 등록 중' : '재고 등록하기';/);
  assert.match(source, /const submitNewItem = async \(values\) => \{/);
  assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
  assert.match(source, /saveInFlightRef\.current = true;/);
  assert.match(source, /setIsSaving\(true\);/);
  assert.match(source, /const saved = await onAddItem\(values\);/);
  assert.match(source, /finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/);
  assert.match(source, /type="submit"\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/);
});

test('inventory quantity edit controls use Korean task labels', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 수정`\}/);
  assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 저장`\}/);
  assert.match(source, />\s*저장\s*<\/PremiumButton>/);
  assert.doesNotMatch(source, />\s*OK\s*<\/PremiumButton>/);
});
