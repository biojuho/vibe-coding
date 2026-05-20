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
  const subscriptionSource = readSource('app/subscription/page.js');
  const successSource = readSource('app/subscription/success/page.js');
  const failSource = readSource('app/subscription/fail/page.js');

  assert.match(subscriptionSource, /Joolife 프리미엄 구독/);
  assert.match(subscriptionSource, /월 9,900원/);
  assert.match(subscriptionSource, /Joolife 사용자/);
  assert.doesNotMatch(subscriptionSource, /Premium Subscription/);
  assert.doesNotMatch(subscriptionSource, /Start smarter farm management/);
  assert.doesNotMatch(subscriptionSource, /KRW 9,900 per month/);
  assert.doesNotMatch(subscriptionSource, /Joolife User/);

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

test('payment confirmation fallback messages use Korean product copy', () => {
  const source = readSource('lib/payment-confirmation.mjs');

  assert.match(source, /결제 승인을 확인하고 있습니다/);
  assert.match(source, /결제 확인에 실패했습니다/);
  assert.match(source, /승인된 결제 금액이 요청 금액과 일치하지 않습니다/);
  assert.match(source, /게이트웨이 응답/);
  assert.doesNotMatch(source, /Payment confirmation is still being verified/);
  assert.doesNotMatch(source, /Payment verification failed/);
  assert.doesNotMatch(source, /Confirmed payment amount does not match/);
  assert.doesNotMatch(source, /Gateway response:/);
});
