# 27 · Data Retention · Privacy · Logging Boundary

> LLM privacy is not only "does the provider train on our data?" The same prompt or output can exist in provider abuse logs, local response caches, JSONL metrics, Langfuse traces, Notion/product databases, media manifests, and reviewer artifacts.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `workspace/execution/llm_metrics.py`, `workspace/execution/harness_middleware.py`, `projects/blind-to-x`, and `projects/shorts-maker-v2`.

## Why This Is Separate

[08-security](08-security.md) covers prompt injection, secrets, PII, and unsafe output handling. [26-prompt-provenance-versioning](26-prompt-provenance-versioning.md) covers prompt identity. This page separates a different operational question:

**Where can prompt/input/output data be stored, for how long, and who controls deletion or sharing?**

For this workspace, that question has four distinct layers:

1. Provider retention and training controls.
2. Local observability and cost metadata.
3. Local/product caches that store generated content.
4. Reviewer/release artifacts that may preserve enough evidence for audits.

Treating all four as "logs" hides the real risk. Token counts are low-risk metadata. Cached drafts, generated scripts, image prompts, audio transcripts, and full rendered prompts can contain private or source-owned content.

Conversation state adds a fifth risk surface. Provider conversation objects, SDK sessions, graph checkpoints, MCP resource snapshots, `.ai` handoff excerpts, and product resume checkpoints can all retain or reintroduce prior context. Use [38-conversation-state-memory-handoff-boundary](38-conversation-state-memory-handoff-boundary.md) to name the state owner before storing or replaying it.

Credentials add a separate capability surface. API keys, OAuth tokens, database URLs, CI secrets, and browser-public client keys should be handled with [39-credentials-secrets-api-key-boundary](39-credentials-secrets-api-key-boundary.md); retention controls do not make a leaked key safe, and key presence does not authorize storing or publishing data.

## Current Code Facts

### 1) Workspace `LLMClient` Stores Response Content In A Local Cache

`workspace/execution/llm_client.py` uses `.tmp/llm_cache.db` for local response caching. The cache key is a SHA-256 hash of `[providers, system_prompt, user_prompt, round(temperature, 4)]`, and the table stores `key`, `content`, and `created_at`. The default `cache_ttl_sec` is 72 hours.

Operational conclusion:

- The table does not store prompt text directly.
- It does store the full model output as `content`.
- Because the key is derived from full prompt text, the key is not a prompt registry and should not be treated as anonymized release evidence.
- Sensitive outputs still need the same deletion/TTL boundary as sensitive inputs.

### 2) Workspace Usage Tables Are Mostly Metadata, But `metadata` Is An Open Field

`workspace/execution/api_usage_tracker.py` table `api_calls` stores provider, model, endpoint, token counts, cost, caller script, bridge status, reason codes, fallback status, language score, provider used, cache creation/read tokens, and timestamp. It does not have prompt or response body columns.

`workspace/execution/llm_metrics.py` writes `.tmp/llm_metrics/llm_calls_YYYY-MM-DD.jsonl` with step, provider, model, token counts, cost, success/error, caller, and `metadata`.

Operational conclusion:

- Current `LLMClient._log_usage()` passes bridge/fallback metadata, not full prompts or responses.
- Future callers must treat `metadata` as a privacy boundary. Do not put full prompts, source posts, private files, or generated drafts there.

### 3) Langfuse Is Opt-In, But Its Retention Is A Separate Control Plane

The workspace Langfuse hook sends provider/model/usage/cost/caller metadata through `start_observation(as_type="generation")` only when `LANGFUSE_ENABLED=1` and keys are present. It does not currently pass prompt or response bodies as `input` or `output`.

Operational conclusion:

- Current workspace trace shape is metadata-first and safer than full prompt tracing.
- If a future integration adds prompt/response content to Langfuse, it must add redaction and retention rules at the same time.
- Langfuse's own retention, deletion, and masking settings are separate from `.tmp` cleanup and provider retention.

### 4) Harness Middleware Keeps Prompt Hashes, Not Prompt Bodies, In Call Records

`workspace/execution/harness_middleware.py` `CallRecord` stores `system_prompt_hash`, `user_prompt_hash`, JSON mode, temperature, provider, model, tokens, cost, latency, success, error, and cache flag. The in-memory `prompt_fingerprint` combines short system/user hashes and JSON mode.

Operational conclusion:

- The harness has the right privacy default for prompt provenance: hashes instead of prompt bodies.
- If harness call logs are ever persisted, keep this hash-only contract unless a task explicitly requires full prompt retention.

### 5) Blind-to-X Draft Cache Stores Generated Text And Image Prompts

`projects/blind-to-x/pipeline/draft_cache.py` persists `drafts_json`, `image_prompt`, provider, creation time, and expiry. The cache key is produced from title, category, source, and output formats in `draft_generator.py`, while the cached value is the generated output.

Operational conclusion:

- This is product data, not just observability metadata.
- Cached drafts and image prompts can contain transformed source content, reviewer-facing copy, and publishable text.
- If source posts are private, confidential, or license-sensitive, the draft cache needs an explicit TTL/deletion decision before reuse or release evidence export.

### 6) Shorts Maker Outputs Are Product Artifacts

Shorts Maker writes scripts, manifests, media, subtitles, retention reports, and cost logs under configured `output`, `logs`, and `runs` paths. Script prompts and review prompts can include research context, narration, visual prompts, retry feedback, and generated scene data.

Operational conclusion:

- Generated scripts, visual prompts, subtitles, and audio/video files are durable product artifacts.
- Do not rely on LLM provider privacy controls to cover local media/output retention.
- If a topic contains user/private source material, the run directory and final media need the same handling decision as the prompt.

## Provider Retention Facts Checked On 2026-06-08

### OpenAI API

OpenAI's data-control docs say API data is not used to train or improve OpenAI models unless the customer opts in. The docs distinguish abuse monitoring logs from application state. Default abuse monitoring can include prompts, responses, and derived metadata for up to 30 days; approved organization/project controls can use Modified Abuse Monitoring or Zero Data Retention, with endpoint-specific limitations and application-state exceptions.

Workspace implication: standard chat/responses/embeddings calls are not the same as Assistants/Threads/Files/Batches/Vector Stores. Before sending private data, record the actual endpoint and whether organization/project data controls are active.

### Anthropic Claude API

Anthropic's API retention docs distinguish standard API retention, Zero Data Retention, HIPAA-ready access, and feature-specific storage. Their privacy article says API inputs and outputs are normally deleted from backend systems within 30 days, with exceptions for longer-retention services, ZDR agreements, usage-policy enforcement, and legal requirements. The API feature table marks standard Messages and token counting as ZDR-eligible, while batch processing, code execution containers, Files API, managed agents, and some connectors have separate retention behavior.

Workspace implication: `cache_strategy="5m"|"1h"` for Anthropic prompt caching is not the same as storing prompts in local `.tmp`. Anthropic's prompt-cache docs in the retention table describe in-memory cache representations and cryptographic hashes for cache TTL; local code still stores generated outputs in `.tmp/llm_cache.db` when local response caching is enabled.

### Gemini API

Gemini's logging docs describe billing-enabled project logs as developer-owned API data that includes the request-to-response process. Logging is opt-in and can be enabled/disabled at project scope. Logs expire after 55 days by default, while datasets can retain selected logs beyond that and may be shared for product improvement/model training if the project owner opts in. The docs warn not to contribute sensitive, confidential, or proprietary information.

Workspace implication: Gemini API calls, AI Studio logs, and datasets are different retention surfaces. Do not share Gemini logs/datasets containing Blind-to-X source posts, private research notes, or unreleased scripts unless that content has been cleared for that use.

### Langfuse

Langfuse data-retention docs say event data such as traces, observations, scores, and media assets are retained indefinitely by default unless project-level retention is configured. The data-masking docs recommend client-side masking before data leaves the application and note that server-side ingestion masking is a centralized safety net for self-hosted deployments.

Workspace implication: "self-hosted" does not automatically mean "short retention" or "redacted." Keep the current metadata-only trace shape unless client-side masking and retention policy are configured.

## Data Classification For This Repo

| Data class | Examples | Default handling |
|---|---|---|
| Provider metadata | provider, model, endpoint, tokens, cost, latency | OK in usage DB/JSONL/Langfuse |
| Prompt identity | prompt hash, prompt id, template path, renderer | OK in release evidence |
| Rendered prompt body | final system/user prompt with source text | Store only when explicitly needed; prefer hash/redacted summary |
| Source material | Blind post, scraped community text, research notes, files/images/audio | Treat as untrusted and possibly private until classified |
| Generated text | X draft, blog draft, script, reviewer rewrite | Product data; cache/export with TTL and owner decision |
| Generated media prompts | image/video/TTS prompts, visual prompts, style prompts | Product data; can reveal source/content strategy |
| Media artifacts | images, audio, video, subtitles, manifests | Product artifacts; local/provider retention both matter |
| Eval datasets | promptfoo cases, Notion review rows, golden/negative sets | Release evidence only after source rights/privacy check |
| Observability traces | Langfuse observations, scores, media assets | Metadata-only by default; retention/masking before bodies |

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Store full prompts/responses everywhere | Easiest debugging | High privacy and retention blast radius | Reject as default |
| B. Metadata plus hashes by default | Low risk, enough for cost/provenance | Debugging may require reproducing prompt from source | Adopt |
| C. Full prompt artifacts for selected release/eval runs | Strongest auditability for important changes | Requires explicit storage and deletion policy | Use only when classified |
| D. Provider ZDR/private mode as the only control | Reduces provider-side retention | Does not cover local caches, Notion, Langfuse, `.tmp`, media outputs | Never rely on it alone |

**Decision:** Adopt B as the default and C only for explicitly classified eval/release evidence. Provider controls are necessary, but local artifact discipline is still required.

## Checklist Before Sending Or Storing Private Data

1. Classify the source as public, user-private, confidential, licensed, or regulated.
2. Record provider, endpoint, model, and data-control state when the input is not clearly public.
3. Keep `api_calls` and JSONL metadata free of full prompts, source text, and generated drafts.
4. Keep Langfuse traces metadata-only unless client-side masking and retention are configured.
5. For local response caches, decide whether 72 hours is acceptable or disable cache for the workflow.
6. For Blind-to-X, treat `drafts_json` and `image_prompt` as product data with TTL/deletion rules.
7. For Shorts Maker, treat run directories, manifests, subtitles, audio, and video as durable artifacts.
8. For evals, store prompt/data hashes plus source provenance; store full examples only when cleared. Citation/source artifacts follow [28-grounding-citation-source-attribution](28-grounding-citation-source-attribution.md) and must still respect this retention boundary.
9. For release evidence, prefer hashes and redacted summaries over full rendered prompts.
10. Recheck provider data-control docs before regulated, contractual, or client-confidential workloads.

## Next Local Improvement Candidate

Add a small `privacy_artifact` or `data_retention_artifact` helper that can be attached to generated outputs and release evidence:

```json
{
  "data_class": "public_source|private_source|confidential|regulated|unknown",
  "provider": "openai|anthropic|gemini|...",
  "endpoint": "chat.completions|messages|generateContent|...",
  "provider_data_control": "default|zdr|modified_abuse_monitoring|gemini_logging_enabled|unknown",
  "local_prompt_storage": "hash_only|redacted|full",
  "local_output_storage": "none|cache_ttl|product_artifact|release_evidence",
  "retention_ttl": "72h|30d|until_deleted|manual",
  "delete_path": ".tmp/llm_cache.db or project output path",
  "source_provenance_hash": "sha256:..."
}
```

Start with Blind-to-X draft cache and Shorts Maker manifests, because both already persist publishable content and media prompts.

## Pitfalls

- Provider "not used for training" does not mean "not stored."
- Provider ZDR does not delete local `.tmp`, Notion rows, Langfuse traces, or generated media.
- Token/cost metadata is lower risk than prompt/output bodies, but an open `metadata` dict can become high risk if callers add raw text.
- A hash is not a deletion substitute. It proves identity; it does not remove cached outputs.
- AI Studio/Workbench/console logs can have different retention from API calls.
- Batch, Files, vector stores, managed agents, datasets, and eval platforms often require application state. Treat them separately from stateless generation.
- Prompt provenance and privacy can conflict. Store enough identity for review, but not more prompt body than the storage policy allows.

## 출처 (1차 우선, 2026-06-08 확인)

- Official: OpenAI API Docs, *Data controls in the OpenAI platform*: <https://developers.openai.com/api/docs/guides/your-data>
- Official: Anthropic Claude API Docs, *API and data retention*: <https://platform.claude.com/docs/en/manage-claude/api-and-data-retention>
- Official: Anthropic Privacy Center, *How long do you store my organization's data?*: <https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data>
- Official: Google AI for Developers, *Gemini API Data Logging and Sharing*: <https://ai.google.dev/gemini-api/docs/logs-policy>
- Primary docs: Langfuse, *Data Retention*: <https://langfuse.com/docs/administration/data-retention>
- Primary docs: Langfuse self-hosting security, *Data Masking*: <https://langfuse.com/self-hosting/security/data-masking>
- Code evidence: `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `workspace/execution/llm_metrics.py`, `workspace/execution/harness_middleware.py`, `projects/blind-to-x/pipeline/draft_cache.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/orchestrator.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
