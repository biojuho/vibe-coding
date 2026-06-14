// T-AB044: SuccessContent + CancelSubscriptionButton source-grep tests
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { strict as assert } from "node:assert";
import { describe, test } from "node:test";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const successSrc = readFileSync(
	join(root, "app/subscription/success/page.js"),
	"utf8",
);
const cancelBtnSrc = readFileSync(
	join(root, "components/subscription/CancelSubscriptionButton.js"),
	"utf8",
);

describe("SuccessContent payment confirmation", () => {
	test("CONFIRM_RETRY_LIMIT is 3", () => {
		assert.match(successSrc, /CONFIRM_RETRY_LIMIT\s*=\s*3/);
	});

	test("retry timer delay is 3000ms", () => {
		assert.match(successSrc, /CONFIRM_RETRY_DELAY_MS\s*=\s*3000/);
	});

	test("success state redirects to dashboard after 3s", () => {
		assert.match(successSrc, /3초 후 대시보드로 자동 이동/);
		assert.match(successSrc, /router\.push\(["']\/["']\)/);
	});

	test("paymentKey and orderId are normalized before use", () => {
		assert.match(successSrc, /normalizePaymentKey/);
		assert.match(successSrc, /normalizePaymentOrderId/);
	});

	test("missing params shows PAYMENT_MISSING_REDIRECT_MESSAGE", () => {
		assert.match(successSrc, /결제 확인에 필요한 정보가 부족합니다/);
	});

	test("invalid identifiers show PAYMENT_INVALID_REDIRECT_MESSAGE", () => {
		assert.match(successSrc, /결제 식별자 정보를 확인해 주세요/);
	});

	test("manual retry button is type=button with accessible label", () => {
		assert.match(successSrc, /type="button"/);
		assert.match(successSrc, /aria-label="결제 다시 확인하기"/);
	});

	test("Suspense wraps SuccessContent with loading fallback", () => {
		assert.match(successSrc, /Suspense/);
		assert.match(successSrc, /결제 정보를 불러오는 중입니다/);
	});
});

describe("CancelSubscriptionButton two-step confirm", () => {
	test("first button opens confirm step, not immediate cancel", () => {
		assert.match(cancelBtnSrc, /setConfirming\(true\)/);
		assert.match(cancelBtnSrc, /aria-label="구독 해지 확인 단계 열기"/);
	});

	test("confirm button shows aria-busy while isPending", () => {
		assert.match(cancelBtnSrc, /aria-busy=\{isPending\}/);
	});

	test("confirm button label changes to processing copy when pending", () => {
		assert.match(cancelBtnSrc, /구독 해지 처리 중/);
		assert.match(cancelBtnSrc, /구독 해지 최종 확인/);
	});

	test("cancel back button calls setConfirming(false)", () => {
		assert.match(cancelBtnSrc, /setConfirming\(false\)/);
	});
});
