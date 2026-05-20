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

test('payment widget exposes Korean product copy for checkout states', () => {
  const source = readSource('components/payment/PaymentWidget.js');

  assert.match(source, /구독 결제/);
  assert.match(source, /결제 수단을 불러오는 중입니다/);
  assert.match(source, /결제를 준비하고 있습니다/);
  assert.match(source, /결제하기/);
  assert.doesNotMatch(source, /Subscription checkout/);
  assert.doesNotMatch(source, /Loading payment methods/);
  assert.doesNotMatch(source, /Preparing payment/);
  assert.doesNotMatch(source, /Pay KRW/);
});

test('subscription result pages avoid bare English loading and status copy', () => {
  const successSource = readSource('app/subscription/success/page.js');
  const failSource = readSource('app/subscription/fail/page.js');

  assert.match(successSource, /결제가 완료되었습니다/);
  assert.match(successSource, /결제 정보를 불러오는 중입니다/);
  assert.match(successSource, /결제 확인을 다시 시도합니다/);
  assert.doesNotMatch(successSource, /Loading\.\.\./);
  assert.doesNotMatch(successSource, /Payment confirmed/);
  assert.doesNotMatch(successSource, /Processing\.\.\./);

  assert.match(failSource, /결제를 완료하지 못했습니다/);
  assert.match(failSource, /결제 실패 정보를 불러오는 중입니다/);
  assert.match(failSource, /오류 코드/);
  assert.doesNotMatch(failSource, /Loading\.\.\./);
  assert.doesNotMatch(failSource, /Code:/);
});
