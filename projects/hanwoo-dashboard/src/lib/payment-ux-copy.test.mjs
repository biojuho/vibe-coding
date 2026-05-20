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
  assert.match(source, /결제 요청을 완료하지 못했습니다/);
  assert.match(source, /결제하기/);
  assert.doesNotMatch(source, /Subscription checkout/);
  assert.doesNotMatch(source, /Loading payment methods/);
  assert.doesNotMatch(source, /Preparing payment/);
  assert.doesNotMatch(source, /Pay KRW/);
  assert.doesNotMatch(source, /setErrorMessage\(error\.message/);
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
  assert.match(successSource, /결제 확인 중 오류가 발생했습니다/);
  assert.doesNotMatch(successSource, /Loading\.\.\./);
  assert.doesNotMatch(successSource, /Payment confirmed/);
  assert.doesNotMatch(successSource, /Processing\.\.\./);
  assert.doesNotMatch(successSource, /setStatus\(`결제 확인 오류: \$\{error\.message\}`\)/);

  assert.match(failSource, /결제를 완료하지 못했습니다/);
  assert.match(failSource, /결제 실패 정보를 불러오는 중입니다/);
  assert.match(failSource, /오류 코드/);
  assert.match(failSource, /const PAYMENT_FAILURE_MESSAGE/);
  assert.match(failSource, /type="button"\s+onClick=\{\(\) => router\.back\(\)\}/);
  assert.doesNotMatch(failSource, /Loading\.\.\./);
  assert.doesNotMatch(failSource, /Code:/);
  assert.doesNotMatch(failSource, /searchParams\.get\(['"]message['"]\)/);
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

test('payment API routes avoid English fallback copy in user responses', () => {
  const prepareRoute = readSource('app/api/payments/prepare/route.js');
  const confirmRoute = readSource('app/api/payments/confirm/route.js');
  const authGuard = readSource('lib/auth-guard.js');

  assert.match(prepareRoute, /결제 고객 정보가 현재 로그인 사용자와 일치하지 않습니다/);
  assert.match(prepareRoute, /Joolife 사용자/);
  assert.match(confirmRoute, /결제 승인에 필요한 정보가 부족합니다/);
  assert.match(confirmRoute, /결제 확인을 완료하지 못했습니다/);
  assert.match(authGuard, /로그인이 필요합니다/);
  assert.doesNotMatch(
    prepareRoute,
    /Joolife User|Customer key mismatch|Unexpected payment amount|Payment preparation failed/,
  );
  assert.doesNotMatch(
    confirmRoute,
    /Missing payment confirmation fields|Order does not belong|Unexpected payment amount|Payment verification failed|TOSS_PAYMENTS_SECRET_KEY is not configured/,
  );
  assert.doesNotMatch(authGuard, /Authentication required/);
});
