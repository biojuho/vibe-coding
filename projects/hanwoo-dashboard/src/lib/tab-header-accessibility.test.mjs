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

test('primary tab header icons are decorative for assistive tech', () => {
  const inventorySource = readSource('components/tabs/InventoryTab.js');
  const salesSource = readSource('components/tabs/SalesTab.js');
  const scheduleSource = readSource('components/tabs/ScheduleTab.js');
  const feedSource = readSource('components/tabs/FeedTab.js');

  assert.match(inventorySource, /<span aria-hidden="true" style=\{\{ fontSize: '20px', lineHeight: 1 \}\}>📦<\/span>/);
  assert.match(salesSource, /<span aria-hidden="true" style=\{\{ fontSize: '20px', lineHeight: 1 \}\}>💰<\/span>/);
  assert.match(scheduleSource, /<span aria-hidden="true" style=\{\{ fontSize: '20px', lineHeight: 1 \}\}>🗓️<\/span>/);
  assert.match(feedSource, /<span className="section-header-icon" aria-hidden="true">🌾<\/span>/);
});

test('schedule form fields expose labels and validation state', () => {
  const scheduleSource = readSource('components/tabs/ScheduleTab.js');

  assert.match(scheduleSource, /<label htmlFor="schedule-title"[\s\S]*?>\s*일정 제목\s*<\/label>/);
  assert.match(scheduleSource, /id="schedule-title"[\s\S]*?aria-invalid=\{Boolean\(errors\.title\)\}/);
  assert.match(scheduleSource, /<label htmlFor="schedule-date"[\s\S]*?>\s*일정 날짜\s*<\/label>/);
  assert.match(scheduleSource, /id="schedule-date"[\s\S]*?aria-invalid=\{Boolean\(errors\.date\)\}/);
  assert.match(scheduleSource, /<label htmlFor="schedule-type"[\s\S]*?>\s*일정 종류\s*<\/label>/);
  assert.match(scheduleSource, /id="schedule-type"[\s\S]*?aria-invalid=\{Boolean\(errors\.type\)\}/);
});
