import assert from 'node:assert/strict';
import test from 'node:test';

import {
  extractWeightHistoryPoints,
  normalizeCattleHistoryRows,
  parseCattleHistoryMetadata,
} from './cattle-history.mjs';

test('parseCattleHistoryMetadata parses valid JSON objects', () => {
  const result = parseCattleHistoryMetadata('{"from": 420, "to": 455}');

  assert.deepEqual(result.metadata, { from: 420, to: 455 });
  assert.equal(result.metadataParseError, false);
  assert.equal(result.metadataRaw, null);
});

test('parseCattleHistoryMetadata marks malformed JSON without throwing', () => {
  const result = parseCattleHistoryMetadata('{"from": 420');

  assert.equal(result.metadata, null);
  assert.equal(result.metadataParseError, true);
  assert.match(result.metadataRaw, /420/);
});

test('normalizeCattleHistoryRows preserves valid rows when one metadata cell is corrupt', () => {
  const rows = normalizeCattleHistoryRows([
    {
      id: 'history-1',
      eventType: 'weight',
      eventDate: '2026-04-01T00:00:00.000Z',
      metadata: '{"to": 455}',
    },
    {
      id: 'history-2',
      eventType: 'movement',
      eventDate: '2026-04-02T00:00:00.000Z',
      metadata: '{"fromBuilding": "A"',
    },
  ]);

  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0].metadata, { to: 455 });
  assert.equal(rows[0].metadataParseError, false);
  assert.equal(rows[1].metadata, null);
  assert.equal(rows[1].metadataParseError, true);
  assert.match(rows[1].metadataRaw, /fromBuilding/);
});

test('extractWeightHistoryPoints accepts multiple metadata field variants and skips invalid ones', () => {
  const points = extractWeightHistoryPoints([
    {
      id: 'history-1',
      eventType: 'weight',
      eventDate: '2026-04-01T00:00:00.000Z',
      metadata: { to: 455 },
    },
    {
      id: 'history-2',
      eventType: 'weight',
      eventDate: '2026-04-02T00:00:00.000Z',
      metadata: { newWeight: '470' },
    },
    {
      id: 'history-3',
      eventType: 'weight',
      eventDate: '2026-04-03T00:00:00.000Z',
      metadata: null,
    },
  ]);

  assert.deepEqual(points, [
    { eventDate: '2026-04-01T00:00:00.000Z', weight: 455 },
    { eventDate: '2026-04-02T00:00:00.000Z', weight: 470 },
  ]);
});
