/**
 * Behavioral tests for auth-guard.js error classes and isAuthenticationError.
 *
 * auth-guard.js imports from "@/auth" and "next/navigation" (framework deps
 * that can't be resolved in Node ESM tests). The error classes and the pure
 * isAuthenticationError detector are re-implemented inline with source-grep
 * guards to catch divergence.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/auth-guard.js"), "utf8");

// ── Inline re-implementations ─────────────────────────────────────────────────

const AUTHENTICATION_REQUIRED_MESSAGE = "로그인이 필요합니다.";

class AuthenticationError extends Error {
	constructor(message = AUTHENTICATION_REQUIRED_MESSAGE) {
		super(message);
		this.name = "AuthenticationError";
	}
}

class AdminAuthorizationError extends Error {
	constructor(message = "관리자 권한이 필요합니다.") {
		super(message);
		this.name = "AdminAuthorizationError";
	}
}

function isAuthenticationError(error) {
	return (
		error instanceof AuthenticationError ||
		error?.name === "AuthenticationError"
	);
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("auth-guard.js isAuthenticationError checks instanceof AND .name", () => {
	assert.match(src, /error instanceof AuthenticationError/);
	assert.match(src, /error\?\.name === ["']AuthenticationError["']/);
});

test("auth-guard.js AuthenticationError default message is Korean", () => {
	assert.match(src, /로그인이 필요합니다/);
	assert.match(src, /AUTHENTICATION_REQUIRED_MESSAGE/);
	assert.match(src, /this\.name = ["']AuthenticationError["']/);
});

test("auth-guard.js AdminAuthorizationError default message is Korean", () => {
	assert.match(src, /관리자 권한이 필요합니다/);
	assert.match(src, /this\.name = ["']AdminAuthorizationError["']/);
});

// ── AuthenticationError behavioral tests ─────────────────────────────────────

test("AuthenticationError has name='AuthenticationError'", () => {
	const error = new AuthenticationError();
	assert.equal(error.name, "AuthenticationError");
});

test("AuthenticationError default message is the Korean constant", () => {
	const error = new AuthenticationError();
	assert.equal(error.message, AUTHENTICATION_REQUIRED_MESSAGE);
	assert.equal(error.message, "로그인이 필요합니다.");
});

test("AuthenticationError accepts a custom message", () => {
	const error = new AuthenticationError("custom error message");
	assert.equal(error.message, "custom error message");
});

test("AuthenticationError is an instance of Error", () => {
	const error = new AuthenticationError();
	assert.ok(error instanceof Error);
});

// ── AdminAuthorizationError behavioral tests ──────────────────────────────────

test("AdminAuthorizationError has name='AdminAuthorizationError'", () => {
	const error = new AdminAuthorizationError();
	assert.equal(error.name, "AdminAuthorizationError");
});

test("AdminAuthorizationError default message is Korean", () => {
	const error = new AdminAuthorizationError();
	assert.equal(error.message, "관리자 권한이 필요합니다.");
});

test("AdminAuthorizationError is an instance of Error", () => {
	assert.ok(new AdminAuthorizationError() instanceof Error);
});

// ── isAuthenticationError behavioral tests ────────────────────────────────────

test("isAuthenticationError returns true for AuthenticationError instances", () => {
	assert.equal(isAuthenticationError(new AuthenticationError()), true);
});

test("isAuthenticationError returns true for plain objects with name='AuthenticationError'", () => {
	assert.equal(isAuthenticationError({ name: "AuthenticationError" }), true);
});

test("isAuthenticationError returns false for other Error types", () => {
	assert.equal(isAuthenticationError(new Error("generic")), false);
	assert.equal(isAuthenticationError(new AdminAuthorizationError()), false);
	assert.equal(isAuthenticationError(new TypeError("type error")), false);
});

test("isAuthenticationError returns false for null and undefined", () => {
	assert.equal(isAuthenticationError(null), false);
	assert.equal(isAuthenticationError(undefined), false);
});

test("isAuthenticationError returns false for non-matching .name values", () => {
	assert.equal(isAuthenticationError({ name: "AdminAuthorizationError" }), false);
	assert.equal(isAuthenticationError({ name: "Error" }), false);
	assert.equal(isAuthenticationError({ name: "" }), false);
});

test("isAuthenticationError returns false for plain strings and numbers", () => {
	assert.equal(isAuthenticationError("AuthenticationError"), false);
	assert.equal(isAuthenticationError(42), false);
});
