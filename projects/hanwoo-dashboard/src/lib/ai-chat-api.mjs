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
    throw new AiChatValidationError('`message` must be a string.');
  }

  const message = value.trim();
  if (!message) {
    throw new AiChatValidationError('`message` is required.');
  }

  if (message.length > AI_CHAT_LIMITS.maxMessageLength) {
    throw new AiChatValidationError(
      `\`message\` must be ${AI_CHAT_LIMITS.maxMessageLength} characters or fewer.`,
    );
  }

  return message;
}

export function normalizeAiChatHistory(history = []) {
  if (history === undefined || history === null) {
    return [];
  }

  if (!Array.isArray(history)) {
    throw new AiChatValidationError('`history` must be an array.');
  }

  if (history.length > AI_CHAT_LIMITS.maxHistoryItems) {
    throw new AiChatValidationError(
      `\`history\` must contain ${AI_CHAT_LIMITS.maxHistoryItems} items or fewer.`,
    );
  }

  return history.map((item, index) => {
    if (!item || typeof item !== 'object') {
      throw new AiChatValidationError(`\`history[${index}]\` must be an object.`);
    }

    if (item.role !== 'user' && item.role !== 'system') {
      throw new AiChatValidationError(`\`history[${index}].role\` must be "user" or "system".`);
    }

    if (typeof item.content !== 'string') {
      throw new AiChatValidationError(`\`history[${index}].content\` must be a string.`);
    }

    const content = item.content.trim();
    if (!content) {
      throw new AiChatValidationError(`\`history[${index}].content\` is required.`);
    }

    if (content.length > AI_CHAT_LIMITS.maxHistoryContentLength) {
      throw new AiChatValidationError(
        `\`history[${index}].content\` must be ${AI_CHAT_LIMITS.maxHistoryContentLength} characters or fewer.`,
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
    throw new AiChatValidationError('Request body must be valid JSON.');
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
          ? 'API key is invalid.'
          : 'Failed to generate an AI response.';
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
      return jsonError(error.message || 'Authentication required.', 401);
    }
    throw error;
  }

  const apiKey = getApiKey();
  if (!apiKey) {
    return jsonError('GEMINI_API_KEY is not configured.', 500);
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
  } catch (error) {
    return jsonError(error.message || 'Failed to start AI chat.', 500);
  }
}
