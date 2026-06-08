# 36 - Evaluation Dataset - LLM Judge - Rubric Boundary

> An eval score is evidence, not approval.
> Code facts were checked on 2026-06-08 from `execution/run_eval_blind_to_x.py`, `execution/blind_to_x_eval_extract.py`, `tests/eval/blind-to-x/promptfooconfig.yaml`, `workspace/execution/harness_eval.py`, `workspace/execution/code_evaluator.py`, `workspace/execution/confidence_verifier.py`, and Blind-to-X quality/review gates.

## Why This Is Separate

[05-eval](05-eval.md) explains how the current promptfoo regression suite runs. This page defines the evidence boundary around that suite: where the dataset came from, what the judge actually graded, which rules were deterministic, when a human decision is still required, and when a score can be promoted into release evidence.

Use these buckets before treating an eval as a gate:

| Bucket | What it proves | What it does not prove |
|---|---|---|
| Eval dataset | The cases reflect a labeled sample | The sample is current, leak-free, representative, or complete |
| Deterministic assertion | A rule such as length or banned text passed | Tone, factuality, or usefulness |
| LLM rubric | A judge model scored output against criteria | Objective truth, policy approval, or stable scoring across judge-model drift |
| Baseline comparison | Candidate changed relative to prior run | Candidate is good enough in absolute terms |
| Runtime generator-evaluator | A generation loop tried to repair against criteria | Offline regression coverage or publish approval |
| Product quality score | Pipeline-specific quality heuristics passed | Eval-suite pass or human approval |
| Human review | An operator accepted or rejected the artifact | That the eval/rubric is calibrated for future cases |

The operating rule is: **offline eval, runtime judge, deterministic gate, product quality score, and human review stay separate fields in evidence.**

## Current Code Facts

### 1) Blind-to-X Promptfoo Is Offline Regression, Not A Publish Gate

`execution/run_eval_blind_to_x.py` validates `tests/eval/blind-to-x/promptfooconfig.yaml`, checks that `npx` exists, requires `golden_cases.yaml`, requires `rejected_cases.yaml` outside quick mode, runs `npx promptfoo eval`, writes `.tmp/eval/blind-to-x/last_run.json`, summarizes pass rate and average rubric score, and compares the summary with `.tmp/eval/blind-to-x/baseline.json`.

The regression threshold is `REGRESSION_THRESHOLD = -0.10`. This catches a large score drop relative to baseline. It does not prove that a draft is safe to publish, X-ready, source-grounded, or approved by a reviewer.

### 2) The Dataset Is Generated From Notion And Is Intentionally Gitignored

`execution/blind_to_x_eval_extract.py` turns Notion pages into promptfoo cases. `EvalCase` stores `page_id`, `source_text`, `accepted_draft`, `rejected_draft`, `reviewer_memo`, and `status`. Approved pages become the golden set. Rejected pages become the rejected set only when they have reviewer memo text.

The promptfoo config imports `golden_cases.yaml` and `rejected_cases.yaml`, but page [05](05-eval.md) records that those generated files are `.gitignore` artifacts. A clone can therefore have a valid eval config but no live dataset. `--dry-run` evidence is useful only as a dataset/env preflight, not as a quality result.

### 3) The Current Promptfoo Config Mixes Rule Checks And LLM Rubric

`tests/eval/blind-to-x/promptfooconfig.yaml` evaluates `prompts/draft_v_current.txt` against three providers:

| Provider label | Configured model | Parameters |
|---|---|---|
| `anthropic-haiku` | `anthropic:messages:claude-haiku-4-5-20251001` | `temperature: 0.4`, `max_tokens: 600` |
| `openai-mini` | `openai:chat:gpt-4o-mini` | `temperature: 0.4`, `max_tokens: 600` |
| `deepseek-chat` | `deepseek:deepseek-chat` | `temperature: 0.4`, `max_tokens: 600` |

The deterministic assertions check output length and banned phrases. The `llm-rubric` assertion has `threshold: 0.7` and asks whether the output preserves source intent, is natural Korean, stays short, and avoids CTA. That split matters: a length pass is hard evidence; a judge score is model-mediated evidence.

Operational conclusion: promptfoo results should preserve assertion type, threshold, judge provider/model, judge prompt/rubric version, and deterministic assertion failures separately.

### 4) Promptfoo And Runtime Prompt Surfaces Are Not Automatically The Same

The eval prompt file is `tests/eval/blind-to-x/prompts/draft_v_current.txt`. Blind-to-X runtime prompt behavior mostly lives in `projects/blind-to-x/rules/prompts.yaml` and `DraftPromptsMixin`, with examples, reviewer memory, tone mappings, and platform formatting inserted at runtime.

Operational conclusion: a promptfoo pass is valid for the prompt file it rendered. If runtime prompt YAML or renderer code changes, release evidence must either sync the promptfoo fixture or state the coverage gap. Page [26](26-prompt-provenance-versioning.md) owns prompt identity; this page owns the eval evidence contract.

### 5) `harness_eval.py` Is A Runtime Generator-Evaluator, But Dormant

`workspace/execution/harness_eval.py` implements a generator-evaluator loop. It asks an evaluator LLM to return JSON with `passed`, `score`, `criteria_results`, and `feedback`, then repairs and retries up to `max_rounds`. It uses low evaluator temperature and treats evaluator failures as failed evaluations.

Page [09](09-agent-harness.md) records the important status: the harness modules are implemented and tested, but production LLM paths are not wired to this evaluator. Do not treat `harness_eval.py` as current Blind-to-X promptfoo coverage, and do not treat promptfoo as runtime repair.

### 6) Product Scoring And Self-Confidence Are Not Eval Approval

Blind-to-X config and pipeline code use thresholds such as `review.min_twitter_quality_score`, `feed_filter.min_editorial_score`, `final_rank_score`, `publish_decision.quality_score`, and `content_strategy.require_human_approval`. Those are product gates and reviewer routing signals.

`workspace/execution/code_evaluator.py` and `workspace/execution/confidence_verifier.py` are separate LLM-mediated evaluators. `CodeEvaluator` returns structured score fields for generated code. `ConfidenceVerifier` asks an LLM to self-score and sometimes self-critique. These can be useful diagnostics, but they are not the promptfoo regression baseline, not deterministic tests, and not human approval.

## Official Boundaries

### Promptfoo Model-Graded Assertions

Promptfoo documents `llm-rubric` as a general-purpose LLM-as-judge assertion. It returns a JSON-like result with a reason, score in the 0.0-1.0 range, and pass boolean. The docs also warn that without a threshold, score alone may not drive pass/fail; with a threshold, both the pass field and score threshold must pass.

Repo implication: every LLM-rubric gate should pin threshold semantics, judge provider/model, grader parameters, and rubric prompt shape. A low-score pass caused by missing threshold is an eval bug, not a product signal.

### OpenAI Evals And Graders

OpenAI Evals define data source schemas and testing criteria that compare generated samples against item fields, such as human-provided ground truth labels. OpenAI's grader docs describe graders that return 0-1 scores against reference answers, with grader types such as string check, text similarity, score model grader, and Python code execution. The current docs also say graders are being deprecated in the workflows they support, so their status must be rechecked before building new long-lived infra around them.

Repo implication: use OpenAI docs here as a contract pattern: dataset schema, sample namespace, item namespace, and grader type must be explicit. Do not copy legacy grader-specific mechanics without rechecking current deprecation timelines.

### Claude Evaluation Guidance

Claude's evaluation guidance starts with success criteria, then eval design. It recommends task-specific evals, edge cases, automation when possible, and choosing the fastest reliable grading method. It distinguishes code-based grading, human grading, and LLM-based grading, and recommends clear rubrics for LLM-based grading. The Claude Console eval tool also supports prompt variables, manual/imported/generated test cases, side-by-side comparisons, quality grading, and rerunning a suite after prompt changes.

Repo implication: prefer deterministic code assertions first, then LLM rubrics for judgments that need nuance, then human review when the decision carries product/account risk or the rubric is not yet calibrated.

### Gemini Enterprise Agent Platform Evaluation

Google's Gemini Enterprise Agent Platform docs describe `EvalTask` for repeated evaluation of models and prompt templates against a fixed dataset with specific metrics. It supports model-based metrics such as pointwise and pairwise metrics, computation-based metrics, and experiment tracking.

Repo implication: the key reusable idea is stable dataset plus explicit metrics plus tracked configuration. That maps to promptfoo config hashes, dataset hashes, baseline artifacts, and generation-parameter artifacts in this repo.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Trust LLM judge scores directly | Flexible and cheap to add | Judge drift, bias, missing threshold, weak calibration | Reject as sole gate |
| B. Deterministic assertions + LLM rubric + baseline + human review | Separates evidence layers and matches current workflows | More metadata to preserve | Adopt |
| C. Runtime generator-evaluator for every output | Can repair high-value outputs | Extra cost/latency and currently dormant | Use selectively after wiring |
| D. Offline promptfoo only | Good regression signal | Does not cover runtime prompt drift or publish policy | Use for regression only |

**Decision:** adopt B. Keep C as a future targeted option for high-value, criteria-clear generation once the harness wiring is fixed. Keep D as the current Blind-to-X offline regression mechanism, but do not call it publish approval.

## Minimum Evaluation Artifact

For any eval result used in release evidence, baseline updates, model/provider selection, or public-output review, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `eval_id` | Stable suite name, such as `blind_to_x.draft.promptfoo` |
| `eval_scope` | Offline regression, runtime generator-evaluator, code evaluator, self-confidence check, etc. |
| `dataset_id` / `dataset_hash` | Stable dataset identity and content hash |
| `dataset_source` | Notion query, fixture file, manually curated holdout, synthetic cases, etc. |
| `dataset_generated_at` | Timestamp/date of extraction or fixture build |
| `case_count` / `golden_count` / `rejected_count` | Dataset size by class |
| `split` | Golden/rejected/holdout/adversarial/source-grounded split |
| `prompt_artifact` | Link/hash from [26-prompt-provenance-versioning](26-prompt-provenance-versioning.md) |
| `runtime_prompt_sync_status` | `mirrors_runtime`, `fixture_only`, `known_gap`, or similar |
| `generation_artifact` | Link/hash from [31-generation-parameters-reproducibility](31-generation-parameters-reproducibility.md) |
| `providers` | Candidate providers/models and parameters under test |
| `judge_provider` / `judge_model` | Actual LLM-as-judge model, when separate |
| `judge_prompt_version` / `rubric_version` | Rubric and judge prompt identity |
| `deterministic_assertions` | Length, banned text, schema, exact match, code checks |
| `llm_rubric_threshold` | Numeric threshold and pass/score semantics |
| `baseline_path` / `baseline_hash` | Baseline used for comparison |
| `avg_score` / `pass_rate` / `regression_delta` | Summary metrics |
| `decision` | `pass`, `regression`, `needs_review`, `blocked_missing_dataset`, etc. |
| `human_review_status` | Notion/reviewer status when publishable artifacts are involved |
| `publish_gate_link` | Link/hash from [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md) |
| `known_biases` | Judge-model bias, stale source distribution, thin rejected set, etc. |
| `cost_budget` | Eval budget cap or observed spend when available |
| `tool_versions` | `promptfoo`/`npx`/SDK versions when available |

This artifact should store hashes and metadata by default. Store raw prompts, raw source text, or reviewer notes only when the retention policy from [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md) allows it.

## Routing Rules

1. Run `py -3.13 execution/run_eval_blind_to_x.py --dry-run` before paid or long evals when dataset freshness is uncertain.
2. Treat missing `golden_cases.yaml` as `blocked_missing_dataset`, not as a passing eval.
3. Treat quick mode without a rejected set as limited evidence; it can catch smoke failures but cannot validate rejection behavior.
4. Do not update `baseline.json` just because a run passed. Require a reviewer reason naming the prompt/model/dataset change.
5. If prompt file, runtime prompt YAML, renderer code, provider/model, generation parameters, judge prompt, or dataset changes, store the hashes before comparing baseline vs candidate.
6. Use deterministic assertions for format, length, banned strings, schema, and exact matches before using LLM rubrics.
7. Do not use the same model as generator and judge when an independent judge is practical; when unavoidable, mark the bias.
8. Rotate or revalidate judge models before relying on old rubric scores. Model deprecation and provider defaults are eval-drift risks.
9. Public output still needs the publish gate from [32](32-safety-moderation-publish-gates.md) even when eval pass rate is high.
10. Runtime generator-evaluator logs should be retained as generation evidence, not merged into the promptfoo baseline unless converted into a stable eval case.

## Pitfalls

- Accepted drafts can leak target style into prompts if fixtures are copied into runtime examples without a provenance record.
- A gitignored dataset can become stale while the eval config still looks current.
- `llm-rubric` without correct threshold/pass semantics can produce false passes.
- Judge-model changes can move scores even when candidate output is unchanged.
- A product `quality_score` can look like an eval score but answer a different question.
- A baseline update can hide regression when the candidate is simply blessed without review.
- Runtime prompt drift can leave promptfoo testing an old prompt file.
- Human approval can be missing even when every automated score is green.

## Implementation Candidates

1. Extend `execution/run_eval_blind_to_x.py --dry-run` or a companion helper to print dataset file hashes, prompt file hashes, promptfoo version, and config hash.
2. Add a `--metadata-json` mode that emits the minimum evaluation artifact next to `last_run.json`.
3. Require a small reviewer note when `--update-baseline` is used.
4. Add a warning when promptfoo's `draft_v_current.txt` hash has no recorded sync relationship with `projects/blind-to-x/rules/prompts.yaml`.
5. Add a release-audit check that refuses "ready to publish" claims when a public-output eval has no publish-gate link or human-review status.
6. Add a dedicated holdout split before any fine-tuning/custom-model work from [30-fine-tuning-custom-model-boundary](30-fine-tuning-custom-model-boundary.md).

## 출처

- Primary docs: Promptfoo, *LLM Rubric*: <https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/>
- Primary docs: Promptfoo, *Model-graded metrics*: <https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/>
- Official: OpenAI API Docs, *Working with evals*: <https://developers.openai.com/api/docs/guides/evals>
- Official: OpenAI API Docs, *Graders*: <https://developers.openai.com/api/docs/guides/graders>
- Official: Claude API Docs, *Define success criteria and build evaluations*: <https://platform.claude.com/docs/en/test-and-evaluate/develop-tests>
- Official: Claude API Docs, *Using the Evaluation Tool*: <https://platform.claude.com/docs/en/test-and-evaluate/eval-tool>
- Official: Google Cloud Docs, *Run an evaluation* (Gemini Enterprise Agent Platform): <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/eval-python-sdk/run-evaluation>
- Official: Google Cloud Docs, *Gen AI evaluation service API*: <https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation>
- Code evidence: `execution/run_eval_blind_to_x.py`, `execution/blind_to_x_eval_extract.py`, `tests/eval/blind-to-x/promptfooconfig.yaml`, `workspace/execution/harness_eval.py`, `workspace/execution/code_evaluator.py`, `workspace/execution/confidence_verifier.py`, `projects/blind-to-x/config.example.yaml`, `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`, `projects/blind-to-x/pipeline/process_stages/filter_profile_stage.py`, `projects/blind-to-x/pipeline/publish_decision.py`, `projects/blind-to-x/pipeline/review_queue.py`.

*외부 자료 검증일: 2026-06-08 · Code verified against current HEAD.*
