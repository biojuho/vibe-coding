# 01 · LLM 아키텍처

> 워크스페이스 통합 클라이언트 `execution.llm_client.LLMClient`의 구조.
> 모든 인용은 `workspace/execution/llm_client.py` (별도 표기 없으면) 기준, 2026-06-08 검증.

## 전체 그림

```
호출자 (execution/*.py, 파이프라인)
   │  generate_json / generate_text  (+ *_bridged 변형)
   ▼
LLMClient._run_simple_loop  ──▶ [로컬 응답 캐시 조회: .tmp/llm_cache.db, 72h]  (hit이면 즉시 반환)
   │  enabled_providers() 순서대로
   ▼
provider 1 ─(실패/재시도 max_retries)─▶ provider 2 ─▶ … ─▶ provider N
   │  성공
   ▼
_generate_once → 5-tuple (content, in_tok, out_tok, cache_creation, cache_read)
   │
   ├─▶ 로컬 응답 캐시 저장
   └─▶ _log_usage ──┬─▶ SQLite  api_calls (.tmp/workspace.db)   [api_usage_tracker]
                    ├─▶ JSONL   .tmp/llm_metrics/llm_calls_*.jsonl [llm_metrics]
                    └─▶ Langfuse trace (opt-in, LANGFUSE_ENABLED=1)
```

## 9개 프로바이더 (비용효율 순)

> ⚠️ `llm_client.py`의 모듈 docstring(L1–14)은 아직 **"7개 프로바이더"**라고 적혀 있다(stale). 코드 상수는 **9개**다 — Ollama·Groq가 나중에 추가됐다. 위키와 코드 기준은 **9개**.

`DEFAULT_PROVIDER_ORDER` (L90–100): 무료/로컬 → 저가 → 고가

```text
ollama → google → groq → deepseek → moonshot → zhipuai → openai → xai → anthropic
```

`DEFAULT_MODELS` (L102–112):

| provider | 기본 모델 | API 키 env (L125–135) | base/SDK |
|----------|-----------|------------------------|----------|
| ollama | `qwen3-coder:30b-a3b-q4_K_M` | `OLLAMA_BASE_URL` (키 불필요) | 로컬 11434 |
| google | `gemini-2.5-flash` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | google-genai SDK |
| groq | `llama-3.3-70b-versatile` | `GROQ_API_KEY` | OpenAI 호환 |
| deepseek | `deepseek-chat` | `DEEPSEEK_API_KEY` | OpenAI 호환 |
| moonshot | `moonshot-v1-8k` | `MOONSHOT_API_KEY` | OpenAI 호환 |
| zhipuai | `glm-4-flash` | `ZHIPUAI_API_KEY` | OpenAI 호환 |
| openai | `gpt-4o-mini` | `OPENAI_API_KEY` | OpenAI SDK |
| xai | `grok-3-mini-fast` | `XAI_API_KEY` / `GROK_API_KEY` | OpenAI 호환 |
| anthropic | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` | anthropic SDK |

- `OPENAI_COMPATIBLE_BASE_URLS` (L115–121): xai·deepseek·moonshot·zhipuai·groq는 OpenAI SDK + `base_url` 교체만으로 동작.
- `PROVIDER_ALIASES` (L66–87): `gemini→google`, `claude→anthropic`, `kimi→moonshot`, `glm/zhipu→zhipuai`, `llama→groq`, `local/qwen→ollama` 등.
- **키 없는 프로바이더는 자동 스킵**: `enabled_providers()`가 키(또는 `OLLAMA_BASE_URL`)가 있는 것만 시도 순서로 남긴다(L324–326).
- 노후 default 모델(`gpt-4o-mini`, `grok-3-mini-fast`, `deepseek-chat`, `moonshot-v1-8k`) 정비 권고는 [02-providers](02-providers.md) 참고.

> **이 워크스테이션의 실제 동작**: ollama default(`qwen3-coder:30b-a3b`)는 22GB+ VRAM이 필요한데 이 PC는 Intel Iris Xe iGPU/RAM 15.75GB라 사실상 ollama가 비활성이다. 따라서 실제 1순위는 **Gemini**가 된다. ollama를 쓰려면 `OLLAMA_DEFAULT_MODEL=gemma3:4b` 등 가벼운 모델로 내려야 한다([local_inference.md](../../../workspace/directives/local_inference.md)).

## Fallback 동작 (L614–684)

1. `enabled_providers()` 순서대로 시도. 비활성 프로바이더면 처음부터 `RuntimeError`(키 없음 메시지).
2. 각 프로바이더당 `max_retries`회 시도(기본 **2**, L288). 재시도 간 백오프 `min(2**attempt, 10)`초 (L678–680).
3. `json.JSONDecodeError`는 **같은 프로바이더에서 재시도** (출력이 JSON이 아닐 때).
4. `NON_RETRYABLE_KEYWORDS`(invalid api key/unauthorized/insufficient_quota/`credit balance is too low`/billing…, L137–146)에 걸리면 **즉시 다음 프로바이더로** 전환(재시도 안 함).
5. 모든 프로바이더 소진 시 누적 에러와 함께 `RuntimeError`.

기타:
- `request_timeout_sec`(기본 120, L289)는 **OpenAI/OpenAI-호환 클라이언트에만** 전달된다. Anthropic·Google SDK 생성자에는 timeout이 명시되지 않는다(알려진 비대칭, L360–380).
- Anthropic 분기는 `max_tokens=2000` **하드코딩**(L460) — 장문 출력은 잘릴 수 있다. 공개 API로 오버라이드 불가([플레이북](07-playbooks.md)의 주의 참고).

## 공개 API 표면

| 함수 | 반환 | 비고 |
|------|------|------|
| `generate_json(system_prompt, user_prompt, temperature=0.7, cache_strategy="off")` | `dict` | OpenAI는 `response_format=json_object`, Gemini는 `response_mime_type=application/json`로 네이티브 강제. 마크다운 펜스 제거 후 `json.loads` (L686–701) |
| `generate_text(...)` | `str` | L721 |
| `generate_json_bridged` / `generate_text_bridged` | dict/str | 언어 브릿지 검증+수정 루프. `mode=="off"`면 평문 경로로 위임 (L953–999) |
| 모듈 함수 `generate_json` / `generate_text` | dict/str | 싱글톤 클라이언트 재사용; `providers=` 지정 시 즉석 생성. **메서드와 달리 `provider` 오버라이드 가능** (L1040–1091) |

> 공개 메서드는 `cache_strategy`만 노출하고 `max_tokens`·`model`·per-call provider 오버라이드는 노출하지 않는다. 모델/순서 변경은 `LLMClient(models=..., providers=...)` 생성자로 한다.

## 언어 브릿지 계층 (`execution/language_bridge.py`)

이종 프로바이더(특히 DeepSeek은 한국어 프롬프트에 중국어/혼합 출력을 내는 경향)에서 **결정론적 한국어 + 스키마 유효 JSON**을 보장하는 순수 함수 정책 계층. HTTP/모델 상태 없음. `LLMClient`가 이 함수들을 import해 호출한다(L46–57).

`BridgePolicy` 기본값 (language_bridge.py L35–47):

| 필드 | 기본 | 의미 |
|------|------|------|
| `target_language` | `ko-KR` | 목표 언어 |
| `mode` | `shadow` | `off`/`shadow`/`enforce`. 그 외 값은 `shadow`로 강등 (L61–63) |
| `repair_attempts` | `1` | 프로바이더당 자가수정 재시도 |
| `fallback_providers` | `('deepseek','google','openai')` | 브릿지 우선순위 |
| `strict_korean` / `min_hangul_ratio` | `True` / `0.75` | 한글 비율 하한 |
| `max_cjk_ratio` / `max_jamo_ratio` | `0.02` / `0.05` | 한자/분해자모 상한 |

- 동작: `build_bridge_system_prompt`가 한국어 규칙 5–6개를 원 system 프롬프트 앞에 덧붙임 → 응답을 `validate_text_content`/`validate_json_payload`로 검사(`empty_content`/`mojibake`/`low_hangul_ratio`/`mixed_language`/`decomposed_jamo`/`json_parse_error`) → 실패 시 `build_repair_messages`로 **온도 0.2 고정** 재생성(llm_client L927).
- `language_score = clamp(hangul_ratio − cjk_ratio*3 − jamo_ratio*2, 0..1)` (language_bridge L226).
- **shadow vs enforce**: `shadow`(기본)는 파싱만 되면 통과시키고 경고만 로깅, `enforce`는 정책 통과해야만 수락(L872–898). 운영 기본은 shadow.
- env 오버라이드: `LLM_BRIDGE_MODE`, `LLM_BRIDGE_MIN_HANGUL_RATIO`, `LLM_BRIDGE_FALLBACKS` 등 (L49–76).
- 자세한 배경: [deepseek_ko_bridge.md](../../../workspace/directives/deepseek_ko_bridge.md).

## 2종 캐시 (혼동 주의)

이름은 둘 다 "캐시"지만 완전히 다른 것이다. → 자세히는 [03-cost-caching](03-cost-caching.md).

| | 로컬 응답 캐시 | Anthropic 프롬프트 캐시 |
|---|---|---|
| 무엇 | 동일 프롬프트 재호출 시 **저장된 응답** 반환 | Anthropic 서버의 system 블록 토큰 캐싱(비용 절감) |
| 위치 | `.tmp/llm_cache.db` (sha256 키, L221–249) | API 파라미터 `cache_control` (L463–475) |
| 제어 | `cache_ttl_sec`(기본 72h, `0`이면 비활성) | `cache_strategy="off"|"5m"|"1h"` |
| 적용 | 전 프로바이더 | **Anthropic 전용** (나머지 8개는 무시) |

## 로깅 싱크 3종 (`_log_usage`, L487–565)

모두 **예외를 삼켜** LLM 호출을 절대 막지 않는다.

1. **SQLite** `api_calls`(`.tmp/workspace.db`) — provider/model/tokens/cost_usd/caller/bridge 메타 + cache 토큰 컬럼.
2. **JSONL** `.tmp/llm_metrics/llm_calls_YYYY-MM-DD.jsonl` (`llm_metrics.record_llm_call`).
3. **Langfuse** trace — `LANGFUSE_ENABLED=1` + 키 있을 때만.

`llm_usage_summary.py`가 1·2를 병합(1초 단위 dedup, JSONL 우선)해 provider/model/caller별 cost·cache_hit_ratio·fallback_rate·error_rate·p95 latency를 리포트한다.

## CLI (L1131–1177)

```bash
py -3.13 workspace/execution/llm_client.py test               # 전 프로바이더 실제 호출 테스트 (✅/❌/⏭️)
py -3.13 workspace/execution/llm_client.py test --provider deepseek
py -3.13 workspace/execution/llm_client.py status             # API 호출 없이 키/모델/순서
```

## 알려진 비대칭/지뢰밭

- docstring "7개" ↔ 코드 "9개" (위 참고).
- Anthropic `max_tokens=2000` 하드코딩(장문 잘림 위험).
- Anthropic/Google에는 `request_timeout_sec` 미전달.
- 워크스페이스 `LLMClient`와 shorts `LLMRouter`가 **PROVIDER_ALIASES/DEFAULT_MODELS를 각자 중복 보유** → drift 위험(예: Gemini default가 2.5 vs 3.1로 이미 갈림). → [06-per-project](06-per-project.md).
