import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("payment widget exposes Korean product copy for checkout states", () => {
	const source = readSource("components/payment/PaymentWidget.js");

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

test("payment widget waits for async payment requests before re-enabling checkout", () => {
	const source = readSource("components/payment/PaymentWidget.js");

	assert.match(source, /const paymentRequestInFlightRef = useRef\(false\)/);
	assert.match(
		source,
		/const \[isSubmitting, setIsSubmitting\] = useState\(false\)/,
	);
	assert.match(
		source,
		/const isPaymentButtonBusy = isSubmitting \|\| !isWidgetReady;/,
	);
	assert.match(
		source,
		/const paymentButtonLabel = isSubmitting\s+\? PAYMENT_PREPARING_MESSAGE\s+: !isWidgetReady\s+\? PAYMENT_WIDGET_PENDING_MESSAGE\s+: `\$\{PAYMENT_BUTTON_PREFIX\} \$\{price\.toLocaleString\(\)\}원`;/,
	);
	assert.match(
		source,
		/const handlePayment = async \(\) => \{\s+if \(paymentRequestInFlightRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(source, /paymentRequestInFlightRef\.current = true;/);
	assert.match(source, /setIsSubmitting\(true\);/);
	assert.match(
		source,
		/await paymentWidget\.requestPayment\(requestPayload\);/,
	);
	assert.match(
		source,
		/finally \{\s+paymentRequestInFlightRef\.current = false;\s+setIsSubmitting\(false\);/,
	);
	assert.match(source, /disabled=\{isPaymentButtonBusy\}/);
	assert.match(source, /aria-busy=\{isPaymentButtonBusy\}/);
	assert.match(source, /aria-label=\{paymentButtonLabel\}/);
	assert.match(source, /title=\{paymentButtonLabel\}/);
	assert.match(source, /cursor: isPaymentButtonBusy \? "wait" : "pointer"/);
	assert.match(source, /opacity: isPaymentButtonBusy \? 0\.72 : 1/);
	assert.match(source, /\{paymentButtonLabel\}/);
});

test("payment widget builds redirect URLs through a guarded helper", () => {
	const source = readSource("components/payment/PaymentWidget.js");

	assert.match(source, /const PAYMENT_SUCCESS_PATH = ["']\/subscription\/success["'];/);
	assert.match(source, /const PAYMENT_FAIL_PATH = ["']\/subscription\/fail["'];/);
	assert.match(source, /function buildPaymentRedirectUrl\(pathname\)/);
	assert.match(source, /if \(typeof window === ["']undefined["']\) \{/);
	assert.match(source, /new URL\(pathname, locationHref\)\.toString\(\)/);
	assert.match(
		source,
		/catch \(error\) \{\s+console\.error\(["']Payment redirect URL creation failed/,
	);
	assert.match(
		source,
		/successUrl: buildPaymentRedirectUrl\(PAYMENT_SUCCESS_PATH\)/,
	);
	assert.match(source, /failUrl: buildPaymentRedirectUrl\(PAYMENT_FAIL_PATH\)/);
	assert.doesNotMatch(source, /window\.location\.origin\}\/subscription/);
});

test("payment widget timeout scheduling and cleanup are guarded", () => {
	const source = readSource("components/payment/PaymentWidget.js");

	assert.match(source, /function withTimeout\(promise, timeoutMs, message\)/);
	assert.match(source, /let timeoutId = null;/);
	assert.match(
		source,
		/try \{\s+timeoutId = window\.setTimeout\(\s+\(\) => reject\(new TimeoutError\(message, timeoutMs\)\),\s+timeoutMs,\s+\);/,
	);
	assert.match(
		source,
		/console\.error\("Payment widget timeout scheduling failed", error\);/,
	);
	assert.match(
		source,
		/if \(timeoutId !== null\) \{\s+try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.doesNotMatch(source, /timeoutId = setTimeout\(/);
	assert.doesNotMatch(source, /\sclearTimeout\(timeoutId\);/);
});

test("subscription result pages avoid bare English loading and status copy", () => {
	const subscriptionSource = readSource("app/subscription/page.js");
	const successSource = readSource("app/subscription/success/page.js");
	const failSource = readSource("app/subscription/fail/page.js");

	assert.match(
		successSource,
		/role="status"\s+aria-live="polite"\s+aria-atomic="true"\s+aria-busy="true"/,
	);
	assert.match(
		failSource,
		/role="status"\s+aria-live="polite"\s+aria-atomic="true"\s+aria-busy="true"/,
	);
	assert.match(
		successSource,
		/aria-live="polite"\s+aria-atomic="true"/,
	);

	assert.match(subscriptionSource, /Joolife 프리미엄 구독/);
	assert.match(subscriptionSource, /월 9,900원/);
	assert.match(subscriptionSource, /더 안정적으로 사용해 주세요/);
	assert.doesNotMatch(subscriptionSource, /더 안정적으로 사용하세요/);
	assert.match(subscriptionSource, /Joolife 사용자/);
	assert.doesNotMatch(subscriptionSource, /Premium Subscription/);
	assert.doesNotMatch(subscriptionSource, /Start smarter farm management/);
	assert.doesNotMatch(subscriptionSource, /KRW 9,900 per month/);
	assert.doesNotMatch(subscriptionSource, /Joolife User/);

	assert.match(successSource, /결제가 완료되었습니다/);
	assert.match(successSource, /결제 정보를 불러오는 중입니다/);
	assert.match(successSource, /결제 확인을 다시 시도합니다/);
	assert.match(successSource, /결제 확인 중 오류가 발생했습니다/);
	assert.match(successSource, /대시보드로 자동 이동하지 못했습니다/);
	assert.match(successSource, /const AMOUNT_INPUT_PATTERN = \/\^\\d\+\$\/;/);
	assert.match(successSource, /function parsePaymentAmount\(value\)/);
	assert.match(
		successSource,
		/const paymentAmount = parsePaymentAmount\(amount\);/,
	);
	assert.match(successSource, /amount: paymentAmount/);
	assert.doesNotMatch(successSource, /Loading\.\.\./);
	assert.doesNotMatch(successSource, /Payment confirmed/);
	assert.doesNotMatch(successSource, /Processing\.\.\./);
	assert.doesNotMatch(successSource, /parseInt\(amount, 10\)/);
	assert.doesNotMatch(
		successSource,
		/setStatus\(`결제 확인 오류: \$\{error\.message\}`\)/,
	);
	assert.match(
		successSource,
		/try \{\s+router\.push\(["']\/["']\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		successSource,
		/console\.error\(["']Payment success redirect failed:/,
	);
	assert.match(
		successSource,
		/setStatus\(PAYMENT_REDIRECT_ERROR_MESSAGE\);/,
	);

	assert.match(failSource, /결제를 완료하지 못했습니다/);
	assert.match(failSource, /결제 실패 정보를 불러오는 중입니다/);
	assert.match(failSource, /오류 코드/);
	assert.match(failSource, /const PAYMENT_RETRY_PATH = ["']\/subscription["'];/);
	assert.match(failSource, /결제 화면으로 자동 이동하지 못했습니다/);
	assert.match(
		failSource,
		/import \{ Suspense, useState \} from ["']react["'];/,
	);
	assert.match(
		failSource,
		/const \[retryStatus, setRetryStatus\] = useState\(["']["']\);/,
	);
	assert.match(
		failSource,
		/const PAYMENT_FAILURE_CODE_FALLBACK = ["']오류 코드 미전달["'];/,
	);
	assert.match(
		failSource,
		/searchParams\.get\(["']code["']\) \|\| PAYMENT_FAILURE_CODE_FALLBACK/,
	);
	assert.match(failSource, /const PAYMENT_FAILURE_MESSAGE/);
	assert.match(
		failSource,
		/const handleRetry = \(\) => \{\s+setRetryStatus\(["']["']\);\s+try \{\s+router\.back\(\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		failSource,
		/console\.error\(["']Payment retry navigation failed:/,
	);
	assert.match(failSource, /router\.push\(PAYMENT_RETRY_PATH\);/);
	assert.match(
		failSource,
		/console\.error\(["']Payment retry fallback navigation failed:/,
	);
	assert.match(
		failSource,
		/setRetryStatus\(PAYMENT_RETRY_NAVIGATION_ERROR_MESSAGE\);/,
	);
	assert.match(
		failSource,
		/role="status"\s+aria-live="polite"\s+aria-atomic="true"/,
	);
	assert.match(
		failSource,
		/type="button"\s+onClick=\{handleRetry\}\s+aria-label="결제 화면으로 돌아가 다시 시도하기"\s+title="결제 화면으로 돌아가 다시 시도하기"/,
	);
	assert.doesNotMatch(failSource, /Loading\.\.\./);
	assert.doesNotMatch(failSource, /Code:/);
	assert.doesNotMatch(failSource, /searchParams\.get\(["']code["']\) \|\| ["']-["']/);
	assert.doesNotMatch(failSource, /searchParams\.get\(['"]message['"]\)/);
});

test("subscription success timers are guarded", () => {
	const source = readSource("app/subscription/success/page.js");

	assert.match(source, /function schedulePaymentStatusTimer\(callback, delay\) \{/);
	assert.match(source, /function clearPaymentStatusTimer\(timeoutId\) \{/);
	assert.match(
		source,
		/try \{\s+return window\.setTimeout\(callback, delay\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Payment success timer scheduling failed:", error\);/,
	);
	assert.match(source, /callback\(\);\s+return null;/);
	assert.match(source, /if \(timeoutId === null\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.match(source, /const invalidAmountTimer = schedulePaymentStatusTimer\(/);
	assert.match(source, /retryTimer = schedulePaymentStatusTimer\(\(\) => \{/);
	assert.match(source, /clearPaymentStatusTimer\(invalidAmountTimer\);/);
	assert.match(source, /clearPaymentStatusTimer\(retryTimer\);/);
	assert.doesNotMatch(source, /const invalidAmountTimer = setTimeout\(/);
	assert.doesNotMatch(source, /retryTimer = setTimeout\(/);
	assert.doesNotMatch(source, /clearTimeout\(invalidAmountTimer\)/);
	assert.doesNotMatch(source, /clearTimeout\(retryTimer\)/);
});

test("payment confirmation fallback messages use Korean product copy", () => {
	const source = readSource("lib/payment-confirmation.mjs");

	assert.match(source, /결제 승인을 확인하고 있습니다/);
	assert.match(source, /결제 확인에 실패했습니다/);
	assert.match(source, /승인된 결제 금액이 요청 금액과 일치하지 않습니다/);
	assert.match(source, /게이트웨이 응답/);
	assert.doesNotMatch(source, /Payment confirmation is still being verified/);
	assert.doesNotMatch(source, /Payment verification failed/);
	assert.doesNotMatch(source, /Confirmed payment amount does not match/);
	assert.doesNotMatch(source, /Gateway response:/);
});

test("payment API routes avoid English fallback copy in user responses", () => {
	const prepareRoute = readSource("app/api/payments/prepare/route.js");
	const confirmRoute = readSource("app/api/payments/confirm/route.js");
	const authGuard = readSource("lib/auth-guard.js");

	assert.match(
		prepareRoute,
		/결제 고객 정보가 현재 로그인 사용자와 일치하지 않습니다/,
	);
	assert.match(prepareRoute, /Joolife 사용자/);
	assert.match(prepareRoute, /function parsePaymentAmount\(value\)/);
	assert.match(prepareRoute, /AMOUNT_INPUT_PATTERN\.test\(value\)/);
	assert.match(prepareRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(confirmRoute, /결제 승인에 필요한 정보가 부족합니다/);
	assert.match(confirmRoute, /결제 확인을 완료하지 못했습니다/);
	assert.match(confirmRoute, /function parsePaymentAmount\(value\)/);
	assert.match(confirmRoute, /AMOUNT_INPUT_PATTERN\.test\(value\)/);
	assert.match(confirmRoute, /Number\.isSafeInteger\(amount\)/);
	assert.match(confirmRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(authGuard, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(authGuard, /로그인이 필요합니다/);
	assert.doesNotMatch(
		prepareRoute,
		/Joolife User|Customer key mismatch|Unexpected payment amount|Payment preparation failed/,
	);
	assert.doesNotMatch(prepareRoute, /message: error\.message/);
	assert.doesNotMatch(
		prepareRoute,
		/Number\(body\?\.amount \?\? PREMIUM_SUBSCRIPTION\.amount\)/,
	);
	assert.doesNotMatch(
		confirmRoute,
		/Missing payment confirmation fields|Order does not belong|Unexpected payment amount|Payment verification failed|TOSS_PAYMENTS_SECRET_KEY is not configured/,
	);
	assert.doesNotMatch(confirmRoute, /message: error\.message/);
	assert.doesNotMatch(confirmRoute, /const amount = Number\(body\?\.amount\)/);
	assert.doesNotMatch(authGuard, /Authentication required/);
});
