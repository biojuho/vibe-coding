export const AI_CHAT_LIMITS = {
	maxMessageLength: 1000,
	maxHistoryItems: 20,
	maxHistoryContentLength: 4000,
};

export class AiChatValidationError extends Error {
	constructor(message) {
		super(message);
		this.name = "AiChatValidationError";
	}
}

function jsonError(message, status) {
	return Response.json(
		{
			success: false,
			message,
			error: message,
		},
		{ status },
	);
}

function isAuthenticationError(error) {
	return error?.name === "AuthenticationError";
}

function normalizeProviderErrorMessage(error) {
	const rawMessage = typeof error?.message === "string" ? error.message : "";
	if (/api[_ -]?key|key/i.test(rawMessage)) {
		return "AI 설정 키가 올바르지 않습니다.";
	}

	return "AI 답변을 생성하지 못했습니다.";
}

function normalizeAiChatStreamOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeAiChatRequestDeps(deps) {
	return deps && typeof deps === "object" && !Array.isArray(deps) ? deps : {};
}

function hasRequiredAiChatDeps(deps) {
	return (
		typeof deps.authenticate === "function" &&
		typeof deps.getApiKey === "function" &&
		typeof deps.buildFarmContext === "function" &&
		typeof deps.createChatStream === "function"
	);
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

export function normalizeAiChatHistory(history = []) {
	if (history === undefined || history === null) {
		return [];
	}

	if (!Array.isArray(history)) {
		throw new AiChatValidationError("대화 이력 형식이 올바르지 않습니다.");
	}

	if (history.length > AI_CHAT_LIMITS.maxHistoryItems) {
		throw new AiChatValidationError(
			`대화 이력은 ${AI_CHAT_LIMITS.maxHistoryItems}개 이하로 보내 주세요.`,
		);
	}

	return history.map((item, index) => {
		if (!item || typeof item !== "object" || Array.isArray(item)) {
			throw new AiChatValidationError(
				`대화 이력 ${index + 1}번째 항목 형식이 올바르지 않습니다.`,
			);
		}

		if (item.role !== "user" && item.role !== "system") {
			throw new AiChatValidationError(
				`대화 이력 ${index + 1}번째 역할이 올바르지 않습니다.`,
			);
		}

		if (typeof item.content !== "string") {
			throw new AiChatValidationError(
				`대화 이력 ${index + 1}번째 내용 형식이 올바르지 않습니다.`,
			);
		}

		const content = item.content.trim();
		if (!content) {
			throw new AiChatValidationError(
				`대화 이력 ${index + 1}번째 내용이 비어 있습니다.`,
			);
		}

		if (content.length > AI_CHAT_LIMITS.maxHistoryContentLength) {
			throw new AiChatValidationError(
				`대화 이력 ${index + 1}번째 내용은 ${AI_CHAT_LIMITS.maxHistoryContentLength}자 이내로 보내 주세요.`,
			);
		}

		return {
			role: item.role,
			content,
		};
	});
}

export function normalizeAiChatHistoryForGemini(history = []) {
	return normalizeAiChatHistory(history).map((item) => ({
		role: item.role === "system" ? "model" : "user",
		parts: [{ text: item.content }],
	}));
}

export async function parseAiChatRequest(request) {
	let body;
	try {
		body = await request.json();
	} catch {
		throw new AiChatValidationError(
			"요청 본문은 올바른 JSON 형식이어야 합니다.",
		);
	}

	return {
		message: parseMessage(body?.message),
		geminiHistory: normalizeAiChatHistoryForGemini(body?.history ?? []),
	};
}

const AI_CHAT_STREAM_IDLE_TIMEOUT_MS = 30000;
export const AI_CHAT_STREAM_TIMEOUT_MESSAGE =
	"AI 응답이 지연되어 연결을 종료했습니다. 잠시 후 다시 시도해 주세요.";
const STREAM_IDLE_TIMEOUT = Symbol("ai-chat-stream-idle-timeout");

export function createAiChatSseStream(options = {}) {
	const {
		chat,
		message,
		encoder = new TextEncoder(),
		idleTimeoutMs = AI_CHAT_STREAM_IDLE_TIMEOUT_MS,
	} = normalizeAiChatStreamOptions(options);
	return new ReadableStream({
		async start(controller) {
			try {
				const result = await chat.sendMessageStream(message);
				// Support both async (real Gemini) and sync (test) iterables so a
				// stalled provider can't hold the connection open forever: each
				// chunk races an idle timer that closes the stream on expiry.
				const source = result.stream;
				const iterator =
					typeof source?.[Symbol.asyncIterator] === "function"
						? source[Symbol.asyncIterator]()
						: source[Symbol.iterator]();

				while (true) {
					let timer;
					const idle = new Promise((resolve) => {
						timer = setTimeout(
							() => resolve(STREAM_IDLE_TIMEOUT),
							idleTimeoutMs,
						);
					});
					let next;
					try {
						next = await Promise.race([
							Promise.resolve(iterator.next()),
							idle,
						]);
					} finally {
						clearTimeout(timer);
					}

					if (next === STREAM_IDLE_TIMEOUT) {
						if (typeof iterator.return === "function") {
							try {
								await iterator.return();
							} catch {
								/* best-effort upstream cancel */
							}
						}
						controller.enqueue(
							encoder.encode(
								`data: ${JSON.stringify({ error: AI_CHAT_STREAM_TIMEOUT_MESSAGE })}\n\n`,
							),
						);
						controller.close();
						return;
					}

					if (next.done) {
						break;
					}

					const text = next.value.text();
					if (text) {
						controller.enqueue(
							encoder.encode(`data: ${JSON.stringify({ text })}\n\n`),
						);
					}
				}

				controller.enqueue(encoder.encode("data: [DONE]\n\n"));
				controller.close();
			} catch (error) {
				const message = normalizeProviderErrorMessage(error);
				controller.enqueue(
					encoder.encode(`data: ${JSON.stringify({ error: message })}\n\n`),
				);
				controller.close();
			}
		},
	});
}

export async function handleAiChatRequest(request, deps) {
	const safeDeps = normalizeAiChatRequestDeps(deps);
	if (!hasRequiredAiChatDeps(safeDeps)) {
		return jsonError(
			"AI 채팅 설정이 올바르지 않습니다. 관리자에게 문의해 주세요.",
			500,
		);
	}

	const {
		authenticate,
		getApiKey,
		buildFarmContext,
		createChatStream,
		systemInstruction,
	} = safeDeps;

	try {
		await authenticate();
	} catch (error) {
		if (isAuthenticationError(error)) {
			return jsonError("로그인이 필요합니다.", 401);
		}
		throw error;
	}

	const apiKey = getApiKey();
	if (!apiKey) {
		return jsonError(
			"AI 비서 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.",
			500,
		);
	}

	let payload;
	try {
		payload = await parseAiChatRequest(request);
	} catch (error) {
		if (error instanceof AiChatValidationError) {
			return jsonError(error.message, 400);
		}
		throw error;
	}

	try {
		const farmContext = await buildFarmContext();
		const stream = createChatStream({
			apiKey,
			message: payload.message,
			history: payload.geminiHistory,
			systemInstruction: `${systemInstruction}\n${farmContext}`,
		});

		return new Response(stream, {
			headers: {
				"Content-Type": "text/event-stream; charset=utf-8",
				"Cache-Control": "no-cache",
				Connection: "keep-alive",
			},
		});
	} catch {
		return jsonError(
			"AI 채팅을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.",
			500,
		);
	}
}
