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

	assert.match(source, /function normalizePaymentWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /function normalizePaymentAmount\(amount\) \{/);
	assert.match(source, /typeof amount === ["']number["'] && Number\.isFinite\(amount\)/);
	assert.match(source, /const parsedAmount = Number\(amount\);/);
	assert.match(source, /export default function PaymentWidget\(options = \{\}\) \{/);
	assert.match(source, /normalizePaymentWidgetOptions\(options\);/);
	assert.match(
		source,
		/const \[price\] = useState\(\(\) => normalizePaymentAmount\(amount\)\);/,
	);
	assert.doesNotMatch(source, /export default function PaymentWidget\(\{\s+clientKey,/);

	assert.match(source, /const paymentRequestInFlightRef = useRef\(false\)/);
	assert.match(source, /const isMountedRef = useRef\(false\)/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;\s+return \(\) => \{\s+isMountedRef\.current = false;\s+paymentRequestInFlightRef\.current = false;\s+\};\s+\}, \[\]\);/,
	);
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
		/finally \{\s+paymentRequestInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSubmitting\(false\);\s+\}/,
	);
	assert.doesNotMatch(
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
		/reject\(new TimeoutError\(message, timeoutMs\)\);/,
	);
	assert.match(
		source,
		/if \(timeoutId !== null\) \{\s+try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.doesNotMatch(source, /timeoutId = setTimeout\(/);
	assert.doesNotMatch(source, /\sclearTimeout\(timeoutId\);/);
});

test("payment widget load-state reset avoids lint suppressions", () => {
	const source = readSource("components/payment/PaymentWidget.js");

	assert.match(source, /function deferPaymentWidgetTask\(callback\) \{/);
	assert.match(
		source,
		/try \{\s+queueMicrotask\(callback\);\s+\} catch \{\s+Promise\.resolve\(\)\.then\(callback\);/,
	);
	assert.match(
		source,
		/deferPaymentWidgetTask\(\(\) => \{\s+if \(!cancelled\) \{\s+setIsWidgetReady\(false\);\s+setErrorMessage\(""\);/,
	);
	assert.doesNotMatch(
		source,
		/queueMicrotask\(\(\) => \{\s+if \(!cancelled\) \{/,
	);
	assert.doesNotMatch(source, /eslint-disable/);
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
	assert.match(
		successSource,
		/import \{ normalizePaymentKey, normalizePaymentOrderId \} from ["']@\/lib\/subscription["'];/,
	);
	assert.match(
		successSource,
		/function normalizeSubscriptionFallbackOptions\(options\) \{/,
	);
	assert.match(
		successSource,
		/function SubscriptionFallback\(options = \{\}\) \{/,
	);
	assert.match(
		successSource,
		/const \{ message \} = normalizeSubscriptionFallbackOptions\(options\);/,
	);
	assert.match(successSource, /const AMOUNT_INPUT_PATTERN = \/\^\\d\+\$\/;/);
	assert.match(successSource, /const PAYMENT_INVALID_REDIRECT_MESSAGE/);
	assert.match(successSource, /function parsePaymentAmount\(value\)/);
	assert.match(
		successSource,
		/const paymentAmount = parsePaymentAmount\(amount\);/,
	);
	assert.match(
		successSource,
		/const paymentKey = normalizePaymentKey\(searchParams\.get\("paymentKey"\)\);/,
	);
	assert.match(
		successSource,
		/const orderId = normalizePaymentOrderId\(searchParams\.get\("orderId"\)\);/,
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
	assert.match(failSource, /const PAYMENT_FAILURE_GENERIC_MESSAGE/);
	assert.match(failSource, /const PAYMENT_FAILURE_MESSAGES = \{/);
	assert.match(failSource, /PAY_PROCESS_CANCELED:/);
	assert.match(
		failSource,
		/결제 진행이 취소되어 완료되지 않았습니다\. 필요하면 다시 시도해 주세요\./,
	);
	assert.match(failSource, /PAY_PROCESS_ABORTED:/);
	assert.match(
		failSource,
		/결제 요청 또는 결제 수단 인증 중 문제가 발생했습니다\./,
	);
	assert.match(failSource, /REJECT_CARD_COMPANY:/);
	assert.match(
		failSource,
		/카드사에서 결제를 승인하지 않았습니다\. 카드 정보를 확인하거나 다른 결제 수단을 선택해 주세요\./,
	);
	assert.match(failSource, /function normalizePaymentFailureCode\(value\) \{/);
	assert.match(
		failSource,
		/typeof value === ["']string["'] && value\.trim\(\)/,
	);
	assert.match(failSource, /function getPaymentFailureMessage\(code\) \{/);
	assert.match(
		failSource,
		/PAYMENT_FAILURE_MESSAGES\[code\] \|\| PAYMENT_FAILURE_GENERIC_MESSAGE/,
	);
	assert.match(
		failSource,
		/const PAYMENT_FAILURE_ORDER_ID_PATTERN = \/\^\[A-Za-z0-9_-\]\{6,128\}\$\/;/,
	);
	assert.match(failSource, /function normalizePaymentFailureOrderId\(value\) \{/);
	assert.match(
		failSource,
		/PAYMENT_FAILURE_ORDER_ID_PATTERN\.test\(orderId\) \? orderId : ["']["']/,
	);
	assert.match(failSource, /overflowWrap: ["']anywhere["']/);
	assert.match(
		failSource,
		/function normalizeSubscriptionFallbackOptions\(options\) \{/,
	);
	assert.match(
		failSource,
		/function SubscriptionFallback\(options = \{\}\) \{/,
	);
	assert.match(
		failSource,
		/const \{ message \} = normalizeSubscriptionFallbackOptions\(options\);/,
	);
	assert.match(failSource, /const PAYMENT_RETRY_PATH = ["']\/subscription["'];/);
	assert.match(
		failSource,
		/const PAYMENT_RETRY_PENDING_MESSAGE = ["']결제 화면으로 이동하고 있습니다\.["'];/,
	);
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
		/const \[isRetrying, setIsRetrying\] = useState\(false\);/,
	);
	assert.match(
		failSource,
		/const PAYMENT_FAILURE_CODE_FALLBACK = ["']미전달["'];/,
	);
	assert.doesNotMatch(failSource, /useRouter/);
	assert.match(
		failSource,
		/function navigateToPaymentRetry\(\) \{\s+if \(typeof window === ["']undefined["']\) \{/,
	);
	assert.match(
		failSource,
		/window\.location\.assign\(PAYMENT_RETRY_PATH\);/,
	);
	assert.match(
		failSource,
		/const errorCode = normalizePaymentFailureCode\(searchParams\.get\(["']code["']\)\);/,
	);
	assert.match(
		failSource,
		/const orderId = normalizePaymentFailureOrderId\(searchParams\.get\(["']orderId["']\)\);/,
	);
	assert.match(
		failSource,
		/const failureMessage = getPaymentFailureMessage\(errorCode\);/,
	);
	assert.match(
		failSource,
		/const retryButtonLabel = isRetrying\s+\? PAYMENT_RETRY_PENDING_MESSAGE\s+: ["']결제 화면으로 돌아가 다시 시도하기["'];/,
	);
	assert.match(failSource, /\{failureMessage\}/);
	assert.match(failSource, /문의용 주문번호/);
	assert.match(failSource, /\{orderId \? \(/);
	assert.doesNotMatch(failSource, /오류 코드 미전달/);
	assert.match(
		failSource,
		/const handleRetry = \(\) => \{\s+if \(isRetrying\) \{\s+return;\s+\}\s+setRetryStatus\(PAYMENT_RETRY_PENDING_MESSAGE\);\s+setIsRetrying\(true\);\s+try \{\s+navigateToPaymentRetry\(\);\s+\} catch \(error\) \{/,
	);
	assert.doesNotMatch(failSource, /router\.push\(PAYMENT_RETRY_PATH\)/);
	assert.match(
		failSource,
		/console\.error\(["']Payment retry navigation failed:/,
	);
	assert.match(failSource, /setIsRetrying\(false\);/);
	assert.match(
		failSource,
		/setRetryStatus\(PAYMENT_RETRY_NAVIGATION_ERROR_MESSAGE\);/,
	);
	assert.doesNotMatch(failSource, /router\.back\(\)/);
	assert.doesNotMatch(
		failSource,
		/Payment retry fallback navigation failed:/,
	);
	assert.match(
		failSource,
		/role="status"\s+aria-live="polite"\s+aria-atomic="true"/,
	);
	assert.match(
		failSource,
		/type="button"\s+onClick=\{handleRetry\}\s+disabled=\{isRetrying\}\s+aria-busy=\{isRetrying\}\s+aria-label=\{retryButtonLabel\}\s+title=\{retryButtonLabel\}/,
	);
	assert.match(failSource, /cursor: isRetrying \? ["']wait["'] : ["']pointer["']/);
	assert.match(failSource, /opacity: isRetrying \? 0\.72 : 1/);
	assert.match(failSource, /\{isRetrying \? ["']이동 중입니다\.\.\.["'] : ["']다시 시도하기["']\}/);
	assert.doesNotMatch(failSource, /Loading\.\.\./);
	assert.doesNotMatch(failSource, /Code:/);
	assert.doesNotMatch(failSource, /searchParams\.get\(["']code["']\) \|\| ["']-["']/);
	assert.doesNotMatch(failSource, /searchParams\.get\(['"]message['"]\)/);
	assert.doesNotMatch(
		successSource,
		/function SubscriptionFallback\(\{ message \}\)/,
	);
	assert.doesNotMatch(
		failSource,
		/function SubscriptionFallback\(\{ message \}\)/,
	);
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

test("subscription success page recovers missing redirect parameters", () => {
	const source = readSource("app/subscription/success/page.js");

	assert.match(
		source,
		/const PAYMENT_CONFIRMATION_INITIAL_MESSAGE = ["']결제를 확인하고 있습니다\.["'];/,
	);
	assert.match(
		source,
		/const PAYMENT_MISSING_REDIRECT_MESSAGE =\s+["']결제 확인에 필요한 정보가 부족합니다\. 결제 화면으로 돌아가 다시 시도해 주세요\.["'];/,
	);
	assert.match(
		source,
		/const PAYMENT_INVALID_REDIRECT_MESSAGE =\s+["']결제 식별자 정보를 확인해 주세요\. 결제 화면으로 돌아가 다시 시도해 주세요\.["'];/,
	);
	assert.match(source, /const PAYMENT_RETRY_PATH = ["']\/subscription["'];/);
	assert.match(source, /const PAYMENT_SUCCESS_STATUS = ["']success["'];/);
	assert.match(
		source,
		/const \[status, setStatus\] = useState\(PAYMENT_CONFIRMATION_INITIAL_MESSAGE\);/,
	);
	assert.match(
		source,
		/const paymentKeyParam = searchParams\.get\("paymentKey"\);/,
	);
	assert.match(
		source,
		/const orderIdParam = searchParams\.get\("orderId"\);/,
	);
	assert.match(source, /const amountParam = searchParams\.get\("amount"\);/);
	assert.match(
		source,
		/const normalizedPaymentKey = normalizePaymentKey\(paymentKeyParam\);/,
	);
	assert.match(
		source,
		/const normalizedOrderId = normalizePaymentOrderId\(orderIdParam\);/,
	);
	assert.match(
		source,
		/const hasPaymentRedirectParameters = Boolean\(\s+paymentKeyParam && orderIdParam && amountParam,\s+\);/,
	);
	assert.match(
		source,
		/const hasInvalidPaymentRedirectIdentifiers = Boolean\(\s+hasPaymentRedirectParameters && \(!normalizedPaymentKey \|\| !normalizedOrderId\),\s+\);/,
	);
	assert.match(
		source,
		/const visibleStatus = !hasPaymentRedirectParameters\s+\? PAYMENT_MISSING_REDIRECT_MESSAGE\s+: hasInvalidPaymentRedirectIdentifiers\s+\? PAYMENT_INVALID_REDIRECT_MESSAGE\s+: status;/,
	);
	assert.match(
		source,
		/const shouldShowPaymentRetryLink =\s+visibleStatus === PAYMENT_MISSING_REDIRECT_MESSAGE \|\|\s+visibleStatus === PAYMENT_INVALID_REDIRECT_MESSAGE;/,
	);
	assert.match(
		source,
		/if \(!paymentKey \|\| !orderId \|\| !amount\) \{\s+return;\s+\}/,
	);
	assert.match(source, /setStatus\(PAYMENT_SUCCESS_STATUS\);/);
	assert.doesNotMatch(
		source,
		/if \(!paymentKey \|\| !orderId \|\| !amount\) \{\s+setStatus\(PAYMENT_MISSING_REDIRECT_MESSAGE\);/,
	);
	assert.match(source, /visibleStatus === PAYMENT_SUCCESS_STATUS/);
	assert.match(source, /shouldShowPaymentRetryLink \? \(/);
	assert.match(
		source,
		/<a[\s\S]*?href=\{PAYMENT_RETRY_PATH\}[\s\S]*?aria-label="결제 화면으로 돌아가기"[\s\S]*?title="결제 화면으로 돌아가기"/,
	);
	assert.match(source, />\s*결제 화면으로 돌아가기\s*<\/a>/);
});

test("subscription success timer callbacks ignore stale cleanup completions", () => {
	const source = readSource("app/subscription/success/page.js");

	assert.match(
		source,
		/let cancelled = false;[\s\S]*?const paymentAmount = parsePaymentAmount\(amount\);/,
	);
	assert.match(
		source,
		/const invalidAmountTimer = schedulePaymentStatusTimer\(\s+\(\) => \{\s+if \(!cancelled\) \{\s+setStatus\(PAYMENT_AMOUNT_ERROR_MESSAGE\);/,
	);
	assert.match(
		source,
		/return \(\) => \{\s+cancelled = true;\s+clearPaymentStatusTimer\(invalidAmountTimer\);/,
	);
	assert.match(
		source,
		/retryTimer = schedulePaymentStatusTimer\(\(\) => \{\s+if \(cancelled\) \{\s+return;\s+\}\s+try \{\s+router\.push\("\/"\);/,
	);
	assert.match(
		source,
		/console\.error\("Payment success redirect failed:", error\);\s+if \(!cancelled\) \{\s+setStatus\(PAYMENT_REDIRECT_ERROR_MESSAGE\);/,
	);
	assert.match(
		source,
		/retryTimer = schedulePaymentStatusTimer\(\(\) => \{\s+if \(!cancelled\) \{\s+void confirmPayment\(attempt \+ 1\);/,
	);
	assert.doesNotMatch(
		source,
		/const invalidAmountTimer = schedulePaymentStatusTimer\(\s+\(\) => setStatus\(PAYMENT_AMOUNT_ERROR_MESSAGE\)/,
	);
	assert.doesNotMatch(
		source,
		/retryTimer = schedulePaymentStatusTimer\(\(\) => \{\s+void confirmPayment\(attempt \+ 1\);/,
	);
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
	assert.match(
		prepareRoute,
		/function normalizePaymentPrepareBody\(body\) \{/,
	);
	assert.match(
		prepareRoute,
		/body && typeof body === ["']object["'] && !Array\.isArray\(body\)/,
	);
	assert.match(
		prepareRoute,
		/const body = normalizePaymentPrepareBody\(await req\.json\(\)\);/,
	);
	assert.match(prepareRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(confirmRoute, /결제 승인에 필요한 정보가 부족합니다/);
	assert.match(confirmRoute, /결제 확인을 완료하지 못했습니다/);
	assert.match(confirmRoute, /function parsePaymentAmount\(value\)/);
	assert.match(confirmRoute, /normalizePaymentKey,/);
	assert.match(confirmRoute, /normalizePaymentOrderId,/);
	assert.match(
		confirmRoute,
		/function normalizePaymentConfirmBody\(body\) \{/,
	);
	assert.match(
		confirmRoute,
		/function normalizePaymentLogFailureOptions\(options\) \{/,
	);
	assert.match(
		confirmRoute,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(
		confirmRoute,
		/const body = normalizePaymentConfirmBody\(await req\.json\(\)\);/,
	);
	assert.match(
		confirmRoute,
		/const paymentKey = normalizePaymentKey\(body\?\.paymentKey\);/,
	);
	assert.match(
		confirmRoute,
		/const orderId = normalizePaymentOrderId\(body\?\.orderId\);/,
	);
	assert.match(confirmRoute, /async function markPaymentLogFailed\(options = \{\}\) \{/);
	assert.match(confirmRoute, /normalizePaymentLogFailureOptions\(options\)/);
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
		prepareRoute,
		/const body = await req\.json\(\);/,
	);
	assert.doesNotMatch(
		confirmRoute,
		/Missing payment confirmation fields|Order does not belong|Unexpected payment amount|Payment verification failed|TOSS_PAYMENTS_SECRET_KEY is not configured/,
	);
	assert.doesNotMatch(confirmRoute, /message: error\.message/);
	assert.doesNotMatch(confirmRoute, /const amount = Number\(body\?\.amount\)/);
	assert.doesNotMatch(
		confirmRoute,
		/const \{ paymentKey, orderId \} = body;/,
	);
	assert.doesNotMatch(
		confirmRoute,
		/const body = await req\.json\(\);\s+const \{ paymentKey, orderId \} = body;/,
	);
	assert.doesNotMatch(
		confirmRoute,
		/async function markPaymentLogFailed\(\{\s*orderId,\s*paymentKey,\s*amount\s*\}\)/,
	);
	assert.doesNotMatch(authGuard, /Authentication required/);
});
