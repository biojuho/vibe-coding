# 34 - Language Bridge - Locale - I18n Boundary

> Multilingual model capability, BCP-47 locale tags, app copy localization, Korean output validation, and TTS voice locale are related but not interchangeable.
> Code facts were checked on 2026-06-08 from `workspace/execution/language_bridge.py`, `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `workspace/directives/deepseek_ko_bridge.md`, and `projects/shorts-maker-v2`.

## Why This Is Separate

A prompt that says "answer in Korean" is not a release gate. A `ko-KR` locale tag is not proof that the generated text is Korean. Unicode normalization can make equivalent strings comparable, but it does not translate text or guarantee copy quality. TTS voice support is also separate from text generation: a voice can support a locale while the script itself still fails Korean quality rules.

Use these buckets before claiming an LLM output is language-safe:

| Bucket | What it proves | What it does not prove |
|---|---|---|
| Provider multilingual capability | The model can likely process or produce many languages | The specific response passed product language rules |
| System prompt / structured output | The request shape asked for Korean or JSON | The model obeyed it under retries, fallback, or repair |
| Unicode NFC normalization | Equivalent Unicode strings can be compared more reliably | The text is grammatically Korean or publish-ready |
| BCP-47 locale tag such as `ko-KR` | The intended language/region identifier | The output actually matches that locale |
| Locale bundle / i18n copy | Product UI/prompt labels can vary by locale | Generated model text is valid Korean |
| Language bridge validation | Runtime text/JSON passed deterministic language checks | Human tone, legal, safety, and platform approval |
| TTS locale / voice | Audio voice capability and accent choice | The source script is correct for that language |

## Current Code Facts

### 1) Workspace Language Bridge Is A Deterministic Korean Guard

`workspace/execution/language_bridge.py` is deterministic policy code, not a provider client. Its default `BridgePolicy` targets `ko-KR`, runs in `shadow` mode, uses one repair attempt, and prefers fallback providers `deepseek`, `google`, and `openai`. It has strict Korean checks with a minimum Hangul ratio of `0.75`, maximum CJK ratio of `0.02`, maximum decomposed jamo ratio of `0.05`, JSON schema enforcement, and JSON key exemptions for metadata-like fields.

The bridge normalizes prompt and output text to NFC, prepends Korean quality rules through `build_bridge_system_prompt()`, validates text through `validate_text_content()`, validates JSON string fields through `validate_json_payload()`, and emits reason codes such as `empty_content`, `mojibake`, `low_hangul_ratio`, `mixed_language`, `decomposed_jamo`, and `json_parse_error`.

Operational conclusion: the bridge is the runtime evidence layer for Korean text/JSON quality. It should be used for automated Korean output paths rather than relying on provider instructions alone.

### 2) Workspace `LLMClient` Wires Shadow, Enforce, Repair, And Fallback

`workspace/execution/llm_client.py` exposes `generate_text_bridged()` and `generate_json_bridged()`. When `mode=="off"`, those methods delegate to the plain text/JSON path. In `shadow`, validation failures are logged while the original output can pass through. In `enforce`, a failed bridge result triggers repair and then provider fallback according to the bridge provider order.

Usage logging records bridge metadata into `api_usage_tracker`: `bridge_mode`, `reason_codes`, `repair_count`, `fallback_used`, `language_score`, and `provider_used`. `workspace/execution/api_usage_tracker.py` also has bridge-specific aggregation helpers for daily activity, reason breakdown, and provider breakdown.

Operational conclusion: a user-facing artifact can say "Korean bridge passed" only when bridge metadata is preserved beside the output. A plain successful LLM call is not enough.

### 3) Shorts Maker Has Locale Bundles, But They Are Product I18n

`projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_prompts.py` loads locale bundles from `locales/<language_code>/script_step.yaml`, merges localized tone presets, personas, CTA words, field names, review criteria, and prompt/review copy, and applies extra Korean hook rules when the configured language starts with `ko`.

Shorts Maker also has tests for `ko-KR` and `en-US` locale bundle loading, malformed locale entry handling, prompt/persona/review overrides, and TTS/i18n smoke coverage.

Operational conclusion: locale bundles are necessary for product copy and prompt scaffolding, but they do not replace bridge validation. They decide what the app asks for and how UI/review text is localized; the bridge decides whether the generated text looks valid enough to accept automatically.

### 4) TTS Locale Is A Media Compatibility Boundary

Shorts Maker uses separate media providers for narration and rendering. Edge TTS voice aliases, OpenAI voices, Azure-style voice locale support, script language, caption fonts, and narration timing need their own evidence. A Korean script can fail if the selected voice is not available, and an available Korean voice does not prove the script passed Korean text checks.

Operational conclusion: TTS artifacts should record both `tts_locale` or voice locale and the language-bridge result for the source script. See [25-multimodal-audio-media-boundary](25-multimodal-audio-media-boundary.md) for the broader media boundary.

## Provider And Standard Boundaries

### Unicode NFC

Unicode UAX #15 defines normalization forms for Unicode text and explains that NFC uses canonical decomposition followed by canonical composition. The repo uses NFC because Hangul can appear as precomposed syllables or decomposed jamo. NFC makes deterministic comparison and jamo checks more reliable, but it is not a translation or quality system.

Repo implication: normalize prompts and outputs before hashing, validating, caching, and comparing language evidence. Do not treat normalization as a language pass.

### BCP-47 / RFC 5646

RFC 5646 describes language tags as subtags separated by hyphens, such as language plus region. The tag `ko-KR` is therefore an identifier for intended Korean as used in Korea. It should be stored as metadata and used to load locale bundles or select voices, but it is not a classifier result.

Repo implication: store locale tags explicitly, but validate output content separately. If a workflow handles mixed-language content, record individual element tags instead of collapsing everything to `mul` or `und`.

### Provider System Instructions And Structured Output

OpenAI Structured Outputs constrain JSON to a schema, Gemini supports system instructions through `GenerateContentConfig`, and Claude prompting guidance recommends clear structure and system roles. These are request-shaping tools. They improve compliance, but runtime code still has to detect refusals, malformed JSON, wrong-language output, and fallback drift.

Repo implication: structured output can prove schema shape only when the provider guarantees it and the response is parsed. It cannot prove that every string field is Korean. Keep JSON schema validation and language validation as separate gates.

### Speech Locale And Voice Support

Azure Speech language support docs list supported locales per feature and explicitly separate speech-to-text, text-to-speech, pronunciation assessment, speech translation, and other capabilities. Text-to-speech support varies by locale, voice, endpoint, and region.

Repo implication: TTS locale evidence belongs in the media artifact. It must not be reused as proof of LLM language quality.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Prompt-only Korean instruction | Cheap and simple | Wrong-language output can pass silently | Reject for automated publishing |
| B. Bridge validation plus repair and fallback | Deterministic, observable, works with current code | Needs metadata and thresholds | Adopt |
| C. Locale bundles only | Good product i18n and prompt copy | Does not validate generated text | Use as product-layer input |
| D. Human review only | Best tone judgment | Too late for runtime guardrails | Use as final publish gate |

**Decision:** adopt B with C and D around it. Locale bundles shape the request. The language bridge validates and repairs the generated text. Human review remains the publish gate for public output.

## Minimum Language Artifact

For any reusable, automated, or user-facing multilingual LLM output, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `target_language` | Intended generated language, normally `ko-KR` for the bridge |
| `input_locale` / `output_locale` | Locale tags for source and final content |
| `normalization_form` | Usually `NFC` |
| `bridge_mode` | `off`, `shadow`, or `enforce` |
| `policy_version` | Bridge threshold/config version or code commit |
| `provider_order` / `provider_used` | Attempted providers and accepted provider |
| `reason_codes` | Deterministic bridge failure/pass reasons |
| `language_score` | Bridge language score, with threshold context |
| `repair_count` | Number of repair attempts used |
| `fallback_used` | Whether a fallback provider produced the accepted output |
| `json_schema_status` | Separate schema validation status for JSON outputs |
| `locale_bundle` | Product i18n bundle used, such as `ko-KR/script_step.yaml` |
| `tts_locale` / `voice` | Audio locale and voice when narration is produced |
| `prompt_artifact` | Prompt provenance from [26](26-prompt-provenance-versioning.md) |
| `generation_artifact` | Sampling/retry/cache evidence from [31](31-generation-parameters-reproducibility.md) |
| `review_status` | Human or platform publish-gate state from [32](32-safety-moderation-publish-gates.md) |
| `retention_class` | Privacy/logging class from [27](27-data-retention-privacy-logging.md) |

## Routing Rules

1. Use plain `generate_text()` or `generate_json()` only when wrong-language output is acceptable or separately reviewed.
2. Use `*_bridged()` for Korean automated output, especially public drafts, Shorts scripts, and JSON fields that later become Korean copy.
3. Keep `shadow` while measuring reason-code noise; move to `enforce` only for paths where repair/fallback behavior is acceptable.
4. Do not loosen Hangul/CJK/jamo thresholds to hide failures. Add allowed terms for brand names and proper nouns instead.
5. Validate JSON shape and language content separately. A schema-valid JSON object can still contain English or mojibake values.
6. Normalize before hashing and validation so prompt provenance, cache keys, and bridge checks are comparable.
7. Record locale bundle and bridge metadata together when an output is published or cached.
8. For TTS, verify source script language, selected voice locale, audio duration, and caption sync as separate checks.

## Pitfalls

- `ko-KR` in config is intent, not evidence.
- Provider multilingual support is capability, not a pass/fail gate.
- Structured Outputs can guarantee JSON shape without guaranteeing Korean string quality.
- NFC can fix representation differences but cannot fix translation, tone, or policy errors.
- A bridge `shadow` warning means the output should not be silently counted as enforce-quality evidence.
- Locale bundles can drift from runtime model output if prompt copy changes without bridge thresholds and tests.
- TTS voice locale and generated script language can diverge.
- Mixed-language proper nouns should be allowed explicitly rather than weakening the whole policy.

## 출처

- 공식: Unicode Consortium, *Unicode Standard Annex #15: Unicode Normalization Forms*: <https://www.unicode.org/reports/tr15/>
- 공식: RFC Editor, *RFC 5646 - Tags for Identifying Languages*: <https://www.rfc-editor.org/rfc/rfc5646>
- 공식: OpenAI API Docs, *Structured model outputs*: <https://developers.openai.com/api/docs/guides/structured-outputs>
- 공식: Google AI for Developers, *Text generation / system instructions*: <https://ai.google.dev/gemini-api/docs/text-generation>
- 공식: Claude API Docs, *Prompting best practices*: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>
- 공식: Microsoft Learn, *Language and voice support for Azure Speech*: <https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support>
- Code evidence: `workspace/execution/language_bridge.py`, `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `workspace/directives/deepseek_ko_bridge.md`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_prompts.py`, `projects/shorts-maker-v2/tests`.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
