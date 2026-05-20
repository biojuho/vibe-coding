import assert from 'node:assert/strict';
import test from 'node:test';

import { buildCattleCsvRows } from './cattle-csv-export.mjs';

test('buildCattleCsvRows exports cattle data with Korean headers', () => {
  const csv = buildCattleCsvRows([
    {
      id: 'cow-1',
      name: '복순이',
      tagNumber: '410001234567',
      birthDate: '2025-01-02T00:00:00.000Z',
      gender: '암',
      status: '사육중',
      buildingId: 'barn-1',
      penNumber: 'A-1',
      memo: '예방접종, 확인',
    },
  ]);

  assert.match(csv, /^\uFEFFID,이름,이력번호,생년월일,성별,상태,축사 ID,칸 번호,메모/);
  assert.match(csv, /복순이/);
  assert.match(csv, /예방접종 확인/);
  assert.doesNotMatch(csv, /Name|Tag Number|Birth Date|Gender|Status|Building ID|Pen Number|Memo/);
});
