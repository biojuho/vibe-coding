# 32 - Safety - Moderation - Publish Gate Boundary

> Provider safety filters, LLM-based moderation, and product publish gates are different control layers.
> Code facts were checked on 2026-06-08 from `projects/blind-to-x/config.yaml`, `projects/blind-to-x/pipeline/regulation_checker.py`, `projects/blind-to-x/pipeline/review_queue.py`, `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`, `projects/blind-to-x/pipeline/draft_quality_gate.py`, `projects/blind-to-x/pipeline/quality_gate.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_review.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/fallback_mixin.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/error_types.py`, and `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/qc_step.py`.

## Why This Is Separate

[29-error-taxonomy-refusal-fallback-boundary](29-error-taxonomy-refusal-fallback-boundary.md) already says a provider refusal or content filter is not a transient API error. This page covers the next operational boundary: a safe provider response is not automatically publishable, and a product publish gate is not the same thing as provider moderation.

Use these layers before any generated output reaches a public surface:

| Layer | Question | Typical evidence | Default owner |
|---|---|---|---|
| Provider safety / refusal | Did the model or provider block the prompt or response? | refusal flag, stop reason, Gemini safety feedback, OpenAI moderation category | LLM adapter |
| LLM moderation classifier | Does a separate model classify user/source/generated content as risky? | category, risk level, explanation, model/version, prompt policy | moderation workflow |
| Product quality gate | Is the output platform-valid, source-faithful, non-duplicative, and strong enough? | quality failures/warnings, fact-check warnings, score thresholds | project pipeline |
| Platform policy gate | Does the output follow X/YouTube/channel rules and disclosure duties? | regulation report, AI disclosure requirement, sensitive-media flag, duplicate/spam check | publisher/reviewer |
| Human approval | Has a person accepted the final artifact and remaining risks? | Notion review status, reviewer memo, publish decision | operator |

The operating rule is: a public post or Short needs a publish-gate artifact that links these layers. Do not collapse them into one Boolean called `safe`.

Eval scores belong beside this artifact, not inside the final approval Boolean. [36-evaluation-dataset-llm-judge-rubric-boundary](36-evaluation-dataset-llm-judge-rubric-boundary.md) separates offline promptfoo regression, runtime LLM judge logs, deterministic assertions, product quality scores, and human review status.

## Current Code Facts

### 1) Blind-to-X Defaults To Human Review, Not Auto-Publish

`projects/blind-to-x/config.yaml`, `config.example.yaml`, and `config.ci.yaml` set `content_strategy.require_human_approval: true`. The local `config.yaml` also keeps `publishing.auto_publish: false`. Review config sets `auto_move_to_review_threshold: 60`, `require_twitter_quality_pass: true`, and `min_twitter_quality_score: 80`.

Operational conclusion: Blind-to-X is designed as a review queue. An LLM draft should be treated as a candidate for Notion review, not as a direct publishing instruction.

### 2) Blind-to-X Has Product Gates That Are Not Provider Safety Filters

`regulation_checker.py` loads platform rules from `classification_rules.yaml`, builds platform-specific guidance, and emits `ValidationReport` objects for X, Threads, and Naver Blog. `draft_quality_gate.py` and `quality_gate.py` separately check length, cliches, forbidden expressions, repetition, CTA patterns, hashtags, creator-take quality, semantic similarity, originality, and platform-specific output constraints. `generate_review_stage.py` can fail with `twitter_quality_gate_failed`, but in `review_only` mode it can also continue with partial review evidence.

Operational conclusion: product gates catch many publish risks that provider safety filters do not know about: platform length, duplicate tone, forbidden local phrasing, missing creator take, weak hook, source copying, fact-check warnings, and review readiness.

### 3) Blind-to-X Review Queue Keeps The Human Decision Visible

`review_queue.py` turns ranked items into `검토필요` when content and score thresholds pass, and rejects missing title/content or low final rank with `review_reason`. `persist_stage.py` stores the publish decision and review status into the Notion-facing path.

Operational conclusion: the Notion review status is the final operator gate. A model-generated `publishability_score` is evidence for review, not approval by itself.

### 4) Shorts Maker Separates Topic Unsuitability, Safety Review, Media Policy, And Final Hold

`script_step.py` raises `TopicUnsuitableError` when supporting sources are unreliable or missing. `script_review.py` adds strict channel-specific review keys, including medical `safety_score`. `error_types.py` classifies text like "content policy", "safety", "content_filter", "blocked", and "moderation" as `CONTENT_FILTER`. Media generation catches `content_policy_violation`, attempts a sanitized retry, and can fall back to stock media with `image_policy` / `stock_policy_fallback` evidence. `qc_step.py` uses `HOLD` for final rendered-output issues instead of pretending render-stage defects are provider failures.

Operational conclusion: Shorts Maker already has multiple safety and publish-readiness outcomes. The missing piece is a single reviewer-facing publish-gate artifact that says which layer passed, held, blocked, or needs disclosure.

## Official Boundaries

### OpenAI Moderation

OpenAI's moderation guide describes text and image classification for harmful categories. The API reference treats moderation as a separate endpoint that classifies input, including multimodal inputs.

Repo implication: OpenAI moderation is a classifier result, not a replacement for Blind-to-X's platform regulations or Shorts' final QC. Store category scores/flags as one layer in the publish-gate artifact.

### Gemini Safety Settings

Gemini safety settings are configurable per request across harm categories such as harassment, hate speech, sexually explicit, and dangerous content. The docs note built-in protections that cannot be adjusted, probability-based blocking, per-request safety settings, `promptFeedback.blockReason`, `Candidate.finishReason == SAFETY`, and `safetyRatings`.

Repo implication: Gemini safety feedback should be captured as provider safety evidence. It should not be converted into "empty output" or "quality gate failed."

### Claude Content Moderation

Anthropic's content moderation guide frames moderation as a classification problem and recommends defining examples and unsafe categories before building the prompt. It also notes that Claude can still flag content deemed dangerous regardless of prompt instructions, and recommends clear feedback when user input is blocked or a response is flagged.

Repo implication: if this repo adds Claude-based moderation, it needs its own moderation prompt/version/examples/eval evidence. Do not hide it behind the same draft-generation prompt.

### X Automation And Platform Rules

X automation rules say automated activity is still subject to X Rules and developer policy. They call out spam, duplicative posts/accounts, misleading links, sensitive media, abusive behavior, private information, and the user's responsibility for account actions.

Repo implication: Blind-to-X must keep `auto_publish=false` as the safe default unless a separate policy-review experiment proves exact consent, duplicate/spam controls, sensitive-media handling, and opt-out/approval semantics.

### YouTube Shorts And AI Disclosure

YouTube Community Guidelines apply to all content types, including links, posts, thumbnails, and private/unlisted content. YouTube also requires disclosure for realistic AI-generated or meaningfully AI-altered content and may apply labels or penalties for repeated nondisclosure.

Repo implication: Shorts Maker media manifests should record whether generated audio/image/video requires YouTube AI disclosure. A provider image safety pass is not the same as YouTube upload compliance.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Trust provider safety filters only | Cheap and already partly available | Misses platform rules, duplicate/spam policy, factuality, AI disclosure | Reject |
| B. Trust local product quality gates only | Fits existing Blind-to-X/Shorts code | Misses provider safety/refusal category evidence and moderation model drift | Reject |
| C. Add one publish-gate sidecar linking all layers | Auditable, matches human review, prevents false "safe" claims | Requires workflow-specific adapters | Adopt |
| D. Direct auto-publish on high score | Fastest path | Converts score into approval and increases platform/account risk | Reject |

**Decision:** adopt C. Keep model safety, moderation classification, product quality, platform policy, and human approval as separate fields in one reviewer artifact.

## Minimum Publish-Gate Artifact

For public or reviewer-facing LLM outputs, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `artifact_id` | Stable ID for the draft/script/media output |
| `output_surface` | X post, Threads post, Naver Blog draft, YouTube Short, image prompt, thumbnail, etc. |
| `provider_safety` | provider/model, refusal flag, stop/finish reason, safety categories, moderation endpoint result |
| `moderation_classifier` | optional second-pass classifier model, prompt policy version, risk categories, risk level |
| `product_quality_gate` | deterministic failures/warnings, scores, fact-check warnings, duplicate/similarity signals |
| `platform_policy_gate` | platform-specific limits, sensitive-media flag, AI disclosure requirement, spam/duplicate checks |
| `human_review` | review status, reviewer memo, approval timestamp/user when available |
| `publish_decision` | `queued_for_review`, `ready_to_post`, `hold`, `drop`, `published`, or equivalent |
| `source_evidence` | link/hash from [28-grounding-citation-source-attribution](28-grounding-citation-source-attribution.md) |
| `generation_artifact` | link/hash from [31-generation-parameters-reproducibility](31-generation-parameters-reproducibility.md) |
| `privacy_retention` | retention class from [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md) |

This is metadata. Do not store raw unsafe content, private source content, or full reviewer prompts unless the retention policy explicitly allows it.

## Routing Rules

1. Provider refusal or safety block routes to safety review, not provider fallback by default.
2. LLM moderation is a classifier with its own eval set; it is not proof that the platform will allow the final post.
3. Product quality failures route to rewrite, rerank, or reviewer hold; do not label them as provider failures.
4. Platform-policy failures route to hold/drop until the platform-specific rule is fixed.
5. Human approval is required when `require_human_approval=true`, even if every automated score passes.
6. Auto-publish requires a separate release decision that names the surface, consent model, duplicate/spam controls, policy checks, rollback path, and monitoring.
7. Media outputs require MIME-aware safety and disclosure metadata; text-only moderation is not enough for generated images/video/audio.
8. Publish-gate artifacts should link prompt/source/generation evidence, but store hashes or redacted summaries when privacy rules require it.

## Implementation Checklist

1. Define a small `publish_gate_artifact` schema for Blind-to-X reviewer output.
2. Start with Blind-to-X because it already has Notion review status, `require_human_approval`, quality gates, regulation reports, fact checks, and publish decisions.
3. Map `ValidationReport`, `QualityResult`, fact-check warnings, `review_reason`, `publish_decision`, and X publish status into one reviewer-facing artifact.
4. Add optional provider moderation/safety fields without changing the current default to auto-publish.
5. Extend Shorts manifests with provider safety, script-review safety score, image-policy fallback, final `HOLD`, and YouTube AI-disclosure requirement.
6. Add tests proving a provider safety pass cannot bypass product quality failure or human approval.
7. Add tests proving product quality failure does not get reported as provider outage.
8. Add one release-audit check that refuses "ready to publish" when publish-gate evidence is missing for a public output.

## Pitfalls

- A low-risk moderation result is not a factuality check.
- A fact-check pass is not a platform policy pass.
- A high publishability score is not human approval.
- Provider image policy fallback can produce acceptable media but still require YouTube AI disclosure.
- Auto-posting near-duplicate drafts can violate platform automation rules even when each individual draft looks safe.
- Raw unsafe content in logs can create a second privacy/security incident.
- A reviewer needs to see why something is held; "blocked by AI" is not enough.
- Provider computer-use safety checks are not publish approval and not browser release evidence; keep the browser QA boundary separate ([33-computer-use-browser-qa-boundary](33-computer-use-browser-qa-boundary.md)).

## 출처

- 공식: OpenAI API Docs, *Moderation*: <https://platform.openai.com/docs/guides/moderation>
- 공식: OpenAI API Reference, *Moderations*: <https://platform.openai.com/docs/api-reference/moderations>
- 공식: Google AI for Developers, *Gemini API safety settings*: <https://ai.google.dev/gemini-api/docs/safety-settings>
- 공식: Claude API Docs, *Content moderation*: <https://platform.claude.com/docs/en/about-claude/use-case-guides/content-moderation>
- 공식: X Help, *Automation rules*: <https://help.x.com/en/rules-and-policies/x-automation>
- 공식: YouTube Help, *Disclosing use of GenAI content*: <https://support.google.com/youtube/answer/14328491?hl=en>
- 공식: YouTube Help, *YouTube's Community Guidelines*: <https://support.google.com/youtube/answer/9288567?hl=en>
- Code evidence: `projects/blind-to-x/config.yaml`, `projects/blind-to-x/pipeline/regulation_checker.py`, `projects/blind-to-x/pipeline/review_queue.py`, `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`, `projects/blind-to-x/pipeline/draft_quality_gate.py`, `projects/blind-to-x/pipeline/quality_gate.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_review.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/media/fallback_mixin.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/error_types.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/qc_step.py`.

*외부 자료 검증일: 2026-06-08. Code verified against current HEAD.*
