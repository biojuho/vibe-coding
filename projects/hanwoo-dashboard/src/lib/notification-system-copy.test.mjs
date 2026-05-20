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

test('notification system trigger exposes a Korean accessible label', () => {
  const source = readSource('components/layout/NotificationSystem.js');
  const tsxSource = readSource('components/layout/NotificationSystem.tsx');

  for (const candidate of [source, tsxSource]) {
    assert.match(candidate, /const notificationLabel = unreadCount > 0/);
    assert.match(candidate, /알림 열기, 읽지 않은 알림/);
    assert.match(candidate, /aria-label=\{notificationLabel\}/);
    assert.match(candidate, /title=\{notificationLabel\}/);
    assert.match(candidate, /aria-hidden="true"/);
    assert.doesNotMatch(candidate, /aria-label="Notifications"/);
    assert.doesNotMatch(candidate, /title="Notifications"/);
  }

  assert.match(source, /BellIcon className="h-5 w-5" aria-hidden="true"/);
  assert.match(tsxSource, /Bell className="h-4 w-4" aria-hidden="true"/);
});

test('notification widget visible heading uses Korean product copy', () => {
  const source = readSource('components/widgets/NotificationWidget.js');

  assert.match(source, /우선 확인 알림/);
  assert.doesNotMatch(source, /Priority Alerts/);
});

test('typescript notification system mirror keeps the same accessible trigger contract', () => {
  const source = readSource('components/layout/NotificationSystem.tsx');

  assert.match(source, /initialNotifications = \[\]/);
  assert.match(source, /useState\(initialNotifications\)/);
  assert.match(source, /notifications\.filter\(\(notification\) => !notification\.read\)\.length/);
  assert.match(source, /알림 열기, 읽지 않은 알림/);
  assert.match(source, /aria-label=\{notificationLabel\}/);
  assert.match(source, /title=\{notificationLabel\}/);
  assert.match(source, /Bell className="h-4 w-4" aria-hidden="true"/);
  assert.match(source, /\{unreadCount > 0 && \(/);
  assert.match(source, /aria-hidden="true"/);
  assert.doesNotMatch(source, /aria-label="Notifications"/);
  assert.doesNotMatch(source, /title="Notifications"/);
});

test('notification systems only show unread badges when there are unread items', () => {
  const source = readSource('components/layout/NotificationSystem.js');
  const tsxSource = readSource('components/layout/NotificationSystem.tsx');

  for (const candidate of [source, tsxSource]) {
    assert.match(candidate, /\{unreadCount > 0 && \(/);
    assert.match(candidate, /aria-hidden="true"/);
  }
});

test('notification mark-all actions use safe button semantics', () => {
  const source = readSource('components/layout/NotificationSystem.js');
  const tsxSource = readSource('components/layout/NotificationSystem.tsx');

  for (const candidate of [source, tsxSource]) {
    assert.match(candidate, /<button\s+type="button"\s+onClick=\{markAllAsRead\}/);
  }
});

test('notification system does not seed demo farm alerts by default', () => {
  const source = readSource('components/layout/NotificationSystem.js');
  const tsxSource = readSource('components/layout/NotificationSystem.tsx');

  for (const candidate of [source, tsxSource]) {
    assert.match(candidate, /initialNotifications = \[\]/);
    assert.match(candidate, /새로운 알림이 없습니다/);
    assert.doesNotMatch(candidate, /useState\(\[/);
    assert.doesNotMatch(candidate, /NOTIFICATIONS = \[/);
    assert.doesNotMatch(candidate, /암소 #?\d+/);
    assert.doesNotMatch(candidate, /재고가 10% 미만입니다/);
  }
});

test('clickable dropdown menu items use native button semantics', () => {
  const source = readSource('components/ui/dropdown-menu.js');

  assert.match(source, /const Element = onClick \? 'button' : 'div'/);
  assert.match(source, /type=\{onClick \? 'button' : undefined\}/);
  assert.match(source, /focus:ring-2/);
  assert.doesNotMatch(source, /<div\s+[^>]*onClick=\{onClick\}/);
});
