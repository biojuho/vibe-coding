# 35 - Local Inference - Hardware - Quantization Boundary

> "Local" means the model server, weights, latency, memory, and privacy boundary are owned by this workstation or local network.
> It does not automatically mean free, offline-safe, feature-equivalent, or launch-ready.
> Code facts were checked on 2026-06-08 from `workspace/execution/local_inference.py`, `workspace/execution/llm_client.py`, `workspace/execution/smart_router.py`, `workspace/directives/local_inference.md`, and `projects/blind-to-x/pipeline/draft_providers.py`.

## Why This Is Separate

Ollama appears in the provider list beside cloud APIs, but it is a different kind of dependency. A cloud provider key proves account access. A local provider needs a running server, installed model tag, enough memory, acceptable latency, matching API surface, and fallback behavior when the machine cannot load the requested model.

Use these buckets before calling an output "local inference ready":

| Bucket | What it proves | What it does not prove |
|---|---|---|
| Local server health | `http://localhost:11434` responds | The requested model is installed or loaded |
| Installed model tag | `/api/tags` lists model metadata | The machine can run it within latency and memory budget |
| Running model state | `/api/ps` lists loaded models, VRAM, context | Future calls will stay loaded or fit a larger context |
| Quantization tag | Weights use a lower-precision format such as `Q4_K_M` | Same quality, determinism, or tool behavior as full precision |
| OpenAI-compatible API | Existing OpenAI SDK clients can often connect | Full OpenAI feature parity |
| Zero API price | No per-token cloud bill | No hardware, electricity, time, or maintenance cost |
| Offline/local privacy | Prompt may stay off cloud provider APIs | No local logs, model license issue, or network exposure risk |

## Current Code Facts

### 1) Workspace Core Defaults To A Heavy Ollama Model

`workspace/execution/local_inference.py` sets `DEFAULT_OLLAMA_BASE_URL` to `http://localhost:11434`, `DEFAULT_OLLAMA_MODEL` to `qwen3-coder:30b-a3b-q4_K_M`, and `OLLAMA_TIMEOUT_SEC` to `180`. Its fallback model list starts with that 30B coder model, then tries smaller coder/reasoning models such as `qwen3-coder:8b`, `deepseek-r1:14b`, `deepseek-r1:8b`, `qwen2.5-coder:7b`, and `codellama:7b`.

`OllamaClient.is_available()` checks `GET /api/tags` with a short timeout. `list_models()` reads installed tags from the same endpoint. `find_best_model()` chooses the first configured fallback model that matches installed local tags. `generate()` calls the native `/api/chat` endpoint with `stream=false`, passes `temperature`, optionally passes `format="json"`, and returns `prompt_eval_count` and `eval_count`.

Operational conclusion: server health and model choice are already separable in code. Release evidence should preserve both. `OLLAMA_BASE_URL` alone is not enough.

### 2) `LLMClient` Treats Ollama As First Provider, But Only If Locally Enabled

`workspace/execution/llm_client.py` includes 9 providers and orders them `ollama -> google -> groq -> deepseek -> moonshot -> zhipuai -> openai -> xai -> anthropic`. It maps aliases such as `local` and `qwen` to `ollama`, sets the Ollama default model to `qwen3-coder:30b-a3b-q4_K_M`, and treats Ollama as enabled when `OLLAMA_BASE_URL` is present. When the client is created for Ollama, it imports `OllamaClient` and rejects the provider if `is_available()` fails.

The module docstring still says "7 providers"; the constants and wiki use 9. Ollama pricing entries are zero, which is correct for API billing but incomplete for local operations.

Operational conclusion: `enabled_providers()` should be read as "eligible to try", not "launch ready". For local inference, a runtime artifact needs server, installed model, memory/context, and timeout evidence.

### 3) The Local SOP And Runtime Defaults Drift

`workspace/directives/local_inference.md` says `OLLAMA_DEFAULT_MODEL` defaults to `gemma3:4b`, while `workspace/execution/local_inference.py` and `workspace/execution/llm_client.py` default to the much heavier `qwen3-coder:30b-a3b-q4_K_M`. The directive's fallback chain also says 9 providers in prose but its table omits Groq.

Operational conclusion: use `gemma3:4b` as the documented light workstation candidate, but do not assume the core default is light. This drift is a documentation/config debt, not proof that Ollama is broken.

### 4) Project Routers Use Ollama Differently

`workspace/execution/smart_router.py` routes SIMPLE prompts to `["ollama"]`, MODERATE prompts to `["ollama", "google", "deepseek", "groq"]`, and COMPLEX prompts to `["google", "anthropic", "openai", "ollama"]`.

`projects/blind-to-x/pipeline/draft_providers.py` puts Ollama last by default after Anthropic, Gemini, xAI, and OpenAI. It health-checks `/api/tags`, uses an OpenAI-compatible client pointed at `http://localhost:11434/v1`, defaults the Ollama draft model to `gemma3:4b`, and uses a longer 90-second Ollama timeout.

Operational conclusion: local inference is not one global policy. Workspace core is local-first when available; Blind-to-X is cloud-first with local fallback; SmartRouter changes order by complexity.

### 5) This Workstation Needs A Light Local Profile

The local machine currently reports about 16.9 GB physical RAM and Intel Iris Xe graphics with about 1 GB adapter RAM via `wmic`. Existing page [01-architecture](01-architecture.md) already records that the heavy Ollama default is not a practical first provider on this workstation.

Operational conclusion: launch evidence should either set and verify a light model such as `gemma3:4b`, or explicitly record Ollama as disabled/skipped and rely on cloud fallback. A heavy local default should not silently be treated as the real first provider.

## Provider Official Boundaries

### Ollama Native API

Ollama's API is served by default at `http://localhost:11434/api`. The native chat endpoint is `POST /api/chat`; it requires `model` and `messages`, supports optional `tools`, `format`, `options`, `stream`, `think`, and `keep_alive`, and returns timing/token fields such as `total_duration`, `load_duration`, `prompt_eval_count`, and `eval_count`.

Repo implication: local inference evidence can be richer than many cloud calls because the native response exposes load and eval timings. Preserve these fields when judging latency or model-fit regressions.

### Ollama Model State Endpoints

`GET /api/tags` lists available local models and includes fields such as model name, size, digest, family, parameter size, and quantization level. `GET /api/ps` lists currently running models and can include `size_vram` and `context_length`.

Repo implication: a robust health check should separate "server up", "model installed", and "model loaded with usable context". The current `is_available()` check proves only the first layer.

### Ollama OpenAI Compatibility

Ollama documents OpenAI compatibility for parts of the OpenAI API and shows `base_url='http://localhost:11434/v1/'` with an `api_key` value that is required by the SDK but ignored by Ollama.

Repo implication: OpenAI-compatible wiring is a convenience adapter, not a guarantee that every cloud OpenAI field, tool path, response format, or usage behavior is supported identically. Use the native API when local-specific timing/model metadata matters.

Cross-boundary note: record local `/api/chat` versus `/v1/chat/completions` versus `/v1/responses` using [37-api-surface-sdk-compatibility-boundary](37-api-surface-sdk-compatibility-boundary.md), because local model readiness and API compatibility are separate launch facts.

### Structured Outputs

Ollama supports structured JSON by passing `format: "json"` or a JSON schema to the native chat endpoint. Its structured-output guide recommends validating with Pydantic or Zod and lowering temperature for more deterministic responses. It also says structured outputs work through the OpenAI-compatible API via `response_format`.

Repo implication: local JSON mode can support structured-output workflows, but product code still needs schema parsing, retry/repair, and language validation from [10](10-structured-outputs.md) and [34](34-language-bridge-locale-i18n-boundary.md).

### Model Size And Quantization

The current Ollama library page lists `gemma3:4b` at 3.3 GB with a 128K context window and `qwen3-coder:30b` at 19 GB with a 256K context window. The Gemma page also lists quantization-aware trained variants and describes lower memory footprint compared with non-quantized models. Hugging Face's Transformers quantization overview describes quantization as representing weights with fewer bits to reduce model size and memory usage, while noting that methods have different pros and cons.

Repo implication: do not infer hardware fit from parameter count alone. Store the exact tag, size, quantization level, context, and observed local timing. Treat a quantized model as a distinct runtime candidate from its full-precision or cloud-served variant.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Force Ollama first whenever `OLLAMA_BASE_URL` exists | Zero API bill when it works | Slow failures, wrong heavy model, weak quality evidence | Reject as launch evidence |
| B. Opportunistic Ollama with health/model/memory evidence and cloud fallback | Keeps local option without blocking output quality | Needs local artifact and fallback reason | Adopt |
| C. Local-only for privacy-sensitive tasks | Avoids cloud provider transfer | Can fail quality or latency if local model is weak | Use only with explicit privacy classification |
| D. Cloud-first for launch-critical public output | Stronger managed model quality and availability | Costs money and sends data to provider | Adopt when local evidence is weak |

**Decision:** adopt B as the default operating boundary and D for launch-critical public artifacts unless a local model has current pass evidence. Use C only when data classification requires local-only generation.

## Minimum Local Inference Artifact

For any reusable, cached, published, or release-evidence local LLM output, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `provider` | Usually `ollama` |
| `api_surface` | `native_chat`, `openai_compat_chat`, `openai_compat_responses`, or other |
| `base_url` | Local or network URL used |
| `server_available` | Result of `/api/tags` or equivalent health probe |
| `model_requested` | Config/default model before fallback |
| `model_used` | Actual installed tag accepted for the call |
| `model_installed` | Whether `/api/tags` listed the model |
| `model_loaded` | Whether `/api/ps` showed the model loaded |
| `model_size_bytes` | Installed model size when available |
| `parameter_size` | Model metadata such as `4B`, `8.0B`, `30B` |
| `quantization_level` | Example: `Q4_K_M`, or `unknown` |
| `context_length` | Current loaded context length or documented context |
| `hardware_profile` | CPU/GPU/RAM class used for the run |
| `memory_budget` | Expected and observed RAM/VRAM fit |
| `timeout_sec` | Local call timeout |
| `temperature` / `json_mode` | Generation controls from [31](31-generation-parameters-reproducibility.md) |
| `prompt_eval_count` / `eval_count` | Native token counters when available |
| `load_duration_ms` / `eval_duration_ms` | Local timing evidence |
| `fallback_provider` | Cloud or alternate local provider accepted after local failure |
| `fallback_reason` | `server_down`, `model_missing`, `timeout`, `memory_fit`, `quality_gate`, etc. |
| `privacy_boundary` | `local_only`, `cloud_allowed`, or classified policy |
| `license_source` | Model/library/license page used for the tag |
| `quality_gate` | Eval/bridge/publish gate result |

This artifact complements, rather than replaces, prompt provenance [26](26-prompt-provenance-versioning.md), data-retention [27](27-data-retention-privacy-logging.md), replay [31](31-generation-parameters-reproducibility.md), safety/publish [32](32-safety-moderation-publish-gates.md), and language-bridge [34](34-language-bridge-locale-i18n-boundary.md) evidence.

## Routing Rules

1. Do not count Ollama as launch-ready only because `OLLAMA_BASE_URL` exists.
2. Probe `/api/tags` before first local use and record whether the requested model is installed.
3. Prefer `/api/ps` evidence when investigating memory, loaded context, or first-token latency.
4. On this workstation, prefer `gemma3:4b` or another light installed model unless an external GPU/profile proves the heavy coder model fits.
5. If the requested local model is missing or too heavy, either override to a light model or record Ollama as skipped and let cloud fallback run.
6. Use native `/api/chat` when you need `prompt_eval_count`, `eval_count`, load duration, or quantization metadata; use `/v1` only when SDK compatibility is the main goal.
7. Keep structured-output parsing and language validation separate from local model success. Local JSON mode is not a publish gate by itself.
8. For privacy-sensitive workflows, record whether cloud fallback was allowed before running fallback.
9. Never expose the local Ollama server on an untrusted network without an explicit security decision.

## Pitfalls

- Zero per-token API price can hide slow runs, hardware cost, and blocked queues.
- A running Ollama server can still lack the requested model.
- A model installed on disk can still fail memory or latency requirements.
- `qwen3-coder:30b-a3b-q4_K_M` and `qwen3-coder:30b` should be treated as distinct tags unless `/api/tags` proves the local alias.
- OpenAI-compatible does not mean full OpenAI feature parity.
- Quantization can change quality, latency, and tool behavior; it is not just compression metadata.
- Offline generation still needs retention/logging policy for local prompts, outputs, and caches.
- Local model licenses and model-card terms are part of release evidence when outputs are shipped.

## Implementation Candidates

1. Add a local-inference status artifact helper that records `/api/tags`, optional `/api/ps`, selected model, quantization level, timing, and fallback reason.
2. Align `workspace/directives/local_inference.md` with the actual code default, or change code/config so the documented light default is explicit.
3. Extend `LLMClient.enabled_providers()` or the Ollama provider path to distinguish `server_available` from `model_ready`.
4. Teach Blind-to-X draft evidence to preserve whether Ollama was skipped because the service was down, model missing, timeout, or quality gate failure.
5. Add a small local-only smoke test that runs only when `OLLAMA_BASE_URL` is present and the requested light model is installed; keep it opt-in so CI is not blocked by missing local hardware.

## 출처

- 공식: Ollama Docs, *API introduction*: <https://docs.ollama.com/api/introduction>
- 공식: Ollama Docs, *Generate a chat message*: <https://docs.ollama.com/api/chat>
- 공식: Ollama Docs, *List models*: <https://docs.ollama.com/api/tags>
- 공식: Ollama Docs, *List running models*: <https://docs.ollama.com/api/ps>
- 공식: Ollama Docs, *OpenAI compatibility*: <https://docs.ollama.com/api/openai-compatibility>
- 공식: Ollama Docs, *Structured Outputs*: <https://docs.ollama.com/capabilities/structured-outputs>
- 공식: Ollama Library, *qwen3-coder*: <https://ollama.com/library/qwen3-coder>
- 공식: Ollama Library, *gemma3*: <https://ollama.com/library/gemma3>
- 공식: Hugging Face Transformers Docs, *Quantization*: <https://huggingface.co/docs/transformers/v4.46.0/en/quantization/overview>
- Code evidence: `workspace/execution/local_inference.py`, `workspace/execution/llm_client.py`, `workspace/execution/smart_router.py`, `workspace/directives/local_inference.md`, `projects/blind-to-x/pipeline/draft_providers.py`.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
