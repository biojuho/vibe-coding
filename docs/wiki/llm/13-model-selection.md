# 13 · 모델 선택 가이드 · 폐기 캘린더

> [02-providers](02-providers.md)가 **레퍼런스 데이터**라면, 이 페이지는 그 위의 **행동 레이어**다 — "이 작업엔 어떤 모델", "언제까지 무엇을 갈아야 하나".
> 가격/한도 세부는 [02-providers](02-providers.md). 외부 폐기 일정은 2026-06-08 공식/1차 확인(아래 §출처). 불확실은 **불확실**로 표기(환각 금지).
> 관련: [01-architecture](01-architecture.md)(DEFAULT_MODELS), [07-playbooks](07-playbooks.md) C(이전 절차), [11-reasoning-models](11-reasoning-models.md), [30-fine-tuning-custom-model-boundary](30-fine-tuning-custom-model-boundary.md).

Fine-tuned/custom model ID를 도입하는 경우는 단순 모델 교체가 아니라 훈련 데이터, holdout eval, retention, base-model deprecation, rollback ID가 필요한 모델 lifecycle 변경으로 취급한다.

Sampling/output parameter changes are a separate release surface from model ID changes. When `temperature`, `top_p`/`topK`, max-token caps, seed, retry/fallback, or cache behavior changes, use [31-generation-parameters-reproducibility](31-generation-parameters-reproducibility.md) instead of treating the change as a model-selection-only update.

Local model selection is also a separate runtime-fit surface. When choosing Ollama or a quantized local tag, use [35-local-inference-hardware-quantization-boundary](35-local-inference-hardware-quantization-boundary.md) to prove server availability, installed tag, memory/context fit, quantization level, and fallback behavior.

## 폐기·노후화 캘린더 (날짜순) — 시급도 순

| 일정 | 대상 | 상태/근거 | repo 영향 | 권장 |
|------|------|-----------|-----------|------|
| **2026-02-13 경과** | OpenAI `gpt-4o`·`gpt-4.1`·`gpt-4.1 mini`·`o4-mini` | **ChatGPT retirement**. 공식 공지는 "API 변경 없음" 명시 | repo 직접 영향 없음 | API 폐기로 오해하지 말 것 |
| **미공시/노후화 위험** | OpenAI **`gpt-4o-mini`** | 직접 `api.openai.com` 폐기일은 공식 deprecations에 없음. 다만 repo default/promptfoo에 오래 핀 모델 | openai default + promptfoo config 둘 다 핀 | 과금/품질 영향 확인 후 `gpt-5.4-mini`/`gpt-5.4-nano`로 계획 이전 |
| **2026-06-01 경과** | Google `gemini-2.0-flash` | 종료(02-providers) | repo default는 2.5라 영향 적음 | 2.5 유지 |
| **2026-07-24 15:59 UTC** | DeepSeek `deepseek-chat` 별칭 | 폐기 예정(공식) | deepseek default(단 async 미배선, [06](06-per-project.md)) | `deepseek-v4-flash`로 이전 |
| 신모델 전환 | Anthropic `budget_tokens` 사고 | Opus 4.6 deprecated / 4.7·4.8 **제거**(adaptive) | repo는 미사용 | 옛 예시 금지([11](11-reasoning-models.md)) |
| 상시(별칭화) | xAI `grok-3-mini-fast` | 독립 문서 소멸 → grok-4.3 resolve 추정 | xai default | `grok-4.3` 명시 핀 |
| 구세대(서비스중) | Moonshot `moonshot-v1-8k` | 폐기일 미공시 | moonshot default | `kimi-k2.5/k2.6` 고려 |

> **가장 명확한 날짜 리스크 = `deepseek-chat` 2026-07-24.** `gpt-4o-mini`는 직접 API 폐기일이 미공시라 "즉시 장애"로 쓰면 안 된다. 다만 오래 핀 default라 모델 선택/가격/품질 재검증을 거쳐 이전 후보로 유지한다.

## 이 repo가 핀한 노후 모델 — 한눈에

`DEFAULT_MODELS`([01-architecture](01-architecture.md)) + 평가 config([05-eval](05-eval.md))에 박힌 노후 ID:

| 위치 | 노후 ID | 갈 곳 |
|------|---------|-------|
| `llm_client.py` DEFAULT_MODELS openai | `gpt-4o-mini` | `gpt-5.4-mini`(균형) / `gpt-5.4-nano`(최저가), 공식 deprecations 재확인 후 |
| `llm_client.py` xai | `grok-3-mini-fast` | `grok-4.3` |
| `llm_client.py` deepseek | `deepseek-chat` | `deepseek-v4-flash` (시한 2026-07-24) |
| `llm_client.py` moonshot | `moonshot-v1-8k` | `kimi-k2.5`(선택) |
| `tests/eval/blind-to-x/promptfooconfig.yaml` | `openai:chat:gpt-4o-mini`, `deepseek:deepseek-chat` | 동반 갱신([05-eval](05-eval.md)) |

> 이전은 [07-playbooks](07-playbooks.md) C 절차로 **`LLMClient`/shorts `llm_models`/btx config 3곳 + `PRICING` + promptfoo**를 함께. 코드 변경은 별도 태스크(이 위키는 문서 전용).

## 작업 → 모델 선택 가이드

비용효율 fallback이 기본이지만, **특정 작업에 1순위를 명시 지정**할 때의 가이드. 단가는 [02-providers](02-providers.md) 기준(per 1M, USD 별도표기).

| 작업 유형 | 권장 1순위 | 이유 | 대안 |
|-----------|-----------|------|------|
| 분류·라우팅·짧은 추출 | `groq llama-3.1-8b-instant` ($0.05/$0.08) | 최저가·최속(~수백 TPS) | `gemini-2.5-flash-lite` |
| **일반 한국어 콘텐츠 생성** | `gemini-2.5-flash` (repo default) | 가성비+한국어 안정+무료tier | `glm-4.5-flash`(무료) |
| 비용 0 강제(품질 양보) | `glm-4.x-flash`(무료) / Gemini free tier | 과금 없음 | ollama(로컬, 단 이 PC 제약 [02](02-providers.md)) |
| 고난도 추론·디버깅·설계 | `claude-sonnet-4-6` ($3/$15, 1M) | 강한 추론+1M ctx | `gpt-5.4` / `gemini-2.5-pro` / `deepseek-v4-pro` |
| 최상위 품질(소수 고가치) | `claude-opus-4-8` ($5/$25) | 최상위 | `gpt-5.5` |
| 초장문 컨텍스트(≥200k) | `claude-sonnet-4-6`(1M, 추가요금 없음) | 롱컨텍스트 표준단가 | `gpt-5.4`(1M) / `deepseek-v4`(1M) |
| 코딩 에이전트(저가) | `grok-build-0.1` ($1/$2, 256k) | 저가 코딩 특화 | `groq gpt-oss-120b` |
| 로컬 임베딩/RAG | `ollama embeddinggemma:300m` | CPU 가능, 무료 | [35](35-local-inference-hardware-quantization-boundary.md) 기준으로 model/server evidence 필요 |

### 비용 의식 선택 원칙

1. **기본 fallback 순서를 신뢰**하라 — 이미 무료/저가→고가 순([01](01-architecture.md)). 비싼 걸 1순위로 강제하지 말 것.
2. 작업의 **80%는 flash급으로 충분**하다. opus/gpt-5.5는 *측정된* 품질 이득이 있을 때만.
3. **무료 모델**(glm-4.x-flash, gemini free, groq 무료tier)을 먼저 시도 — 콘텐츠 자동화 다수가 여기서 해결된다.
4. 추론모델은 사고 토큰이 출력으로 과금([11](11-reasoning-models.md)) — effort를 작업에 맞춰 낮춰라.
5. 큰 재사용 system 프롬프트는 캐싱([03](03-cost-caching.md)).

## 지뢰밭

- **`gpt-4o-mini`는 "폐기 확정"이 아니라 "노후화/재검증 필요"** — 직접 API deprecations에 없으면 장애 확정처럼 기록하지 말 것.
- ChatGPT 은퇴 공지 ≠ API 폐기 공지. repo는 **직접 API**(`api.openai.com`)다 — ChatGPT/Azure/Foundry 날짜를 그대로 적용 말 것.
- `deepseek-chat`은 **2026-07-24 시한**이 명확 — 달력에 박아둘 것.
- 모델 ID는 수시로 바뀐다 — 이전 전 **공식 페이지 재확인**([02](02-providers.md) 재검증 절차).
- 선택을 1순위로 강제하면 그 provider 장애 시 fallback이 의도와 달라질 수 있다 — 가능하면 순서만 조정.

## 출처 (1차 우선, 2026-06-08 확인)

- OpenAI, *Retiring GPT-4o and older models in ChatGPT* (공식 문구상 API 변경 없음): <https://openai.com/index/retiring-gpt-4o-and-older-models/> · 직접 API Deprecations: <https://developers.openai.com/api/docs/deprecations>
- `gpt-4o-mini` 직접 API 폐기일은 2026-06-08 기준 공식 deprecations에서 미확인. Azure/Foundry 일정은 별도 플랫폼 일정이므로 직접 API에 그대로 적용 금지.
- DeepSeek `deepseek-chat` 2026-07-24 폐기·Anthropic adaptive thinking·기타: [02-providers](02-providers.md)/[11-reasoning-models](11-reasoning-models.md)의 공식 출처
- 코드 근거: `workspace/execution/llm_client.py` DEFAULT_MODELS, `tests/eval/blind-to-x/promptfooconfig.yaml` (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
