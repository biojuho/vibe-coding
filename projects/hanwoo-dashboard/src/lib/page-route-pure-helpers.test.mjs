/**
 * Behavioral tests for private pure helpers in:
 *   src/app/page.js              — isNextControlFlowError, logInitialDataLoadFailure
 *   src/app/subscription/page.js — source-grep guards for subscription views
 *
 * Both files import Next.js/React; cannot be loaded in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

const pageSrc = readFileSync(
	path.join(SRC_ROOT, "app/page.js"),
	"utf8",
);
const subPageSrc = readFileSync(
	path.join(SRC_ROOT, "app/subscription/page.js"),
	"utf8",
);

// ── Inline re-implementations ────────────────────────────────────────────────

function isNextControlFlowError(error) {
	const digest = typeof error?.digest === "string" ? error.digest : "";
	return (
		digest.startsWith("NEXT_REDIRECT") || digest.startsWith("NEXT_NOT_FOUND")
	);
}

function logInitialDataLoadFailure(sectionId, error) {
	const errorName =
		typeof error?.name === "string" && error.name.length > 0
			? error.name
			: "Error";
	const errorMessage =
		typeof error?.message === "string" && error.message.length > 0
			? error.message
			: "initial data unavailable";

	console.warn(
		`[hanwoo-dashboard] degraded initial ${sectionId} data load: ${errorName}: ${errorMessage}`,
	);
}

// ── Source-grep guards: page.js ───────────────────────────────────────────────

test("page.js isNextControlFlowError checks NEXT_REDIRECT and NEXT_NOT_FOUND prefixes", () => {
	assert.match(pageSrc, /function isNextControlFlowError\(error\)/);
	assert.match(pageSrc, /digest\.startsWith\(["']NEXT_REDIRECT["']\)/);
	assert.match(pageSrc, /digest\.startsWith\(["']NEXT_NOT_FOUND["']\)/);
});

test("page.js logInitialDataLoadFailure uses console.warn with sectionId/errorName/errorMessage", () => {
	assert.match(pageSrc, /function logInitialDataLoadFailure\(sectionId, error\)/);
	assert.match(pageSrc, /console\.warn/);
	assert.match(pageSrc, /hanwoo-dashboard/);
	assert.match(pageSrc, /["']initial data unavailable["']/);
});

test("page.js isNextControlFlowError re-throws Next control flow errors in loadInitialDataSection", () => {
	assert.match(pageSrc, /if \(isNextControlFlowError\(error\)\)/);
	assert.match(pageSrc, /throw error/);
});

// ── Source-grep guards: subscription/page.js ──────────────────────────────────

test("subscription/page.js TrialSubscriptionView: daysLeft>0 conditional text", () => {
	assert.match(subPageSrc, /function TrialSubscriptionView/);
	assert.match(subPageSrc, /daysLeft != null && daysLeft > 0/);
	assert.match(subPageSrc, /체험 기간이 오늘 만료됩니다/);
});

test("subscription/page.js ActiveSubscriptionView: toLocaleDateString for nextPaymentDate", () => {
	assert.match(subPageSrc, /function ActiveSubscriptionView/);
	assert.match(subPageSrc, /toLocaleDateString\(["']ko-KR["']\)/);
});

test("subscription/page.js SubscriptionPage: requireAuthenticatedSession with redirectToLogin", () => {
	assert.match(subPageSrc, /requireAuthenticatedSession/);
	assert.match(subPageSrc, /redirectToLogin: true/);
});

test("subscription/page.js SubscriptionPage: getSubscriptionStatus check", () => {
	assert.match(subPageSrc, /getSubscriptionStatus/);
	assert.match(subPageSrc, /buildCustomerKey/);
});

// ── isNextControlFlowError behavioral tests ───────────────────────────────────

test("isNextControlFlowError returns true for NEXT_REDIRECT digest", () => {
	assert.equal(isNextControlFlowError({ digest: "NEXT_REDIRECT:abc" }), true);
	assert.equal(isNextControlFlowError({ digest: "NEXT_REDIRECT" }), true);
});

test("isNextControlFlowError returns true for NEXT_NOT_FOUND digest", () => {
	assert.equal(isNextControlFlowError({ digest: "NEXT_NOT_FOUND:xyz" }), true);
	assert.equal(isNextControlFlowError({ digest: "NEXT_NOT_FOUND" }), true);
});

test("isNextControlFlowError returns false for arbitrary error digest", () => {
	assert.equal(isNextControlFlowError({ digest: "some-other-error" }), false);
	assert.equal(isNextControlFlowError({ digest: "SERVER_ERROR" }), false);
});

test("isNextControlFlowError returns false for non-string digest", () => {
	assert.equal(isNextControlFlowError({ digest: 42 }), false);
	assert.equal(isNextControlFlowError({ digest: null }), false);
	assert.equal(isNextControlFlowError({ digest: undefined }), false);
});

test("isNextControlFlowError returns false for error with no digest", () => {
	assert.equal(isNextControlFlowError({}), false);
	assert.equal(isNextControlFlowError(new Error("oops")), false);
});

test("isNextControlFlowError returns false for null/undefined error", () => {
	assert.equal(isNextControlFlowError(null), false);
	assert.equal(isNextControlFlowError(undefined), false);
});

test("isNextControlFlowError does NOT match strings that merely contain NEXT_ but don't start with them", () => {
	assert.equal(isNextControlFlowError({ digest: "prefix_NEXT_REDIRECT" }), false);
});

// ── logInitialDataLoadFailure behavioral tests ────────────────────────────────

test("logInitialDataLoadFailure calls console.warn with formatted message", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("cattle", new Error("DB connection failed"));
		assert.ok(warns.length === 1);
		assert.ok(warns[0].includes("[hanwoo-dashboard]"));
		assert.ok(warns[0].includes("cattle"));
		assert.ok(warns[0].includes("Error"));
		assert.ok(warns[0].includes("DB connection failed"));
	} finally {
		console.warn = origWarn;
	}
});

test("logInitialDataLoadFailure uses 'Error' fallback for non-string name", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("feed", { name: null, message: "failed" });
		assert.ok(warns[0].includes("Error:"));
	} finally {
		console.warn = origWarn;
	}
});

test("logInitialDataLoadFailure uses 'initial data unavailable' fallback for non-string message", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("sales", { name: "TypeError", message: "" });
		assert.ok(warns[0].includes("initial data unavailable"));
	} finally {
		console.warn = origWarn;
	}
});

test("logInitialDataLoadFailure uses fallback for both name and message when error is a plain string", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("market", "something went wrong");
		assert.ok(warns[0].includes("Error:"));
		assert.ok(warns[0].includes("initial data unavailable"));
	} finally {
		console.warn = origWarn;
	}
});

test("logInitialDataLoadFailure uses fallback for null error", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("schedule", null);
		assert.ok(warns[0].includes("Error:"));
		assert.ok(warns[0].includes("initial data unavailable"));
	} finally {
		console.warn = origWarn;
	}
});

test("logInitialDataLoadFailure includes the sectionId in the log message", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("calving-data", new Error("timeout"));
		assert.ok(warns[0].includes("calving-data"));
	} finally {
		console.warn = origWarn;
	}
});

test("logInitialDataLoadFailure uses 'initial data unavailable' for empty-string message", () => {
	const warns = [];
	const origWarn = console.warn;
	console.warn = (...args) => warns.push(args.join(" "));
	try {
		logInitialDataLoadFailure("feed", { name: "Error", message: "" });
		assert.ok(warns[0].includes("initial data unavailable"));
	} finally {
		console.warn = origWarn;
	}
});
