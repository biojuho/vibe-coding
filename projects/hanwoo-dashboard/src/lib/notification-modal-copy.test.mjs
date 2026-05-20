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

test('notification modal close button has Korean accessible copy', () => {
  const source = readSource('components/ui/NotificationModal.js');

  assert.match(source, /aria-label="닫기"/);
  assert.match(source, /title="닫기"/);
  assert.match(source, /<button\s+type="button"\s+onClick=\{onClose\}/);
  assert.doesNotMatch(source, /aria-label="Close"/);
  assert.doesNotMatch(source, /title="Close"/);
});

test('notification modal exposes dialog semantics with a visible title label', () => {
  const source = readSource('components/ui/NotificationModal.js');

  assert.match(source, /role="dialog"/);
  assert.match(source, /aria-modal="true"/);
  assert.match(source, /aria-labelledby="notification-modal-title"/);
  assert.match(source, /id="notification-modal-title"/);
  assert.match(source, /알림 센터/);
});

test('notification modal can be dismissed with Escape from the dialog surface', () => {
  const source = readSource('components/ui/NotificationModal.js');

  assert.match(source, /const handleDialogKeyDown = \(event\) => \{/);
  assert.match(source, /event\.key === 'Escape'/);
  assert.match(source, /event\.stopPropagation\(\);/);
  assert.match(source, /onKeyDown=\{handleDialogKeyDown\}/);
  assert.match(source, /tabIndex=\{-1\}/);
});

test('notification modal decorative status icons are hidden from assistive tech', () => {
  const source = readSource('components/ui/NotificationModal.js');

  assert.match(source, /className="animate-bounce" aria-hidden="true"/);
  assert.match(source, /<div aria-hidden="true" style=\{\{fontSize:"40px"/);
  assert.match(source, /className="animate-pulse" aria-hidden="true"/);
});

test('notification modal SMS action uses safe button semantics and Korean copy', () => {
  const source = readSource('components/ui/NotificationModal.js');

  assert.match(source, /<button\s+type="button"\s+onClick=\{onTestSMS\}/);
  assert.match(source, /문자 알림 연동이 필요하며 발송 비용이 발생할 수 있습니다\./);
  assert.doesNotMatch(source, /Twilio \/ Kakao API 연동 필요/);
});
