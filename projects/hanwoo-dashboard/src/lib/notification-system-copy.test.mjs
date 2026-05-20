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

  assert.match(source, /const unreadCount = NOTIFICATIONS\.length/);
  assert.match(source, /알림 열기, 읽지 않은 알림/);
  assert.match(source, /aria-label=\{notificationLabel\}/);
  assert.match(source, /title=\{notificationLabel\}/);
  assert.match(source, /Bell className="h-4 w-4" aria-hidden="true"/);
  assert.match(source, /aria-hidden="true"/);
  assert.doesNotMatch(source, /aria-label="Notifications"/);
  assert.doesNotMatch(source, /title="Notifications"/);
});
