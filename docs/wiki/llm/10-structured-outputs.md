# 10 · 구조화 출력 (JSON / 스키마 강제)

> 이 프로젝트의 거의 모든 LLM 산출물(topic·draft·script)은 **JSON**이다. 그래서 "JSON을 얼마나 강하게 강제하느냐"가 신뢰성의 핵심이다.
> 코드 사실은 `workspace/execution/llm_client.py` 기준 2026-06-08 현재 HEAD 검증. 외부 API는 각 사 공식 문서로 확인(아래 §출처).
> 관련: [01-architecture](01-architecture.md)(generate_json), [09-agent-harness](09-agent-harness.md)(generator-evaluator), [05-eval](05-eval.md).

## 한 줄 요약

이 repo는 **세 단계 중 가장 약한 tier**(구문만 보장 또는 프롬프트 의존)를 **모든 프로바이더에 일괄** 적용한다. 스키마를 강제하는 최신 tier(OpenAI `json_schema` strict, Gemini `responseSchema`, Anthropic tool-use/Structured Outputs)는 **쓰지 않는다.** 이는 9-프로바이더 fallback의 "최소공통분모" 전략으로 **합리적 측면이 있고**, 동시에 JSON 파싱 실패의 근본 원인이기도 하다.

## 구조화 출력의 3단계 강도

| tier | 보장 | 메커니즘 |
|------|------|----------|
| **0. 프롬프트 의존** | 없음(설득) | system 프롬프트에 "JSON만 출력" |
| **1. 구문 JSON** | 유효 JSON **구문**(스키마는 자유) | OpenAI `json_object`, Gemini `responseMimeType` |
| **2. 스키마 강제** | 제공 스키마 **100% 일치**(grammar로 토큰 제약) | OpenAI `json_schema`+`strict`, Gemini `responseSchema`, Anthropic tool-use/SO |

> tier 2는 "JSON을 내달라고 부탁"하는 게 아니라 **디코딩 단계에서 스키마 위반 토큰을 물리적으로 못 내게** 한다(grammar-constrained). 사후 검증이 아니라 샘플링 시점 강제.

## 현 코드 실태 (검증) — provider별로 무엇을 쓰나

`_generate_once`(llm_client.py L398–485)가 `json_mode`일 때:

| provider | 실제 코드 | tier | file\:line |
|----------|-----------|------|-----------|
| openai·xai·deepseek·moonshot·zhipuai·groq | `response_format={"type":"json_object"}` | **1** (구문만) | L425–426 |
| google(Gemini) | `response_mime_type="application/json"` (단, `response_schema` **없음**) | **1** (구문만) | L441–442 |
| anthropic | JSON 모드 **자체가 없음** — system 프롬프트 + 파싱 의존. `max_tokens=2000` 하드코딩 | **0** (프롬프트) | L456–483 |
| ollama | 자체 클라이언트에 `json_mode` 전달(Ollama `format:json`) | 1 | L404–413 |

- 출력 파싱: `generate_json`이 **마크다운 펜스 제거 후 `json.loads`**(L686–701). `json.JSONDecodeError`는 **같은 프로바이더에서 재시도**([01-architecture](01-architecture.md)).
- 즉 **스키마(키·타입·필수)는 어떤 프로바이더에서도 강제되지 않는다.** 모델이 키를 빠뜨리거나 타입을 틀려도 구문만 맞으면 통과 → 다운스트림에서 KeyError/검증 실패로 나타난다.

## 프로바이더별 최신 구조화 출력 API (2026 기준)

### OpenAI (+ 호환) — `json_schema` strict
```python
response_format={
  "type": "json_schema",
  "json_schema": {"name": "topics", "strict": True, "schema": {...}},
}
```
- strict 모드 규칙: 모든 객체에 **`additionalProperties: false`**, 모든 속성은 **`required`**(옵셔널은 `anyOf`+`null` 타입), 지원 모델에서 **100% 스키마 일치**.
- refusal을 **일급 에러로 처리**해야 함(거부 시 `refusal` 필드).
- **호환 프로바이더 주의**: xAI(Grok)는 structured outputs 지원. **deepseek·moonshot·zhipuai·groq는 strict `json_schema` 지원이 제각각**(다수가 `json_object`까지만) → 일괄 적용 불가. 이 차이는 provider/model 문제가 아니라 API surface 문제이기도 하므로 [37-api-surface-sdk-compatibility-boundary](37-api-surface-sdk-compatibility-boundary.md)의 endpoint/SDK/parser artifact와 함께 기록한다.

### Google Gemini — `responseSchema`
```python
config = types.GenerateContentConfig(
  response_mime_type="application/json",
  response_schema=schema,        # ← 현 코드엔 없음. 이걸 추가하면 tier 2
)
```
- `responseMimeType`(현 코드) + `responseSchema`(미사용)를 **함께** 줘야 스키마 강제. 현재는 앞만 있어 tier 1.

### Anthropic — 글로벌 JSON 모드 없음, 두 경로
1. **Structured Outputs(GA)**: `output_config.format={type:"json_schema", schema:...}`로 응답 본문을 JSON 스키마에 맞춘다. 기존 beta 헤더(`structured-outputs-2025-11-13`)는 전환 기간용 레거시 경로다.
2. **Strict tool use(범용)**: `input_schema`를 가진 도구에 `strict: true`를 지정하고 `tool_choice`로 강제 → 도구 이름/입력 스키마를 grammar-constrained sampling으로 보장한다.
- 현 코드는 **둘 다 안 씀** → Anthropic 분기는 tier 0(가장 약함) + `max_tokens=2000` 잘림 위험([07-playbooks](07-playbooks.md) G).

## A/B — 현 LCD 방식 vs 스키마 강제

| 측면 | **A. 현행(json_object/MIME/프롬프트)** | **B. 스키마 강제(json_schema strict/responseSchema/tool_choice)** |
|------|------------------------------------|--------------------------------------------------|
| 스키마 보장 | ❌ 없음(구문만) | ✅ 키·타입·필수 100% |
| 코드 경로 | **단일**(모든 provider 동일 1줄) | provider별 **분기** 필요 |
| 멀티-프로바이더 fallback | ✅ 9개 전부 호환(LCD) | ⚠️ compat 6종 중 일부 미지원 → 분기/예외 |
| 실패 양상 | 키 누락/타입오류가 다운스트림서 터짐 | 거부(refusal)·스키마 컴파일 에러를 앞단서 처리 |
| 구현 비용 | 0(현 상태) | 스키마 정의 + provider capability 매트릭스 + refusal 처리 |
| 출력 품질 | 모델 따라 흔들림 | 안정적·결정적 |

**권장(이 프로젝트):** **점진적·프로바이더 선별 업그레이드.**
- fallback 1순위 그룹(Gemini·OpenAI·xAI)부터 **tier 2**로: Gemini는 `response_schema` 한 줄 추가, OpenAI/xAI는 `json_schema`+`strict`. 가장 효과 크고 안전.
- deepseek·moonshot·zhipuai·groq는 **지원 확인 후**(미지원이면 `json_object` 유지) — 일괄 strict는 fallback을 깨뜨릴 수 있다.
- Anthropic은 응답 본문이면 **`output_config.format`**, 도구 입력이면 **strict tool use**로 분리 적용한다. 동시에 `max_tokens` 하드코딩도 함께 손볼 것.
- 핵심 통찰: **현 LCD(json_object)는 "9개를 한 코드로"라는 제약의 합리적 산물**이다. tier 2로 가려면 **provider별 capability 분기**를 받아들여야 하고, 그게 이 업그레이드의 진짜 비용이다.

> 코드 변경은 별도 태스크([07-playbooks](07-playbooks.md) B 절차 준수, `LLMClient`/`LLMRouter` 2곳 동기화). 이 위키는 문서 전용이라 미변경.

## 실패 모드와 현재 보강책

Provider refusal and content-filter markers should be handled before parser repair. See [29-error-taxonomy-refusal-fallback-boundary](29-error-taxonomy-refusal-fallback-boundary.md) for the retry/fallback boundary between provider errors, model refusals, structured-output failures, and product gates.

스키마 강제가 없으므로, 이 repo는 **출력 측 방어**로 메운다:

1. **마크다운 펜스 제거 + `json.loads`**(L686–701) — ```json 래핑 흔한 케이스 흡수.
2. **JSONDecodeError 동일-프로바이더 재시도**([01-architecture](01-architecture.md)) — 일시적 깨짐 복구.
3. **언어 브릿지 `validate_json_payload`**([01-architecture](01-architecture.md)) — 한국어/모지바케 검사(스키마 검사는 아님).
4. **Best-of-N**(blind-to-x, [06-per-project](06-per-project.md)) — 후보 중 유효한 것 선택.
5. **generator-evaluator**(dormant, [09-agent-harness](09-agent-harness.md)) — 기준 명시 시 형식 위반까지 잡을 수 있으나 미배선.

> 이들은 **스키마 강제의 대체가 아니라 사후 보정**이다. tier 2를 켜면 1·2 의존을 크게 줄일 수 있다.

## 지뢰밭

- 모든 프로바이더가 **tier 0~1** — 어디서도 스키마(키/타입/필수)를 강제하지 않는다. "JSON 모드니 안전"은 오해.
- Anthropic 분기는 JSON 모드조차 없음(tier 0) + `max_tokens=2000` 잘림 → 장문 JSON에서 특히 취약.
- `json_object`를 compat 6종에 **일괄** 전송 — 지원 안 하는 프로바이더는 `response_format` 에러로 fallback될 수 있음(검증 권장).
- 업그레이드 시 strict 스키마 규칙(`additionalProperties:false`, 전 필드 required, 옵셔널=`anyOf null`)을 어기면 OpenAI가 스키마 자체를 거부한다.

## 출처 (1차 우선, 2026-06-08 확인)

- OpenAI, *Structured model outputs* (json_schema strict vs json_object): <https://developers.openai.com/api/docs/guides/structured-outputs> · 발표: <https://openai.com/index/introducing-structured-outputs-in-the-api/>
- xAI, *Structured Outputs*: <https://docs.x.ai/developers/model-capabilities/text/structured-outputs>
- Google, *Generate structured output (Gemini API)* — `responseSchema`/controlled generation: <https://firebase.google.com/docs/ai-logic/generate-structured-output>
- Anthropic, *Structured outputs*(`output_config.format`, strict tool use, beta header transition): <https://platform.claude.com/docs/en/build-with-claude/structured-outputs> · 도구 사용 문서: <https://platform.claude.com/docs/en/build-with-claude/tool-use>
- 코드 근거: `workspace/execution/llm_client.py` L398–485, L686–701 (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
