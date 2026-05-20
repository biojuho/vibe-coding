import assert from 'node:assert/strict';
import test from 'node:test';

import { buildSetupProgressItems } from './setup-progress.mjs';

test('buildSetupProgressItems identifies the next incomplete onboarding step', () => {
  const progress = buildSetupProgressItems({
    farmSettings: { name: '주호목장', location: '전북 남원' },
    buildings: [{ id: 'b1', name: '1동' }],
    cattleList: [],
    inventoryList: [],
    scheduleEvents: [],
  });

  assert.equal(progress.completed, 2);
  assert.equal(progress.total, 5);
  assert.equal(progress.percent, 40);
  assert.equal(progress.nextItem.id, 'cattle');
  assert.equal(progress.nextItem.actionId, 'add-cattle');
});

test('buildSetupProgressItems marks setup complete when all required operating data exists', () => {
  const progress = buildSetupProgressItems({
    farmSettings: { name: '주호목장', location: '전북 남원' },
    buildings: [{ id: 'b1' }],
    cattleList: [{ id: 'c1' }],
    inventoryList: [{ id: 'i1' }],
    scheduleEvents: [{ id: 's1' }],
  });

  assert.equal(progress.completed, 5);
  assert.equal(progress.percent, 100);
  assert.equal(progress.nextItem, null);
  assert.deepEqual(
    progress.items.map((item) => item.done),
    [true, true, true, true, true],
  );
});
