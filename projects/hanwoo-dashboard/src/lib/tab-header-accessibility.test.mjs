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

  assert.match(inventorySource, /<span aria-hidden="true" style=\{\{ fontSize: '20px', lineHeight: 1 \}\}>📦<\/span>/);
  assert.match(salesSource, /<span aria-hidden="true" style=\{\{ fontSize: '20px', lineHeight: 1 \}\}>💰<\/span>/);
  assert.match(scheduleSource, /<span aria-hidden="true" style=\{\{ fontSize: '20px', lineHeight: 1 \}\}>🗓️<\/span>/);
});
