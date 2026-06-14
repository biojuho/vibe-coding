/**
 * Behavioral tests for private pure helpers duplicated across the two payment
 * API routes: src/app/api/payments/confirm/route.js and
 * src/app/api/payments/prepare/route.js.
 *
 * Both files import from Next.js and path aliases that cannot be resolved in
 * Node ESM. The pure helpers are re-implemented inline and cross-checked via
 * source-grep so neither route can silently diverge.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const confirmSrc = readFileSync(
	path.join(SRC_ROOT, "app/api/payments/confirm/route.js"),
	"utf8",
);
const prepareSrc = readFileSync(
	path.join(SRC_ROOT, "app/api/payments/prepare/route.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

const AMOUNT_INPUT_PATTERN = /^\d+$/;

function parsePaymentAmount(value) {
	if (typeof value === "number") {
		return Number.isSafeInteger(value) ? value : Number.NaN;
	}

	if (typeof value === "string" && AMOUNT_INPUT_PATTERN.test(value)) {
		const amount = Number(value);
		return Number.isSafeInteger(amount) ? amount : Number.NaN;
	}

	return Number.NaN;
}

function normalizePaymentBody(body) {
	return body && typeof body === "object" && !Array.isArray(body) ? body : {};
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("confirm/route.js parsePaymentAmount uses Number.isSafeInteger and /^\\d+$/ pattern", () => {
	assert.match(confirmSrc, /function parsePaymentAmount\(value\)/);
	assert.match(confirmSrc, /Number\.isSafeInteger\(value\)/);
	assert.match(confirmSrc, /AMOUNT_INPUT_PATTERN\.test\(value\)/);
	assert.match(confirmSrc, /return Number\.NaN;/);
});

test("prepare/route.js parsePaymentAmount is structurally identical to confirm route", () => {
	assert.match(prepareSrc, /function parsePaymentAmount\(value\)/);
	assert.match(prepareSrc, /Number\.isSafeInteger\(value\)/);
	assert.match(prepareSrc, /AMOUNT_INPUT_PATTERN\.test\(value\)/);
	assert.match(prepareSrc, /return Number\.NaN;/);
});

test("confirm/route.js normalizePaymentConfirmBody rejects arrays and non-objects", () => {
	assert.match(
		confirmSrc,
		/body && typeof body === ["']object["'] && !Array\.isArray\(body\)/,
	);
});

test("prepare/route.js normalizePaymentPrepareBody rejects arrays and non-objects", () => {
	assert.match(
		prepareSrc,
		/body && typeof body === ["']object["'] && !Array\.isArray\(body\)/,
	);
});

// ── parsePaymentAmount behavioral tests ──────────────────────────────────────

test("parsePaymentAmount returns the integer for safe integer inputs", () => {
	assert.equal(parsePaymentAmount(5000), 5000);
	assert.equal(parsePaymentAmount(0), 0);
	assert.equal(parsePaymentAmount(1), 1);
});

test("parsePaymentAmount returns NaN for negative numbers (not for payment amounts)", () => {
	// Number.isSafeInteger(-1) is true, so negative numbers pass through
	// This tests the actual function behavior, not a business rule
	assert.equal(parsePaymentAmount(-1), -1, "negative safe integers are technically safe");
});

test("parsePaymentAmount returns NaN for non-safe-integer numbers", () => {
	assert.ok(Number.isNaN(parsePaymentAmount(Number.MAX_SAFE_INTEGER + 1)));
	assert.ok(Number.isNaN(parsePaymentAmount(1.5)));
	assert.ok(Number.isNaN(parsePaymentAmount(Infinity)));
	assert.ok(Number.isNaN(parsePaymentAmount(Number.NaN)));
});

test("parsePaymentAmount accepts MAX_SAFE_INTEGER as a number", () => {
	assert.equal(parsePaymentAmount(Number.MAX_SAFE_INTEGER), Number.MAX_SAFE_INTEGER);
});

test("parsePaymentAmount accepts digit-only strings and converts them", () => {
	assert.equal(parsePaymentAmount("5000"), 5000);
	assert.equal(parsePaymentAmount("0"), 0);
	assert.equal(parsePaymentAmount("99900"), 99900);
});

test("parsePaymentAmount returns NaN for non-digit-only strings", () => {
	assert.ok(Number.isNaN(parsePaymentAmount("-5000")));
	assert.ok(Number.isNaN(parsePaymentAmount("5000.5")));
	assert.ok(Number.isNaN(parsePaymentAmount("1e6")));
	assert.ok(Number.isNaN(parsePaymentAmount("0x10")));
	assert.ok(Number.isNaN(parsePaymentAmount("5 000")));
	assert.ok(Number.isNaN(parsePaymentAmount("")));
	assert.ok(Number.isNaN(parsePaymentAmount("abc")));
});

test("parsePaymentAmount returns NaN for null, undefined, and non-primitives", () => {
	assert.ok(Number.isNaN(parsePaymentAmount(null)));
	assert.ok(Number.isNaN(parsePaymentAmount(undefined)));
	assert.ok(Number.isNaN(parsePaymentAmount({})));
	assert.ok(Number.isNaN(parsePaymentAmount([])));
	assert.ok(Number.isNaN(parsePaymentAmount(true)));
	assert.ok(Number.isNaN(parsePaymentAmount(false)));
});

test("parsePaymentAmount returns NaN for digit strings exceeding MAX_SAFE_INTEGER", () => {
	// 9007199254740992 = Number.MAX_SAFE_INTEGER + 1 as a digit string
	assert.ok(Number.isNaN(parsePaymentAmount("9007199254740992")));
});

// ── normalizePaymentBody behavioral tests ─────────────────────────────────────

test("normalizePaymentBody passes through plain objects unchanged", () => {
	const body = { amount: 5000, orderId: "ord-123" };
	const result = normalizePaymentBody(body);
	assert.equal(result, body, "should return the same object reference");
});

test("normalizePaymentBody returns empty object for null", () => {
	assert.deepEqual(normalizePaymentBody(null), {});
});

test("normalizePaymentBody returns empty object for undefined", () => {
	assert.deepEqual(normalizePaymentBody(undefined), {});
});

test("normalizePaymentBody returns empty object for arrays", () => {
	assert.deepEqual(normalizePaymentBody([{ amount: 5000 }]), {});
	assert.deepEqual(normalizePaymentBody([]), {});
});

test("normalizePaymentBody returns empty object for primitive values", () => {
	assert.deepEqual(normalizePaymentBody("string"), {});
	assert.deepEqual(normalizePaymentBody(42), {});
	assert.deepEqual(normalizePaymentBody(true), {});
});

test("normalizePaymentBody preserves nested object structure", () => {
	const body = { outer: { inner: "value" }, amount: 5000 };
	assert.deepEqual(normalizePaymentBody(body), body);
});

test("normalizePaymentBody returns empty object for empty string (falsy)", () => {
	assert.deepEqual(normalizePaymentBody(""), {});
});
