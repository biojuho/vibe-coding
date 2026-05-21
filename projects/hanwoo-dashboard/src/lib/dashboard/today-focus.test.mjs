import assert from 'node:assert/strict';
import test from 'node:test';

import { buildTodayFocusItems } from './today-focus.mjs';

test('buildTodayFocusItems prioritizes offline, critical alerts, schedules, and low stock', () => {
  const items = buildTodayFocusItems({
    isOnline: false,
    now: new Date('2026-05-18T10:00:00+09:00'),
    notifications: [
      { id: 'n1', level: 'critical', message: '12번 개체 분만 예정일이 임박했습니다.' },
      { id: 'n2', level: 'warning', message: '발정 알림' },
    ],
    scheduleEvents: [
      { id: 's2', title: '축사 소독', date: '2026-05-20', isCompleted: false },
      { id: 's1', title: '백신 접종', date: '2026-05-19', isCompleted: false },
    ],
    inventoryList: [
      { id: 'i1', name: '배합사료', quantity: 4, threshold: 5, unit: '포' },
      { id: 'i2', name: '장갑', quantity: 20, threshold: 5, unit: '개' },
    ],
    monthlySalesCount: 3,
  });

  assert.deepEqual(
    items.map((item) => item.id),
    ['offline', 'critical-alerts', 'next-schedule', 'low-stock'],
  );
  assert.equal(items[2].title, '백신 접종');
  assert.equal(items[2].detail, '내일 예정');
  assert.equal(items[3].detail, '배합사료: 4포 남음');
});

test('buildTodayFocusItems keeps a useful sales prompt when no urgent work exists', () => {
  const items = buildTodayFocusItems({
    now: new Date('2026-05-18T10:00:00+09:00'),
    monthlySalesCount: 0,
  });

  assert.deepEqual(items, [
    {
      id: 'monthly-sales',
      type: 'sales',
      title: '이번 달 출하 0두',
      detail: '출하 기록을 추가하면 월간 흐름이 살아납니다.',
      meta: '출하 기록',
      tone: 'neutral',
      targetTab: 'sales',
    },
  ]);
});

test('buildTodayFocusItems skips malformed schedule dates', () => {
  const items = buildTodayFocusItems({
    now: new Date('2026-05-18T10:00:00+09:00'),
    scheduleEvents: [
      { id: 'bad', title: '깨진 일정', date: 'not-a-date', isCompleted: false },
      { id: 'past', title: '지난 일정', date: '2026-05-17', isCompleted: false },
      { id: 'done', title: '완료 일정', date: '2026-05-18', isCompleted: true },
      { id: 'next', title: '정상 일정', date: '2026-05-19', isCompleted: false },
    ],
    monthlySalesCount: 0,
  });

  const scheduleItem = items.find((item) => item.id === 'next-schedule');
  assert.equal(scheduleItem?.title, '정상 일정');
  assert.equal(items.some((item) => item.title === '깨진 일정'), false);
});
