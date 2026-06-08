# 11 · 추론 / 사고 (Reasoning · Thinking)

> "추론"에는 **두 가지 다른 것**이 섞여 있다 — 혼동 주의.
> **(A) 프로바이더 네이티브 사고**(모델이 답 전에 내부적으로 "생각"하는 thinking/reasoning 토큰)와 **(B) repo의 오케스트레이션 추론**(LLMClient 위에 올린 분해·검증·반증 파이프라인).
> 코드 사실은 2026-06-08 현재 HEAD 검증. 외부 API는 각 사 공식 문서(아래 §출처).
> 관련: [01-architecture](01-architecture.md), [06-per-project](06-per-project.md)(shorts thinking_level), [09-agent-harness](09-agent-harness.md).

## (A) 프로바이더 네이티브 사고 — 현황 (2026)

모델이 응답 전에 추가 "사고 토큰"을 써서 정확도를 높인다. **사고 토큰은 보통 출력 토큰으로 과금**되고 지연이 늘어난다(정확도↔비용/속도 트레이드오프).

| 프로바이더 | 파라미터 | 사고 토큰 가시성 | 비고 |
|-----------|----------|-----------------|------|
| **Anthropic** | (구) `thinking={type:"enabled", budget_tokens}` → **deprecated** | thinking 블록 노출 | **budget_tokens는 Opus 4.6 deprecated, Opus 4.7/4.8에서 제거 → adaptive thinking**(모델이 사고량 자동 결정). 명시 예산 API는 레거시 |
| **OpenAI** | Responses API `reasoning.effort` = none/minimal/low/medium/high/xhigh(모델별 지원) | **숨김**(원본 추론 토큰 미반환) | effort↑ = 정확/느림/비쌈 |
| **Google Gemini** | `thinking_config`(`thinking_level`, `include_thoughts`) | `include_thoughts`로 요약 노출 가능 | 사고 예산/레벨 제어 |
| **DeepSeek** | V4 **dual-mode**(thinking/non-thinking), reasoner는 자동 | reasoning_content 노출 | OpenAI ChatCompletions·Anthropic 양 API 지원 |

> 핵심: Anthropic 최신(Opus 4.7/4.8)은 **명시적 budget_tokens를 더 안 받는다**(adaptive). 옛 코드/문서의 `budget_tokens` 예시는 신모델에 안 통한다.

### 현 코드 실태 (검증)

- **표준 `LLMClient`는 reasoning 파라미터를 노출하지 않는다.** `generate_json(system_prompt, user_prompt, temperature, cache_strategy)` 시그니처에 `reasoning.effort`/`thinking`류가 없다([01-architecture](01-architecture.md)). → 추론모델을 골라도 **기본 사고 설정으로 무제어** 실행된다.
- **유일한 부분 배선**: shorts-maker-v2 `LLMRouter`의 **Gemini `thinking_level`**(minimal/low/medium/high, google 분기 전용, [06-per-project](06-per-project.md) llm_router.py:259–272).
- 비용 추적(`PRICING`, [03-cost-caching](03-cost-caching.md))은 사고 토큰을 **별도 계상하지 않는다** — reasoning 모델을 쓰면 출력 토큰이 부풀어 예상보다 비쌀 수 있다.

> 즉 이 repo는 provider-native 사고를 **거의 안 쓴다**. 대신 아래 (B) 오케스트레이션으로 "추론 품질"을 확보한다.

## (B) repo의 오케스트레이션 추론 스택 (`local_inference.md`)

`LLMClient` **위에** 올린 **모델-무관** 추론 패턴들. 어떤 프로바이더든(특히 로컬 Ollama) 쓸 수 있다. 도메인은 주로 로컬 추론 + 콘텐츠 패턴 학습.

| 모듈 | 패턴 | 한 줄 | file |
|------|------|-------|------|
| `smart_router.py` | 복잡도 라우팅 | 프롬프트 복잡도(SIMPLE/MODERATE/COMPLEX)를 **결정론적 키워드**로 분류 → 로컬(무료) vs 클라우드(정확) 동적 선택 | `SmartRouter.route` |
| `thought_decomposer.py` | **Forest-of-Thought** | 복잡 요청을 독립 서브태스크 트리로 분해 → 각각 독립 LLM 호출 → bottom-up 합성. **"context rot"(긴 컨텍스트 추론 저하) 방지** | `ThoughtDecomposer(llm_client).solve()` |
| `confidence_verifier.py` | **SAGE** | LLM이 자기 답변 confidence(0~1) 자기평가 + self-critique(반론 생성) → **높으면 조기 종료**(overthinking·토큰 낭비 방지) | `ConfidenceVerifier(llm_client)` |
| `reasoning_engine.py` | **Popper 반증주의** | 사실 추출 → 가설 생성(기존 패턴 교차) → **반증 시도**, 생존 가설만 패턴 승격(귀납 학습) | `ReasoningAdapter.run_full_reasoning` |
| `reasoning_chain.py` | 체인 오케스트레이션 | 위 단계들을 묶는 파이프라인(directive 참조) | — |

- 전부 `LLMClient`를 주입받아 동작 → fallback/비용/캐싱([01](01-architecture.md)/[03](03-cost-caching.md))을 그대로 상속.
- 설계 의도: **로컬 모델의 약한 단발 추론을, 분해·검증·반증으로 보강**해 클라우드 의존을 줄인다([02-providers](02-providers.md) Ollama 현실 참고 — 이 PC는 무거운 로컬 모델이 안 돎).
- 로컬 추론을 실제 릴리스 근거로 쓰려면 [35-local-inference-hardware-quantization-boundary](35-local-inference-hardware-quantization-boundary.md)의 서버/model/quantization/hardware/fallback artifact가 먼저 필요하다.

## A/B — 네이티브 사고 vs 오케스트레이션 추론

| 측면 | **A. 프로바이더 네이티브 사고** | **B. 오케스트레이션(분해/검증/반증)** |
|------|-------------------------------|----------------------------------|
| 구현 | API 파라미터 1개 | 다단계 코드 파이프라인(이미 존재) |
| 모델 의존 | 추론 지원 모델 필요 | **모델 무관**(로컬 포함) |
| 비용 | 사고 토큰=출력 과금(↑) | 다중 호출(↑) but 저가/로컬 가능 |
| 가시성 | 대개 숨김(OpenAI) | **완전 가시**(각 단계 로깅) |
| 제어 | effort/level 다이얼 | 분해 깊이·confidence 임계 등 세밀 |
| 적합 | 단일 모델의 강한 추론이 필요할 때 | 로컬·저가 모델로 품질 끌어올릴 때, 투명성 필요할 때 |

**권장(이 프로젝트):**
- **콘텐츠 생성(topic/draft/script)**: 대부분 추론 불필요 → 네이티브 사고는 **none/minimal/low**, 오케스트레이션도 불필요. 비용·속도 우선.
- **분석/디버깅/설계**(error_analyzer·code_improver 등 [12-llm-features](12-llm-features.md)): 클라우드 모델이면 **reasoning effort medium~high**가 효과적이나 **현재 LLMClient가 노출 안 함** → 필요하면 노출 추가가 선결.
- **로컬 우선·투명성 필요**: **B(오케스트레이션)** — thought_decomposer로 분해 + confidence_verifier로 조기종료가 로컬 모델 한계를 보완.
- 둘은 **결합 가능**: 네이티브 사고 모델을 thought_decomposer의 서브태스크 솔버로 써도 된다.

## 사고 강도 ↔ 작업 매핑 (일반 지침)

| effort/사고 | 비용·지연 | 적합 작업 |
|-------------|-----------|-----------|
| none/minimal | 최저 | 분류·라우팅·짧은 요약·CRUD 카피 |
| low | 낮음 | 일반 콘텐츠 생성, 단순 변환 |
| medium | 중간 | 일반 문제해결, 리서치, 멀티스텝 |
| high/xhigh | 높음 | 복잡 수학·논리·아키텍처 설계·심층 디버깅 |

> 콘텐츠 자동화의 대다수는 low 이하로 충분하다. high는 **소수 고난도**에만 — 안 그러면 비용/지연만 늘고 품질 이득은 작다.

## 지뢰밭

- **두 "추론"을 혼동 말 것**: 네이티브 thinking 토큰(A) ≠ repo 오케스트레이션(B).
- Anthropic **budget_tokens는 신모델(Opus 4.7/4.8)에서 제거**됨 → adaptive. 옛 예시 복붙 금지.
- 표준 `LLMClient`엔 reasoning 다이얼이 **없다** → 추론모델을 써도 무제어. 비용 추적도 사고 토큰을 분리 계상 안 함.
- OpenAI는 추론 토큰을 **반환하지 않는다** → 디버깅 시 "왜 비싼지"가 안 보일 수 있음(usage의 reasoning_tokens 필드만 참고).
- 오케스트레이션(B)은 호출 수가 곱으로 늘 수 있음 → `thought_decomposer` 분해 깊이/`confidence_verifier` 임계로 폭주 제어.

## 출처 (1차 우선, 2026-06-08 확인)

- Anthropic, *Extended/adaptive thinking*: <https://platform.claude.com/docs/en/build-with-claude/extended-thinking>
- OpenAI, *Reasoning* (`reasoning.effort`): <https://developers.openai.com/api/docs/guides/reasoning>
- Google, *Gemini thinking*: <https://ai.google.dev/gemini-api/docs/thinking>
- DeepSeek, *V4 dual-mode(thinking/non-thinking)*: <https://api-docs.deepseek.com/> · V4 공지 <https://api-docs.deepseek.com/news/news260424>
- 코드 근거: `workspace/execution/{smart_router,thought_decomposer,confidence_verifier,reasoning_engine}.py`, `projects/shorts-maker-v2/.../llm_router.py` (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
