import assert from 'node:assert/strict';
import test from 'node:test';

import {
  AI_CHAT_LIMITS,
  createAiChatSseStream,
  handleAiChatRequest,
  normalizeAiChatHistoryForGemini,
  parseAiChatRequest,
} from './ai-chat-api.mjs';

function jsonRequest(body) {
  return new Request('https://joolife.local/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function readJson(response) {
  return response.json();
}

async function readStreamText(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let output = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    output += decoder.decode(value, { stream: true });
  }

  return output;
}

function makeDeps(overrides = {}) {
  return {
    authenticate: async () => ({ user: { id: 'user-1' } }),
    getApiKey: () => 'gemini-key',
    buildFarmContext: async () => 'farm context',
    createChatStream: ({ message, history, systemInstruction }) =>
      new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                text: `${message}:${history.length}:${systemInstruction.includes('farm context')}`,
              })}\n\n`,
            ),
          );
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        },
      }),
    systemInstruction: 'system',
    ...overrides,
  };
}

test('parseAiChatRequest normalizes valid chat input for Gemini', async () => {
  const result = await parseAiChatRequest(
    jsonRequest({
      message: '  feed advice  ',
      history: [
        { role: 'user', content: 'first question' },
        { role: 'system', content: 'first answer' },
      ],
    }),
  );

  assert.equal(result.message, 'feed advice');
  assert.deepEqual(result.geminiHistory, [
    { role: 'user', parts: [{ text: 'first question' }] },
    { role: 'model', parts: [{ text: 'first answer' }] },
  ]);
});

test('parseAiChatRequest rejects malformed JSON and invalid message payloads', async () => {
  await assert.rejects(
    () =>
      parseAiChatRequest(
        new Request('https://joolife.local/api/ai/chat', {
          method: 'POST',
          body: '{bad-json',
        }),
      ),
    /valid JSON/,
  );

  await assert.rejects(() => parseAiChatRequest(jsonRequest({ message: '' })), /required/);
  await assert.rejects(
    () =>
      parseAiChatRequest(
        jsonRequest({ message: 'x'.repeat(AI_CHAT_LIMITS.maxMessageLength + 1) }),
      ),
    /characters or fewer/,
  );
});

test('normalizeAiChatHistoryForGemini rejects unsafe history shapes', () => {
  assert.throws(() => normalizeAiChatHistoryForGemini('not-array'), /must be an array/);
  assert.throws(
    () =>
      normalizeAiChatHistoryForGemini(
        Array.from({ length: AI_CHAT_LIMITS.maxHistoryItems + 1 }, () => ({
          role: 'user',
          content: 'x',
        })),
      ),
    /must contain 20 items or fewer/,
  );
  assert.throws(
    () => normalizeAiChatHistoryForGemini([{ role: 'assistant', content: 'x' }]),
    /role/,
  );
});

test('handleAiChatRequest returns SSE for a valid authenticated request', async () => {
  const response = await handleAiChatRequest(
    jsonRequest({
      message: 'hello',
      history: [{ role: 'user', content: 'previous question' }],
    }),
    makeDeps(),
  );

  assert.equal(response.status, 200);
  assert.match(response.headers.get('Content-Type'), /text\/event-stream/);
  const output = await readStreamText(response.body);
  assert.match(output, /hello:1:true/);
  assert.match(output, /\[DONE\]/);
});

test('handleAiChatRequest blocks unauthenticated callers before API-key and farm work', async () => {
  let apiKeyRead = false;
  let farmContextBuilt = false;
  const authError = new Error('Authentication required.');
  authError.name = 'AuthenticationError';

  const response = await handleAiChatRequest(
    jsonRequest({ message: 'hello' }),
    makeDeps({
      authenticate: async () => {
        throw authError;
      },
      getApiKey: () => {
        apiKeyRead = true;
        return 'gemini-key';
      },
      buildFarmContext: async () => {
        farmContextBuilt = true;
        return 'farm context';
      },
    }),
  );

  assert.equal(response.status, 401);
  assert.equal(apiKeyRead, false);
  assert.equal(farmContextBuilt, false);
  assert.deepEqual(await readJson(response), {
    success: false,
    message: 'Authentication required.',
    error: 'Authentication required.',
  });
});

test('handleAiChatRequest reports validation and configuration failures consistently', async () => {
  const invalid = await handleAiChatRequest(jsonRequest({ message: 123 }), makeDeps());
  assert.equal(invalid.status, 400);
  assert.equal((await readJson(invalid)).success, false);

  const missingKey = await handleAiChatRequest(
    jsonRequest({ message: 'hello' }),
    makeDeps({ getApiKey: () => '' }),
  );
  assert.equal(missingKey.status, 500);
  assert.match((await readJson(missingKey)).message, /GEMINI_API_KEY/);
});

test('createAiChatSseStream emits chunks and converts provider errors to SSE errors', async () => {
  const okStream = createAiChatSseStream({
    message: 'question',
    chat: {
      async sendMessageStream() {
        return {
          stream: [
            { text: () => 'one' },
            { text: () => 'two' },
          ],
        };
      },
    },
  });

  assert.match(await readStreamText(okStream), /"one"/);

  const errorStream = createAiChatSseStream({
    message: 'question',
    chat: {
      async sendMessageStream() {
        throw new Error('API_KEY_INVALID');
      },
    },
  });

  assert.match(await readStreamText(errorStream), /API key is invalid/);
});
