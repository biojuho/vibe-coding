# 06 · 프로젝트별 LLM 라우터

> 같은 9-프로바이더 아이디어를 **세 곳이 서로 다르게** 구현한다. 함께 고쳐야 drift를 막는다.
> 인용은 2026-06-08 검증. 운영 SOP: [llm_fallback.md](../../../workspace/directives/llm_fallback.md).

## 3종 비교 요약

| 측면 | workspace `LLMClient` | shorts-maker-v2 `LLMRouter` | blind-to-x draft |
|------|----------------------|-----------------------------|------------------|
| 파일 | `workspace/execution/llm_client.py` | `projects/shorts-maker-v2/.../providers/llm_router.py` | `projects/blind-to-x/pipeline/draft_generator.py` (+`draft_providers.py`) |
| 동기/비동기 | **동기** (`time.sleep`) | 동기 | **비동기** (`async/await`) |
| fallback | 순차 | 순차 | 순차 (race 아님) |
| 프로바이더 | 9 (ollama 포함, mimo 없음) | 9 (**mimo 추가**, ollama 없음) | tracked config상 7개, 코드 helper상 5개 |
| 비용 추적 | ✅ api_calls(workspace.db) | ❌ 없음 | ✅ btx_costs.db (별도) |
| 프롬프트 캐시 | ✅ cache_strategy | ❌ 없음 | ✅ (anthropic) |
| 응답 캐시 | ✅ llm_cache.db 72h | ❌ | ❌ |
| 서킷 브레이커 | ❌ | ❌ | ✅ provider_failures |
| Best-of-N | ❌ | ❌ | ✅ (순차, 기본 1) |
| 언어 브릿지 | ✅ (직접 import) | ✅ (동적 import) | 자체 anthropic 캐싱 경로 |

세 곳이 **PROVIDER_ALIASES / DEFAULT_MODELS / base-URL 표를 각자 중복 보유**한다 → drift 위험. 예: Gemini default가 workspace `gemini-2.5-flash` vs shorts `gemini-3.1-flash-lite-preview`로 이미 갈라졌다. 새 프로바이더/모델 추가 시 3곳을 함께 본다.

---

## 1) workspace `LLMClient` (표준)

전체는 [01-architecture](01-architecture.md). 요점: 동기 순차 fallback, 비용효율 순 9개, 비용+캐싱+응답캐시+3싱크 로깅. 다른 두 곳의 기준점.

---

## 2) shorts-maker-v2 `LLMRouter`

루트 클라이언트의 **독립 포크**. self-contained(자체 PROVIDER_ALIASES/DEFAULT_MODELS/base-URL).

- **프로바이더 9개**: openai, google, anthropic, xai, deepseek, moonshot, zhipuai, groq, **mimo(Xiaomi)** — `mimo`를 추가하고 `ollama`는 없음 (llm_router.py:65–97).
- `DEFAULT_MODELS` (llm_router.py:87–97): google=`gemini-3.1-flash-lite-preview`(루트와 다름), mimo=`mimo-v2-flash`, base `https://api.xiaomimimo.com/v1`. 나머지는 루트와 동일.
- **설정**: `projects/shorts-maker-v2/config.yaml`의 `providers:` 블록 3키
  - `llm` (단일 default) = `openai` (L60)
  - `llm_providers` (fallback 순서) = `google → groq → mimo → deepseek → moonshot → zhipuai → openai → xai → anthropic` (L61–70)
  - `llm_models` (provider→model 맵) (L71–80)
  - `config.py`가 이를 `ProviderSettings`로 파싱(L387–408), `orchestrator.py`/`cli.py`가 `LLMRouter(providers=..., models=...)`로 주입.
- **fallback**: enabled 순서대로, provider당 max_retries=2, 백오프 `min(2**attempt,10)`s, NON_RETRYABLE 즉시 전환, JSON 파싱 실패는 같은 provider 재시도 (llm_router.py:346–394). 루트와 동일 형태.
- **차이**: 비용/사용량 추적 **없음**, 프롬프트 캐시 **없음**, 내장 기본 순서 **없음**(config 없으면 `['openai']`).
- **Gemini thinking_level**(minimal/low/medium/high) 지원 — google 분기에만 적용(llm_router.py:259–272).
- 브릿지: `language_bridge`를 5x parent `sys.path` fixup로 동적 import(llm_router.py:19–60). `mode=='off'`면 평문 경로 위임.

### 지뢰밭

- anthropic 분기 `max_tokens=2000` 하드코딩(llm_router.py:296) — 장문 스크립트 잘림 위험.
- `generate_json`의 사람용 에러 문자열은 7개 provider만 나열(GROQ/MIMO 누락, llm_router.py:339–341) — cosmetic이지만 실제 지원셋과 stale.
- `topic_validator.py`는 raw dict로 자체 `LLMRouter`를 만든다(L107–111) — orchestrator와 같은 모델/순서를 쓰는지 미검증.

---

## 3) blind-to-x async draft 생성

> 📌 **정정**: 과거 메모/브리프는 blind-to-x가 `asyncio.FIRST_COMPLETED` **멀티-프로바이더 레이스(~15s)**를 쓴다고 했으나, **현재 코드엔 그런 레이스가 없다.** 실제는 **비동기 순차 fallback + 서킷브레이커 + Best-of-N**이다. `FIRST_COMPLETED`/`as_completed`/15s 창은 코드 어디에도 없음(grep 무매치).
> Batch API, streaming, local async fallback, provider race의 운영 차이는 [24-batch-async-latency](24-batch-async-latency.md)에 따로 분리했다.

- **구조** (draft_generator.py): 바깥 `for provider in providers` → 안쪽 `for attempt in range(1, max_retries_per_provider+1)` 순차 루프, 첫 성공에 반환(L129–171, `_call_llm_with_fallback` L533–569). 유일한 async 동시성 프리미티브는 **단일** provider 코루틴을 감싸는 `asyncio.wait_for(coro, timeout=...)` (draft_providers.py:327).
- **설정** (`config.example.yaml`/`config.ci.yaml`): `strategy: "fallback"`, `providers = gemini → deepseek → xai → moonshot → zhipuai → openai → anthropic`, `max_retries_per_provider: 2`, `request_timeout_seconds: 45`. `config.example.yaml`은 `openai.enabled=false`, `config.ci.yaml`은 `openai.enabled=true`. 로컬 `projects/blind-to-x/config.yaml`은 비밀값을 담을 수 있어 wiki 기준 manifest에서 제외한다.
- **per-provider 타임아웃**(레이스 컷이 아니라 개별 데드라인): ollama 90s / anthropic·openai 45s / 기타 min(30,45)=30s (draft_providers.py:153–159).
- **서킷 브레이커**: 최근 비복구 실패 provider를 fallback 전에 스킵(`_available_providers_after_recent_failures` L94–108). 백오프 1/4/12/24/72h(cost_db.py:494–500).
- **Best-of-N**: fallback 위에 후보 N개 생성하되 **순차**(병렬/레이스 아님). 기본 1(draft_generator.py:114, 357–366).
- **비용**: 프로젝트 전용 `.tmp/btx_costs.db`(cost_db.py:25). anthropic 프롬프트 캐시 가중(write 1.25/2.0, read 0.10) 동일. 일일 예산 **$3**. `BTX_USAGE_FORWARD=1`일 때만 workspace로 미러([03-cost-caching](03-cost-caching.md)).
- **관측**: per-attempt 호출을 workspace Langfuse 후크로 위임(LANGFUSE_ENABLED 시).
- **litellm**: lockfile(1.60.0)에만 있고 **코드에서 import 안 함**.

### 지뢰밭 (중요)

- ⚠️ **tracked config는 `deepseek`/`moonshot`/`zhipuai`를 fallback 목록에 두지만**, `DraftProvidersMixin._enabled_providers`/PROVIDER_ALIASES는 anthropic/gemini/xai/openai/ollama만 배선한다(draft_providers.py:139–147) — **deepseek/moonshot/zhipuai async 클라이언트나 `_generate_with_deepseek`가 없다.** 즉 config provider 목록과 실제 생성 helper 목록이 다르다. T-1580부터 이 mismatch는 `config-facts.json`의 `blind_to_x_config_*_runtime_helpers` warning으로도 고정된다.
- 비동기라 동기 워크스페이스 클라이언트와 디버깅 방식이 다르다(stack trace가 코루틴 경유).

---

## 수렴/포크 방침

세 라우터가 의도적 포크인지 수렴 대상인지 **확정 ADR이 없다**. 중복된 alias/모델/base 표가 drift를 키우므로, 변경 시 [07-playbooks](07-playbooks.md)의 "프로바이더/모델 추가" 절차로 3곳을 함께 다룬다.

## 출처

- 코드/config 근거: `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/shorts-maker-v2/config.yaml`, `projects/blind-to-x/config.example.yaml`, `projects/blind-to-x/config.ci.yaml`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/blind-to-x/pipeline/cost_db.py`, `docs/wiki/llm/code-facts.json`, `docs/wiki/llm/config-facts.json` (2026-06-08 현재 HEAD).
- `https://api.xiaomimimo.com/v1`은 Shorts 라우터 코드에 박힌 base URL이다. 이 페이지는 MiMo 가격/한도/공식 모델 지원을 주장하지 않는다. 해당 provider를 실제 운영 1순위로 올리려면 [02-providers](02-providers.md)의 재검증 절차로 공식 문서와 live API를 별도 확인한다.

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
