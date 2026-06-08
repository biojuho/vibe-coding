# 38 - Conversation State - Memory - Handoff Boundary

> Conversation state is not the same thing as token budget, prompt provenance, provider retention, or API surface.
> Code facts were checked on 2026-06-08 from `workspace/execution/llm_client.py`, `workspace/execution/harness_middleware.py`, `workspace/execution/graph_engine.py`, `execution/session_orient.py`, `execution/llm_wiki_objective_audit.py`, and `.agents/skills/auto-research/scripts/*`.

## Why This Is Separate

Pages 21, 26, 27, 31, and 37 already cover context windows, prompt identity, privacy retention, replay parameters, and API surface. They still leave one operational gap:

**Which state made the next LLM turn different from a fresh call, and who owns that state?**

For this repo, "state" can mean several incompatible things:

| State surface | Owner | What it can prove | What it cannot prove |
|---|---|---|---|
| Provider conversation state | OpenAI/Anthropic/Gemini or another provider | The provider can continue from a server-side response, conversation, thread, or cached prefix | Local reproducibility unless the ID and retention policy are recorded |
| SDK session memory | Client SDK or app database | The app can replay or summarize prior turns across runs | Provider-side state, unless explicitly synced |
| LangGraph checkpoint/thread state | App-owned graph runtime | A graph can resume or inspect workflow state by thread/checkpoint | That a provider saw the same prompt body |
| MCP resources/tools/prompts | MCP host and servers | What context/actions/templates were available to the model | Durable app memory unless persisted elsewhere |
| Local `.ai` handoff | This workspace | What the next AI tool should read first and which boundaries remain blocked | Model memory, user approval, or release authorization |
| Local `.tmp` artifacts | Deterministic scripts | Machine-readable evidence from selectors, audits, and browser QA | Authorization to stage, commit, push, or retry external blockers |
| Product database/output state | Product workflow | User-facing durable data and generated artifacts | Provider retention or prompt replay by itself |

The rule: every cached, evaluated, published, or release-gated LLM output needs to name the state surface it depended on. A successful follow-up answer is not enough evidence unless the continuation mechanism is recorded.

Credential state is intentionally separate. `.ai` handoff and `.tmp` evidence can record that a redacted key check passed, but they must not store API keys, OAuth tokens, database URLs, or CI secret values. Use [39-credentials-secrets-api-key-boundary](39-credentials-secrets-api-key-boundary.md) for credential ownership, storage, rotation, and live side-effect authorization.

## Current Code Facts

### 1. Common `LLMClient` Is Stateless Across Provider Turns

`workspace/execution/llm_client.py` sends each common generation request as explicit `system_prompt` plus `user_prompt`. OpenAI and OpenAI-compatible providers use Chat Completions `messages`, Gemini uses `models.generate_content`, Anthropic uses Messages with top-level `system`, and Ollama uses the local client. The common path does not pass OpenAI `conversation`, `previous_response_id`, `auto_previous_response_id`, or an Agents SDK `Session`.

Operational conclusion: for common workspace LLM calls, continuation must be supplied by the caller through prompt text, retrieval context, product state, or a wrapper artifact. Do not assume provider-side conversation memory is active.

### 2. Local Response Cache Is Output Reuse, Not Conversation Memory

The common client stores `.tmp/llm_cache.db` rows keyed by providers, system prompt, user prompt, and temperature, with the generated `content` as value. This can return an old output for an exact repeated prompt family.

Operational conclusion: a cache hit proves exact-key reuse, not that a conversation was continued. Cache evidence belongs with pages 03, 26, and 27; conversation-state evidence belongs here.

### 3. Harness Sessions Track Call Identity, Budget, And Loop Patterns

`workspace/execution/harness_middleware.py` creates a per-run `session_id`, `request_id`, prompt hashes, budget counters, call logs, and loop fingerprints. It wraps `LLMClient`; it does not store provider message history or raw prompt bodies.

Operational conclusion: harness sessions are run-scoped observability/budget state. They are useful evidence, but they are not long-term memory unless a caller persists the call log under a retention policy.

### 4. LangGraph Uses Threaded Checkpoint State In One Workflow

`workspace/execution/graph_engine.py` compiles a LangGraph `StateGraph` with `checkpointer=self.checkpointer`, defaulting to `MemorySaver()`, and invokes with `config={"configurable": {"thread_id": thread_id}}`.

Operational conclusion: this is a graph workflow state surface, not the common LLM client state surface. If it becomes product-critical, the state artifact must record thread ID, checkpoint backend, and replay procedure.

### 5. `.ai` And `.tmp` Are Shared Agent Handoff State

This workspace intentionally uses `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/DECISIONS.md`, `.ai/SESSION_LOG.md`, `execution/session_orient.py --json`, and `.tmp/*current.json` artifacts as the continuation surface across Codex, Claude Code, and Gemini.

Operational conclusion: `.ai` and `.tmp` are app/operator state, not LLM memory. They can tell the next tool what is blocked and what evidence exists. They do not grant permission to stage, commit, push, revert, call `update_goal`, or retry external Supabase T-251.

## Official Boundaries

### OpenAI

OpenAI documents multiple state mechanisms. Responses can chain turns with `previous_response_id`; Conversations can persist conversation items; response objects have retention behavior; and all prior input tokens in a chained response are still billed as input tokens. The Agents SDK sessions guide also separates SDK-managed client-side session memory from OpenAI server-managed continuation and says not to combine sessions with `conversation_id`, `previous_response_id`, or `auto_previous_response_id` in the same run.

Repo implication: if a workflow adopts OpenAI Responses state, record `state_surface=openai_response_state`, the response/conversation ID policy, `store` behavior, billing expectation, and whether an SDK session was deliberately not used.

### Anthropic Claude

Anthropic Messages calls require the caller to send structured messages for the current request. Prompt caching can make repeated long prompts cheaper and faster, including multi-turn conversations, but caching is a prefix-processing optimization with TTL, exact-match constraints, and its own retention behavior.

Repo implication: Anthropic prompt caching is not durable application memory. Record cache strategy separately from the message-history source and the local artifact that rebuilt that history.

### Claude Code Memory

Claude Code documents `CLAUDE.md` and auto memory as cross-session context loaded into new sessions, while also noting that such files are context rather than hard enforcement. It treats `AGENTS.md` sharing as a way to make multiple coding agents read the same project instructions.

Repo implication: this repo's mirrored `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` and `.ai` relay files are durable instruction and handoff context. They still need deterministic gates for enforcement.

### LangGraph

LangGraph persistence saves graph state as checkpoints organized by threads. It also distinguishes checkpointed thread state from memory stores that can retain information across threads.

Repo implication: if a workflow uses LangGraph for agent state, `thread_id`, `checkpoint_id`, checkpointer backend, and memory-store namespace are app-owned state fields and must be preserved outside provider metadata.

### MCP

MCP servers expose tools, resources, and prompts as separate primitives. Tools are model-controlled actions, resources are application-controlled context, and prompts are user-controlled templates.

Repo implication: an MCP resource read or tool result is context/tool evidence, not durable memory, unless the host or product writes it to an explicit state store.

## A/B Operating Choice

| Choice | Upside | Risk | Repo decision |
|---|---|---|---|
| A. Rely on implicit provider conversation state | Minimal local plumbing | Not replayable locally, retention/billing can be unclear, IDs can expire | Reject as default |
| B. App-owned state artifact plus explicit provider state IDs | Auditable, replayable enough, compatible with dirty-handoff boundaries | More metadata to emit | Adopt |
| C. Store full transcripts for every run | Easiest debugging | High privacy/retention cost and noisy release evidence | Use only for classified debug runs |
| D. Treat vector/semantic memory as universal state | Powerful personalization | Hard to audit, easy to leak stale/private context | Defer until a workflow has scoped consent and deletion |
| E. Treat `.ai` handoff as authorization | Simple continuation | Confuses evidence with permission | Reject |

**Decision:** adopt B. Use explicit state artifacts and keep provider IDs, SDK sessions, LangGraph checkpoints, MCP context, `.ai` handoff, and product state as separate fields.

## Minimum State Artifact

For any workflow that depends on conversation history, memory, handoff, checkpointing, or deferred continuation, preserve these fields where practical:

| Field | Meaning |
|---|---|
| `workflow_id` | Stable workflow name, such as `llm_wiki.auto_research` or `blind_to_x.draft_review` |
| `state_surface` | `provider_conversation`, `provider_previous_response`, `sdk_session`, `langgraph_checkpoint`, `mcp_resource_snapshot`, `ai_handoff`, `tmp_evidence`, `product_db`, etc. |
| `state_owner` | `provider`, `sdk`, `repo`, `product_db`, `mcp_host`, or `operator` |
| `state_reference` | Redacted response ID, conversation ID, thread ID, checkpoint ID, session ID, resource URI, or artifact path |
| `api_surface` | Linkage to page 37: Responses, Chat Completions, Anthropic Messages, Gemini GenerateContent, etc. |
| `prompt_artifact_id` | Linkage to page 26 when prompt behavior matters |
| `generation_artifact_id` | Linkage to page 31 when replay parameters matter |
| `included_context_hash` | Hash of prior messages, summary, retrieved context, handoff excerpt, or resource snapshot |
| `history_policy` | `full_history`, `summary`, `last_n`, `retrieval`, `none`, or `unknown` |
| `compaction_policy` | How long history is compacted, summarized, or discarded |
| `retention_class` | Linkage to page 27: cache TTL, provider store, release evidence, product artifact, manual deletion |
| `privacy_class` | public, user-private, confidential, regulated, unknown |
| `mcp_context` | Resource URIs, prompt names, tool names, and whether tool outputs were persisted |
| `local_handoff_paths` | `.ai/*` and `.tmp/*` artifacts used to continue the run |
| `authorization_boundary` | What the artifact does not authorize, such as no stage/commit/push/T-251 retry |
| `last_verified` | Date the state contract and source docs were last checked |
| `replay_procedure` | Deterministic command or manual steps to rebuild the state for review |
| `next_action` | The next safe continuation step when the run resumes |

This artifact is metadata by default. Store full prompts, transcripts, resource bodies, or tool outputs only when the privacy boundary from page 27 allows it.

## Routing Rules

1. Before claiming a multi-turn run is reproducible, identify the state surface that carried prior context.
2. Do not mix OpenAI server-managed conversation state with Agents SDK sessions unless the SDK docs explicitly support the combination for that run.
3. For Anthropic, distinguish message history from prompt-cache hits. A cache hit is cost/latency evidence, not memory evidence.
4. For LangGraph, preserve `thread_id` and checkpoint backend when graph state affects output.
5. For MCP, record resources, tools, prompts, and persisted outputs separately.
6. For `.ai` handoff, record the dirty-tree signature and selector status when it changes. Keep handoff evidence separate from authorization.
7. For product workflows, product database state outranks LLM memory. The generated output should name the product record, cache, or artifact it read.
8. If context was summarized or compacted, preserve the summary hash and compaction policy. Do not claim full-history replay.
9. If state contains private or licensed source material, use hashes/redacted summaries unless full retention was approved.
10. If a state reference expires or is not locally readable, mark replay as partial and fall back to deterministic local evidence.

## Implementation Candidates

1. Add a small `state_artifact` helper beside the prompt and API-surface artifacts.
2. Start with the auto-research loop because it already has `.ai` handoff, `.tmp/*current.json`, selector status, dirty signatures, and no-stage/no-commit/no-push boundaries.
3. Extend Blind-to-X draft/review artifacts with `history_policy`, reviewer-memory hash, cache key, Notion/product row reference, and prompt-cache strategy.
4. Extend Shorts Maker run manifests with `state_surface=product_run_manifest`, resume checkpoint path, source research hash, prompt artifact, and media artifact retention class.
5. If OpenAI Responses state is adopted later, add a per-workflow migration checklist and tests before switching from Chat Completions.
6. If LangGraph graph state becomes release-critical, replace default in-memory checkpoints with a named persistent backend and record migrations/deletion rules.

## Pitfalls

- "The model remembered" is not evidence. Record the state carrier.
- Provider `previous_response_id` can make a local prompt artifact incomplete unless the referenced response is retained or summarized.
- Prompt caching lowers cost/latency; it does not prove durable memory.
- `.ai/HANDOFF.md` is a relay, not a hard control plane.
- `.tmp` evidence can be regenerated or deleted, so release evidence must name the command that rebuilds it.
- MCP tool results can include data not visible in `resources/list`; persist links or hashes when needed.
- Long-term memory can silently import stale preferences into a new run. Make memory scope and deletion visible.

## 출처

- Official: OpenAI API Docs, *Conversation state*: <https://developers.openai.com/api/docs/guides/conversation-state>
- Official: OpenAI Agents SDK, *Sessions*: <https://openai.github.io/openai-agents-python/sessions/>
- Official: Anthropic Claude API Reference, *Messages*: <https://platform.claude.com/docs/en/api/messages>
- Official: Anthropic Claude API Docs, *Prompt caching*: <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
- Official: Claude Code Docs, *How Claude remembers your project*: <https://code.claude.com/docs/en/memory>
- Primary docs: LangGraph, *Persistence*: <https://docs.langchain.com/oss/python/langgraph/persistence>
- Standard docs: Model Context Protocol, *Understanding MCP servers*: <https://modelcontextprotocol.io/docs/learn/server-concepts>
- Code evidence: `workspace/execution/llm_client.py`, `workspace/execution/harness_middleware.py`, `workspace/execution/graph_engine.py`, `execution/session_orient.py`, `execution/llm_wiki_objective_audit.py`, `.agents/skills/auto-research/scripts/dirty_worktree_handoff_plan.py`, `.agents/skills/auto-research/scripts/next_experiment_selector.py`.

*외부 자료 검증일: 2026-06-08 - Code verified against current HEAD.*
