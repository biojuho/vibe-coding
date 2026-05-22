import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
	AI_CHAT_LIMITS,
	createAiChatSseStream,
	handleAiChatRequest,
	normalizeAiChatHistoryForGemini,
	parseAiChatRequest,
} from "./ai-chat-api.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function jsonRequest(body) {
	return new Request("https://joolife.local/api/ai/chat", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body),
	});
}

async function readJson(response) {
	return response.json();
}

async function readStreamText(stream) {
	const reader = stream.getReader();
	const decoder = new TextDecoder();
	let output = "";

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		output += decoder.decode(value, { stream: true });
	}

	return output;
}

function makeDeps(overrides = {}) {
	return {
		authenticate: async () => ({ user: { id: "user-1" } }),
		getApiKey: () => "gemini-key",
		buildFarmContext: async () => "farm context",
		createChatStream: ({ message, history, systemInstruction }) =>
			new ReadableStream({
				start(controller) {
					const encoder = new TextEncoder();
					controller.enqueue(
						encoder.encode(
							`data: ${JSON.stringify({
								text: `${message}:${history.length}:${systemInstruction.includes("farm context")}`,
							})}\n\n`,
						),
					);
					controller.enqueue(encoder.encode("data: [DONE]\n\n"));
					controller.close();
				},
			}),
		systemInstruction: "system",
		...overrides,
	};
}

test("parseAiChatRequest normalizes valid chat input for Gemini", async () => {
	const result = await parseAiChatRequest(
		jsonRequest({
			message: "  feed advice  ",
			history: [
				{ role: "user", content: "first question" },
				{ role: "system", content: "first answer" },
			],
		}),
	);

	assert.equal(result.message, "feed advice");
	assert.deepEqual(result.geminiHistory, [
		{ role: "user", parts: [{ text: "first question" }] },
		{ role: "model", parts: [{ text: "first answer" }] },
	]);
});

test("parseAiChatRequest rejects malformed JSON and invalid message payloads", async () => {
	await assert.rejects(
		() =>
			parseAiChatRequest(
				new Request("https://joolife.local/api/ai/chat", {
					method: "POST",
					body: "{bad-json",
				}),
			),
		/올바른 JSON/,
	);

	await assert.rejects(
		() => parseAiChatRequest(jsonRequest({ message: "" })),
		/질문을 입력/,
	);
	await assert.rejects(
		() =>
			parseAiChatRequest(
				jsonRequest({
					message: "x".repeat(AI_CHAT_LIMITS.maxMessageLength + 1),
				}),
			),
		/1000자 이내/,
	);
});

test("normalizeAiChatHistoryForGemini rejects unsafe history shapes", () => {
	assert.throws(
		() => normalizeAiChatHistoryForGemini("not-array"),
		/대화 이력 형식/,
	);
	assert.throws(
		() =>
			normalizeAiChatHistoryForGemini(
				Array.from({ length: AI_CHAT_LIMITS.maxHistoryItems + 1 }, () => ({
					role: "user",
					content: "x",
				})),
			),
		/20개 이하/,
	);
	assert.throws(
		() =>
			normalizeAiChatHistoryForGemini([{ role: "assistant", content: "x" }]),
		/역할이 올바르지 않습니다/,
	);
});

test("handleAiChatRequest returns SSE for a valid authenticated request", async () => {
	const response = await handleAiChatRequest(
		jsonRequest({
			message: "hello",
			history: [{ role: "user", content: "previous question" }],
		}),
		makeDeps(),
	);

	assert.equal(response.status, 200);
	assert.match(response.headers.get("Content-Type"), /text\/event-stream/);
	const output = await readStreamText(response.body);
	assert.match(output, /hello:1:true/);
	assert.match(output, /\[DONE\]/);
});

test("handleAiChatRequest blocks unauthenticated callers before API-key and farm work", async () => {
	let apiKeyRead = false;
	let farmContextBuilt = false;
	const authError = new Error("Authentication required.");
	authError.name = "AuthenticationError";

	const response = await handleAiChatRequest(
		jsonRequest({ message: "hello" }),
		makeDeps({
			authenticate: async () => {
				throw authError;
			},
			getApiKey: () => {
				apiKeyRead = true;
				return "gemini-key";
			},
			buildFarmContext: async () => {
				farmContextBuilt = true;
				return "farm context";
			},
		}),
	);

	assert.equal(response.status, 401);
	assert.equal(apiKeyRead, false);
	assert.equal(farmContextBuilt, false);
	assert.deepEqual(await readJson(response), {
		success: false,
		message: "로그인이 필요합니다.",
		error: "로그인이 필요합니다.",
	});
});

test("handleAiChatRequest reports validation and configuration failures consistently", async () => {
	const invalid = await handleAiChatRequest(
		jsonRequest({ message: 123 }),
		makeDeps(),
	);
	assert.equal(invalid.status, 400);
	assert.deepEqual(await readJson(invalid), {
		success: false,
		message: "질문은 문자열로 입력해 주세요.",
		error: "질문은 문자열로 입력해 주세요.",
	});

	const missingKey = await handleAiChatRequest(
		jsonRequest({ message: "hello" }),
		makeDeps({ getApiKey: () => "" }),
	);
	assert.equal(missingKey.status, 500);
	assert.deepEqual(await readJson(missingKey), {
		success: false,
		message: "AI 비서 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.",
		error: "AI 비서 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.",
	});
});

test("createAiChatSseStream emits chunks and converts provider errors to SSE errors", async () => {
	const okStream = createAiChatSseStream({
		message: "question",
		chat: {
			async sendMessageStream() {
				return {
					stream: [{ text: () => "one" }, { text: () => "two" }],
				};
			},
		},
	});

	assert.match(await readStreamText(okStream), /"one"/);

	const errorStream = createAiChatSseStream({
		message: "question",
		chat: {
			async sendMessageStream() {
				throw new Error("API_KEY_INVALID");
			},
		},
	});

	assert.match(
		await readStreamText(errorStream),
		/AI 설정 키가 올바르지 않습니다/,
	);
});

test("AI chat route farm context avoids English fallback copy", () => {
	const source = readFileSync(
		path.join(SRC_ROOT, "app/api/ai/chat/route.js"),
		"utf8",
	);

	assert.match(source, /import \{ toFiniteNumber \} from '@\/lib\/utils';/);
	assert.match(source, /function formatSaleDateForContext\(value\) \{/);
	assert.match(source, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
	assert.match(source, /date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
	assert.match(source, /return '출하일 미등록';/);
	assert.match(source, /return date\.toISOString\(\)\.slice\(0, 10\);/);
	assert.match(
		source,
		/\(toFiniteNumber\(sale\.price\) \/ 10000\)\.toFixed\(0\)/,
	);
	assert.match(source, /Joolife AI 농장 비서/);
	assert.match(source, /AI 농장 컨텍스트 구성 실패/);
	assert.match(source, /현재 농장 정보/);
	assert.match(source, /개체명 미등록/);
	assert.match(source, /이력번호 미등록/);
	assert.match(source, /출하일 미등록/);
	assert.match(source, /최근 판매 기록 없음/);
	assert.match(source, /Joolife 한우 농장/);
	assert.doesNotMatch(
		source,
		/new Date\(sale\.saleDate\)\.toISOString\(\)\.slice\(0, 10\)/,
	);
	assert.doesNotMatch(source, /Joolife AI farm assistant/);
	assert.doesNotMatch(source, /Answer in Korean/);
	assert.doesNotMatch(source, /Failed to build farm context/);
	assert.doesNotMatch(source, /unknown/);
	assert.doesNotMatch(source, /No recent sales records/);
	assert.doesNotMatch(source, /Current farm context/);
	assert.doesNotMatch(source, /Farm data could not be loaded/);
	assert.doesNotMatch(source, /man KRW/);
});
