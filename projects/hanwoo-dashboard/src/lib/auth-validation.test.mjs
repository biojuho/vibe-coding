import assert from "node:assert/strict";
import test from "node:test";

import {
	MAX_PASSWORD_LENGTH,
	MAX_USERNAME_LENGTH,
	MIN_PASSWORD_LENGTH,
	MIN_USERNAME_LENGTH,
	USERNAME_PATTERN,
	validateChangePasswordPayload,
	validateRegistrationPayload,
} from "./auth-validation.mjs";

// ── Exported constants ────────────────────────────────────────────────────────

test("MAX_PASSWORD_LENGTH is 72 (bcrypt DoS guard)", () => {
	assert.equal(MAX_PASSWORD_LENGTH, 72);
});

test("MIN_PASSWORD_LENGTH is 8", () => {
	assert.equal(MIN_PASSWORD_LENGTH, 8);
});

test("USERNAME_PATTERN allows lowercase letters, digits, underscores only", () => {
	assert.ok(USERNAME_PATTERN.test("abc_123"));
	assert.ok(!USERNAME_PATTERN.test("ABC"));
	assert.ok(!USERNAME_PATTERN.test("user-name"));
	assert.ok(!USERNAME_PATTERN.test("user name"));
	assert.ok(!USERNAME_PATTERN.test("user@domain"));
});

// ── validateRegistrationPayload ───────────────────────────────────────────────

test("validateRegistrationPayload accepts a valid username and password", () => {
	const result = validateRegistrationPayload({
		username: "joolife_user",
		password: "securepass1",
	});
	assert.equal(result.username, "joolife_user");
	assert.equal(result.password, "securepass1");
	assert.ok(!result.error);
});

test("validateRegistrationPayload trims whitespace from username", () => {
	const result = validateRegistrationPayload({
		username: "  valid_user  ",
		password: "password123",
	});
	assert.equal(result.username, "valid_user");
});

test("validateRegistrationPayload rejects username shorter than MIN_USERNAME_LENGTH (3)", () => {
	const result = validateRegistrationPayload({ username: "ab", password: "password123" });
	assert.ok(result.error, "expected error");
	assert.ok(result.error.includes("3"), `error should mention min: ${result.error}`);
});

test("validateRegistrationPayload rejects username longer than MAX_USERNAME_LENGTH (30)", () => {
	const result = validateRegistrationPayload({
		username: "a".repeat(MAX_USERNAME_LENGTH + 1),
		password: "password123",
	});
	assert.ok(result.error, "expected error");
	assert.ok(result.error.includes(String(MAX_USERNAME_LENGTH)), result.error);
});

test("validateRegistrationPayload rejects usernames with uppercase letters", () => {
	const result = validateRegistrationPayload({ username: "UserName", password: "password123" });
	assert.ok(result.error);
	assert.ok(result.error.includes("영문 소문자"), result.error);
});

test("validateRegistrationPayload rejects usernames with hyphens", () => {
	const result = validateRegistrationPayload({ username: "user-name", password: "password123" });
	assert.ok(result.error);
});

test("validateRegistrationPayload rejects password shorter than MIN_PASSWORD_LENGTH (8)", () => {
	const result = validateRegistrationPayload({ username: "valid", password: "short" });
	assert.ok(result.error);
	assert.ok(result.error.includes(String(MIN_PASSWORD_LENGTH)), result.error);
});

test("validateRegistrationPayload rejects password longer than MAX_PASSWORD_LENGTH (72) — bcrypt DoS guard", () => {
	const result = validateRegistrationPayload({
		username: "valid",
		password: "a".repeat(MAX_PASSWORD_LENGTH + 1),
	});
	assert.ok(result.error);
	assert.ok(result.error.includes(String(MAX_PASSWORD_LENGTH)), result.error);
});

test("validateRegistrationPayload accepts password exactly at MAX_PASSWORD_LENGTH boundary", () => {
	const result = validateRegistrationPayload({
		username: "valid",
		password: "a".repeat(MAX_PASSWORD_LENGTH),
	});
	assert.ok(!result.error, `unexpected error: ${result.error}`);
	assert.equal(result.password.length, MAX_PASSWORD_LENGTH);
});

test("validateRegistrationPayload accepts password exactly at MIN_PASSWORD_LENGTH boundary", () => {
	const result = validateRegistrationPayload({
		username: "valid",
		password: "a".repeat(MIN_PASSWORD_LENGTH),
	});
	assert.ok(!result.error, `unexpected error: ${result.error}`);
});

test("validateRegistrationPayload handles missing body fields gracefully", () => {
	const result1 = validateRegistrationPayload({});
	assert.ok(result1.error);
	const result2 = validateRegistrationPayload(null);
	assert.ok(result2.error);
	const result3 = validateRegistrationPayload(undefined);
	assert.ok(result3.error);
});

test("validateRegistrationPayload ignores non-string username values", () => {
	const result = validateRegistrationPayload({ username: 42, password: "password123" });
	assert.ok(result.error);
});

// ── validateChangePasswordPayload ─────────────────────────────────────────────

test("validateChangePasswordPayload accepts valid currentPassword and newPassword", () => {
	const result = validateChangePasswordPayload({
		currentPassword: "oldpassword",
		newPassword: "newpassword1",
	});
	assert.equal(result.currentPassword, "oldpassword");
	assert.equal(result.newPassword, "newpassword1");
	assert.ok(!result.error);
});

test("validateChangePasswordPayload rejects empty currentPassword", () => {
	const result = validateChangePasswordPayload({
		currentPassword: "",
		newPassword: "newpassword1",
	});
	assert.ok(result.error);
	assert.ok(result.error.includes("현재 비밀번호"), result.error);
});

test("validateChangePasswordPayload rejects missing currentPassword", () => {
	const result = validateChangePasswordPayload({ newPassword: "newpassword1" });
	assert.ok(result.error);
});

test("validateChangePasswordPayload rejects newPassword shorter than MIN_PASSWORD_LENGTH (8)", () => {
	const result = validateChangePasswordPayload({
		currentPassword: "oldpassword",
		newPassword: "short",
	});
	assert.ok(result.error);
	assert.ok(result.error.includes(String(MIN_PASSWORD_LENGTH)), result.error);
});

test("validateChangePasswordPayload rejects newPassword longer than MAX_PASSWORD_LENGTH (72)", () => {
	const result = validateChangePasswordPayload({
		currentPassword: "oldpassword",
		newPassword: "a".repeat(MAX_PASSWORD_LENGTH + 1),
	});
	assert.ok(result.error);
	assert.ok(result.error.includes(String(MAX_PASSWORD_LENGTH)), result.error);
});

test("validateChangePasswordPayload rejects same-as-current newPassword", () => {
	const result = validateChangePasswordPayload({
		currentPassword: "samepassword123",
		newPassword: "samepassword123",
	});
	assert.ok(result.error);
	assert.ok(result.error.includes("달라야"), result.error);
});

test("validateChangePasswordPayload accepts newPassword exactly at MAX_PASSWORD_LENGTH (72)", () => {
	const result = validateChangePasswordPayload({
		currentPassword: "oldpassword",
		newPassword: "a".repeat(MAX_PASSWORD_LENGTH),
	});
	assert.ok(!result.error, `unexpected error: ${result.error}`);
});

test("validateChangePasswordPayload handles null body gracefully", () => {
	const result = validateChangePasswordPayload(null);
	assert.ok(result.error);
});

test("validateChangePasswordPayload treats non-string passwords as empty", () => {
	const result = validateChangePasswordPayload({ currentPassword: 12345, newPassword: "valid123" });
	// non-string currentPassword → empty string → "현재 비밀번호를 입력해 주세요."
	assert.ok(result.error);
});

// ── Constant boundary consistency ─────────────────────────────────────────────

test("MIN_USERNAME_LENGTH=3 and MAX_USERNAME_LENGTH=30 define a sensible range", () => {
	assert.equal(MIN_USERNAME_LENGTH, 3);
	assert.equal(MAX_USERNAME_LENGTH, 30);
	assert.ok(MIN_USERNAME_LENGTH < MAX_USERNAME_LENGTH);
	assert.ok(MIN_PASSWORD_LENGTH < MAX_PASSWORD_LENGTH);
});
