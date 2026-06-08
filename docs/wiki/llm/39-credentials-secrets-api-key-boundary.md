# 39 - Credentials - Secrets - API Key Boundary

> Credentials are not the same thing as security posture, data retention, conversation state, cost budget, or release evidence.
> Code facts were checked on 2026-06-08 from `.gitignore`, `.env.example`, `workspace/directives/agent_permissions.yaml`, `workspace/execution/harness_security_checklist.py`, `execution/commit_scope_guard.py`, `execution/product_readiness_score.py`, `execution/langfuse_preflight.py`, `projects/blind-to-x/config.py`, `projects/blind-to-x/config.ci.yaml`, `projects/shorts-maker-v2/src/shorts_maker_v2/config.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/hanwoo-dashboard/.env.example`, and `projects/hanwoo-dashboard/scripts/*`.

## Why This Is Separate

Pages 08, 27, and 38 cover security controls, retention/privacy, and state handoff. They still leave a launch-critical question:

**Which credential authorizes which action, where is it allowed to live, and what proof is valid without exposing the secret?**

For this workspace, credential surfaces are deliberately mixed across local development, product launches, CI, external OAuth, and AI-provider calls. A green local test can prove that a key is present, but it does not prove that the key is least-privilege, current, owned by the right operator, safe to publish, or approved for a side-effecting run.

The rule: credentials are capability boundaries. Treat key presence as preflight evidence only, not as release approval.

## Credential Surfaces In This Repo

| Surface | Examples | Owner | Valid evidence | Invalid evidence |
|---|---|---|---|---|
| LLM provider keys | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY` | Provider account/project owner | Redacted key presence, provider/project scope, model/budget/rate-limit policy, last rotation date | Printing key value, checking in `.env`, assuming one key is safe for every project |
| Product API credentials | Notion, X/Twitter, Cloudinary, YouTube, Pexels, Freesound, Brave, NotebookLM | Product/integration owner | Env key names, token policy, target workspace/database/channel ID, dry-run result | A successful draft generation that never touches the publish target |
| Database and backend secrets | Supabase/Postgres `DATABASE_URL`, Redis URLs, Auth.js secrets, admin seed password, payment secret key | Product operator | Placeholder check, live DB smoke when authorized, redacted pooler host/project, connection role | Treating `.env.example` as configured, retrying live DB after a known credential-control-plane blocker |
| Browser-safe public config | `NEXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY`, Supabase publishable/anon keys when RLS is correct | Frontend/product owner | Explicit public designation plus paired server-side secret policy | Exposing service-role/admin keys because a similar public key exists |
| CI/runtime secrets | GitHub Actions secrets, Vercel/Netlify/cloud env vars, Supabase function secrets | Deployment owner | Secret name, scope, environment, job that consumes it, redacted audit/check result | Assuming local `.env` transfers to CI or that CI can read a secret not referenced in workflow |
| OAuth/user tokens | `credentials.json`, `token.json`, NotebookLM auth token file, Notion OAuth access/refresh tokens | User/workspace admin | Gitignored path, expiration/revocation plan, least-access page/workspace selection | Treating local user token files as shared agent state |
| Observability secrets | Langfuse public/secret key, host, self-host passwords | Observability operator | `langfuse_preflight.py` pass and metadata-only trace policy | Enabling traces with prompt bodies before retention/masking is configured |

## Current Code Facts

### 1. Secret Files Are Globally Ignored, But Ignore Rules Are Hygiene, Not Proof

Root `.gitignore` excludes `.env`, `.env.*`, `credentials.json`, `token.json`, PEM/key files, Brave local secrets, NotebookLM local auth, `.tmp/`, logs, build output, and nested tool state. It explicitly allows `.env.example`.

Operational conclusion: the repo has a baseline "do not commit real secrets" policy. It still needs preflight or secret scanning before commit/push, because `.gitignore` cannot prove that history, generated artifacts, screenshots, logs, or Markdown snippets are clean.

### 2. The Harness Permission Matrix Denies Secret Paths By Default

`workspace/directives/agent_permissions.yaml` denies `**/.env`, `**/credentials.json`, `**/token.json`, and `**/.git/**` in the default profile, then grants project-specific allowed paths and tools. It also requires human approval for shell, Python execution, HTTP requests, and file deletion in the declarative harness model.

Operational conclusion: local agents should not treat credential files as normal context. If a workflow needs to check secret readiness, it should inspect redacted assignment presence through a deterministic script, not read or quote secret values.

### 3. Secret Hygiene Has Multiple Guards With Different Scopes

`workspace/execution/harness_security_checklist.py` can scan content for common secret patterns, check `.env` permissions, verify `.gitignore` has credential entries, detect tracked credential filenames, and flag `.env` under public build directories.

`execution/commit_scope_guard.py` marks `.env`, `credentials.json`, and `token.json` as forbidden staged paths.

Operational conclusion: these are hygiene guards, not credential managers. They help detect accidental exposure. They do not rotate keys, check provider-side permissions, or authorize side effects.

### 4. Root And Project Env Templates Use Placeholders By Design

Root `.env.example` groups LLM keys, social/external service keys, Telegram, GitHub, Brave, NotebookLM, n8n bridge, Langfuse, and project settings. Project templates add narrower launch requirements:

| Project | Template facts | Boundary |
|---|---|---|
| `blind-to-x` | Notion DB/API, Blind login, multi-provider LLM keys, Cloudinary, X/Twitter, optional enrichment/search keys, Langfuse forwarding flags | Drafting, review, image upload, and publish credentials are separate; one green draft test does not prove publish authority |
| `shorts-maker-v2` | `OPENAI_API_KEY` and `GEMINI_API_KEY` template, with runtime code also recognizing Anthropic, Pexels, Freesound, Notion, YouTube, and XAI in specific paths | Generation, media, calendar, and analytics credentials should be scoped per task |
| `hanwoo-dashboard` | Supabase `DATABASE_URL`, Auth.js secrets, admin seed password, Gemini, Toss payment public/secret pair, KAPE/MTRACE service keys, Redis/BullMQ | Public client keys and server-only secrets share one product but must never share exposure rules |
| `knowledge-dashboard` | Server-only `DASHBOARD_API_KEY`, optional `DASHBOARD_SESSION_SECRET`, data dir, read-only GitHub PAT, NotebookLM token path | No `NEXT_PUBLIC_` prefix is allowed for dashboard auth secrets |

Operational conclusion: `.env.example` is documentation and lint input. It is not readiness evidence. Readiness comes from redacted presence checks, live smoke tests where authorized, and provider/dashboard scope checks.

### 5. Product Readiness Checks Read Presence And Placeholder State

`execution/product_readiness_score.py` checks project `.env` files for usable key presence and placeholder values. It has explicit checks for Blind-to-X Notion/provider keys, Shorts provider keys, Hanwoo Supabase `DATABASE_URL`, and Knowledge Dashboard runtime auth.

Operational conclusion: these checks can say "missing", "placeholder", or "configured enough to run the next validation." They cannot say the external credential is valid until the relevant live or dry-run endpoint is exercised under authorization.

### 6. Hanwoo T-251 Is A Credential-Control Boundary, Not A Local Code Boundary

Hanwoo's `scripts/prisma7-runtime-test.mjs` and `scripts/verify-db-indexes.mjs` load `projects/hanwoo-dashboard/.env`, reject missing/placeholder `DATABASE_URL`, and then require a live Supabase/Postgres connection for the live path.

Operational conclusion: once the live retry returns the known Supabase credential/control-plane blocker, more local code retries do not improve evidence. The next action is owner-side Supabase database password/pooler resync, then a live check.

### 7. CI Secrets Are Not Local Env Files

The repo uses local `.env` files for development, but GitHub Actions secrets are separate runtime variables. GitHub Actions secrets must be explicitly referenced by a workflow before a job can read them.

Operational conclusion: release evidence must distinguish "local key configured" from "CI environment secret configured and consumed by this workflow." Current-head CI proof needs workflow artifacts or job summaries, not local `.env` state.

## Official Boundaries

### OpenAI

OpenAI treats API keys as secrets, warns against sharing or exposing them in client-side code, recommends environment variables or a key-management service on servers, and documents project-scoped access, service accounts, key permissions, budgets, and rate limits. OpenAI also distinguishes standard API keys from Admin API keys and short-lived access tokens.

Repo implication: use project/service-account keys for automation where possible, record which project owns the key, and do not let a personal all-purpose key become shared launch infrastructure. Admin keys belong only to admin workflows.

### Anthropic Claude

Anthropic recommends environment variables and cloud secret stores, adding dotenv files to `.gitignore` for local work, rotating keys regularly, using separate keys by environment or purpose, scanning repositories, and revoking suspected compromised keys.

Repo implication: `ANTHROPIC_API_KEY` presence is not enough. For launch evidence, record development/test/production separation and the last rotation or revocation plan.

### Google Cloud And Gemini

Google Cloud recommends API key restrictions, avoiding API keys in URL query parameters, deleting unused keys, avoiding client-code or repository exposure, and migrating many production cases to IAM or short-lived service-account credentials. The docs also note that API keys are bearer credentials.

Repo implication: a `GOOGLE_API_KEY`/`GEMINI_API_KEY` should be treated as spend-bearing and data-bearing even if originally created for a narrow feature. Prefer restrictions, quotas, and per-project keys.

### Supabase

Supabase separates publishable/anon keys that can be browser-safe under Row Level Security from secret/service-role keys that bypass RLS and must not be used in browsers. Supabase also documents local `.env` files, production secrets, dashboard/CLI management, and never checking `.env` into Git.

Repo implication: Hanwoo and any future Supabase functions must label publishable versus secret credentials explicitly. A browser-safe key is only browser-safe under the matching RLS design.

### Notion

Notion API requests use Bearer tokens for internal integrations and PATs. OAuth token exchange and refresh use client credentials. Notion PAT docs state token creators/admins control revocation, token secrets are not revealable by other admins, PATs expire, and revoked tokens stop working for API requests.

Repo implication: Notion DB IDs are identifiers, but tokens are workspace access. Blind-to-X and Shorts Notion writes should preserve target database/page evidence without logging token values.

### GitHub Actions And OWASP

GitHub Actions secrets are encrypted before they reach GitHub and are only readable by a workflow when explicitly included. OWASP's secrets guidance emphasizes centralized storage, provisioning, auditing, rotation, CI/CD credential scope, caller attribution, and short-lived/dynamic credentials where possible.

Repo implication: CI secret presence must be proven at the workflow boundary. Local `.env` and `.tmp` artifacts should never be treated as CI secret inventory.

### Twelve-Factor Config

The Twelve-Factor config principle says deploy-varying config, including database handles and external-service credentials, should be separated from code and stored in environment variables.

Repo implication: keep `.env.example` tracked, keep real values untracked, and treat per-deploy variable names as a contract that deterministic scripts can inspect without exposing values.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. One shared all-powerful local `.env` for every tool | Simple setup | Poor attribution, hard rotation, accidental cross-project spend or writes | Reject for launch-critical work |
| B. Scoped per-service/per-project keys plus redacted readiness artifacts | Auditable, rotatable, compatible with CI and product ownership | More setup and inventory work | Adopt |
| C. Treat key presence as launch proof | Fast gating | A placeholder or revoked key can pass presence checks; permissions may be wrong | Reject |
| D. Run live side-effect checks whenever a key exists | Finds invalid keys | Can spend money, mutate data, or publish unexpectedly | Only with explicit side-effect authorization |
| E. Put secrets in `.ai` handoff so every agent has context | Convenient continuation | Turns handoff into a credential leak | Reject |

**Decision:** adopt B. Use scoped keys, redacted evidence, provider/project ownership, and separate local/CI/production secret stores. Use D only for explicitly authorized live checks.

## Minimum Credential Artifact

For any LLM/product workflow that depends on a credential, preserve a redacted artifact with these fields where practical:

| Field | Meaning |
|---|---|
| `credential_name` | Env var or secret name, such as `OPENAI_API_KEY` or `DATABASE_URL` |
| `credential_type` | `provider_api_key`, `admin_api_key`, `oauth_token`, `database_url`, `public_client_key`, `ci_secret`, `service_role_key`, etc. |
| `scope_owner` | Provider project, workspace, GitHub environment, product, or human owner |
| `allowed_surface` | `server_only`, `browser_public`, `ci_runtime`, `local_dev`, `edge_function`, `manual_operator_only` |
| `disallowed_surface` | Surfaces where the value must never appear, such as browser, `.ai`, logs, screenshots, committed files |
| `storage_location` | `local_env`, `github_actions_secret`, `vercel_env`, `supabase_secret`, `user_oauth_file`, etc. |
| `value_evidence` | `present_redacted`, `missing`, `placeholder`, `revoked`, `unknown`; never the secret value |
| `permission_scope` | Project, endpoint, database/page, RLS role, read/write/admin, or unknown |
| `rotation_policy` | Last rotation, expiry, owner action, or `unknown` |
| `live_validation` | Dry-run/live command, date, and side-effect class |
| `cost_or_mutation_risk` | `none`, `spend`, `write`, `publish`, `delete`, `admin`, `unknown` |
| `redaction_policy` | How logs, artifacts, and errors remove the credential value |
| `next_action` | The next safe step: configure, rotate, run dry-run, request owner action, or live-check after approval |

Credential artifacts should be metadata-only. Store token values only in the approved secret store.

## Routing Rules

1. Never read or quote real `.env`, `credentials.json`, `token.json`, OAuth tokens, or secret manager values into `.ai`, wiki pages, commit messages, or logs.
2. Treat `.env.example` and README snippets as schema documentation, not configured state.
3. Use redacted presence/placeholder checks before any live call.
4. Separate local development keys from CI, staging, production, and publish-target keys.
5. Separate browser-safe public keys from server-only secrets. A `NEXT_PUBLIC_` key is a public contract, not a naming shortcut.
6. For OpenAI/Anthropic/Gemini keys, record provider project/environment and budget/permission assumptions before launch-critical use.
7. For Notion/X/Cloudinary/YouTube publish paths, distinguish draft generation from write/publish authority.
8. For Supabase/Postgres, distinguish `DATABASE_URL` presence from live credential validity; stop on the known external T-251 credential blocker until the owner resets/resyncs the pooler password.
9. For CI, prove secret consumption through workflow logs/artifacts, not local `.env`.
10. On suspected exposure, rotate/revoke first, then update local/CI/production stores and rerun redacted validation.

## Implementation Candidates

1. Add a `credential_artifact` helper used by `product_readiness_score.py` and release packets.
2. Extend the LLM Wiki release summary with a redacted credential-surface checklist: local-only, CI, provider project, publish target, and live side-effect authorization.
3. Add a docs-only matrix generated from `.env.example` files that marks each variable as `server_only`, `browser_public`, `oauth_file`, `database_url`, or `observability`.
4. Extend Blind-to-X publish dry-runs with target Notion database and X account identifiers while redacting tokens.
5. Extend Hanwoo T-251 handoff with exactly one owner-side action and the next live validation command after Supabase reset.
6. Add secret scanning to the scoped commit/release path before push authorization, while keeping false-positive handling deterministic.

## Pitfalls

- A key that works locally may be a personal key with the wrong billing owner.
- A key that is present may be a placeholder, revoked, expired, overprivileged, or scoped to the wrong project.
- Public browser keys can still be abused if restrictions, quotas, RLS, or paired server checks are wrong.
- CI secrets are unavailable unless the workflow explicitly maps them into the job.
- OAuth refresh tokens and local `token.json` files are user authorization, not shared repo state.
- Printing only the first few characters of a token can still leak enough for correlation. Prefer `present_redacted` and secret IDs, not prefixes.
- Retention controls and secret controls are separate. Zero-data-retention does not protect a leaked API key.

## 출처

- Official: OpenAI Help Center, *Best Practices for API Key Safety*: <https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety>
- Official: OpenAI Help Center, *Managing projects in the API platform*: <https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform>
- Official: OpenAI API Reference, *Authentication*: <https://developers.openai.com/api/reference/overview#authentication>
- Official: Anthropic Help Center, *API Key Best Practices: Keeping Your Keys Safe and Secure*: <https://support.claude.com/en/articles/9767949-api-key-best-practices-keeping-your-keys-safe-and-secure>
- Official: Google Cloud Documentation, *Best practices for managing API keys*: <https://docs.cloud.google.com/docs/authentication/api-keys-best-practices>
- Official: Supabase Docs, *Environment Variables*: <https://supabase.com/docs/guides/functions/secrets>
- Official: Notion Docs, *Authorization*: <https://developers.notion.com/guides/get-started/authorization>
- Official: Notion Docs, *Personal access tokens*: <https://developers.notion.com/guides/get-started/personal-access-tokens>
- Official: GitHub Docs, *Secrets*: <https://docs.github.com/en/actions/concepts/security/secrets>
- Standard: OWASP Cheat Sheet Series, *Secrets Management Cheat Sheet*: <https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html>
- Standard: The Twelve-Factor App, *Config*: <https://www.12factor.net/config>
- Code evidence: `.gitignore`, `.env.example`, `workspace/directives/agent_permissions.yaml`, `workspace/execution/harness_security_checklist.py`, `execution/commit_scope_guard.py`, `execution/product_readiness_score.py`, `execution/langfuse_preflight.py`, `projects/blind-to-x/config.py`, `projects/blind-to-x/config.ci.yaml`, `projects/shorts-maker-v2/src/shorts_maker_v2/config.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/hanwoo-dashboard/.env.example`, `projects/hanwoo-dashboard/scripts/prisma7-runtime-test.mjs`, `projects/hanwoo-dashboard/scripts/verify-db-indexes.mjs`.

*외부 자료 검증일: 2026-06-08 - Code verified against current HEAD.*
