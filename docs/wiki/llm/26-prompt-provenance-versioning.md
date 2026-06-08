# 26 · Prompt Provenance · Versioning · Cache/Eval Contract

> Prompt text is a source artifact. A rendered prompt instance is a runtime artifact. Cached LLM outputs and eval reports must preserve enough prompt metadata to prove what was actually tested or reused.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `workspace/execution/harness_middleware.py`, `projects/blind-to-x`, `projects/shorts-maker-v2`, and `tests/eval/blind-to-x/promptfooconfig.yaml`.

## Why This Is Separate

The existing wiki covers models, structured outputs, evaluation, caching, and media boundaries. Prompt lifecycle still needs its own contract because prompt text changes can silently alter behavior while leaving model names, schemas, cache tables, and eval commands unchanged.

The practical rule is:

1. A **prompt template** is version-controlled text or code that contains variables.
2. A **rendered prompt** is the exact system/user/developer input sent to a model after variables, examples, locale overrides, retrieval context, and retry feedback are inserted.
3. A **prompt artifact** is the metadata that lets reviewers connect a generated output, cache hit, eval score, or production incident to the prompt template and rendered input family that produced it.

Without that split, a stale cache can look like a successful prompt change, and an eval report can look current while it is testing a different prompt path from production.

Prompt provenance is necessary but not sufficient for replay. The generated output also needs the generation-parameter artifact from [31-generation-parameters-reproducibility](31-generation-parameters-reproducibility.md), because temperature, output caps, provider defaults, fallback, and cache hits can change behavior even when the prompt hash is stable.

Prompt provenance also does not prove continuation state. If a rendered prompt included a conversation summary, reviewer memory, provider response ID, SDK session, graph checkpoint, MCP resource, `.ai` handoff, or product record, the state carrier belongs in [38-conversation-state-memory-handoff-boundary](38-conversation-state-memory-handoff-boundary.md).

## Current Code Facts

### 1) Workspace `LLMClient` Hashes Raw Prompt Content Only For Cache

`workspace/execution/llm_client.py` builds the local response cache key from `[providers, system_prompt, user_prompt, round(temperature, 4)]`. That means exact prompt text changes naturally miss the local cache, but the cache table stores only `key`, `content`, and `created_at`. It does not store `prompt_id`, `prompt_version`, model, schema version, parser version, eval suite, or the human-readable prompt source file.

Operational conclusion: the workspace cache is useful for exact-repeat cost control, but it is not a prompt registry or release-evidence artifact by itself.

### 2) Harness Middleware Already Has Prompt Fingerprints

`workspace/execution/harness_middleware.py` stores `system_prompt_hash`, `user_prompt_hash`, `json_mode`, provider, model, tokens, cost, latency, success, and error in `CallRecord`. Its `prompt_fingerprint` combines the short system/user hashes plus JSON mode.

Operational conclusion: the harness has the right primitive for prompt provenance, but the production LLM entrypoints still need a shared manifest before reviewers can rely on prompt identity across workflows.

### 3) Blind-to-X Prompts Are Centralized, But Draft Cache Does Not Include Prompt Source

Blind-to-X keeps most draft prompt policy in `projects/blind-to-x/rules/prompts.yaml`. `DraftPromptsMixin` loads that YAML, merges tone mappings, golden examples, performance examples, reviewer memory, and platform-specific templates into the prompt sent by `TweetDraftGenerator`.

The draft cache is different. `TweetDraftGenerator._make_cache_key()` uses title, category, source, and output formats. `DraftCache` stores `cache_key`, `drafts_json`, `image_prompt`, provider, `created_at`, and `expires_at`.

Operational conclusion: changing `rules/prompts.yaml`, example-selection logic, review memory formatting, or model/provider order can leave old cached drafts available until TTL unless the cache is cleared or the key includes prompt provenance. Do not use a Blind-to-X draft cache hit as evidence that the current prompt template was tested.

### 4) Blind-to-X Promptfoo Eval Is A Separate Prompt Surface

`tests/eval/blind-to-x/promptfooconfig.yaml` points promptfoo at `prompts/draft_v_current.txt` and allows a future `draft_v_next.txt` comparison. It compares configured providers and assertions, but that eval prompt file is not automatically generated from `rules/prompts.yaml`.

Operational conclusion: promptfoo is the right offline regression gate, but each eval result should record the prompt file hash and whether it mirrors the runtime prompt builder. Runtime YAML changes require either a mirrored promptfoo fixture update or a note that the eval does not cover the changed prompt surface.

### 5) Shorts Maker Prompts Are Runtime-Built From Code And Locale Bundles

Shorts Maker builds script prompts in `script_prompts.py` and `script_step.py`. The prompt copy starts from code defaults, can be overridden by `locales/<language>/script_step.yaml`, and is then rendered with channel persona, hook/tone/structure choices, research context, retry feedback, duration constraints, and field-name overrides before calling `LLMRouter.generate_json()`.

Operational conclusion: Shorts Maker needs prompt provenance at the rendered-prompt family level, not only a single static prompt file. A manifest should capture code prompt version, locale bundle path/hash, channel key, structure preset, model/provider, schema/parser version, and duration target.

## External Guidance That Matters Here

- OpenAI's prompt engineering guide says complex applications should pin production model snapshots and build tests/evals that measure prompt behavior when prompts or model versions change.
- OpenAI prompt caching is automatic, but cache hits require exact prompt-prefix matches. Static instructions and examples should be placed before variable request data when optimizing for cache reuse.
- Anthropic's prompt-engineering overview starts with success criteria, empirical tests, and a first draft prompt before iteration. It also frames prompt engineering as transparent because prompts are human-readable.
- Gemini's prompt-design guide says prompt engineering is iterative, recommends clear instructions, examples, response formats, and consistent formatting for few-shot examples.
- Promptfoo supports file-based prompts, prompt labels/IDs, multiple prompt variants, provider-specific prompt selection, and matrix views across prompts/providers. It also exposes CLI failure behavior for eval gates.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Ad-hoc prompt strings plus input-only cache keys | Fast and already works | Prompt changes can be invisible in cache/eval evidence | Keep only for low-risk throwaway calls |
| B. Repo-local prompt provenance manifest | Auditable, cheap, fits current Git workflow | Requires small metadata plumbing per workflow | Adopt as the next operating contract |
| C. External prompt-management platform now | Collaboration, labels, production/staging prompt channels | Adds another control plane before the repo has one prompt manifest | Defer until two workflows need live prompt editing |
| D. Promptfoo-only prompt versioning | Good offline A/B testing | Does not cover runtime YAML/code prompt builders by itself | Use as an eval surface, not the whole registry |

**Decision:** Adopt B and D. Keep prompts in Git for now, but require generated outputs, cache records, eval reports, and release evidence to carry prompt identity when the workflow is user-facing or reused.

## Minimum Prompt Artifact Schema

For any workflow that caches, evaluates, publishes, or bills LLM output, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `prompt_id` | Stable human name, such as `blind_to_x.draft` or `shorts.script_step` |
| `prompt_version` | Semantic or date-based version when the team intentionally changes behavior |
| `prompt_hash` | Hash of the canonical template bundle or rendered prompt family |
| `system_prompt_hash` / `user_prompt_hash` | Hashes of the exact rendered prompt parts when available |
| `template_paths` | YAML/TXT/PY files that produced the prompt |
| `renderer` | Code path/function that rendered the final prompt |
| `provider` / `model` | Actual provider and model snapshot used |
| `schema_id` / `schema_version` | Output contract expected by the parser |
| `parser_version` | Parser or postprocessor version when output parsing is nontrivial |
| `eval_suite_id` / `eval_dataset_hash` | Eval config and dataset used for release evidence |
| `cache_policy` | Local cache TTL, provider prompt-cache setting, or disabled |
| `source_context_hash` | Retrieval/research/examples/reviewer-memory bundle hash when inserted |

The rule is not that every exploratory call needs all fields. The rule is that a reviewer must be able to answer: **which prompt behavior produced this output, and which cache/eval evidence is still valid after this prompt changed?**

## Cache And Eval Rules

1. Local response caches may key on exact rendered prompt text, but user-facing workflows should also store a prompt artifact beside the output.
2. Input-only cache keys are unsafe for prompt iteration. Add prompt hash/version or clear the cache when prompt templates, examples, parser contracts, or provider order change.
3. Provider prompt caching should put stable instructions/examples first and volatile request data later; this optimizes cache reuse without hiding which prompt version was used.
4. Eval results must record prompt file hash, provider/model, temperature, output schema/parser version, dataset hash, and assertion config hash.
5. A promptfoo pass is valid only for the prompt surface it actually renders. If production uses YAML/code prompt builders, either mirror them into promptfoo fixtures or mark the coverage gap.
6. Release notes should call out prompt behavior changes separately from model/provider changes.
7. Prompt hash changes should invalidate or annotate generated media/script/draft artifacts, not just text drafts.
8. Eval-specific evidence should also follow [36-evaluation-dataset-llm-judge-rubric-boundary](36-evaluation-dataset-llm-judge-rubric-boundary.md): dataset hash, deterministic assertion config, LLM judge model, rubric version, baseline hash, and human-review linkage are separate from prompt provenance.

## Implementation Checklist

1. Add a tiny `prompt_artifact` helper before adding a platform-wide prompt-management system.
2. Start with Blind-to-X draft generation because it already has centralized `rules/prompts.yaml`, draft cache, image prompt output, and promptfoo evals.
3. Include `rules/prompts.yaml` hash, `draft_prompts.py` renderer hash or version, provider/model, output formats, and cache key in the Blind-to-X draft artifact.
4. Include `script_prompts.py`, locale bundle hash, channel key, structure preset, duration range, provider/model, and script parser version in Shorts Maker script artifacts.
5. Extend promptfoo release evidence to print prompt file hashes and dataset hashes before comparing baseline vs candidate.
6. Treat prompt provenance as release evidence, not as observability-only metadata. Langfuse traces can help, but Git artifacts must be enough for local review.
7. Keep privacy boundaries from [08-security](08-security.md) and [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md): do not persist full rendered prompts with private source data unless the storage/retention policy allows it. Store hashes plus redacted summaries when needed.

## Pitfalls

- `prompt_version` without a content hash can lie after emergency edits.
- A content hash without a human `prompt_id` is hard to review.
- Promptfoo prompt IDs do not automatically cover runtime code-built prompts.
- A draft cache hit proves only that the cache key matched, not that the current prompt template was executed.
- Model upgrades can invalidate prompt evidence even when prompt text is unchanged.
- Schema/parser changes can invalidate prompt evidence even when model and prompt are unchanged.
- Prompt caching and response caching are different. Provider prompt caching saves prefix processing; local response caching returns an old output.

## 출처 (1차 우선, 2026-06-08 확인)

- Official: OpenAI API Docs, *Prompt engineering*: <https://developers.openai.com/api/docs/guides/prompt-engineering>
- Official: OpenAI API Docs, *Prompt caching*: <https://developers.openai.com/api/docs/guides/prompt-caching>
- Official: Claude API Docs, *Prompt engineering overview*: <https://anthropic.mintlify.app/en/docs/build-with-claude/prompt-engineering/overview>
- Official: Google AI for Developers, *Prompt design strategies*: <https://ai.google.dev/gemini-api/docs/prompting-strategies>
- Primary docs: Promptfoo, *Prompt Configuration*: <https://www.promptfoo.dev/docs/configuration/prompts/>
- Primary docs: Promptfoo, *Intro*: <https://www.promptfoo.dev/docs/intro/>
- Primary docs: Promptfoo, *Assertions and Metrics*: <https://www.promptfoo.dev/docs/configuration/expected-outputs/>
- Primary docs: Promptfoo, *Command Line*: <https://www.promptfoo.dev/docs/usage/command-line/>
- Code evidence: `workspace/execution/llm_client.py`, `workspace/execution/harness_middleware.py`, `projects/blind-to-x/rules/prompts.yaml`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/draft_cache.py`, `projects/blind-to-x/pipeline/draft_prompts.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_prompts.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`, `tests/eval/blind-to-x/promptfooconfig.yaml`.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
