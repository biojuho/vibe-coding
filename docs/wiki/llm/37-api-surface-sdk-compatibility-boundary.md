# 37 - API Surface - SDK Compatibility - OpenAI-Compatible Boundary

> Provider/model choice is not the same thing as API surface choice.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/openai_client.py`, `projects/blind-to-x/pipeline/draft_providers.py`, and `projects/blind-to-x/pipeline/editorial_reviewer.py`.

## Why This Is Separate

This wiki already covers model selection, structured output, tool calling, generation parameters, local inference, and eval evidence. API surface is the narrower compatibility question: which request and response contract did a workflow actually use?

These are distinct surfaces:

| Surface | Typical endpoint or SDK call | Shape that matters |
|---|---|---|
| OpenAI Responses | `POST /v1/responses`, `client.responses.create(...)` | `input`, `instructions`, response items, built-in tools, state, `text` config |
| OpenAI Chat Completions | `POST /v1/chat/completions`, `client.chat.completions.create(...)` | `messages`, `choices[0].message`, Chat-style tools, Chat usage fields |
| Anthropic Messages | `POST /v1/messages`, `client.messages.create(...)` | top-level `system`, `messages`, content blocks, `stop_reason`, `usage` |
| Gemini GenerateContent | `models.generateContent`, `client.models.generate_content(...)` | `contents`, `systemInstruction`, `generationConfig`, `tools`, `candidates`, `usageMetadata` |
| OpenAI-compatible adapters | OpenAI SDK plus provider `base_url` | a provider-specific subset, not full OpenAI feature parity |
| Ollama native | `POST /api/chat` | local timing, model load, eval counts, local `format` behavior |

Operational rule: every cached, evaluated, published, or release-gated LLM output needs to preserve the API surface and parser shape, not only provider and model.

Stateful continuation is a separate compatibility field. Responses `previous_response_id`, Conversations, SDK sessions, Anthropic message history, LangGraph checkpoints, MCP context, and `.ai` handoff have different ownership and replay behavior; record them with [38-conversation-state-memory-handoff-boundary](38-conversation-state-memory-handoff-boundary.md).

## Current Code Facts

### 1. Workspace `LLMClient` Uses Multiple API Surfaces

`workspace/execution/llm_client.py` defines OpenAI-compatible base URLs for xAI, DeepSeek, Moonshot, ZhipuAI, and Groq. It instantiates those providers with the OpenAI SDK and a replaced `base_url`, while OpenAI itself uses the default OpenAI client. Ollama is routed through the repo-local `OllamaClient` rather than the OpenAI-compatible client.

The shared generation branch then sends:

- OpenAI-compatible providers: optional `response_format={"type": "json_object"}` and `client.chat.completions.create(**kwargs)`.
- Gemini: `response_mime_type="application/json"` when JSON mode is requested and `client.models.generate_content(...)`.
- Anthropic: `client.messages.create(**create_kwargs)`.

Code evidence: `workspace/execution/llm_client.py` lines 115, 348-350, 368-374, 426-427, 442-444, and 477.

Operational conclusion: the common client is not a provider-neutral Responses API abstraction. It is a mixed-surface fallback client with one Chat Completions adapter family, one Gemini GenerateContent path, one Anthropic Messages path, and one local Ollama native path.

### 2. Shorts Maker Has The Same Mixed Boundary

`projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py` keeps its own `OPENAI_COMPATIBLE_BASE_URLS`, builds OpenAI SDK clients for those base URLs, sends OpenAI/xAI/DeepSeek/Moonshot/ZhipuAI/Groq/Mimo through Chat Completions, sends Gemini through `models.generate_content`, and sends Anthropic through Messages with `max_tokens=2000`.

Code evidence: `llm_router.py` lines 103, 215-221, 255-256, 279-284, and 292-296.

`projects/shorts-maker-v2/src/shorts_maker_v2/providers/openai_client.py` also uses OpenAI Chat Completions for JSON generation and separate OpenAI audio/image surfaces for TTS, transcription, and image generation. Code evidence: `openai_client.py` lines 31-37, 60, 95-98, and 118.

Operational conclusion: Shorts generation cannot be replayed from provider/model alone. A script, transcript, or generated image can involve different OpenAI API families even when the provider is "openai".

### 3. Blind-to-X Uses SDK And Raw REST Compatibility Paths

`projects/blind-to-x/pipeline/draft_providers.py` imports `AsyncAnthropic` and `AsyncOpenAI`. It uses:

- Anthropic `messages.create`.
- OpenAI and xAI `chat.completions.create`.
- Ollama through `AsyncOpenAI(api_key="ollama", base_url=...)`.
- Gemini through raw REST `...:generateContent`, then parses `candidates` and `usageMetadata`.

Code evidence: `draft_providers.py` lines 15-16, 125-127, 215, 231, 242, 254, 266-290, and 383-390.

`projects/blind-to-x/pipeline/editorial_reviewer.py` has another raw REST branch for DeepSeek and xAI using `https://api.deepseek.com/v1/chat/completions` and `https://api.x.ai/v1/chat/completions`, then parses `choices[0].message.content`.

Code evidence: `editorial_reviewer.py` lines 77, 83, 89, 404, 427-448, and 467-471.

Operational conclusion: a compatibility bug can be hidden by the phrase "OpenAI-compatible". The SDK branch and raw REST branch must both record endpoint, base URL, response parser, and error shape.

### 4. Existing Wiki Evidence Is Close But Incomplete

Page 31 already includes `api_surface` in the minimum generation-parameter artifact. Page 35 already says Ollama OpenAI-compatible wiring is not full OpenAI feature parity. Page 23 already records that the common `LLMClient` uses Chat Completions rather than OpenAI Responses tools.

The missing piece was a dedicated artifact contract for SDK/API compatibility. This page is that contract.

## Official Boundaries

### OpenAI

OpenAI describes the Responses API as its most advanced interface for model responses and lists `POST https://api.openai.com/v1/responses` as the creation endpoint. The same API reference still exposes Chat Completions as a separate resource.

Repo implication: moving a workflow from Chat Completions to Responses is a migration, not a rename. `messages` do not become equivalent to `input` unless the parser, tools, structured-output settings, streaming, state, usage handling, and tests migrate together.

### Anthropic

The Claude Messages API creates a message from a structured list of input messages, requires a model and output limit in common examples, and returns a message object with content blocks, stop reason, and usage semantics that differ from OpenAI `choices`.

Repo implication: Anthropic should stay behind a Messages-specific adapter. Do not normalize Anthropic content blocks into Chat `choices` until a parser test proves the lossy parts are either unused or explicitly preserved.

### Gemini

Gemini `models.generateContent` accepts a `GenerateContentRequest` with `contents`, optional `tools`, `toolConfig`, `safetySettings`, `systemInstruction`, and `generationConfig`; responses are built around `candidates` and `usageMetadata`.

Repo implication: Gemini JSON mode, tools, safety settings, grounding, and thinking config are not Chat Completions fields. Keep the GenerateContent request and response shape in the artifact.

### OpenAI-Compatible Providers

DeepSeek documents `POST /chat/completions` with Chat-style `messages`, `response_format`, `tools`, streaming, and a `chat.completion` response object, but also exposes provider-specific fields such as `thinking` and different model IDs. xAI documents `/v1/chat/completions` and also has a Responses surface. Groq states its API is mostly compatible with OpenAI client libraries, gives `https://api.groq.com/openai/v1` as the base URL, and lists unsupported OpenAI features and field constraints. Ollama documents compatibility with parts of the OpenAI API and separately exposes native local endpoints.

Repo implication: "OpenAI-compatible" must mean "this exact endpoint, SDK version, request fields, and parser passed", not "all OpenAI features are supported".

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Force one provider-neutral superset | One caller signature | Hides incompatible fields, weakens tool/JSON/media semantics | Reject |
| B. Keep per-surface adapters and emit API-surface artifacts | Accurate, testable, preserves provider differences | More metadata fields | Adopt |
| C. Migrate all OpenAI calls to Responses immediately | Newer OpenAI surface | Breaks existing Chat-compatible providers and parsers | Defer per workflow |
| D. Treat OpenAI-compatible providers as equivalent to OpenAI | Simple base URL swap | False feature parity, silent parser drift | Reject |

**Decision:** adopt B. Chat Completions, Responses, Anthropic Messages, Gemini GenerateContent, OpenAI-compatible Chat, and Ollama native/OpenAI-compatible local paths stay explicit until a workflow-specific migration proves parity.

## Minimum API Surface Artifact

| Field | Meaning |
|---|---|
| `provider` | Actual provider used after fallback |
| `model` | Actual model sent to the provider |
| `api_surface` | `openai_responses`, `openai_chat_completions`, `anthropic_messages`, `gemini_generate_content`, `openai_compat_chat`, `ollama_native_chat`, etc. |
| `sdk_package` / `sdk_version` | Package and version when using an SDK |
| `endpoint` | Full route family, not necessarily full secret-bearing URL |
| `base_url` | Provider base URL, redacted if needed |
| `compatibility_mode` | `native`, `openai_sdk_base_url`, `raw_rest_openai_compat`, `local_native`, etc. |
| `request_fields` | Explicit fields sent, including fields intentionally omitted |
| `omitted_fields` | Important fields left to provider default or unsupported |
| `response_shape_version` | Parser contract such as `choices_message_v1`, `gemini_candidates_v1`, `anthropic_content_blocks_v1` |
| `usage_shape` | Where usage tokens are read from, or `not_available` |
| `error_shape` | SDK exception class or REST error body contract |
| `streaming` | `none`, `sse`, SDK stream helper, deferred response, etc. |
| `tools_surface` | `none`, Chat tools, Responses tools, Anthropic tools, Gemini tools, provider server tools |
| `structured_output_surface` | `json_object`, `json_schema`, Gemini MIME/schema, Anthropic structured output/tool use, prompt-only |
| `reasoning_surface` | provider-specific fields such as `reasoning`, `thinking`, `thinking_config`, or `unsupported` |
| `media_surface` | text only, vision input, audio, TTS, image generation, video, file inputs |
| `timeout_retry` | timeout, retry count, fallback path, deferred polling window |
| `adapter_path` | Code path that built the request |
| `parser_path` | Code path that parsed the response |
| `provider_request_id` | Request ID when available and allowed by privacy policy |
| `last_verified` | Date this surface was last verified |
| `fallback_reason` | Why this provider/surface was reached or skipped |

This is metadata, not a requirement to persist private prompts or full raw responses. Link to the privacy boundary on page 27 when request IDs or prompts are sensitive.

## Routing Rules

1. Record `api_surface` whenever an output is cached, evaluated, published, or used as release evidence.
2. Do not send Responses-only fields through a Chat Completions adapter.
3. Do not assume an OpenAI-compatible provider accepts every OpenAI Chat field. Gate fields per provider and model.
4. Treat usage/error/parser shape drift as compatibility failures, not model-quality failures.
5. If moving OpenAI paths to Responses, add per-workflow tests before migration and keep Chat-compatible providers on their existing adapter until proved.
6. For tools, structured outputs, reasoning, and multimodal inputs, use surface-specific wrappers instead of adding a blind pass-through to the common client.
7. For raw REST compatibility paths, preserve the endpoint and parser contract because SDK exception handling is absent.
8. For local Ollama, choose native `/api/chat` when local timing/model evidence matters and `/v1` only when SDK compatibility is the goal.

## Pitfalls

- A provider can share the OpenAI SDK and still reject OpenAI fields.
- Chat Completions and Responses differ in request shape, response shape, state, tools, streaming, and structured-output configuration.
- Anthropic `content` blocks are not OpenAI `choices`.
- Gemini `candidates` and `usageMetadata` are not Chat `choices` and `usage`.
- `response_format={"type":"json_object"}` proves syntax intent, not schema parity or provider support.
- A successful fallback can change the API surface even when the output text looks normal.
- Raw REST callers need their own timeout, error, and parser evidence.

## Implementation Candidates

1. Add a small `api_surface_artifact` helper beside the generation-parameter artifact from page 31.
2. Start with Blind-to-X because it already mixes SDK Chat, raw REST Chat-compatible, Gemini REST, Anthropic Messages, and Ollama OpenAI-compatible local paths.
3. Extend Shorts generation artifacts with `api_surface`, `sdk_package`, `sdk_version`, `base_url`, `request_fields`, `parser_path`, and `response_shape_version`.
4. Add adapter tests that fixture one minimal response shape per surface: Chat `choices`, Responses `output_text` or output items, Gemini `candidates`, Anthropic content blocks, and Ollama native chat.
5. Add a pre-migration checklist for OpenAI Responses adoption so Chat-compatible providers are not broken by newer OpenAI-only request fields.

## 출처

- 공식: OpenAI API Reference, *Responses*: <https://platform.openai.com/docs/api-reference/responses>
- 공식: OpenAI API Reference, *Chat Completions*: <https://platform.openai.com/docs/api-reference/chat>
- 공식: Anthropic Claude API Reference, *Messages*: <https://platform.claude.com/docs/en/api/messages>
- 공식: Google AI for Developers, *Generating content*: <https://ai.google.dev/api/generate-content>
- 공식: DeepSeek API Docs, *Create Chat Completion*: <https://api-docs.deepseek.com/api/create-chat-completion>
- 공식: xAI Docs, *Chat REST API Reference*: <https://docs.x.ai/developers/rest-api-reference/inference/chat>
- 공식: xAI Docs, *Chat Completions*: <https://docs.x.ai/developers/model-capabilities/legacy/chat-completions>
- 공식: Groq Docs, *OpenAI Compatibility*: <https://console.groq.com/docs/openai>
- 공식: Groq Docs, *API Reference*: <https://console.groq.com/docs/api-reference>
- 공식: Ollama Docs, *OpenAI compatibility*: <https://docs.ollama.com/api/openai-compatibility>
- Code evidence: `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/openai_client.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/blind-to-x/pipeline/editorial_reviewer.py`.

*외부 자료 검증일: 2026-06-08 · Code verified against current HEAD.*
