# 30 - Fine-tuning - Custom Model - Local Scorer Boundary

> Fine-tuning, prompt iteration, RAG, provider managed agents, and local ML scoring solve different problems.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `projects/blind-to-x/pipeline/ml_scorer.py`, `projects/blind-to-x/pipeline/content_intelligence/builder.py`, `projects/blind-to-x/config.example.yaml`, and `projects/blind-to-x/config.ci.yaml`.

## Why This Is Separate

The wiki already covers model selection, prompt provenance, RAG, evals, privacy, and error routing. This page decides when the repo should change model weights, when it should avoid that path, and how local predictive models differ from LLM provider customization.

Use these buckets before saying "custom model":

| Bucket | What changes | Repo example | Default stance |
|---|---|---|---|
| Prompt / few-shot examples | Request text and examples | Blind-to-X prompts, Shorts script prompts | First option |
| RAG / grounding | Retrieved context and source artifact | Shorts grounding, Blind-to-X source context | Use for factual/current data |
| Provider fine-tuning | Provider model weights/checkpoint | None in current repo | Do not add until evals and data policy are ready |
| Provider managed agents/skills | Hosted agent config, files, sessions, tools | None in current repo | Treat as orchestration, not fine-tuning |
| Local ML scorer | Local sklearn/joblib predictor | Blind-to-X `MLScorer` | Product ranking signal, not an LLM |

## Current Code Facts

### 1) Workspace LLMClient Has No Fine-tuned Model Surface

`workspace/execution/llm_client.py` routes text/JSON generation through provider model IDs, fallback order, cache, bridge validation, and usage tracking. It does not create provider fine-tuning jobs, upload training files, manage checkpoints, or route to a recorded fine-tuned model ID.

Operational conclusion: adding `ft:*`, `tunedModels/*`, or a custom provider deployment must be treated as a model-selection/config change plus eval release, not as a transparent prompt tweak.

### 2) Blind-to-X Has Local Predictive ML, Not LLM Fine-tuning

`projects/blind-to-x/pipeline/ml_scorer.py` trains a local sklearn model from `draft_analytics` rows:

- below `BTX_ML_MIN_LOGISTIC_ROWS` it returns a heuristic fallback;
- between logistic and full thresholds it uses logistic regression;
- at `BTX_ML_MIN_ROWS` or above it can use gradient boosting;
- the persisted model is `.tmp/ml_scorer.joblib`;
- retraining is triggered by row-growth threshold.

`content_intelligence/builder.py` uses this only to resolve `performance_score`; if the scorer is inactive or unavailable, the workflow falls back to deterministic scoring.

Operational conclusion: local ML improves ranking/selection evidence. It is not a text generator and must not be described as LLM model customization.

### 3) Blind-to-X Config Exposes ML Thresholds Separately From LLM Providers

`config.example.yaml` and `config.ci.yaml` have an `ml` section with `min_training_rows` and `retrain_threshold`. The `llm` section separately controls provider fallback, retries, timeout, cache, and pricing.

Operational conclusion: keep training data, model artifact retention, and evaluation gates separate from provider LLM call settings.

## Provider Official Boundaries

### OpenAI

OpenAI's model optimization docs frame optimization as an eval -> prompt -> optional fine-tune -> eval loop. They also say fine-tuning/evals surfaces are moving into legacy documentation, with transition timelines on deprecations pages.

The current supervised fine-tuning guide states that the fine-tuning platform is being wound down and is not accessible to new users; existing fine-tuned models remain available for inference until their base models are deprecated. The same guide still documents the historical SFT flow: build a dataset, upload JSONL training data, create a job, and evaluate the resulting model ID through Responses or Chat Completions.

Reinforcement fine-tuning remains documented as a grader-driven method for reasoning models and requires training/test datasets plus grader configuration. The graders guide itself says graders are being deprecated as part of the evals/fine-tuning workflows they support.

Repo implication: do not plan new OpenAI fine-tuning as the default improvement path. For this repo, use prompt provenance, promptfoo evals, structured outputs, and product gates first. If an existing organization can still use fine-tuning, require a dated deprecation check, data-sharing/retention decision, holdout eval, and rollback model ID before switching runtime config.

### Gemini

The Gemini API model-tuning guide says that after Gemini 1.5 Flash-001 was deprecated in May 2025, there is no model available for fine-tuning in the Gemini API or AI Studio, while tuning is supported in Gemini Enterprise Agent Platform. The page also says there are no immediate plans to bring fine-tuning support back to the API surface.

The `tunedModels` API reference still documents endpoints such as `tunedModels.create` and `tunedModels/*:generateContent`, but the current guide is the stronger operating signal for API/AI Studio availability.

Repo implication: do not add Gemini API fine-tuning tasks to the local backlog. If Gemini Enterprise Agent Platform becomes relevant, treat it as a separate enterprise deployment experiment with its own credentials, retention rules, and eval suite.

### Claude / Anthropic

The Claude API overview lists direct Messages, Message Batches, Token Counting, and Models as generally available APIs, plus beta Files, Skills, Agents, Sessions, and Environments. It does not list a self-serve fine-tuning API in that overview.

Repo implication: Claude customization in this repo should remain prompt/system/tool/harness configuration unless a current official fine-tuning or custom-model API is explicitly available for the account and has been verified. Managed Agents or Skills are orchestration artifacts, not weight-tuned models.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Fine-tune provider models now | Could reduce prompt length and improve narrow style | Current provider availability/deprecation risk, data governance, no repo eval gate for weight changes | Reject as default |
| B. Improve prompts, schemas, RAG, and evals first | Cheap, reversible, already supported by repo tooling | May not fix stable behavioral failures | Adopt first |
| C. Use local ML scorer for ranking/selection | Deterministic local artifact, no provider data upload | Only predicts product performance; does not generate text | Keep separate |
| D. Enterprise custom model / managed agent | Can fit regulated or high-scale needs | External contract, credentials, retention, deployment drift | Future separate experiment |

**Decision:** adopt B plus C. The repo should treat provider fine-tuning as an exceptional model lifecycle change, not a routine quality-polish step. The current local ML scorer can continue to mature as a ranking signal, while LLM generation quality should first move through prompt provenance, grounding, structured outputs, evals, and product review gates.

## Fine-tuning Readiness Gate

Before any provider fine-tuned/custom model is allowed into runtime config, require all of these:

1. A task-specific eval suite with baseline model results and holdout data, with dataset/judge/rubric evidence following [36-evaluation-dataset-llm-judge-rubric-boundary](36-evaluation-dataset-llm-judge-rubric-boundary.md).
2. A training-data manifest with source, consent/retention classification, redaction status, and leak risk.
3. A prompt/RAG attempt recorded as insufficient, with evidence of the remaining failure mode.
4. A provider availability check dated within the current cycle.
5. A model ID/version manifest, base model deprecation check, and rollback target.
6. A generation-parameter manifest from [31-generation-parameters-reproducibility](31-generation-parameters-reproducibility.md), including sampling/output caps, retry/fallback, cache, and replay settings for baseline and candidate runs.
7. A cost estimate for training and inference, including retry/fallback behavior.
8. A safety/refusal/error taxonomy check so policy failures are not trained away accidentally.
9. A release gate proving the fine-tuned model beats the baseline on representative cases.

## Local ML Scorer Checklist

For Blind-to-X `MLScorer`, keep a different gate:

1. Track row count, target type, schema version, model tier, and training timestamp.
2. Keep `.tmp/ml_scorer.joblib` as regenerable local output, not source.
3. Verify fallback behavior when sklearn/joblib is unavailable or data is insufficient.
4. Watch for label leakage from publish decisions back into draft ranking.
5. Separate `performance_score` from publish readiness; a high predicted performance score is not a fact-check or policy pass.
6. Log `trained_on`, `model_tier`, and `target_type` as ranking evidence, not provider LLM metadata.

## Implementation Checklist

1. Do not add provider fine-tuning code paths to `LLMClient` until the readiness gate above has artifacts.
2. If a fine-tuned model ID is introduced, add it to model-selection docs, config facts, source inventory, and release evidence.
3. Extend promptfoo or another deterministic eval before changing generation model IDs.
4. Keep Blind-to-X `MLScorer` tests focused on local ranking behavior and fallback paths.
5. Tie any training data export to the retention/privacy page before upload.
6. Recheck Gemini/OpenAI availability before each fine-tuning-related change because the official surfaces are volatile.

## Pitfalls

- Fine-tuning is not a substitute for fresh facts or citations.
- Provider fine-tuning can memorize bad examples if reviewer data is noisy.
- A model that copies style better can still fail platform constraints, safety, or fact checks.
- Managed agents, skills, and hosted sessions can look like "custom models" to users, but they are orchestration/configuration surfaces.
- Local ML ranking can bias which posts reach review without changing generation quality.
- Deprecated base models can make a fine-tuned model a future migration liability.

## 출처

- 공식: OpenAI API Docs, *Model optimization*: <https://developers.openai.com/api/docs/guides/model-optimization>
- 공식: OpenAI API Docs, *Supervised fine-tuning*: <https://developers.openai.com/api/docs/guides/supervised-fine-tuning>
- 공식: OpenAI API Docs, *Reinforcement fine-tuning*: <https://developers.openai.com/api/docs/guides/reinforcement-fine-tuning>
- 공식: OpenAI API Docs, *Graders*: <https://developers.openai.com/api/docs/guides/graders>
- 공식: Google AI for Developers, *Fine-tuning with the Gemini API*: <https://ai.google.dev/gemini-api/docs/model-tuning>
- 공식: Google AI for Developers, *Tuning API reference*: <https://ai.google.dev/api/tuning>
- 공식: Claude API Docs, *API overview*: <https://platform.claude.com/docs/en/api/overview>
- Code evidence: `workspace/execution/llm_client.py`, `projects/blind-to-x/pipeline/ml_scorer.py`, `projects/blind-to-x/pipeline/content_intelligence/builder.py`, `projects/blind-to-x/config.example.yaml`, `projects/blind-to-x/config.ci.yaml`.

*외부 자료 검증일: 2026-06-08. Code verified against current HEAD.*
