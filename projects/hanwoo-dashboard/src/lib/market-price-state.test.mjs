import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildUnavailableMarketPrice,
  MARKET_PRICE_FRESH_TTL_MS,
  normalizeCachedMarketPrice,
  normalizeLiveMarketPrice,
  shouldPersistLiveMarketPrice,
} from './market-price-state.mjs';

test('normalizeCachedMarketPrice returns a fresh trusted cache state for recent realtime snapshots', () => {
  const now = new Date('2026-04-07T12:00:00.000Z');
  const result = normalizeCachedMarketPrice(
    {
      issueDate: '2026-04-06',
      fetchedAt: '2026-04-07T11:40:00.000Z',
      isRealtime: true,
      bullGrade1pp: 21500,
      bullGrade1p: 19800,
      bullGrade1: 18500,
      cowGrade1pp: 18500,
      cowGrade1p: 17200,
      cowGrade1: 16000,
    },
    { now },
  );

  assert.equal(result.source, 'kape-cache');
  assert.equal(result.isStale, false);
  assert.equal(result.available, true);
  assert.equal(result.date, '2026.04.06');
});

test('normalizeCachedMarketPrice marks old trusted snapshots as degraded stale cache', () => {
  const now = new Date('2026-04-07T12:00:00.000Z');
  const result = normalizeCachedMarketPrice(
    {
      issueDate: '2026-04-05',
      fetchedAt: '2026-04-07T10:00:00.000Z',
      isRealtime: true,
      bullGrade1pp: 21500,
      bullGrade1p: 19800,
      bullGrade1: 18500,
      cowGrade1pp: 18500,
      cowGrade1p: 17200,
      cowGrade1: 16000,
    },
    { now, freshnessMs: MARKET_PRICE_FRESH_TTL_MS },
  );

  assert.equal(result.source, 'cache-stale');
  assert.equal(result.degraded, true);
  assert.equal(result.isRealtime, false);
  assert.match(result.message, /trusted KAPE snapshot/i);
});

test('normalizeCachedMarketPrice rejects legacy non-realtime snapshots so synthetic rows are ignored', () => {
  const result = normalizeCachedMarketPrice({
    issueDate: '2026-04-05',
    fetchedAt: '2026-04-07T10:00:00.000Z',
    isRealtime: false,
    bullGrade1pp: 21500,
    bullGrade1p: 19800,
    bullGrade1: 18500,
    cowGrade1pp: 18500,
    cowGrade1p: 17200,
    cowGrade1: 16000,
  });

  assert.equal(result, null);
});

test('normalizeLiveMarketPrice returns a persistable live KAPE state', () => {
  const now = new Date('2026-04-07T12:00:00.000Z');
  const result = normalizeLiveMarketPrice(
    {
      issueDate: '20260406',
      bull: { grade1pp: 21500, grade1p: 19800, grade1: 18500 },
      cow: { grade1pp: 18500, grade1p: 17200, grade1: 16000 },
    },
    { now },
  );

  assert.equal(result.source, 'kape-live');
  assert.equal(result.available, true);
  assert.equal(result.issueDate, '2026-04-06');
  assert.equal(shouldPersistLiveMarketPrice(result), true);
});

test('normalizeLiveMarketPrice rejects incomplete live payloads', () => {
  const result = normalizeLiveMarketPrice({
    issueDate: '20260406',
    bull: { grade1pp: 21500, grade1p: 19800, grade1: 0 },
    cow: { grade1pp: 18500, grade1p: 17200, grade1: 16000 },
  });

  assert.equal(result, null);
});

test('buildUnavailableMarketPrice returns an explicit degraded unavailable state', () => {
  const now = new Date('2026-04-07T12:00:00.000Z');
  const result = buildUnavailableMarketPrice({ now });

  assert.equal(result.available, false);
  assert.equal(result.source, 'unavailable');
  assert.equal(result.degraded, true);
  assert.equal(result.bull, null);
});
