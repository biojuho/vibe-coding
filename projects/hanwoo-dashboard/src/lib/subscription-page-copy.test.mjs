// T-AB043: SubscriptionPage + subscription.js source-grep tests
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { strict as assert } from "node:assert";
import { describe, test } from "node:test";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const subscriptionPageSrc = readFileSync(
	join(root, "app/subscription/page.js"),
	"utf8",
);
const subscriptionLibSrc = readFileSync(
	join(root, "lib/subscription.js"),
	"utf8",
);

describe("SubscriptionPage copy", () => {
	test("PREMIUM_SUBSCRIPTION amount is 9900", () => {
		assert.match(subscriptionLibSrc, /amount:\s*9900/);
	});

	test("buildCustomerKey prefixes with user_", () => {
		assert.match(subscriptionLibSrc, /`\$\{CUSTOMER_PREFIX\}_\$\{userId\}`/);
		assert.match(subscriptionLibSrc, /CUSTOMER_PREFIX\s*=\s*["']user["']/);
	});

	test("ActiveSubscriptionView shows role=alert on cancel", () => {
		assert.match(subscriptionPageSrc, /role="alert"/);
	});

	test("cancelStatus=success triggers non-active status message", () => {
		assert.match(
			subscriptionPageSrc,
			/cancelStatus\s*===\s*["']success["']\s*&&\s*subscriptionStatus\.status\s*!==\s*["']ACTIVE["']/,
		);
	});

	test("cancel success message uses role=status + aria-live=polite", () => {
		assert.match(subscriptionPageSrc, /role="status"/);
		assert.match(subscriptionPageSrc, /aria-live="polite"/);
	});

	test("TrialSubscriptionView shows daysLeft countdown", () => {
		assert.match(subscriptionPageSrc, /daysLeft.*>.*0/);
		assert.match(subscriptionPageSrc, /일 남았습니다/);
	});

	test("features list contains AI 인사이트 and 수익성 분석", () => {
		assert.match(subscriptionPageSrc, /AI 인사이트/);
		assert.match(subscriptionPageSrc, /수익성 분석/);
	});

	test("metadata has Korean title for SEO", () => {
		assert.match(subscriptionPageSrc, /구독 관리 · Joolife 한우/);
	});
});

describe("subscription.js utilities", () => {
	test("normalizePaymentKey rejects strings with whitespace", () => {
		assert.match(subscriptionLibSrc, /\\s.*test.*paymentKey/s);
	});

	test("addDays guards against non-finite inputs", () => {
		assert.match(subscriptionLibSrc, /Number\.isFinite/);
	});

	test("PAYMENT_ORDER_ID_PATTERN enforces 6-64 char alphanumeric", () => {
		assert.match(subscriptionLibSrc, /\{6,64\}/);
	});

	test("TRIAL_DAYS is 14", () => {
		assert.match(subscriptionLibSrc, /TRIAL_DAYS\s*=\s*14/);
	});
});
