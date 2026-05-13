# REFACTOR.md — llm_client.py

> Internal refactor plan for `workspace/execution/llm_client.py`. Behavior-preserving only. **Do not rename public interfaces.**

## Target

`workspace/execution/llm_client.py` — 1199 lines. Central LLM fallback client used by ~14 production modules and 5 test files.

## Public API surface (frozen — no rename, no signature change)

### Module-level constants (imported by callers/tests)
- `PROVIDER_ALIASES`, `DEFAULT_PROVIDER_ORDER`, `DEFAULT_MODELS`
- `OPENAI_COMPATIBLE_BASE_URLS`, `API_KEY_ENV_VARS`, `NON_RETRYABLE_KEYWORDS`, `PRICING`

### Module-level functions
- `cache_cleanup(ttl_sec=259200) -> int`
- `get_default_client(**kwargs) -> LLMClient`
- `generate_json(*, system_prompt, user_prompt, temperature=0.7, providers=None, caller_script="", cache_strategy="off") -> dict`
- `generate_text(*, system_prompt, user_prompt, temperature=0.7, providers=None, caller_script="", cache_strategy="off") -> str`
- `generate_json_bridged(*, system_prompt, user_prompt, temperature=0.7, providers=None, caller_script="", policy=None) -> dict`
- `generate_text_bridged(*, system_prompt, user_prompt, temperature=0.7, providers=None, caller_script="", policy=None) -> str`
- `main() -> int`
- `_emit_langfuse_trace(...)` — under-prefixed but explicitly imported by `projects/blind-to-x/pipeline/draft_providers.py` and `workspace/tests/test_llm_client_langfuse.py`.

### Class
- `LLMClient.__init__(*, providers=None, models=None, max_retries=2, request_timeout_sec=120, track_usage=True, caller_script="", cache_ttl_sec=259200)`
- `LLMClient.enabled_providers()`, `LLMClient.all_provider_status()`
- `LLMClient.generate_json(*, system_prompt, user_prompt, temperature=0.7, cache_strategy="off")`
- `LLMClient.generate_text(*, system_prompt, user_prompt, temperature=0.7, cache_strategy="off")`
- `LLMClient.generate_json_bridged(*, system_prompt, user_prompt, temperature=0.7, policy=None)`
- `LLMClient.generate_text_bridged(*, system_prompt, user_prompt, temperature=0.7, policy=None)`
- `LLMClient.test_provider(provider)`, `LLMClient.test_all_providers()`

## External consumers (importers)

Production (callers must keep working):
- `workspace/execution/{confidence_verifier,graph_engine,harness_middleware,pr_self_review,reasoning_chain,reasoning_engine,smart_router,thought_decomposer,topic_auto_generator}.py`
- `projects/blind-to-x/pipeline/draft_providers.py`
- `infrastructure/n8n/bridge_server.py` (subprocess invoking `cache_cleanup`)

Tests:
- `workspace/tests/test_llm_client.py` (1360 lines — primary)
- `workspace/tests/test_llm_fallback_chain.py`
- `workspace/tests/test_llm_client_langfuse.py`
- `workspace/tests/test_llm_client_anthropic_cache.py`
- `workspace/tests/test_llm_bridge_integration.py`

## Identified duplication / simplification opportunities

1. **`generate_json` and `generate_text` share their provider/retry/cache loop** (~85 lines each, ~70% structural overlap). Differ only in:
   - JSON requires `_clean_json` + `json.loads` + `JSONDecodeError` branch
   - Cache encoding: JSON dumps the dict; text caches raw content
   - Log line texts ("JSON" vs "텍스트", "JSON 캐시 히트" vs "텍스트 캐시 히트")

2. **Inlined `cache_creation_multiplier`**: `2.0 if cache_strategy == "1h" else 1.25` is repeated in both `generate_json` and `generate_text`.

3. **Module-level convenience functions** (`generate_json`, `generate_text`, `generate_json_bridged`, `generate_text_bridged`) share the same client-resolution pattern:
   ```python
   client = (
       LLMClient(providers=providers, caller_script=caller_script)
       if providers
       else get_default_client(caller_script=caller_script)
   )
   ```

## Constraints

- **No rename** of public names (constants, functions, methods).
- **No signature change** on any of the listed public APIs.
- **No behavior change** in: cache hit/miss semantics, error messages text (tests assert on substrings), log message format, fallback ordering, retry timing, JSON cleaning, Langfuse trace timing.
- Module-level private helpers (`_cache_key`, `_cache_get`, `_cache_set`, `_emit_langfuse_trace`) are imported by tests/callers — preserve as-is.
- Internal `LLMClient._*` methods MAY change if they have no external importers (verified by grep below) and tests don't reach into them.

## Checkpoint plan

Each checkpoint: code change → run `workspace/tests/test_llm_client*.py` + `test_llm_fallback_chain.py` → only proceed on green.

1. **CP1 — multiplier helper.** Add `_cache_creation_multiplier(cache_strategy) -> float`. Replace the two inlined expressions. Tiny, pure.

2. **CP2 — module-level client resolution helper.** Add `_resolve_client(providers, caller_script) -> LLMClient`. Use in all 4 convenience functions.

3. **CP3 — extract `_run_simple_loop` for `generate_json` / `generate_text`.** Introduce a private method that runs the provider × retry loop with a per-mode parser+cache codec callable. Both public methods delegate to it. This is the largest change — gated by full test pass.

4. **CP4 — final verification.** Full test slice, ruff format/check, `code_review_gate`, graph rebuild.

## Out of scope

- Splitting `_generate_once` per-provider into separate functions (would change call patterns observable to tests via patches).
- Replacing `time.sleep` retry with structured backoff (would change retry timing — tests likely assert on it).
- Reworking Langfuse smoke or `_log_usage` (separate concerns, T-280 territory).
- Touching the bridged path beyond the multiplier helper (already well-decomposed).
- File-splitting into a package (`llm_client/` package) — would force every importer to update or require a shim.
