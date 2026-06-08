# 07 · 플레이북 (자주 하는 작업)

> "이걸 하려면 어디를 건드리나"를 단계로. 각 항목은 [01-architecture](01-architecture.md)~[06-per-project](06-per-project.md)를 전제로 한다.
> 모든 코드 위치는 2026-06-08 검증.

## A. LLM 기능을 새로 추가한다

단일 provider를 직접 호출하지 말고 **항상 라우터를 거친다**.

```python
from execution.llm_client import LLMClient          # workspace 내부
client = LLMClient(caller_script="my_feature")        # caller_script로 사용량 추적 라벨링
data = client.generate_json(system_prompt=SYS, user_prompt=usr)
```

- 한국어 출력이 중요한 자동화면 `generate_json_bridged` 사용([01-architecture](01-architecture.md) 언어 브릿지).
- shorts-maker-v2 안이면 `LLMRouter`, blind-to-x 안이면 기존 async draft 경로를 쓴다([06-per-project](06-per-project.md)).
- 비결정 출력을 원하면 응답 캐시 끄기: `LLMClient(cache_ttl_sec=0)`.

## B. 프로바이더 또는 모델을 추가한다

drift를 막으려면 관련 위치를 **모두** 본다([llm_fallback.md](../../../workspace/directives/llm_fallback.md) "새 프로바이더 추가 시"):

1. `.env`에 API 키 추가(키 env 이름은 [01-architecture](01-architecture.md) 표).
2. `workspace/execution/llm_client.py`: `PROVIDER_ALIASES`, `DEFAULT_PROVIDER_ORDER`, `DEFAULT_MODELS`, `API_KEY_ENV_VARS`, OpenAI 호환이면 `OPENAI_COMPATIBLE_BASE_URLS`, 비용 추적 원하면 `PRICING`.
3. 필요 시 `projects/shorts-maker-v2/.../llm_router.py` + `config.yaml`의 `providers.llm_providers`/`llm_models`.
4. blind-to-x면 `config.yaml`의 `llm.providers` + draft_providers의 async 클라이언트 배선(⚠️ 단순 config 추가만으론 안 돈다 — [06-per-project](06-per-project.md) 지뢰밭 참고).
5. `health_check.py`의 API 체크에 추가.
6. `py -3.13 workspace/execution/llm_client.py test --provider <new>`로 검증.
7. [02-providers](02-providers.md) 표와 이 위키 갱신.

## C. 노후 default 모델을 현행으로 이전한다

대상: `gpt-4o-mini`, `grok-3-mini-fast`, `deepseek-chat`, `moonshot-v1-8k`([02-providers](02-providers.md) 정비 권고).

1. [02-providers](02-providers.md)에서 권고 모델 확인(예: openai→`gpt-5.4-mini`, xai→`grok-4.3`, deepseek→`deepseek-v4-flash`).
2. **공식 페이지에서 현재 ID/가격 재확인**(웹) — 모델 ID는 수시로 바뀐다.
3. `DEFAULT_MODELS`(workspace)와 shorts `llm_models`, btx `config.yaml`을 함께 수정.
4. 비용 추적 정확도를 위해 `PRICING`(workspace, per-1K)과 btx `DEFAULT_TEXT_PRICING`(per-1M)도 갱신([03-cost-caching](03-cost-caching.md) 단위 차이 주의).
5. `llm_client.py test --provider <p>`로 새 모델 호출 확인.
6. promptfoo config의 provider/model 라벨도 영향받으면 갱신([05-eval](05-eval.md)).

> deepseek-chat은 **2026-07-24 폐기 예정**이라 시한이 있다.

## D. 비용을 줄인다

1. 기본 fallback 순서가 이미 비용효율 순 — 비싼 provider를 1순위로 강제하지 말 것.
2. 큰 재사용 system 프롬프트(≥1024토큰, 5분 내 ≥2회)는 `cache_strategy="5m"`([03-cost-caching](03-cost-caching.md)).
3. 동일 입력 반복 작업은 응답 캐시 활용(`cache_ttl_sec`).
4. 비실시간 대량은 Batch API(~50% 절감).
5. `alerts`를 cron으로: `py -3.13 workspace/execution/api_usage_tracker.py alerts` (cost spike/dead provider 조기 감지).
6. 사용량 확인: `py -3.13 workspace/execution/llm_usage_summary.py --by model`.

## E. 한국어 출력이 깨진다 (한자/모지바케/분해자모)

1. 해당 호출을 `generate_text_bridged`/`generate_json_bridged`로 전환.
2. 필요 시 `LLM_BRIDGE_MODE=enforce`로 승격(기본 shadow는 통과시키고 경고만)([01-architecture](01-architecture.md) 언어 브릿지).
3. 임계 조정: `LLM_BRIDGE_MIN_HANGUL_RATIO`, `LLM_BRIDGE_MAX_CJK_RATIO`.
4. DeepSeek가 자주 범인이면 `LLM_BRIDGE_FALLBACKS`로 우선순위 조정([deepseek_ko_bridge.md](../../../workspace/directives/deepseek_ko_bridge.md)).
5. 브랜드/고유명사가 한글 비율을 깎으면 `LLM_BRIDGE_ALLOWED_TERMS`로 마스킹.

See [34-language-bridge-locale-i18n-boundary](34-language-bridge-locale-i18n-boundary.md) when debugging whether the failure is provider instruction drift, BCP-47 locale metadata, product i18n bundle selection, bridge validation, or TTS voice locale.

## F. fallback이 자꾸 돈다 / 특정 provider가 죽었다

1. 키/순서 점검(호출 없이): `py -3.13 workspace/execution/llm_client.py status`.
2. 실제 연결: `py -3.13 workspace/execution/llm_client.py test`.
3. 이상 검출: `py -3.13 workspace/execution/api_usage_tracker.py alerts --expected-providers google,deepseek,openai` — fallback rate>50% / dead provider(14일) 보고.
4. provider별 fallback_rate/error_rate: `py -3.13 workspace/execution/llm_usage_summary.py --by provider`.
5. 흔한 원인: `credit balance is too low`/`unauthorized` 등 NON_RETRYABLE → 키/잔액 확인([01-architecture](01-architecture.md) fallback). blind-to-x면 서킷브레이커가 해당 provider를 1~72h 스킵 중일 수 있다([06-per-project](06-per-project.md)).

## G. JSON 파싱 실패 / 출력이 잘린다

- JSON 깨짐: OpenAI/Gemini는 네이티브 JSON 강제가 켜진다. Anthropic은 프롬프트 의존이라 깨지기 쉬움 → system 프롬프트에 "JSON object만" 명시(브릿지 json_mode가 자동 추가).
- **장문 잘림**: Anthropic 분기 `max_tokens=2000` 하드코딩(workspace L460, shorts L296). 2000 토큰 넘는 출력이 필요하면 Anthropic을 1순위에서 빼거나 코드 수정이 필요(공개 API로 오버라이드 불가) — [01-architecture](01-architecture.md) 지뢰밭.

## H. 관측을 켠다 (Langfuse)

[04-observability](04-observability.md)의 "켜는 법" 3단계 → `execution/langfuse_preflight.py` exit 0 확인 후 `LANGFUSE_ENABLED=1`. 끄면 완전 no-op.

## I. 품질 회귀를 평가한다 (promptfoo)

```bash
py -3.13 execution/run_eval_blind_to_x.py --dry-run    # 환경/데이터셋 점검
py -3.13 execution/run_eval_blind_to_x.py --quick      # 빠른 회귀
```

데이터셋이 없으면 먼저 Notion 추출(`blind_to_x_eval_extract.py`). 자세히는 [05-eval](05-eval.md).

## J. 이 위키/문서를 갱신한다

- 코드 변경(프로바이더·모델·가중치)은 해당 페이지의 file\:line·표를 즉시 갱신.
- 외부 가격/모델은 [02-providers](02-providers.md) "재검증 절차"로 분기별 갱신.
- 큰 사실 변경은 `.ai/SESSION_LOG.md` 기록, 노후 directive는 함께 정정([INDEX.md](../../../workspace/directives/INDEX.md)).
