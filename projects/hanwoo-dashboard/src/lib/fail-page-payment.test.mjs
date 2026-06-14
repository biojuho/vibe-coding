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

test("FailContent normalizes payment failure code with fallback for missing values", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /function normalizePaymentFailureCode\(value\) \{/);
	assert.match(source, /PAYMENT_FAILURE_CODE_FALLBACK/);
	assert.match(source, /typeof value === ["']string["'] && value\.trim\(\)/);
	assert.match(source, /value\.trim\(\)\s*:\s*PAYMENT_FAILURE_CODE_FALLBACK/);
});

test("FailContent getPaymentFailureMessage returns generic fallback for unknown code", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /function getPaymentFailureMessage\(code\) \{/);
	assert.match(source, /PAYMENT_FAILURE_MESSAGES\[code\] \|\| PAYMENT_FAILURE_GENERIC_MESSAGE/);
	assert.match(source, /PAYMENT_FAILURE_GENERIC_MESSAGE/);
	assert.match(source, /결제 상태를 확인하지 못했습니다/);
});

test("FailContent normalizePaymentFailureOrderId validates orderId against pattern", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /function normalizePaymentFailureOrderId\(value\) \{/);
	assert.match(
		source,
		/PAYMENT_FAILURE_ORDER_ID_PATTERN\s*=\s*\/\^\[A-Za-z0-9_-\]\{6,128\}\$\//,
	);
	assert.match(source, /PAYMENT_FAILURE_ORDER_ID_PATTERN\.test\(orderId\)/);
	assert.match(source, /typeof value !== ["']string["']/);
});

test("FailContent button is type=button with aria-busy on retry", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /type="button"/);
	assert.match(source, /aria-busy=\{isRetrying\}/);
	assert.match(source, /disabled=\{isRetrying\}/);
	assert.match(
		source,
		/cursor: isRetrying \? ["']wait["'] : ["']pointer["']/,
	);
});

test("FailContent has accessible failure message with role=alert and aria-live", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /role="alert"/);
	assert.match(source, /aria-live="assertive"/);
	assert.match(source, /aria-atomic="true"/);
});

test("FailContent retry status feedback has role=status", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /role="status"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(
		source,
		/PAYMENT_RETRY_NAVIGATION_ERROR_MESSAGE/,
	);
	assert.match(source, /결제 화면으로 자동 이동하지 못했습니다/);
});

test("FailContent shows PAY_PROCESS_CANCELED and REJECT_CARD_COMPANY messages", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /PAY_PROCESS_CANCELED/);
	assert.match(source, /PAY_PROCESS_ABORTED/);
	assert.match(source, /REJECT_CARD_COMPANY/);
	assert.match(source, /카드사에서 결제를 승인하지 않았습니다/);
});

test("FailContent wrapped in Suspense with loading fallback", () => {
	const source = readSource("app/subscription/fail/page.js");

	assert.match(source, /<Suspense/);
	assert.match(source, /fallback=/);
	assert.match(source, /PAYMENT_FAILURE_LOADING_MESSAGE/);
	assert.match(source, /결제 실패 정보를 불러오는 중입니다/);
});
