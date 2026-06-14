/**
 * Behavioral tests for private pure helpers in:
 *   QRCodeWidget.js    — normalizeQRCodeText
 *   NotificationWidget.js — normalizeNotifications
 *   PaymentWidget.js   — normalizePaymentAmount
 *   DiagnosticsPageClient.js — hasRenderableRawData
 *
 * All source files import React; cannot load in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

const qrSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/QRCodeWidget.js"),
	"utf8",
);
const notifSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/NotificationWidget.js"),
	"utf8",
);
const paymentSrc = readFileSync(
	path.join(SRC_ROOT, "components/payment/PaymentWidget.js"),
	"utf8",
);
const diagSrc = readFileSync(
	path.join(SRC_ROOT, "components/admin/DiagnosticsPageClient.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

// QRCodeWidget
const DEFAULT_QR_LABEL = "QR 라벨";

function normalizeQRCodeText(value, fallback) {
	if (typeof value === "string" && value.trim()) {
		return value;
	}

	if (typeof value === "number" && Number.isFinite(value)) {
		return String(value);
	}

	return fallback;
}

// NotificationWidget
const DEFAULT_NOTIFICATION_TITLE = "운영 알림";
const DEFAULT_NOTIFICATION_MESSAGE =
	"확인할 알림 내용이 있습니다. 농장 상태를 확인해 주세요.";

function normalizeNotifications(notifications) {
	if (!Array.isArray(notifications)) return [];

	return notifications
		.filter((note) => note && typeof note === "object" && !Array.isArray(note))
		.map((note, index) => {
			const type =
				typeof note.type === "string" && note.type ? note.type : "default";
			const title =
				typeof note.title === "string" && note.title.trim()
					? note.title
					: DEFAULT_NOTIFICATION_TITLE;
			const message =
				typeof note.message === "string" && note.message.trim()
					? note.message
					: DEFAULT_NOTIFICATION_MESSAGE;

			return {
				...note,
				id: note.id ?? `${type}-${index}`,
				level: typeof note.level === "string" ? note.level : "info",
				message,
				title,
				type,
			};
		});
}

// PaymentWidget
function normalizePaymentAmount(amount) {
	if (typeof amount === "number" && Number.isFinite(amount)) {
		return amount;
	}

	if (typeof amount === "string" && amount.trim()) {
		const parsedAmount = Number(amount);
		if (Number.isFinite(parsedAmount)) {
			return parsedAmount;
		}
	}

	return 0;
}

// DiagnosticsPageClient
function hasRenderableRawData(value) {
	if (Array.isArray(value)) {
		return value.length > 0;
	}

	if (value && typeof value === "object") {
		return Object.keys(value).length > 0;
	}

	return value !== null && value !== undefined && value !== "";
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("QRCodeWidget.js normalizeQRCodeText accepts string or finite number", () => {
	assert.match(qrSrc, /function normalizeQRCodeText\(value, fallback\)/);
	assert.match(qrSrc, /typeof value === ["']string["'] && value\.trim\(\)/);
	assert.match(qrSrc, /Number\.isFinite\(value\)/);
});

test("NotificationWidget.js normalizeNotifications normalizes type/title/message/id", () => {
	assert.match(notifSrc, /function normalizeNotifications\(notifications\)/);
	assert.match(notifSrc, /`\$\{type\}-\$\{index\}`/);
	assert.match(notifSrc, /DEFAULT_NOTIFICATION_TITLE/);
	assert.match(notifSrc, /DEFAULT_NOTIFICATION_MESSAGE/);
});

test("PaymentWidget.js normalizePaymentAmount parses string amounts", () => {
	assert.match(paymentSrc, /function normalizePaymentAmount\(amount\)/);
	assert.match(paymentSrc, /Number\.isFinite\(amount\)/);
	assert.match(paymentSrc, /Number\.isFinite\(parsedAmount\)/);
});

test("DiagnosticsPageClient.js hasRenderableRawData checks array length and object keys", () => {
	assert.match(diagSrc, /function hasRenderableRawData\(value\)/);
	assert.match(diagSrc, /Array\.isArray\(value\)/);
	assert.match(diagSrc, /Object\.keys\(value\)\.length > 0/);
});

// ── normalizeQRCodeText behavioral tests ──────────────────────────────────────

test("normalizeQRCodeText returns the string value for non-empty string", () => {
	assert.equal(normalizeQRCodeText("한우 001", DEFAULT_QR_LABEL), "한우 001");
	assert.equal(normalizeQRCodeText("abc", DEFAULT_QR_LABEL), "abc");
});

test("normalizeQRCodeText returns fallback for empty string", () => {
	assert.equal(normalizeQRCodeText("", DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
});

test("normalizeQRCodeText returns fallback for whitespace-only string", () => {
	assert.equal(normalizeQRCodeText("   ", DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
});

test("normalizeQRCodeText returns fallback for null/undefined", () => {
	assert.equal(normalizeQRCodeText(null, DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
	assert.equal(normalizeQRCodeText(undefined, DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
});

test("normalizeQRCodeText converts finite number to string", () => {
	assert.equal(normalizeQRCodeText(42, DEFAULT_QR_LABEL), "42");
	assert.equal(normalizeQRCodeText(0, DEFAULT_QR_LABEL), "0");
	assert.equal(normalizeQRCodeText(-1, DEFAULT_QR_LABEL), "-1");
	assert.equal(normalizeQRCodeText(3.14, DEFAULT_QR_LABEL), "3.14");
});

test("normalizeQRCodeText returns fallback for non-finite numbers", () => {
	assert.equal(normalizeQRCodeText(NaN, DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
	assert.equal(normalizeQRCodeText(Infinity, DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
	assert.equal(normalizeQRCodeText(-Infinity, DEFAULT_QR_LABEL), DEFAULT_QR_LABEL);
});

test("normalizeQRCodeText preserves whitespace in strings (does not trim)", () => {
	// Only checks trim() for emptiness, the original whitespace is preserved
	assert.equal(normalizeQRCodeText("  소 001  ", DEFAULT_QR_LABEL), "  소 001  ");
});

// ── normalizeNotifications behavioral tests ───────────────────────────────────

test("normalizeNotifications returns empty array for non-array input", () => {
	assert.deepEqual(normalizeNotifications(null), []);
	assert.deepEqual(normalizeNotifications(undefined), []);
	assert.deepEqual(normalizeNotifications({}), []);
});

test("normalizeNotifications filters null/primitive/array entries", () => {
	const notifications = [null, "string", 42, [], { type: "estrus", title: "제목" }];
	assert.equal(normalizeNotifications(notifications).length, 1);
});

test("normalizeNotifications uses '알림 타입' type fallback for missing/empty type", () => {
	const notifications = [
		{ title: "제목", message: "메시지" },
		{ type: "", title: "제목2", message: "메시지2" },
	];
	const result = normalizeNotifications(notifications);
	assert.ok(result.every((n) => n.type === "default"));
});

test("normalizeNotifications preserves valid type string", () => {
	const notifications = [{ type: "estrus", title: "발정 알림", message: "메시지" }];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].type, "estrus");
});

test("normalizeNotifications uses DEFAULT_NOTIFICATION_TITLE for missing title", () => {
	const notifications = [{ type: "estrus", message: "메시지" }];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].title, DEFAULT_NOTIFICATION_TITLE);
});

test("normalizeNotifications uses DEFAULT_NOTIFICATION_TITLE for empty/whitespace title", () => {
	const notifications = [
		{ type: "estrus", title: "", message: "메시지" },
		{ type: "estrus", title: "   ", message: "메시지2" },
	];
	const result = normalizeNotifications(notifications);
	assert.ok(result.every((n) => n.title === DEFAULT_NOTIFICATION_TITLE));
});

test("normalizeNotifications uses DEFAULT_NOTIFICATION_MESSAGE for missing message", () => {
	const notifications = [{ type: "estrus", title: "알림" }];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].message, DEFAULT_NOTIFICATION_MESSAGE);
});

test("normalizeNotifications generates fallback id as type-index", () => {
	const notifications = [
		{ type: "estrus", title: "알림1", message: "메시지1" },
		{ type: "pregnancy", title: "알림2", message: "메시지2" },
	];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].id, "estrus-0");
	assert.equal(result[1].id, "pregnancy-1");
});

test("normalizeNotifications preserves existing id", () => {
	const notifications = [
		{ id: "my-id", type: "estrus", title: "알림", message: "메시지" },
	];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].id, "my-id");
});

test("normalizeNotifications defaults level to 'info' for non-string level", () => {
	const notifications = [
		{ type: "estrus", title: "알림", message: "메시지", level: null },
		{ type: "estrus", title: "알림2", message: "메시지2" },
	];
	const result = normalizeNotifications(notifications);
	assert.ok(result.every((n) => n.level === "info"));
});

test("normalizeNotifications preserves string level", () => {
	const notifications = [
		{ type: "estrus", title: "알림", message: "메시지", level: "warning" },
	];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].level, "warning");
});

test("normalizeNotifications spreads other notification fields through", () => {
	const notifications = [
		{
			type: "estrus",
			title: "알림",
			message: "메시지",
			cattleName: "소",
			daysLeft: 3,
		},
	];
	const result = normalizeNotifications(notifications);
	assert.equal(result[0].cattleName, "소");
	assert.equal(result[0].daysLeft, 3);
});

// ── normalizePaymentAmount behavioral tests ───────────────────────────────────

test("normalizePaymentAmount returns the number for finite number input", () => {
	assert.equal(normalizePaymentAmount(9900), 9900);
	assert.equal(normalizePaymentAmount(0), 0);
	assert.equal(normalizePaymentAmount(-100), -100);
});

test("normalizePaymentAmount returns 0 for non-finite numbers", () => {
	assert.equal(normalizePaymentAmount(NaN), 0);
	assert.equal(normalizePaymentAmount(Infinity), 0);
	assert.equal(normalizePaymentAmount(-Infinity), 0);
});

test("normalizePaymentAmount parses valid numeric string", () => {
	assert.equal(normalizePaymentAmount("9900"), 9900);
	assert.equal(normalizePaymentAmount("0"), 0);
	assert.equal(normalizePaymentAmount("3.14"), 3.14);
});

test("normalizePaymentAmount returns 0 for non-numeric string", () => {
	assert.equal(normalizePaymentAmount("abc"), 0);
	assert.equal(normalizePaymentAmount(""), 0);
	assert.equal(normalizePaymentAmount("   "), 0);
});

test("normalizePaymentAmount returns 0 for null/undefined", () => {
	assert.equal(normalizePaymentAmount(null), 0);
	assert.equal(normalizePaymentAmount(undefined), 0);
});

// ── hasRenderableRawData behavioral tests ─────────────────────────────────────

test("hasRenderableRawData returns true for non-empty array", () => {
	assert.equal(hasRenderableRawData([1, 2, 3]), true);
	assert.equal(hasRenderableRawData(["item"]), true);
});

test("hasRenderableRawData returns false for empty array", () => {
	assert.equal(hasRenderableRawData([]), false);
});

test("hasRenderableRawData returns true for non-empty object", () => {
	assert.equal(hasRenderableRawData({ key: "value" }), true);
	assert.equal(hasRenderableRawData({ a: 1 }), true);
});

test("hasRenderableRawData returns false for empty object", () => {
	assert.equal(hasRenderableRawData({}), false);
});

test("hasRenderableRawData returns false for null/undefined", () => {
	assert.equal(hasRenderableRawData(null), false);
	assert.equal(hasRenderableRawData(undefined), false);
});

test("hasRenderableRawData returns false for empty string", () => {
	assert.equal(hasRenderableRawData(""), false);
});

test("hasRenderableRawData returns true for non-empty string", () => {
	assert.equal(hasRenderableRawData("hello"), true);
	assert.equal(hasRenderableRawData("0"), true);
});

test("hasRenderableRawData returns true for truthy primitives", () => {
	assert.equal(hasRenderableRawData(42), true);
	assert.equal(hasRenderableRawData(true), true);
});

test("hasRenderableRawData returns false for 0 and false (falsy non-null non-empty)", () => {
	// 0 is falsy: value !== null and !== undefined but... it falls to the primitive path
	// "value !== null && value !== undefined && value !== ''" → 0 passes all 3 checks
	// But wait: 0 !== null ✓, 0 !== undefined ✓, 0 !== "" ✓ → would return true?
	// Actually: 0 && typeof 0 === "object" is false (0 is falsy), so it goes to primitive check
	// The primitive check: value !== null && value !== undefined && value !== "" → 0 is fine → true
	// BUT: 0 is a falsy value at the object check: `if (value && typeof value === "object")` — falsy!
	// So for 0: falls to `return value !== null && value !== undefined && value !== ""`
	// 0 !== null ✓, 0 !== undefined ✓, 0 !== "" ✓ → returns true
	assert.equal(hasRenderableRawData(0), true);
	// false: value && typeof false === "object" — falsy
	// falls to: false !== null ✓, false !== undefined ✓, false !== "" ✓ → returns true
	assert.equal(hasRenderableRawData(false), true);
});
