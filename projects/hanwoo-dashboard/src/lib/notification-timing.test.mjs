import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildNotificationTiming,
  formatNotificationTime,
  getNotificationTargetDate,
} from './notification-timing.mjs';

test('getNotificationTargetDate advances estrus alerts to the next expected cycle', () => {
  const result = getNotificationTargetDate('estrus', '2026-03-01T00:00:00.000Z', {
    now: '2026-04-07T00:00:00.000Z',
  });

  assert.equal(result?.toISOString(), '2026-04-12T00:00:00.000Z');
});

test('getNotificationTargetDate converts pregnancy dates into calving dates', () => {
  const result = getNotificationTargetDate('calving', '2026-01-01T00:00:00.000Z');

  assert.equal(result?.toISOString(), '2026-10-13T00:00:00.000Z');
});

test('buildNotificationTiming returns stable iso timestamps for estrus notifications', () => {
  const result = buildNotificationTiming('estrus', '2026-03-01T00:00:00.000Z', {
    now: '2026-04-07T00:00:00.000Z',
  });

  assert.equal(result.date, '2026-04-12T00:00:00.000Z');
  assert.equal(result.targetDate, '2026-04-12T00:00:00.000Z');
  assert.equal(result.time, formatNotificationTime('2026-04-12T00:00:00.000Z'));
});

test('buildNotificationTiming returns an empty shape for invalid dates', () => {
  const result = buildNotificationTiming('calving', 'not-a-date');

  assert.deepEqual(result, {
    date: null,
    time: '-',
    targetDate: null,
  });
});
