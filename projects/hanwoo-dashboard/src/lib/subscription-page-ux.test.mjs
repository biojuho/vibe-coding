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

test("subscription page has metadata, main landmark, and SEO-friendly title", () => {
	const source = readSource("app/subscription/page.js");

	assert.match(source, /export const metadata = \{/);
	assert.match(source, /구독 관리 · Joolife 한우/);
	assert.match(source, /id="main-content"/);
	assert.match(source, /<main\b/);
	assert.match(source, /<\/main>/);
	assert.doesNotMatch(source, /return \(\s+<div\s+style=\{\{[\s\S]{0,80}maxWidth/);
});

test("subscription page requires authenticated session with login redirect", () => {
	const source = readSource("app/subscription/page.js");

	assert.match(source, /requireAuthenticatedSession\(\{ redirectToLogin: true \}\)/);
	assert.doesNotMatch(source, /requireAuthenticatedSession\(\)/);
});

test("subscription cancellation success banner is shown outside ActiveSubscriptionView", () => {
	const source = readSource("app/subscription/page.js");

	assert.match(source, /cancelStatus === ["']success["'] && subscriptionStatus\.status !== ["']ACTIVE["']/);
	assert.match(source, /role="status"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /구독이 해지되었습니다/);
});

test("subscription features grid renders a labelled list of premium features", () => {
	const source = readSource("app/subscription/page.js");

	assert.match(source, /AI 인사이트/);
	assert.match(source, /수익성 분석/);
	assert.match(source, /실시간 시세/);
	assert.match(source, /엑셀 내보내기/);
	assert.match(source, /스마트 알림/);
	assert.match(source, /features\.map/);
});

test("subscription active view shows next payment date and cancel button", () => {
	const source = readSource("app/subscription/page.js");

	assert.match(source, /function ActiveSubscriptionView\(/);
	assert.match(source, /프리미엄 구독 중/);
	assert.match(source, /다음 결제일:/);
	assert.match(source, /<CancelSubscriptionButton \/>/);
});

test("subscription trial view shows days remaining and payment widget", () => {
	const source = readSource("app/subscription/page.js");

	assert.match(source, /function TrialSubscriptionView\(/);
	assert.match(source, /무료 체험판 사용 중/);
	assert.match(source, /일 남았습니다/);
	assert.match(source, /<PaymentWidget/);
});

test("subscription success page uses main landmark and has aria-live for payment status", () => {
	const source = readSource("app/subscription/success/page.js");

	assert.match(source, /id="main-content"/);
	assert.match(source, /<main\b/);
	assert.match(source, /<\/main>/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /aria-atomic="true"/);
	assert.match(source, /결제가 완료되었습니다/);
});

test("subscription success page payment re-check button has aria-label", () => {
	const source = readSource("app/subscription/success/page.js");

	assert.match(source, /aria-label="결제 다시 확인하기"/);
	assert.match(source, /결제 다시 확인하기/);
});

test("CancelSubscriptionButton trigger has aria-label and confirm button has aria-busy", () => {
	const source = readSource("components/subscription/CancelSubscriptionButton.js");

	assert.match(source, /aria-label="구독 해지 확인 단계 열기"/);
	assert.match(source, /aria-busy=\{isPending\}/);
	assert.match(source, /aria-label=\{isPending \? "구독 해지 처리 중"/);
	assert.match(source, /구독 해지 최종 확인/);
});
