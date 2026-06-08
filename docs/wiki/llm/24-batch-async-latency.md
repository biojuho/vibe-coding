# 24 · Batch · Async · Latency · Concurrency Boundary

> Provider Batch API, repo-local async fallback, streaming, timeout, concurrency를 섞지 않기 위한 운영 페이지.
> 코드 사실은 2026-06-08 현재 HEAD 기준으로 `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `docs/wiki/llm/06-per-project.md`에서 재확인했다.

## 왜 따로 보나

다음 네 가지는 모두 "느린 LLM 작업을 다루는 방법"처럼 보이지만 운영 의미가 다르다.

- **Provider Batch API**: provider에 대량 요청 묶음을 제출하고 나중에 결과를 받는 비실시간 비동기 처리다. 비용/처리량에는 좋지만 사용자 인터랙션 대기시간을 줄이는 기능이 아니다.
- **Repo-local async fallback**: Python `async/await`로 단일 요청의 provider 호출을 감싼다. blind-to-x는 이 범주지만 provider race가 아니라 순차 fallback이다.
- **Concurrent provider race**: 여러 provider를 동시에 호출하고 먼저 성공한 응답을 채택하는 패턴이다. 현재 주요 LLM 생성 경로에는 없다.
- **Streaming**: 응답 일부를 먼저 보여주는 UX/연결 방식이다. 전체 비용 절감이나 대량 처리 큐를 자동으로 제공하지 않는다.

따라서 "비동기"라는 단어 하나로 batch, streaming, timeout, race, fallback을 묶으면 비용·SLA·rate limit 판단이 틀어진다.

## 현재 구현 사실

### 1) workspace `LLMClient`: 동기 순차 fallback

`workspace/execution/llm_client.py`는 provider 순서대로 호출하고, provider마다 retry를 소진한 뒤 다음 provider로 넘어간다.

- `_run_simple_loop`는 바깥 `for provider in providers`, 안쪽 `for attempt in range(1, self.max_retries + 1)` 순서다(L628-L630).
- 성공하면 즉시 usage를 기록하고 return한다(L640-L662).
- retry sleep은 `time.sleep(min(2**attempt, 10))` 형태다(L678-L680).
- public surface는 `generate_json(...)`, `generate_text(...)`, bridged 변형이다(L686-L735, L953-L987).
- 현재 공통 client에는 batch submit/poll/result API, streaming public API, provider race primitive가 없다.

이 경로는 즉시 응답이 필요한 워크스페이스 자동화의 기본값이다. 대량 eval/report/replay를 처리하려면 batch용 manifest와 result ingest 계층이 별도로 필요하다.

### 2) Shorts Maker V2 `LLMRouter`: 동기 순차 fallback

`projects/shorts-maker-v2/.../llm_router.py`도 같은 shape다.

- `generate_json`은 enabled provider를 순차 순회하고 provider당 retry한다(L336-L394).
- `generate_text`도 같은 provider 순서와 retry를 쓴다(L404-L429).
- OpenAI-compatible client에는 `timeout=self.request_timeout_sec`가 전달되지만, batch/streaming/race public surface는 없다(L203-L227, L330-L429).
- 비용 DB와 batch accounting이 없으므로, Shorts bulk generation을 batch로 옮기려면 비용 기록 schema부터 분리해야 한다.

### 3) blind-to-x: async지만 race가 아니다

`projects/blind-to-x/pipeline/draft_generator.py`와 `draft_providers.py`는 async를 쓰지만, 현재 구현은 provider 동시 race가 아니다.

- `_call_llm_with_fallback`은 `for provider in self._enabled_providers()` 뒤에 provider별 retry loop를 돈다(L529-L569).
- `_generate_once`는 provider별 coroutine 하나를 `asyncio.wait_for(coro, timeout=timeout)`로 감싼다(draft_providers.py L310-L329).
- 실패 시 다음 provider로 순차 이동하고, retry sleep은 `await asyncio.sleep(min(2**attempt, 10))`다(draft_generator.py L557-L568).
- [06-per-project](06-per-project.md)는 `FIRST_COMPLETED`/`as_completed` provider race가 없다는 grep 근거를 이미 고정했다.

이 경로는 per-provider deadline과 circuit breaker를 갖춘 실시간 fallback이지, Batch API가 아니다.

## Provider 공식 기준

### OpenAI Batch API

OpenAI Batch API는 비동기 job이다. 공식 문서는 Batch API가 즉시 응답이 필요 없는 작업에 적합하고, standard endpoint 대비 50% 비용 할인, 별도 rate-limit pool, 24시간 turnaround를 제공한다고 설명한다. 입력은 JSONL file이고, request마다 `custom_id`를 둔다. 결과 order는 입력 order와 다를 수 있으므로 `custom_id`로 매핑해야 한다.

이 repo 적용:

- eval, 대량 classification, embedding repository 처리, offline report generation에 맞다.
- 사용자 클릭 직후 보여줘야 하는 Shorts/Blind-to-X reviewer output에는 기본값이 아니다.
- 결과 ingest는 `custom_id`, provider, model, prompt version, schema version, cost estimate를 함께 저장해야 한다.

### Anthropic Message Batches API

Anthropic Message Batches API는 대량 Messages request를 비동기로 처리한다. 공식 문서는 immediate response가 필요 없는 작업, 대규모 eval/content moderation/data analysis/bulk generation에 적합하다고 설명한다. 주요 운영 제약은 batch size limit, 24시간 expiration, result availability, batch/request rate limit, spend limit overshoot 가능성이다. `stream: true`는 batch request에서 지원되지 않는다. 결과도 input order와 다를 수 있어 `custom_id` 매핑이 필요하다.

이 repo 적용:

- Anthropic prompt caching과 함께 쓸 수 있지만, cache pre-warming(`max_tokens: 0`)은 batch 안에서 지원되지 않는다.
- batch가 spend limit을 약간 넘을 수 있다는 문서상 주의가 있으므로, local preflight budget([21-token-budget-context](21-token-budget-context.md))과 batch cap을 먼저 둔다.
- ZDR 대상이 아니라는 retention 주의가 있으므로 민감 데이터 bulk 처리에는 별도 승인/마스킹이 필요하다.

### Gemini Batch API

Gemini Batch API는 대량 request를 비동기로 처리하고 표준 interactive API cost의 50%로 과금한다고 설명한다. inline requests와 JSONL input file 두 가지 제출 방식을 지원하며, 공식 FAQ는 모델별 batch 지원, 24시간 SLO, context caching support를 명시한다.

이 repo 적용:

- Gemini embedding/dedup이나 offline eval에 적합하다.
- interactive `generateContent`/`streamGenerateContent`와 같은 UX 경로로 취급하면 안 된다.
- cached content를 batch request에 쓰는 경우에도 cache hit/cost accounting을 별도 확인해야 한다.

### Groq Batch API

Groq Batch API는 대규모 workload를 비동기 batch로 처리하고, standard rate limits에 영향을 주지 않으며, 24시간부터 7일까지 processing window를 둘 수 있다고 설명한다. 공식 문서는 synchronous API 대비 50% 비용 할인과 chat/audio endpoint 지원 범위를 명시한다.

이 repo 적용:

- Groq가 속도형 실시간 provider라는 인식과 별개로, Batch API는 비실시간 대량 작업용이다.
- batch discount는 prompt caching discount와 stack되지 않는다고 문서가 명시하므로, [03-cost-caching](03-cost-caching.md)의 비용 계산에서 별도 rate로 다룬다.
- 7일 window는 "더 낮은 latency"가 아니라 "더 긴 완료 여유"로 해석한다.

### Streaming 공식 기준

OpenAI streaming 문서는 full response를 기다리지 않고 output beginning을 처리할 수 있게 한다고 설명한다. Anthropic streaming은 `stream: true`로 SSE를 사용하고, SDK가 streaming을 내부적으로 써서 긴 응답의 HTTP timeout을 피할 수 있다고 설명한다. Gemini API reference도 standard generation은 full response를 반환하고 streaming generation은 SSE chunk를 보내 interactive UX에 더 적합하다고 구분한다.

이 repo 적용:

- streaming은 "사용자에게 빨리 보이기" 문제다.
- batch는 "많은 작업을 싸고 안정적으로 나중에 끝내기" 문제다.
- 둘 다 추가하려면 usage/cost accounting과 partial/error handling contract가 다르다.

## A/B 운영 선택

| 선택 | 장점 | 리스크 | 이 repo 권장 |
|---|---|---|---|
| A. 현행 real-time sequential fallback 유지 | 단순, 즉시 UX, 기존 비용/로그와 호환 | 대량 작업 비용/처리량 비효율 | 기본값 |
| B. offline Batch API 계층 추가 | eval/report/replay/embedding 대량 처리 비용 절감 | job manifest, polling, partial failure, result ingest 필요 | 대량 비실시간 작업에 선별 도입 |
| C. provider concurrent race | p95 latency를 낮출 수 있음 | 중복 비용, rate-limit 폭주, abort/정산 복잡 | 현재 비권장 |
| D. streaming UI 추가 | perceived latency 개선, 긴 응답 timeout 완화 | partial output schema, cancellation, UI/로그 복잡 | UX 화면별 별도 실험 |

**결론:** 현행 생성 경로는 A를 유지한다. B는 "사용자가 기다리는 workflow"가 아니라 "offline bulk workflow"에만 추가한다. C는 예산·rate-limit·abort semantics를 먼저 설계하기 전에는 열지 않는다. D는 UI 체감 개선용이며 batch 비용 절감 대체재가 아니다.

## Batch 도입 체크리스트

1. workload를 interactive / offline bulk / scheduled replay / eval로 분류한다.
2. batch manifest에 `batch_id`, provider, model, prompt version, schema version, caller, `custom_id`, input hash, expected output schema를 남긴다.
3. 제출 전 [21-token-budget-context](21-token-budget-context.md) 기준으로 token/cost upper bound를 계산한다.
4. provider별 batch eligibility와 current pricing을 과금 직전 공식 문서로 재확인한다.
5. result order를 믿지 말고 `custom_id`로 join한다.
6. partial success, validation error, expired/canceled result를 각각 재시도/폐기/수정 대상으로 분리한다.
7. batch output을 reviewer 없이 곧바로 publish하지 않는다.
8. batch discount와 prompt cache/context cache discount를 한 rate로 섞지 않는다.
9. `.tmp/` result 파일은 중간 산출물로 보고, 최종 reviewer output은 Notion/DB/리포트 같은 사용자 접근 가능한 표면에 저장한다.
10. 실시간 fallback 장애를 batch queue로 숨기지 않는다. user-facing SLA 장애는 [20-rate-limit-reliability](20-rate-limit-reliability.md)의 retry/fallback/circuit 기준으로 처리한다.

## 지뢰밭

- **async 함수 != batch job.** `asyncio.wait_for`는 단일 provider call deadline일 뿐이다.
- **batch discount != latency improvement.** batch는 대부분 더 늦게 끝난다.
- **streaming != cheaper.** partial output을 빨리 볼 수 있을 뿐, token/cost 정책은 별도다.
- **provider race는 비용을 늘린다.** 먼저 온 응답만 써도 동시에 보낸 다른 호출은 비용/limit을 소비할 수 있다.
- **batch output order는 안정 계약이 아니다.** `custom_id` 없이 index 기반 merge를 하지 않는다.
- **interactive publish path에 batch를 끼우면 reviewer UX가 흐려진다.** batch는 후보 생성과 평가에 쓰고, 게시 결정은 최신 context에서 별도 검증한다.

## 출처 (1차 우선, 2026-06-08 확인)

- OpenAI, *Batch API*: <https://developers.openai.com/api/docs/guides/batch>
- OpenAI, *Streaming API responses*: <https://developers.openai.com/api/docs/guides/streaming-responses>
- Anthropic/Claude, *Batch processing*: <https://platform.claude.com/docs/en/build-with-claude/batch-processing>
- Anthropic/Claude, *Streaming messages*: <https://platform.claude.com/docs/en/build-with-claude/streaming>
- Gemini API, *Batch API*: <https://ai.google.dev/gemini-api/docs/batch-api>
- Gemini API, *Gemini API reference*: <https://ai.google.dev/api>
- Groq, *Batch API*: <https://console.groq.com/docs/batch>
- 코드 근거: `workspace/execution/llm_client.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `projects/blind-to-x/pipeline/draft_generator.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `docs/wiki/llm/06-per-project.md` (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08*
