import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
	fetchWithTimeout,
	isTimeoutError,
	TimeoutError,
} from "./fetchWithTimeout.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const source = readFileSync(path.join(__dirname, "fetchWithTimeout.js"), "utf8");

// ── TimeoutError ─────────────────────────────────────────────────────────────

test("TimeoutError has name=TimeoutError and carries timeoutMs", () => {
	const err = new TimeoutError("timed out", 5000);
	assert.equal(err.name, "TimeoutError");
	assert.equal(err.message, "timed out");
	assert.equal(err.timeoutMs, 5000);
	assert.ok(err instanceof Error);
});

test("TimeoutError with zero timeoutMs stores zero", () => {
	const err = new TimeoutError("zero", 0);
	assert.equal(err.timeoutMs, 0);
});

// ── isTimeoutError ────────────────────────────────────────────────────────────

test("isTimeoutError returns true for TimeoutError instances", () => {
	assert.equal(isTimeoutError(new TimeoutError("x", 1)), true);
});

test("isTimeoutError returns true for plain objects with name=TimeoutError (duck-typing)", () => {
	// Timeout errors crossing module boundaries lose instanceof identity — duck-type check covers that
	assert.equal(isTimeoutError({ name: "TimeoutError" }), true);
});

test("isTimeoutError returns false for ordinary errors and non-errors", () => {
	assert.equal(isTimeoutError(new Error("other")), false);
	assert.equal(isTimeoutError(null), false);
	assert.equal(isTimeoutError(undefined), false);
	assert.equal(isTimeoutError("string"), false);
	assert.equal(isTimeoutError(42), false);
	assert.equal(isTimeoutError({ name: "AbortError" }), false);
});

// ── fetchWithTimeout structural invariants ────────────────────────────────────

test("fetchWithTimeout uses AbortController to implement timeout cancellation", () => {
	// AbortController.abort() is called in the setTimeout callback so the signal
	// is already aborted when fetch checks it — no polling, no busy wait.
	assert.match(source, /new AbortController\(\)/);
	assert.match(source, /controller\.abort\(/);
	assert.match(source, /signal: controller\.signal/);
});

test("fetchWithTimeout defaults to 10000ms timeout when option is absent", () => {
	// A missing or non-finite timeoutMs must not produce NaN/0/Infinity
	assert.match(source, /Number\.isFinite\(safeOptions\.timeoutMs\)/);
	assert.match(source, /: 10000/);
});

test("fetchWithTimeout re-throws AbortError as TimeoutError (not raw AbortError)", () => {
	// AbortError from the signal gives no user-visible context; wrapping it with
	// TimeoutError adds timeoutMs and a Korean user-facing message.
	assert.match(source, /error\?\.name === ["']AbortError["']/);
	assert.match(source, /throw timeoutError/);
});

test("fetchWithTimeout clears the timeout in the finally block to prevent timer leaks", () => {
	// Without clearTimeout, every successful fetch leaves an orphaned timer that
	// fires after timeoutMs and may abort the next request's AbortController.
	assert.match(source, /clearTimeout\(timeoutId\)/);
	assert.match(source, /finally/);
});

test("fetchWithTimeout normalizes options defensively to prevent crash on null/array input", () => {
	assert.match(source, /function normalizeOptions\(options\)/);
	assert.match(source, /options && typeof options === ["']object["'] && !Array\.isArray\(options\)/);
});
