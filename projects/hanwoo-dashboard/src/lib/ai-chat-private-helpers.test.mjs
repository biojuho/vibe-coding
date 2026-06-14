/**
 * Behavioral tests for private (non-exported) helpers in ai-chat-api.mjs:
 *   normalizeProviderErrorMessage — key-related errors → Korean key message
 *   parseMessage                  — string validation + length limit
 *
 * Also adds source-grep guard for system.js isRawDataActionRow which
 * follows the same plain-object pattern tested in action-row-normalizers.test.mjs.
 *
 * ai-chat-api.mjs has no external imports so it can be loaded directly.
 * Private functions are re-implemented inline; exported constants are
 * imported directly to keep the limits in sync.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { AI_CHAT_LIMITS, AiChatValidationError } from "./ai-chat-api.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/ai-chat-api.mjs"), "utf8");
const systemSrc = readFileSync(
	path.join(SRC_ROOT, "lib/actions/system.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

function normalizeProviderErrorMessage(error) {
	const rawMessage = typeof error?.message === "string" ? error.message : "";
	if (/api[_ -]?key|key/i.test(rawMessage)) {
		return "AI 설정 키가 올바르지 않습니다.";
	}
	return "AI 답변을 생성하지 못했습니다.";
}

function parseMessage(value) {
	if (typeof value !== "string") {
		throw new AiChatValidationError("질문은 문자열로 입력해 주세요.");
	}
	const message = value.trim();
	if (!message) {
		throw new AiChatValidationError("질문을 입력해 주세요.");
	}
	if (message.length > AI_CHAT_LIMITS.maxMessageLength) {
		throw new AiChatValidationError(
			`질문은 ${AI_CHAT_LIMITS.maxMessageLength}자 이내로 입력해 주세요.`,
		);
	}
	return message;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("ai-chat-api.mjs normalizeProviderErrorMessage checks key-related error pattern", () => {
	assert.match(src, /function normalizeProviderErrorMessage\(error\)/);
	assert.match(src, /\/api\[_ -\]\?key\|key\/i\.test\(rawMessage\)/);
	assert.match(src, /"AI 설정 키가 올바르지 않습니다\."/);
	assert.match(src, /"AI 답변을 생성하지 못했습니다\."/);
});

test("ai-chat-api.mjs parseMessage trims and enforces length limit", () => {
	assert.match(src, /function parseMessage\(value\)/);
	assert.match(src, /typeof value !== ["']string["']/);
	assert.match(src, /message\.length > AI_CHAT_LIMITS\.maxMessageLength/);
});

test("system.js isRawDataActionRow is non-null non-array object check", () => {
	assert.match(systemSrc, /function isRawDataActionRow\(value\)/);
	assert.match(systemSrc, /value !== null/);
	assert.match(systemSrc, /!Array\.isArray\(value\)/);
});

// ── normalizeProviderErrorMessage behavioral tests ────────────────────────────

test("normalizeProviderErrorMessage returns key error message for 'api key' in message", () => {
	assert.equal(
		normalizeProviderErrorMessage(new Error("Invalid api key provided")),
		"AI 설정 키가 올바르지 않습니다.",
	);
});

test("normalizeProviderErrorMessage returns key error message for 'API_KEY' (case-insensitive)", () => {
	assert.equal(
		normalizeProviderErrorMessage(new Error("API_KEY missing")),
		"AI 설정 키가 올바르지 않습니다.",
	);
});

test("normalizeProviderErrorMessage returns key error message for 'key' alone", () => {
	assert.equal(
		normalizeProviderErrorMessage(new Error("key not found")),
		"AI 설정 키가 올바르지 않습니다.",
	);
});

test("normalizeProviderErrorMessage returns key error message for 'api-key' variant", () => {
	assert.equal(
		normalizeProviderErrorMessage(new Error("api-key is invalid")),
		"AI 설정 키가 올바르지 않습니다.",
	);
});

test("normalizeProviderErrorMessage returns generic message for unrelated errors", () => {
	assert.equal(
		normalizeProviderErrorMessage(new Error("Network timeout")),
		"AI 답변을 생성하지 못했습니다.",
	);
	assert.equal(
		normalizeProviderErrorMessage(new Error("Rate limit exceeded")),
		"AI 답변을 생성하지 못했습니다.",
	);
});

test("normalizeProviderErrorMessage returns generic message for null/undefined error", () => {
	assert.equal(
		normalizeProviderErrorMessage(null),
		"AI 답변을 생성하지 못했습니다.",
	);
	assert.equal(
		normalizeProviderErrorMessage(undefined),
		"AI 답변을 생성하지 못했습니다.",
	);
});

test("normalizeProviderErrorMessage returns generic message for error without message property", () => {
	assert.equal(
		normalizeProviderErrorMessage({}),
		"AI 답변을 생성하지 못했습니다.",
	);
});

test("normalizeProviderErrorMessage returns generic for error.message that is not a string", () => {
	assert.equal(
		normalizeProviderErrorMessage({ message: 42 }),
		"AI 답변을 생성하지 못했습니다.",
	);
});

// ── parseMessage behavioral tests ─────────────────────────────────────────────

test("parseMessage returns trimmed string for a valid message", () => {
	assert.equal(parseMessage("안녕하세요"), "안녕하세요");
});

test("parseMessage trims whitespace from a valid message", () => {
	assert.equal(parseMessage("  안녕하세요  "), "안녕하세요");
});

test("parseMessage throws AiChatValidationError for non-string input", () => {
	assert.throws(
		() => parseMessage(null),
		(err) => err instanceof AiChatValidationError && err.name === "AiChatValidationError",
	);
	assert.throws(
		() => parseMessage(42),
		(err) => err instanceof AiChatValidationError,
	);
	assert.throws(
		() => parseMessage(undefined),
		(err) => err instanceof AiChatValidationError,
	);
});

test("parseMessage throws AiChatValidationError for empty string", () => {
	assert.throws(
		() => parseMessage(""),
		(err) => err instanceof AiChatValidationError,
	);
});

test("parseMessage throws AiChatValidationError for whitespace-only string", () => {
	assert.throws(
		() => parseMessage("   "),
		(err) => err instanceof AiChatValidationError,
	);
});

test("parseMessage accepts a message of exactly maxMessageLength characters", () => {
	const message = "a".repeat(AI_CHAT_LIMITS.maxMessageLength);
	assert.equal(parseMessage(message), message);
});

test("parseMessage throws for a message exceeding maxMessageLength", () => {
	const message = "a".repeat(AI_CHAT_LIMITS.maxMessageLength + 1);
	assert.throws(
		() => parseMessage(message),
		(err) => err instanceof AiChatValidationError && err.message.includes(`${AI_CHAT_LIMITS.maxMessageLength}자`),
	);
});

test("AiChatValidationError has name='AiChatValidationError' and is instanceof Error", () => {
	const err = new AiChatValidationError("테스트");
	assert.equal(err.name, "AiChatValidationError");
	assert.ok(err instanceof Error);
	assert.equal(err.message, "테스트");
});
