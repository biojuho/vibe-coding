# 40 - Side Effect - Idempotency - Replay Boundary

> Retrying generation, validation, or provider calls is not the same as replaying external writes safely.
> Code facts were checked on 2026-06-08 from `projects/blind-to-x/pipeline/process_stages/dedup_stage.py`, `projects/blind-to-x/pipeline/process_stages/persist_stage.py`, `projects/blind-to-x/pipeline/notion/_cache.py`, `projects/blind-to-x/pipeline/notion/_upload.py`, `projects/blind-to-x/pipeline/image_upload.py`, `projects/blind-to-x/pipeline/twitter_poster.py`, and `projects/blind-to-x/pipeline/publish_decision.py`.

## Why This Is Separate

[20-rate-limit-reliability](20-rate-limit-reliability.md) covers when to retry a provider failure. [31-generation-parameters-reproducibility](31-generation-parameters-reproducibility.md) covers replaying model generation evidence. [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md) covers whether an output may be published. [39-credentials-secrets-api-key-boundary](39-credentials-secrets-api-key-boundary.md) covers whether a credential authorizes a surface.

This page covers the next boundary: once a workflow can write to Notion, Cloudinary, X, YouTube, a database, or another external system, retries can create duplicate pages, duplicate assets, duplicate posts, or partial publish records. A publish gate decides whether the write is allowed; an idempotency boundary decides whether the same allowed write can be replayed without another side effect.

The operating rule is: every side-effecting operation needs a stable operation key and a recovery record before the first live write.

## Current Code Facts

### 1. Blind-to-X Has URL Dedup, Not An Operation Ledger

`run_dedup_stage()` calls `notion_uploader.is_duplicate(ctx.url)` before generation/persist. `NotionCacheMixin` canonicalizes URLs, warms an in-memory cache from recent Notion pages, and falls back to a Notion query when the cache is not ready.

Operational conclusion: this is useful source deduplication. It is not an exactly-once write boundary, because it does not persist a per-operation status such as `planned`, `inflight`, `succeeded`, or `failed_unknown` before the create call.

### 2. Notion Page Creation Registers The URL Only After Success

`NotionUploadMixin.upload()` builds the page payload, calls `self.client.pages.create(...)` through `_safe_notion_call`, and only after a successful response calls `_register_url_in_cache(post_data.get("url", ""))` before returning the Notion URL and page ID.

Operational conclusion: if the Notion page is created but the process loses the response, crashes before the caller persists `page_id`, or reruns with a cold cache, the repo needs a reconciliation path before another `pages.create` call. The current URL cache reduces normal duplicates but does not record unknown-side-effect recovery.

### 3. Cloudinary Upload Retries A Mutating Upload Without A Stable Asset ID

`ImageUploader._upload_to_cloudinary()` calls `cloudinary.uploader.upload(filepath)` through the shared retry helper. The local call does not pass a deterministic `public_id` or `overwrite=false`.

Operational conclusion: retrying a transient upload failure can be correct, but the repo currently relies on Cloudinary defaults for asset identity. For generated assets that belong to a publish run, the operation needs a stable asset key, stored `public_id`, stored `secure_url`, and an explicit duplicate policy.

### 4. X Posting Retries Around A Create Call

`TwitterPoster.post_tweet()` retries on `tweepy.TooManyRequests` and server-side errors, uploads media through v1.1 when `image_path` is present, then calls `self.client_v2.create_tweet(...)` and returns the resulting X URL.

Operational conclusion: the publish decision can say "Ready to Post", and the credential can allow X writes, but a lost response after `create_tweet` is still an unknown side-effect state. X posting needs one operation key per intended post and a reconciliation rule before re-posting.

### 5. Publish Decisions And Credentials Are Gates, Not Idempotency

`decide_publish()` returns `PUBLISH`, `HOLD`, or `DROP`, and `persist_stage.py` checks human approval, `AUTO_PUBLISH`, and `require_human_approval` before posting. This is the correct policy gate, but it does not make the downstream write replay-safe.

Operational conclusion: policy approval, credential readiness, and idempotent execution are three separate artifacts. They should be linked, not collapsed.

## Official Boundaries

### Provider-Native Idempotency

Stripe documents the strong version: a client supplies an idempotency key for `POST` requests, Stripe stores the first status/body for that key, compares later parameters against the original request, and returns the saved result on repeat requests. This is provider-owned response replay.

Google Cloud's retry guidance says callers should consider idempotency before retrying retryable responses, because non-idempotent retries can cause races or conflicts. Some operations are conditionally idempotent only when preconditions or ETags are supplied. Google Cloud Run function retry guidance also recommends using event IDs as idempotency keys with APIs that support them and making code internally idempotent with a state check before mutation.

AWS Lambda Powertools idempotency provides the application-owned pattern: choose an idempotency key from the payload, persist it, return the previous result for repeated calls, and guard concurrent requests, timeouts, missing keys, and payload tampering.

Repo implication: use provider-native idempotency when it exists, but keep a repo-owned operation ledger because Notion, X, media uploads, and multi-step publish flows do not share one universal idempotency surface.

### Notion

Notion's create-page endpoint returns a new page object. Its status-code docs include `409 conflict_error`, `429 rate_limited`, and retry guidance through error details or rate-limit documentation, but the create-page docs do not expose a Stripe-style idempotency key in the documented request body.

Repo implication: Notion writes should carry a repo operation key, ideally also stored on the target page when the schema allows it. On `failed_unknown`, query by operation key or canonical source URL before creating another page.

### X

X documents `POST /2/tweets` as a create/edit post endpoint that returns `201` with a post ID when creating a new post. The documented create body names post content fields such as `text`, `media`, `reply`, and `edit_options`; it does not describe a request-level idempotency key for creating a post.

Repo implication: treat X create-post as a non-idempotent side effect unless the repo can prove otherwise for the exact API surface in use. A retry after an unknown result should reconcile by stored post ID, target account timeline, or manual operator check before another create.

### Cloudinary

Cloudinary documents random `public_id` assignment by default, deterministic naming controls, `overwrite`, and duplicate-avoidance patterns. For uploads with deterministic `public_id`, `overwrite=false` can prevent re-uploading an existing asset, and responses indicate whether an existing or overwritten asset was involved. Cloudinary also documents duplicate detection via `etag`, pHash, and ETag-as-public-ID settings.

Repo implication: generated assets should use deterministic IDs where the repo owns the asset namespace. Store `public_id`, `secure_url`, and `etag` as the replay evidence; do not rely only on a final URL string.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Existing URL cache and duplicate query only | Already implemented for Notion source dedup | Does not cover unknown writes, media uploads, X posts, or multi-step publish recovery | Keep as a weak guard |
| B. Provider-native idempotency only | Strong when available, low custom code | Not universal across Notion/X/Cloudinary and does not link multi-step operations | Use when available, but not alone |
| C. Repo-owned side-effect ledger | Works across providers, supports recovery, links publish/credential evidence | Requires a small persistence layer and workflow adapters | Adopt |
| D. No live writes without human replay | Safest while building | Blocks approved automation and does not solve operator retries | Use only for unapproved surfaces |

**Decision:** adopt C, with B as an optimization where a provider supports it. Keep A as a preflight duplicate check. Do not rely on D after a surface is explicitly authorized for live writes.

## Minimum Side-Effect Operation Artifact

For each external write, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `operation_id` | Unique local record ID |
| `operation_key` | Stable replay key derived from source ID, target surface, action, and payload hash |
| `parent_run_id` | Pipeline or publish run that groups related writes |
| `surface` | `notion_page_create`, `notion_page_update`, `cloudinary_upload`, `x_post_create`, `youtube_upload`, etc. |
| `target` | Notion database/page, Cloudinary folder/cloud, X account, YouTube channel, database table |
| `side_effect_class` | `write`, `publish`, `asset_upload`, `status_update`, `delete`, or `admin` |
| `payload_hash` | Hash of the redacted request body or canonical payload |
| `source_artifact_id` | Link/hash from source or generation evidence |
| `publish_gate_artifact_id` | Link/hash from [32-safety-moderation-publish-gates](32-safety-moderation-publish-gates.md) |
| `credential_artifact_id` | Link/hash from [39-credentials-secrets-api-key-boundary](39-credentials-secrets-api-key-boundary.md) |
| `provider_idempotency_key` | Provider-native idempotency key when supported |
| `status` | `planned`, `inflight`, `succeeded`, `confirmed`, `failed_retryable`, `failed_unknown`, `failed_terminal`, `reconciled` |
| `attempt_count` | Number of provider attempts made under the same key |
| `provider_request_id` | Provider request/trace ID when available |
| `target_object_id` | Notion page ID, Cloudinary public ID, X post ID, YouTube video ID, etc. |
| `target_url` | Final visible URL when available |
| `first_attempt_at` | First live attempt timestamp |
| `last_attempt_at` | Last attempt or reconciliation timestamp |
| `replay_policy` | `return_existing`, `reconcile_before_retry`, `manual_review_required`, or `never_retry` |
| `recovery_action` | Next action when state is unknown |

This artifact is metadata. Redact tokens, private source bodies, and full prompt text according to [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md).

## Routing Rules

1. Generation, parsing, scoring, and dry-run validation can retry under their own retry budgets; external writes must go through the side-effect ledger.
2. Compute `operation_key` before the first provider write from stable inputs. Do not use timestamps alone.
3. Persist `planned` or `inflight` before the provider call. If two workers claim the same key, one should win and the other should wait, return existing evidence, or fail fast.
4. If a retry sees `succeeded` or `confirmed`, return the stored target object instead of calling the provider again.
5. If a retry sees `failed_unknown`, reconcile with the target system before creating another object.
6. Provider-native idempotency keys should be derived from the repo operation key and recorded in the artifact.
7. Notion create-page replay should query by operation key or canonical source URL before `pages.create`.
8. Cloudinary upload replay should use deterministic `public_id` plus `overwrite=false` where the repo owns the namespace, then store `public_id`, `secure_url`, and `etag`.
9. X post replay should never call `create_tweet` again after an unknown result until the target account has been reconciled.
10. Media upload and public post creation are separate operations linked by `parent_run_id`; a media success does not imply post success.
11. Human approval authorizes a side effect once. It does not authorize duplicate side effects after unknown failure.
12. Credential presence proves capability, not replay safety.

## Implementation Candidates

1. Add a small `side_effect_ledger` helper for Blind-to-X with a SQLite table or Notion-safe operation-key property, whichever is easiest to verify locally first.
2. Wrap Notion page creation with `operation_key`, `payload_hash`, `status`, `page_id`, and a reconciliation query before duplicate create.
3. Add deterministic Cloudinary `public_id` generation for generated assets and set `overwrite=false` for replay-protected uploads.
4. Wrap X posting so an approved post gets exactly one operation key, one post attempt sequence, and a manual reconciliation state for unknown results.
5. Extend release readiness to refuse auto-publish when a public side-effect surface lacks a ledger or replay policy.
6. Add tests for the hardest case: provider call succeeds, local response handling fails, rerun must not create another page/asset/post.

## Pitfalls

- A successful retry strategy can make duplicate side effects worse if the operation is not idempotent.
- A Notion URL cache is not proof that an earlier page create did or did not happen.
- A Cloudinary secure URL is not enough to reconcile duplicates; keep the provider object identity.
- A high quality score or `Ready to Post` status does not protect against double-posting.
- Provider SDK retries may hide how many live attempts were made unless the repo records attempts itself.
- Dry-run evidence cannot prove live replay behavior.
- Manual cleanup after duplicate publishes is not a rollback strategy for public surfaces.

## 출처

- Official: Stripe API Reference, *Idempotent requests*: <https://docs.stripe.com/api/idempotent_requests>
- Official: Google Cloud Documentation, *Cloud Storage retry strategy - Idempotency*: <https://docs.cloud.google.com/storage/docs/retry-strategy>
- Official: Google Cloud Documentation, *Configure event-driven function retries*: <https://docs.cloud.google.com/run/docs/tips/function-retries>
- Official: AWS Documentation, *Powertools for AWS Lambda (Python) - Idempotency*: <https://docs.aws.amazon.com/powertools/python/3.10.0/utilities/idempotency/>
- Official: Notion Docs, *Create a page*: <https://developers.notion.com/reference/post-page>
- Official: Notion Docs, *Status codes*: <https://developers.notion.com/reference/status-codes>
- Official: X Docs, *Create or Edit Post*: <https://docs.x.com/x-api/posts/create-post>
- Official: Cloudinary Documentation, *Upload API reference*: <https://cloudinary.com/documentation/image_upload_api_reference>
- Official: Cloudinary Documentation, *Customizing uploads*: <https://cloudinary.com/documentation/upload_parameters>
- Official: Cloudinary Documentation, *Programmatically uploading images - Avoiding duplicate uploads*: <https://cloudinary.com/documentation/upload_images#avoiding_duplicate_uploads>
- Official: Cloudinary Documentation, *Avoiding and detecting duplicate uploads*: <https://cloudinary.com/documentation/ts_how_can_cloudinary_help_me_to_avoid_or_detect_duplicated_uploads_in_my_account>
- Code evidence: `projects/blind-to-x/pipeline/process_stages/dedup_stage.py`, `projects/blind-to-x/pipeline/process_stages/persist_stage.py`, `projects/blind-to-x/pipeline/notion/_cache.py`, `projects/blind-to-x/pipeline/notion/_upload.py`, `projects/blind-to-x/pipeline/image_upload.py`, `projects/blind-to-x/pipeline/twitter_poster.py`, `projects/blind-to-x/pipeline/publish_decision.py`.

*외부 자료 검증일: 2026-06-08. Code verified against current HEAD.*
