export const AI_CHAT_LIMITS = {
  maxMessageLength: 1000,
  maxHistoryItems: 20,
  maxHistoryContentLength: 4000,
};

export class AiChatValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AiChatValidationError';
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
  return error?.name === 'AuthenticationError';
}

function parseMessage(value) {
  if (typeof value !== 'string') {
    throw new AiChatValidationError('질문은 문자열로 입력해 주세요.');
  }

  const message = value.trim();
  if (!message) {
    throw new AiChatValidationError('질문을 입력해 주세요.');
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
    throw new AiChatValidationError('대화 이력 형식이 올바르지 않습니다.');
  }

  if (history.length > AI_CHAT_LIMITS.maxHistoryItems) {
    throw new AiChatValidationError(
      `대화 이력은 ${AI_CHAT_LIMITS.maxHistoryItems}개 이하로 보내 주세요.`,
    );
  }

  return history.map((item, index) => {
    if (!item || typeof item !== 'object') {
      throw new AiChatValidationError(`대화 이력 ${index + 1}번째 항목 형식이 올바르지 않습니다.`);
    }

    if (item.role !== 'user' && item.role !== 'system') {
      throw new AiChatValidationError(`대화 이력 ${index + 1}번째 역할이 올바르지 않습니다.`);
    }

    if (typeof item.content !== 'string') {
      throw new AiChatValidationError(`대화 이력 ${index + 1}번째 내용 형식이 올바르지 않습니다.`);
    }

    const content = item.content.trim();
    if (!content) {
      throw new AiChatValidationError(`대화 이력 ${index + 1}번째 내용이 비어 있습니다.`);
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
    role: item.role === 'system' ? 'model' : 'user',
    parts: [{ text: item.content }],
  }));
}

export async function parseAiChatRequest(request) {
  let body;
  try {
    body = await request.json();
  } catch {
    throw new AiChatValidationError('요청 본문은 올바른 JSON 형식이어야 합니다.');
  }

  return {
    message: parseMessage(body?.message),
    geminiHistory: normalizeAiChatHistoryForGemini(body?.history ?? []),
  };
}

export function createAiChatSseStream({ chat, message, encoder = new TextEncoder() }) {
  return new ReadableStream({
    async start(controller) {
      try {
        const result = await chat.sendMessageStream(message);

        for await (const chunk of result.stream) {
          const text = chunk.text();
          if (text) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`));
          }
        }

        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      } catch (error) {
        const message = error?.message?.includes('API_KEY')
          ? 'AI 설정 키가 올바르지 않습니다.'
          : 'AI 답변을 생성하지 못했습니다.';
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: message })}\n\n`));
        controller.close();
      }
    },
  });
}

export async function handleAiChatRequest(request, deps) {
  const {
    authenticate,
    getApiKey,
    buildFarmContext,
    createChatStream,
    systemInstruction,
  } = deps;

  try {
    await authenticate();
  } catch (error) {
    if (isAuthenticationError(error)) {
      return jsonError('로그인이 필요합니다.', 401);
    }
    throw error;
  }

  const apiKey = getApiKey();
  if (!apiKey) {
    return jsonError('AI 비서 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.', 500);
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
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch {
    return jsonError('AI 채팅을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.', 500);
  }
}
