/**
 * Behavioral tests for private pure helpers across several component files:
 *   formatCacheAgeLabel   — src/components/widgets/AIInsightWidget.js
 *   formatDaysLeftLabel   — src/components/forms/CattleDetailModal.js (and ScheduleTab.js)
 *   buildLoginReturnHref  — src/components/layout/LegalReturnLink.js
 *   getMarketPriceForGrade — src/components/tabs/AnalysisTab.js
 *   isPaymentWidgetUnavailableError + getPaymentRequestErrorMessage
 *                         — src/components/payment/PaymentWidget.js
 *
 * These files import from React / Next.js and use browser APIs that cannot
 * be resolved in Node ESM. Pure helpers are re-implemented inline with
 * source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const insightWidgetSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/AIInsightWidget.js"),
	"utf8",
);
const cattleDetailSrc = readFileSync(
	path.join(SRC_ROOT, "components/forms/CattleDetailModal.js"),
	"utf8",
);
const legalReturnSrc = readFileSync(
	path.join(SRC_ROOT, "components/layout/LegalReturnLink.js"),
	"utf8",
);
const analysisTabSrc = readFileSync(
	path.join(SRC_ROOT, "components/tabs/AnalysisTab.js"),
	"utf8",
);
const paymentWidgetSrc = readFileSync(
	path.join(SRC_ROOT, "components/payment/PaymentWidget.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

// From AIInsightWidget.js
function formatCacheAgeLabel(ageSeconds) {
	const seconds = Number(ageSeconds);
	if (!Number.isFinite(seconds) || seconds < 0) return null;
	if (seconds < 60) return "방금 분석";
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}분 전 캐시`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}시간 전 캐시`;
	return "오늘 분석 결과";
}

// From CattleDetailModal.js (identical in ScheduleTab.js)
function formatDaysLeftLabel(daysLeft) {
	return daysLeft === 0 ? "오늘" : `${daysLeft}일 남음`;
}

// From LegalReturnLink.js
const LEGAL_RETURN_TARGETS_LOGIN_HREF = "/login";

function buildLoginReturnHref(callbackTarget = "") {
	if (
		typeof callbackTarget !== "string" ||
		callbackTarget.length === 0 ||
		callbackTarget === "/"
	) {
		return LEGAL_RETURN_TARGETS_LOGIN_HREF;
	}

	const params = new URLSearchParams();
	params.set("callbackUrl", callbackTarget);
	return `${LEGAL_RETURN_TARGETS_LOGIN_HREF}?${params.toString()}#login`;
}

// From AnalysisTab.js
const MARKET_GRADE_MAP = { "1++": "grade1pp", "1+": "grade1p", "1": "grade1" };

function getMarketPriceForGrade(marketPrice, grade, gender) {
	if (!marketPrice) return null;
	const key = MARKET_GRADE_MAP[grade];
	if (!key) return null;
	const isBull = typeof gender === "string" && gender.includes("수");
	const tier = isBull ? marketPrice.bull : marketPrice.cow;
	return tier?.[key] ?? null;
}

// From PaymentWidget.js
const PAYMENT_WIDGET_UNAVAILABLE_MESSAGE =
	"결제 설정을 확인해야 합니다. 관리자에게 Toss 결제위젯 키와 UI 설정을 확인해 달라고 요청해 주세요.";
const PAYMENT_WIDGET_PENDING_MESSAGE = "결제 수단을 불러오는 중입니다.";
const PAYMENT_REQUEST_ERROR_MESSAGE =
	"결제 요청을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.";

function isPaymentWidgetUnavailableError(error) {
	const errorMessage =
		error instanceof Error ? error.message : String(error ?? "");

	return (
		errorMessage === PAYMENT_WIDGET_PENDING_MESSAGE ||
		errorMessage === PAYMENT_WIDGET_UNAVAILABLE_MESSAGE ||
		errorMessage.includes("결제 UI가 아직 렌더링되지 않았습니다")
	);
}

function getPaymentRequestErrorMessage(error) {
	return isPaymentWidgetUnavailableError(error)
		? PAYMENT_WIDGET_UNAVAILABLE_MESSAGE
		: PAYMENT_REQUEST_ERROR_MESSAGE;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("AIInsightWidget.js formatCacheAgeLabel thresholds: 60s/60m/24h", () => {
	assert.match(insightWidgetSrc, /function formatCacheAgeLabel\(ageSeconds\)/);
	assert.match(insightWidgetSrc, /if \(seconds < 60\) return ["']방금 분석["'];/);
	assert.match(insightWidgetSrc, /if \(hours < 24\) return/);
	assert.match(insightWidgetSrc, /return ["']오늘 분석 결과["'];/);
});

test("CattleDetailModal.js formatDaysLeftLabel returns '오늘' for 0", () => {
	assert.match(cattleDetailSrc, /function formatDaysLeftLabel\(daysLeft\)/);
	assert.match(cattleDetailSrc, /daysLeft === 0 \? ["']오늘["'] : /);
});

test("LegalReturnLink.js buildLoginReturnHref falls back for empty/slash callbackTarget", () => {
	assert.match(legalReturnSrc, /function buildLoginReturnHref\(/);
	assert.match(legalReturnSrc, /callbackTarget\.length === 0/);
	assert.match(legalReturnSrc, /callbackTarget === ["']\/["']/);
});

test("AnalysisTab.js getMarketPriceForGrade uses MARKET_GRADE_MAP", () => {
	assert.match(analysisTabSrc, /function getMarketPriceForGrade\(marketPrice, grade, gender\)/);
	assert.match(analysisTabSrc, /MARKET_GRADE_MAP\[grade\]/);
	assert.match(analysisTabSrc, /gender\.includes\(["']수["']\)/);
});

test("PaymentWidget.js isPaymentWidgetUnavailableError checks Korean message strings", () => {
	assert.match(paymentWidgetSrc, /function isPaymentWidgetUnavailableError\(error\)/);
	assert.match(paymentWidgetSrc, /errorMessage === PAYMENT_WIDGET_PENDING_MESSAGE/);
	assert.match(paymentWidgetSrc, /errorMessage\.includes\(/);
});

// ── formatCacheAgeLabel behavioral tests ──────────────────────────────────────

test("formatCacheAgeLabel returns null for negative input", () => {
	assert.equal(formatCacheAgeLabel(-1), null);
	assert.equal(formatCacheAgeLabel(-Infinity), null);
});

test("formatCacheAgeLabel returns null for non-finite input", () => {
	assert.equal(formatCacheAgeLabel(NaN), null);
	assert.equal(formatCacheAgeLabel(Infinity), null);
	assert.equal(formatCacheAgeLabel(undefined), null);
	// null → Number(null) = 0 → finite and ≥0 → treated as 0 seconds → "방금 분석"
	assert.equal(formatCacheAgeLabel(null), "방금 분석");
});

test("formatCacheAgeLabel returns '방금 분석' for 0 seconds", () => {
	assert.equal(formatCacheAgeLabel(0), "방금 분석");
});

test("formatCacheAgeLabel returns '방금 분석' for < 60 seconds", () => {
	assert.equal(formatCacheAgeLabel(1), "방금 분석");
	assert.equal(formatCacheAgeLabel(59), "방금 분석");
});

test("formatCacheAgeLabel returns '1분 전 캐시' for exactly 60 seconds", () => {
	assert.equal(formatCacheAgeLabel(60), "1분 전 캐시");
});

test("formatCacheAgeLabel returns minutes label for 60-3599 seconds", () => {
	assert.equal(formatCacheAgeLabel(120), "2분 전 캐시");
	assert.equal(formatCacheAgeLabel(3599), "59분 전 캐시");
});

test("formatCacheAgeLabel returns '1시간 전 캐시' for exactly 3600 seconds", () => {
	assert.equal(formatCacheAgeLabel(3600), "1시간 전 캐시");
});

test("formatCacheAgeLabel returns hours label for 3600-86399 seconds", () => {
	assert.equal(formatCacheAgeLabel(7200), "2시간 전 캐시");
	assert.equal(formatCacheAgeLabel(86399), "23시간 전 캐시");
});

test("formatCacheAgeLabel returns '오늘 분석 결과' for >= 86400 seconds (24 hours)", () => {
	assert.equal(formatCacheAgeLabel(86400), "오늘 분석 결과");
	assert.equal(formatCacheAgeLabel(172800), "오늘 분석 결과");
});

// ── formatDaysLeftLabel behavioral tests ──────────────────────────────────────

test("formatDaysLeftLabel returns '오늘' for 0", () => {
	assert.equal(formatDaysLeftLabel(0), "오늘");
});

test("formatDaysLeftLabel returns 'N일 남음' for positive integers", () => {
	assert.equal(formatDaysLeftLabel(1), "1일 남음");
	assert.equal(formatDaysLeftLabel(7), "7일 남음");
	assert.equal(formatDaysLeftLabel(21), "21일 남음");
});

// ── buildLoginReturnHref behavioral tests ─────────────────────────────────────

test("buildLoginReturnHref returns '/login' for empty string", () => {
	assert.equal(buildLoginReturnHref(""), "/login");
});

test("buildLoginReturnHref returns '/login' with no argument (default)", () => {
	assert.equal(buildLoginReturnHref(), "/login");
});

test("buildLoginReturnHref returns '/login' for '/' (root path)", () => {
	assert.equal(buildLoginReturnHref("/"), "/login");
});

test("buildLoginReturnHref returns '/login' for non-string input", () => {
	assert.equal(buildLoginReturnHref(null), "/login");
	assert.equal(buildLoginReturnHref(42), "/login");
	assert.equal(buildLoginReturnHref(undefined), "/login");
});

test("buildLoginReturnHref appends callbackUrl param for non-empty, non-slash strings", () => {
	const result = buildLoginReturnHref("/dashboard");
	assert.ok(result.startsWith("/login?"));
	assert.ok(result.includes("callbackUrl=%2Fdashboard"));
	assert.ok(result.endsWith("#login"));
});

test("buildLoginReturnHref URL-encodes the callbackUrl parameter", () => {
	const result = buildLoginReturnHref("/cattle?id=123&tab=feed");
	assert.ok(result.includes("callbackUrl="));
	assert.ok(result.endsWith("#login"));
	// The value should be URL-encoded
	assert.ok(!result.includes("/cattle?id=123&tab=feed"), "raw query should be encoded");
});

// ── getMarketPriceForGrade behavioral tests ────────────────────────────────────

test("getMarketPriceForGrade returns null for null/missing marketPrice", () => {
	assert.equal(getMarketPriceForGrade(null, "1++", "암"), null);
	assert.equal(getMarketPriceForGrade(undefined, "1++", "암"), null);
});

test("getMarketPriceForGrade returns null for unknown grade", () => {
	const mp = { cow: { grade1pp: 9500000 }, bull: { grade1pp: 8000000 } };
	assert.equal(getMarketPriceForGrade(mp, "2", "암"), null);
	assert.equal(getMarketPriceForGrade(mp, "", "암"), null);
	assert.equal(getMarketPriceForGrade(mp, null, "암"), null);
});

test("getMarketPriceForGrade uses cow tier for non-bull gender", () => {
	const mp = { cow: { grade1pp: 9500000 }, bull: { grade1pp: 8000000 } };
	assert.equal(getMarketPriceForGrade(mp, "1++", "암"), 9500000);
});

test("getMarketPriceForGrade uses bull tier for gender containing '수'", () => {
	const mp = { cow: { grade1pp: 9500000 }, bull: { grade1pp: 8000000 } };
	assert.equal(getMarketPriceForGrade(mp, "1++", "수"), 8000000);
	assert.equal(getMarketPriceForGrade(mp, "1++", "거세수"), 8000000);
});

test("getMarketPriceForGrade maps all three grades correctly", () => {
	const mp = { cow: { grade1pp: 1, grade1p: 2, grade1: 3 }, bull: {} };
	assert.equal(getMarketPriceForGrade(mp, "1++", "암"), 1);
	assert.equal(getMarketPriceForGrade(mp, "1+", "암"), 2);
	assert.equal(getMarketPriceForGrade(mp, "1", "암"), 3);
});

test("getMarketPriceForGrade returns null when tier key is missing in marketPrice", () => {
	const mp = { cow: {} };
	assert.equal(getMarketPriceForGrade(mp, "1++", "암"), null);
});

// ── isPaymentWidgetUnavailableError behavioral tests ──────────────────────────

test("isPaymentWidgetUnavailableError returns true for pending message Error", () => {
	assert.equal(
		isPaymentWidgetUnavailableError(new Error(PAYMENT_WIDGET_PENDING_MESSAGE)),
		true,
	);
});

test("isPaymentWidgetUnavailableError returns true for unavailable message Error", () => {
	assert.equal(
		isPaymentWidgetUnavailableError(new Error(PAYMENT_WIDGET_UNAVAILABLE_MESSAGE)),
		true,
	);
});

test("isPaymentWidgetUnavailableError returns true for message including '결제 UI가 아직 렌더링되지 않았습니다'", () => {
	assert.equal(
		isPaymentWidgetUnavailableError(new Error("결제 UI가 아직 렌더링되지 않았습니다.")),
		true,
	);
});

test("isPaymentWidgetUnavailableError returns false for other Errors", () => {
	assert.equal(isPaymentWidgetUnavailableError(new Error("Network error")), false);
	assert.equal(isPaymentWidgetUnavailableError(new Error("")), false);
});

test("isPaymentWidgetUnavailableError returns false for null/undefined", () => {
	assert.equal(isPaymentWidgetUnavailableError(null), false);
	assert.equal(isPaymentWidgetUnavailableError(undefined), false);
});

// ── getPaymentRequestErrorMessage behavioral tests ────────────────────────────

test("getPaymentRequestErrorMessage returns unavailable message for widget errors", () => {
	assert.equal(
		getPaymentRequestErrorMessage(new Error(PAYMENT_WIDGET_PENDING_MESSAGE)),
		PAYMENT_WIDGET_UNAVAILABLE_MESSAGE,
	);
});

test("getPaymentRequestErrorMessage returns request error message for other errors", () => {
	assert.equal(
		getPaymentRequestErrorMessage(new Error("some other error")),
		PAYMENT_REQUEST_ERROR_MESSAGE,
	);
	assert.equal(
		getPaymentRequestErrorMessage(null),
		PAYMENT_REQUEST_ERROR_MESSAGE,
	);
});
