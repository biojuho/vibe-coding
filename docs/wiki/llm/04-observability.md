# 04 · 관측 (Langfuse)

> LLM 호출 가시성(provider/model/cost/token/cache/failure)을 **Langfuse v3 셀프호스트**로 통합.
> Local-First(ADR-002)에 따라 Cloud가 아닌 로컬만 사용. 운영 SOP: [llm_observability_langfuse.md](../../../workspace/directives/llm_observability_langfuse.md). 데이터 보존·마스킹 경계는 [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md)에서 따로 다룬다.
> 인용은 `workspace/execution/llm_client.py` 기준, 2026-06-08 검증.

## 핵심 성질

- **opt-in, 기본 OFF**: `LANGFUSE_ENABLED=0`이 기본(.env.example L62). `=1`이고 `LANGFUSE_PUBLIC_KEY`+`LANGFUSE_SECRET_KEY`가 둘 다 있어야 동작.
- **꺼져 있으면 SDK import조차 안 함** (L188, L190–191) — 비활성 시 완전 no-op.
- **모든 실패는 silent drop**: SDK 미설치/네트워크/잘못된 키 → 예외 삼킴(L216–218). **관측이 LLM 호출을 막는 일은 없다.**
- **PII 제외**: 프롬프트 원문은 기본 trace 메타데이터에 넣지 않음(directive L58–59).

## 무엇을 기록하나

호출당 generation observation 1개 (`get_client().start_observation(as_type="generation")`, L196–215):
- provider, model, endpoint
- 토큰: input/output/total + `input_cache_creation`/`input_cache_read`
- cost_usd, caller_script + caller 메타데이터

`_emit_langfuse_trace`(L167–218)는 per-call 로깅 경로(L554)에서 호출된다. Langfuse는 **3개 싱크 중 하나**일 뿐 — 항상 켜지는 로컬 JSONL(`record_llm_call`)과는 별개([03-cost-caching](03-cost-caching.md) 참고).

## 켜는 법

```bash
# 1) 로컬 v3 스택 기동 (web/worker/Postgres17/ClickHouse/Redis7/MinIO, 포트는 127.0.0.1만)
docker compose -f infrastructure/langfuse/docker-compose.yml up -d
# 2) .env 설정
#    LANGFUSE_HOST=http://127.0.0.1:3030
#    LANGFUSE_PUBLIC_KEY=...  LANGFUSE_SECRET_KEY=...
# 3) preflight 통과 후 활성화
py -3.13 execution/langfuse_preflight.py     # exit 0 = 켜도 안전  (루트 execution/)
#    LANGFUSE_ENABLED=1
```

- UI 기본 호스트: 루프백 **포트 3030** (L195 setdefault).
- 운영 문서: `infrastructure/langfuse/README.md` (기동/키 발급/up·down·wipe/트러블슈팅).

## Preflight 5단계 (`langfuse_preflight.py`)

순서대로 검사, 첫 실패에서 중단(exit 0 안전 / 1·2 실패):

1. 키 존재
2. SDK 설치
3. compose 설정
4. health 엔드포인트
5. 실제 smoke trace (운영 후크 `_emit_langfuse_trace`를 그대로 사용, L206)

## 적용 범위

| 진입점 | 상태 |
|--------|------|
| 워크스페이스 `LLMClient` 동기 호출 | ✅ per-call trace |
| blind-to-x async draft 프로바이더 | ✅ 위임 후크 `_emit_workspace_langfuse_trace`(draft_providers.py L34–72), 성공/실패 모두 trace |
| shorts-maker-v2 `LLMRouter` async | ⏳ directive상 **Later** — 코드 배선 미확인 |

## 알려진 한계 (검증 필요)

- shorts `LLMRouter`의 observation은 아직 미배선 가능성.
- langfuse Python SDK 로컬 설치 여부는 preflight 2단계에서 검사 — 미설치면 `ENABLED=1`이어도 silent drop.
- smoke 단계는 비동기 flush라 즉시 UI 조회를 보장하진 않음.
- `LLMClient`를 우회해 프로바이더를 직접 호출하는 진입점은 trace에 안 잡힐 수 있음.
- blind-to-x 위임 후크는 `cost_usd`를 전달하지 않아 해당 trace의 비용 필드가 0일 수 있음.
- Langfuse 자체 retention은 `.tmp` 캐시 TTL과 별개다. 현재 trace는 metadata-only지만, prompt/response body를 추가하기 전에는 client-side masking과 project retention을 먼저 정해야 한다([27-data-retention-privacy-logging](27-data-retention-privacy-logging.md)).
