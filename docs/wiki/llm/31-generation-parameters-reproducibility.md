# 31 - Generation Parameters - Reproducibility - Replay Boundary

> Model ID and prompt identity are not enough to reproduce an LLM output.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/blind-to-x/config.example.yaml`, and `tests/eval/blind-to-x/promptfooconfig.yaml`.

## Why This Is Separate

The existing wiki covers model selection, prompt provenance, evals, token budgets, rate limits, and error routing. This page covers the smaller but operationally important question: which generation knobs shaped the output, and can a reviewer replay or compare the run without guessing them?

Use these buckets before calling an output "reproducible":

| Bucket | Examples | Repo status |
|---|---|---|
| Sampling controls | `temperature`, `top_p`, `topK`, provider defaults | Partly passed through, not normalized |
| Output caps | `max_tokens`, `maxOutputTokens`, stop sequences, truncation | Hardcoded in several paths |
| Replay hints | `seed`, provider/model snapshot, prompt hashes, dataset hash | Mostly absent outside eval config |
| Orchestration controls | retry count, timeout, provider order, fallback, repair loops | Present in code, not emitted as one artifact |
| Cache controls | local response cache TTL/key, Anthropic prompt cache strategy | Present, but cache rows are not replay manifests |

The operating rule is: generated output evidence must preserve the request shape that matters for generation, not only the prompt text and model name.

## Current Code Facts

### 1) Workspace `LLMClient` Exposes Temperature But Not A Parameter Manifest

`workspace/execution/llm_client.py` passes `temperature` through OpenAI-compatible chat completions, Gemini `GenerateContentConfig`, Anthropic Messages, and Ollama. `generate_json()`, `generate_text()`, and bridged variants default to `temperature=0.7`. Anthropic calls hardcode `max_tokens=2000`; OpenAI-compatible calls do not set an explicit output cap in the shared path; Gemini calls do not set `topP`, `topK`, `seed`, or `maxOutputTokens`.

The local cache key includes `[providers, system_prompt, user_prompt, round(temperature, 4)]`, but cache rows store only `key`, `content`, and `created_at`.

Operational conclusion: exact cache misses include temperature drift, but the cache is not enough to prove which generation parameters, retry settings, output caps, or fallback path produced a user-facing result.

### 2) Blind-to-X Draft Generation Has Hardcoded Provider Parameters

`projects/blind-to-x/pipeline/draft_providers.py` hardcodes Anthropic `max_tokens=1500`, Gemini `generationConfig.temperature=0.7`, and Ollama `temperature=0.7`. OpenAI and xAI draft calls currently omit an explicit temperature/output cap. `TweetDraftGenerator` separately controls provider order, `llm.max_retries_per_provider`, `llm.request_timeout_seconds`, `llm.best_of_n`, draft cache keys, and quality-feedback retry prompts.

Operational conclusion: Blind-to-X has real generation controls, but they are split across code and config. A reviewer cannot reconstruct "candidate A vs candidate B" from the draft text alone.

### 3) Shorts Maker Router Has Runtime Parameters But No Replay Artifact

`projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py` passes `temperature` to OpenAI-compatible providers, Gemini, Anthropic, and bridge repair paths. It also supports Gemini `thinking_level`, defaults generation calls to `temperature=0.7`, hardcodes Anthropic `max_tokens=2000`, and controls provider retries plus request timeout in the router constructor.

Operational conclusion: Shorts scripts need generation-parameter evidence next to prompt provenance because runtime retry feedback, bridge validation, provider fallback, and thinking settings can change the generated script even when the prompt family is unchanged.

### 4) Promptfoo Eval Already Records A Narrow Parameter Contract

`tests/eval/blind-to-x/promptfooconfig.yaml` pins three eval providers with `temperature: 0.4` and `max_tokens: 600`. That is the strongest existing reproducibility example in the repo, but it covers only the promptfoo eval surface, not production draft caches or Shorts generation.

Operational conclusion: promptfoo should remain the example contract, but runtime workflows need a similar sidecar artifact if their outputs are used for publishing, cost review, or release decisions.

## Provider Official Boundaries

### OpenAI

The current Responses API reference exposes sampling controls such as `temperature` and `top_p`, recommends changing one rather than both, and describes `top_logprobs` as optional per-token probability evidence. It also exposes state/tool/text configuration on the response object.

Repo implication: when moving shared code from Chat Completions-style calls toward Responses, do not translate only `model` and `messages`. Record which sampling and text-output parameters were intentionally set, which were omitted to use provider defaults, and whether tool/text/structured-output settings changed the response surface.

### Gemini

Gemini `GenerationConfig` includes `candidateCount`, `maxOutputTokens`, `temperature`, `topP`, `topK`, `seed`, penalties, logprobs, `thinkingConfig`, image/media/speech config, and response-format config. The API reference notes that model defaults vary and that some models do not allow `topK`.

Repo implication: Gemini replay evidence must include both explicit request parameters and "provider default used" when a parameter is omitted. A seed is only useful when the model/version and the rest of the request shape are recorded too.

### Claude / Anthropic

Claude Messages examples show `max_tokens` as part of basic requests. Current Claude docs also warn that `temperature`, `top_p`, and `top_k` are unsupported on Claude Opus 4.7 and later, and setting non-default values returns a 400 error.

Repo implication: do not assume every Claude model accepts the same sampling controls. Provider adapters should omit unsupported sampling fields per model, and replay artifacts should record omission as an intentional compatibility decision rather than a missing value.

### Promptfoo

Promptfoo provider configuration supports model parameter overrides per eval, including common fields such as temperature and token limits.

Repo implication: keep promptfoo configs as explicit eval contracts. When production runtime parameters differ from eval parameters, release evidence should say so instead of treating a promptfoo pass as a full runtime replay.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Keep parameters implicit in provider code | No new plumbing | Reviewers cannot replay drift, defaults can change silently | Reject for user-facing workflows |
| B. Force `temperature=0` everywhere | Simpler comparison | Does not guarantee full determinism and hurts creative drafting | Reject as a blanket rule |
| C. Add a repo-local generation-parameter sidecar | Auditable, cheap, fits existing prompt/source manifests | Needs one helper per workflow | Adopt |
| D. Rely only on provider trace dashboards | Rich when enabled | Optional, external, and not enough for local release review | Use as secondary evidence |

**Decision:** adopt C. Keep creative workflows allowed to use nonzero temperature, but require a sidecar manifest for outputs that are cached, evaluated, published, or used as release evidence.

## Minimum Generation Parameter Artifact

For any reusable or user-facing LLM output, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `provider` / `model` | Actual provider and model snapshot used |
| `api_surface` | Chat Completions, Responses, Gemini GenerateContent, Claude Messages, local Ollama, etc. |
| `sampling` | Explicit `temperature`, `top_p`/`topP`, `top_k`/`topK`, penalties, or `provider_default` markers |
| `output_limits` | `max_tokens`, `maxOutputTokens`, stop sequences, truncation policy, expected output format |
| `replay_hint` | `seed` when supported, plus a clear note when unsupported or omitted |
| `prompt_artifact` | Link/hash from [26-prompt-provenance-versioning](26-prompt-provenance-versioning.md) |
| `schema_artifact` | JSON schema/parser version or free-text output contract |
| `orchestration` | provider order, retry count, timeout, fallback used, repair loop used, best-of-N index |
| `cache_policy` | response-cache key/TTL, provider prompt-cache strategy, cache hit/miss |
| `eval_artifact` | promptfoo/provider config hash, dataset hash, assertion config, judge model |
| `provider_request_id` | Request ID when available, stored only if retention/privacy policy allows |

This is a metadata contract, not a demand to store private prompts or raw provider responses. Use hashes and redacted summaries when privacy boundaries require it.

## Replay Rules

1. Do not compare two generated outputs unless the model, prompt artifact, schema, and generation parameters are all visible.
2. A `temperature=0` run is lower-variance evidence, not a mathematical replay guarantee.
3. `top_p`/`topK` availability is provider/model-specific; missing support should be recorded as `unsupported`, not guessed.
4. Max-token truncation is a product-quality signal. Capture stop reason or truncation status where the provider exposes it.
5. Retry and fallback can produce different providers/models for the same prompt. Record the winning attempt and all skipped providers when possible.
6. Best-of-N workflows must record N, candidate provider/model/parameters, selected index, and selection scorer.
7. Promptfoo passes are valid for the eval provider config they ran, not for production settings that silently differ.
8. Cache hits need the generation-parameter artifact from the original generation, not only the current request.
9. Public-output replay evidence should link to the publish-gate artifact from [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md), so reviewers can see whether safety, platform policy, and human approval matched the generated run.

## Implementation Checklist

1. Add a small `generation_artifact` helper beside the future `prompt_artifact` helper from page 26.
2. Start with Blind-to-X draft generation because it already has promptfoo eval parameters, draft cache, best-of-N, and publish review surfaces.
3. Emit `temperature`, output cap, provider/model, provider order, retry count, timeout, cache hit/miss, best-of-N index, and prompt artifact hash next to each cached draft.
4. Extend Shorts script artifacts with temperature, thinking level, provider order, bridge mode, retry/repair outcome, output parser version, and language/locale evidence from [34-language-bridge-locale-i18n-boundary](34-language-bridge-locale-i18n-boundary.md).
5. For Gemini, distinguish omitted provider defaults from explicit `topP`/`topK`/`seed` values.
6. For Claude, gate sampling fields by model capability and record intentional omission for Opus 4.7+ style models.
7. Extend promptfoo release evidence so it prints provider config hashes and flags runtime/eval parameter mismatches.
8. Keep retention/privacy rules from [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md): do not persist raw provider request IDs or full prompts into shared artifacts without classification.

## Pitfalls

- A model ID plus prompt hash is still incomplete if temperature/output caps changed.
- Provider defaults can change or vary by model; omission is a parameter choice.
- A seed without model/version/request-shape evidence is weak replay evidence.
- Nonzero temperature is not wrong for creative drafts; undocumented temperature is the problem.
- Hardcoded `max_tokens` can hide truncation regressions until output quality drops.
- A fallback success can look like the primary provider passed unless attempt metadata is preserved.
- Eval parameters that differ from runtime parameters can create false release confidence.

## 출처

- 공식: OpenAI API Reference, *Responses object*: <https://platform.openai.com/docs/api-reference/responses/object>
- 공식: Google AI for Developers, *GenerateContent GenerationConfig*: <https://ai.google.dev/api/generate-content#v1beta.GenerationConfig>
- 공식: Google AI for Developers, *Models API model defaults*: <https://ai.google.dev/api/models#v1beta.Model>
- 공식: Claude API Docs, *Using the Messages API*: <https://platform.claude.com/docs/en/build-with-claude/working-with-messages>
- 공식: Claude API Docs, *Handling stop reasons*: <https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons>
- Primary docs: Promptfoo, *LLM Providers*: <https://www.promptfoo.dev/docs/providers/>
- Code evidence: `workspace/execution/llm_client.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/blind-to-x/config.example.yaml`, `tests/eval/blind-to-x/promptfooconfig.yaml`.

*외부 자료 검증일: 2026-06-08. Code verified against current HEAD.*
