# 29 - Error Taxonomy - Refusal - Fallback Boundary

> Provider errors, model refusals, structured-output failures, and product quality gates must not collapse into one generic "LLM failed" bucket.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_review.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`, `projects/blind-to-x/pipeline/process_stages/persist_stage.py`, `projects/blind-to-x/pipeline/regulation_checker.py`, and `projects/blind-to-x/pipeline/publish_decision.py`.

## Why This Is Separate

The retry page covers rate limits and backoff, and the structured-output page covers JSON/schema behavior. This page defines the error taxonomy that decides whether a failure should retry, fall back to another provider, repair the model output, block publication, or ask a human to inspect the artifact.

Use these buckets before choosing an action:

| Bucket | Typical signal | Default action |
|---|---|---|
| Transport/network | connection error, timeout, cancelled stream | Retry within a bounded budget; then fallback |
| Provider service | 500, 503, 504, overloaded/capacity | Retry with jitter or switch provider/model |
| Rate/quota/billing | 429, quota, billing, resource exhausted | Respect provider limits; do not blind-loop |
| Auth/permission/model | 401, 403, 404, model not found, permission denied | Stop that provider until config is fixed |
| Request shape/context | malformed request, invalid argument, request too large, context too long | Fix prompt/request sizing; fallback usually will not help |
| Safety/refusal/content filter | refusal field, stop_reason/refusal, finishReason SAFETY, prompt block | Treat as a policy/safety outcome, not a transient failure |
| Structured-output failure | JSON parse error, schema mismatch, incomplete max-token response | Repair once or regenerate with stricter schema; log reason code |
| Product quality gate | fact check warning, regulation failure, low verifiability, publish HOLD/DROP | Keep local evidence and route to reviewer/product policy |

## Current Code Facts

### 1) Workspace LLMClient Has Provider Fallback But No Normalized API Error Artifact

`LLMClient` carries `NON_RETRYABLE_KEYWORDS` and `_is_non_retryable()` to stop retrying a provider when error text looks like invalid key, authorization, quota, billing, permission, model-not-found, or similar. The simple loop accumulates string `all_errors`, retries JSON parse failures and generic exceptions, sleeps with exponential backoff, then raises one joined failure string after all providers are exhausted.

Operational conclusion:

- The current core can avoid obvious bad-provider loops, but classification is string-based.
- JSON parse failures and provider API failures both end up in the same `all_errors` list.
- The raised error is useful for a log, but it is not machine-queryable by status code, provider error type, request ID, refusal flag, or safety category.

### 2) Bridge Validation Records Output Reason Codes, Not Provider Error Classes

The bridged path logs `bridge_mode`, `reason_codes`, `repair_count`, `fallback_used`, `language_score`, and `provider_used` into `api_usage_tracker.py`. The tracker can summarize top bridge reason codes, fallback calls, provider fallback rates, and dead providers.

Operational conclusion:

- This is good observability for output validation and fallback behavior.
- It does not yet distinguish `rate_limit_error` from `authentication_error`, `overloaded_error`, request-too-large, timeout, provider refusal, or safety block.
- A future normalized error artifact should sit next to these bridge reason codes rather than replace them.

### 3) Shorts Maker LLMRouter Mirrors The Same Boundary

`projects/shorts-maker-v2/.../llm_router.py` has its own `NON_RETRYABLE_KEYWORDS`, JSON parse retry loop, and final "All LLM providers failed" / "All bridge providers failed" errors. `script_step.py` separately detects local content unsuitability through `no_reliable_source`, schema warnings, review score failures, and `verifiability_score < 4`.

Operational conclusion:

- Provider execution failure and topic unsuitability are different failure types.
- `TopicUnsuitableError` should not be grouped with provider outages or rate limits.
- Low verifiability is a product-quality signal; switching providers may produce a more fluent script, but it does not fix missing source evidence.

### 4) Blind-to-X Keeps Product Failure Reasons But Provider Errors Are Still Text

`draft_generator.py` returns `_generation_failure()` for no providers, failed draft generation, or all best-of-N candidates failing. The retry helper stores provider errors as strings and raises a joined message. `generate_review_stage.py` separately sets `error_code` and `failure_reason` for missing generators, generation failure, and twitter quality-gate failure. Later stages validate fact checks, regulation reports, publish decisions, and X upload errors.

Operational conclusion:

- Blind-to-X already has useful product-level `failure_reason` values.
- Provider failure details are not normalized before they enter those product outcomes.
- Product gates such as `twitter_quality_gate_failed`, regulation failures, and publish `HOLD`/`DROP` must remain distinct from API retry/fallback behavior.

## Provider Official Boundaries

### OpenAI

OpenAI's error guide separates authentication, bad request, conflict, not found, permission denied, rate limit, unprocessable entity, connection, timeout, and internal server errors. It recommends checking request shape for bad requests, pacing for rate limits, retrying internal/server issues, and providing error message/code plus timestamp when persistent errors need support.

Structured Outputs add a separate model-output edge case: a model may refuse for safety, and the response can include a `refusal` field that does not follow the requested schema. OpenAI also notes incomplete structured outputs can happen when max-token limits are reached.

Repo implication: a `refusal` field is not a JSON parser bug. Preserve it as `class=safety_refusal` or equivalent before any schema repair loop tries to "fix" the output.

### Anthropic / Claude

Anthropic documents predictable HTTP error types such as `invalid_request_error`, `authentication_error`, `billing_error`, `permission_error`, `not_found_error`, `request_too_large`, `rate_limit_error`, `api_error`, `timeout_error`, and `overloaded_error`. Errors include an `error.type`, `error.message`, and `request_id`; streaming can still emit errors after an HTTP 200 response.

Claude message responses also include `stop_reason`. A `stop_reason` of `refusal` means the model refused for safety. Newer Opus models can include `stop_details` with category and explanation, but the explanation is not stable enough for programmatic parsing.

Repo implication: store `error.type` and `request_id` for provider errors, and store `stop_reason=refusal` separately from transport/API failures. Do not parse free-text refusal explanations as routing logic.

### Gemini

Gemini's troubleshooting guide lists backend error codes including `INVALID_ARGUMENT`, `FAILED_PRECONDITION`, `PERMISSION_DENIED`, `NOT_FOUND`, `RESOURCE_EXHAUSTED`, `CANCELLED`, `INTERNAL`, `UNAVAILABLE`, and `DEADLINE_EXCEEDED`. It also calls out model parameter errors, wrong API versions/models, blocked/leaked API keys, safety issues, `BlockedReason.OTHER`, and `RECITATION`.

Gemini safety feedback is a separate response surface. Prompt blocks appear in `promptFeedback.blockReason`; response blocks can surface through `Candidate.finishReason == SAFETY` and `Candidate.safetyRatings`, and blocked content is not returned.

Repo implication: `finishReason=SAFETY`, `promptFeedback.blockReason`, and `safetyRatings` are safety outcomes, not empty-output parser failures. A parser should see a structured blocked/safety artifact before it sees an empty string.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Keep joined error strings only | Simple and already implemented | Cannot trend auth vs quota vs safety vs schema failures | Reject as final state |
| B. Add provider-specific exception branches only | Better retry decisions | Duplicates logic across clients and projects | Partial step only |
| C. Normalize error artifacts at provider boundary | One taxonomy across workspace, Shorts, and Blind-to-X | Requires adapters and tests | Adopt next |
| D. Store raw provider responses/errors everywhere | Maximum debug detail | Privacy, retention, schema churn | Debug-only with classification |

**Decision:** adopt C. Every LLM call path should be able to return or log a normalized sidecar error artifact before the product layer converts it into a user-facing failure reason.

Suggested shape:

```json
{
  "schema_version": 1,
  "provider": "openai|anthropic|google|deepseek|xai|moonshot|zhipuai|ollama|local",
  "model": "provider-model-id",
  "phase": "request|stream|parse|schema|safety|quality_gate|publish_gate",
  "class": "transport|provider_service|rate_limit|quota|auth|permission|not_found|request_shape|context_limit|timeout|safety_refusal|content_filter|structured_output|product_quality",
  "retryable": false,
  "fallback_allowed": false,
  "http_status": 429,
  "provider_error_type": "rate_limit_error",
  "provider_error_code": "RESOURCE_EXHAUSTED",
  "request_id": "req_...",
  "stop_reason": "refusal",
  "finish_reason": "SAFETY",
  "safety_categories": ["HARM_CATEGORY_DANGEROUS_CONTENT"],
  "local_reason_codes": ["json_invalid", "language_mismatch"],
  "message_redacted": "short redacted diagnostic"
}
```

## Routing Rules

1. Retry only transport, provider service, timeout, and rate-limit classes, and only within a bounded provider budget.
2. Do not retry auth, permission, billing, model-not-found, blocked/leaked key, request-too-large, or malformed request as if they were transient.
3. Let fallback switch providers only when the class is provider/service/transport/rate-limit and the task semantics still hold.
4. Do not fallback away from safety/refusal unless a human or product policy says the request is allowed and should be rephrased.
5. Run structured-output repair only after checking for refusal/content-filter/incomplete-output markers.
6. Product quality gates should emit product failure reasons, not overwrite provider error classes.
7. Store request IDs, provider error types, and safety categories in redacted metrics; do not store raw prompts or raw unsafe content in generic usage logs.
8. Add dashboard dimensions for `error.class`, `retryable`, `fallback_allowed`, and `provider_error_type` next to existing `fallback_used` and bridge `reason_codes`.

## Implementation Checklist

1. Add a small normalized error dataclass or dict builder in the shared LLM boundary.
2. Map OpenAI SDK/API exceptions into status, provider error type/code, request ID, and retryability.
3. Map Anthropic HTTP/SSE errors and `stop_reason=refusal` into separate provider-error and model-refusal artifacts.
4. Map Gemini backend status codes plus `promptFeedback.blockReason`, `Candidate.finishReason`, and `safetyRatings`.
5. Teach JSON parse/schema repair to short-circuit when the response is a refusal or safety block.
6. Extend `api_usage_tracker.py` with optional error columns or a companion table without breaking existing usage rows.
7. Preserve Blind-to-X `failure_reason` and Shorts `TopicUnsuitableError` as product-layer outcomes linked to the normalized provider artifact when available.
8. Add tests for one retryable provider-service error, one non-retryable auth error, one structured-output refusal, one Gemini safety block, and one product quality-gate failure.

## Pitfalls

- "Empty response" can mean safety block, token limit, SDK parsing behavior, or a real empty model answer.
- A provider refusal is often a successful API response with a policy outcome, not an exception.
- Retrying a malformed request burns budget and can hide the real fix.
- Switching providers after a safety refusal can create policy bypass behavior.
- Product regulation checks are not provider safety filters.
- A final joined error string is useful for humans but weak for operations, dashboards, and recovery automation.

For public outputs, this taxonomy is only the provider/error side of the decision. [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md) defines the downstream publish gate that keeps safety/refusal, LLM moderation, product quality, platform policy, and human approval distinct.

## 출처

- 공식: OpenAI API Docs, *Error codes*: <https://developers.openai.com/api/docs/guides/error-codes>
- 공식: OpenAI API Docs, *Structured model outputs*: <https://developers.openai.com/api/docs/guides/structured-outputs>
- 공식: Anthropic Claude API Docs, *Errors*: <https://platform.claude.com/docs/en/api/errors>
- 공식: Anthropic Claude API Docs, *Handling stop reasons*: <https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons>
- 공식: Google AI for Developers, *Gemini API troubleshooting*: <https://ai.google.dev/gemini-api/docs/troubleshooting>
- 공식: Google AI for Developers, *Gemini API safety settings*: <https://ai.google.dev/gemini-api/docs/safety-settings>
- Code evidence: `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_review.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/process_stages/generate_review_stage.py`, `projects/blind-to-x/pipeline/process_stages/persist_stage.py`, `projects/blind-to-x/pipeline/regulation_checker.py`, `projects/blind-to-x/pipeline/publish_decision.py`.

*외부 자료 검증일: 2026-06-08 - Code verified against current HEAD.*
