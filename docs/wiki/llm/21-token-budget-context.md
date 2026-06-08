# 21 · Token Budget · Context Window

> LLM 호출 전에 입력·출력 토큰 예산과 context window를 어떻게 판단할지 정리한 운영 문서.
> 코드 위치는 2026-06-08 현재 `workspace/execution/llm_client.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py` 기준이다.

## 왜 따로 보나

[02-providers](02-providers.md)는 모델별 context window와 가격을 표로 다루고, [03-cost-caching](03-cost-caching.md)은 호출 후 사용량/비용을 집계한다. 하지만 긴 문서·코드 diff·툴 출력·구조화 JSON을 넣는 작업에서는 호출 전에 다음 네 가지를 따로 판단해야 한다.

| 관점 | 질문 | 현재 위치 |
|---|---|---|
| Context window | system + user + tool/schema + 예상 출력이 모델 한도 안에 들어가는가 | 외부 모델 문서, provider Models API |
| Output cap | `max_tokens` 또는 모델의 max output이 응답을 자르지 않는가 | 로컬 코드, 외부 모델 문서 |
| Preflight count | 실제 호출 전 입력 토큰을 계산하거나 보수 추정하는가 | 현재 core에는 없음 |
| Post-call usage | 호출 후 비용·관측용 토큰 수를 기록하는가 | `LLMClient`, blind-to-x provider layer |

핵심은 **post-call usage는 관측이고, preflight token budget은 장애 예방**이라는 점이다. 호출 후 usage가 정확해도, context 초과나 output truncation은 이미 발생한 뒤다.

## 현재 구현 사실

| 범위 | 현재 동작 | 근거 |
|---|---|---|
| workspace OpenAI/OpenAI-compatible | 응답 후 `usage.prompt_tokens`와 `usage.completion_tokens`를 읽음 | `llm_client.py` L430-L431 |
| workspace Gemini | 응답 후 `usage_metadata.prompt_token_count`와 `candidates_token_count`를 읽음 | `llm_client.py` L451-L453 |
| workspace Anthropic | `max_tokens=2000`으로 호출하고, 응답 후 input/output/cache 토큰을 읽음 | `llm_client.py` L460, L479-L482 |
| workspace core preflight | 호출 전 token count/helper/context guard 없음 | 공개 API와 `_run_simple_loop` 경로 기준 |
| blind-to-x Anthropic | `max_tokens=1500`으로 호출하고, 응답 후 input/output/cache 토큰을 읽음 | `draft_providers.py` L196, L217-L220 |
| blind-to-x OpenAI/xAI/Ollama | 응답 후 OpenAI-compatible usage를 읽음 | `draft_providers.py` L237-L263 |
| blind-to-x Gemini REST | 응답 후 `usageMetadata.promptTokenCount`와 `candidatesTokenCount`를 읽음 | `draft_providers.py` L290-L292 |
| shorts-maker-v2 Anthropic | `max_tokens=2000`으로 호출 | `llm_router.py` L296 |

따라서 현재 구현은 비용·관측에는 쓸 수 있지만, 호출 전에는 긴 입력이 모델 context를 넘는지, 하드코딩된 output cap이 긴 JSON/스크립트를 자를지, reasoning/thinking token budget이 응답 예산을 잠식할지 미리 막지 않는다.

Local Ollama adds one more preflight axis: context window and output budget are not enough if the installed quantized model cannot fit memory or load within timeout. See [35-local-inference-hardware-quantization-boundary](35-local-inference-hardware-quantization-boundary.md) for `/api/tags`, `/api/ps`, VRAM/context, and local fallback evidence.

Conversation state is another separate axis: fitting the next request into a context window does not prove which provider response, SDK session, graph checkpoint, MCP resource, `.ai` handoff, or product record carried prior context. Use [38-conversation-state-memory-handoff-boundary](38-conversation-state-memory-handoff-boundary.md) for that artifact.

## 공식 기준

- OpenAI 모델 비교 문서는 모델별 `Context Window`와 `Max Output Tokens`를 분리해 제공한다. 이 값은 모델별로 바뀌므로 과금·배포 직전 공식 표를 다시 본다.
- OpenAI Cookbook의 tiktoken 예시는 chat message token counting이 모델/메시지 포맷에 따라 달라질 수 있으므로 추정치로 다뤄야 한다고 설명한다.
- Claude API overview는 Token Counting API를 `POST /v1/messages/count_tokens`로 제공하며, 메시지를 보내기 전에 비용과 rate limit 관리를 위해 token을 셀 수 있다고 설명한다.
- Gemini token 문서는 `count_tokens`를 호출 전 입력 크기 확인에 쓰고, `usage_metadata`는 호출 후 input/output/total/thinking/cache 토큰 관측에 쓴다고 설명한다.
- Gemini Models API는 model metadata에 `inputTokenLimit`과 `outputTokenLimit`을 제공한다.

## A/B 비교

| 기준 | A. 현재 post-call usage 중심 | B. local preflight estimator | C. provider-native token count |
|---|---|---|---|
| 호출 전 차단 | 없음 | 보수 추정으로 일부 차단 | provider 토크나이저 기준으로 더 정확 |
| 비용/지연 | 추가 비용/지연 없음 | 로컬 계산만 있으면 낮음 | provider별 API 호출/지연 가능 |
| 정확도 | 호출 후에는 정확 | 모델별 encoding/메시지 overhead 오차 | provider가 제공하는 범위 안에서 가장 정확 |
| 멀티프로바이더 | 이미 사용량 기록은 통합됨 | provider metadata 표가 필요 | OpenAI/Anthropic/Gemini별 구현 분기 필요 |
| 위험 | context 초과와 truncation을 사전에 못 막음 | 과소추정하면 여전히 실패 | 장애 시 preflight 자체가 실패할 수 있음 |

**현재 채택:** A를 현재 동작으로 문서화하고, 긴 입력은 사람이 사전에 줄이거나 chunking한다.

**다음 코드 후보:** B를 먼저 작게 구현한다. `TokenBudget(input_estimate, output_cap, model_context_limit, safety_margin)` 같은 순수 자료구조와 보수적 estimator를 추가하고, 공식 provider-native count API는 C 단계에서 선택적으로 붙인다. 현재 dirty handoff boundary에서는 코드 변경하지 않는다.

## 운영 절차

### 1. 긴 입력을 넣기 전

1. 모델의 context window와 max output token을 공식 모델 문서에서 확인한다.
2. 입력을 system, user, tool/schema, retrieved document, expected output으로 나눠 본다.
3. 입력이 길면 provider 오류를 기다리지 말고 먼저 chunking 또는 retrieval로 줄인다.
4. output이 긴 JSON, 스크립트, 긴 기사/대본이면 local hard cap(`1500`/`2000`)으로 잘릴 수 있음을 먼저 의심한다.

### 2. 결과가 잘리거나 형식이 깨지면

1. `stop_reason`, provider error, post-call usage를 먼저 확인한다.
2. Anthropic 경로에서는 `max_tokens=1500` 또는 `2000` 하드코딩 경로를 확인한다.
3. structured output이면 prompt를 더 길게 만드는 방식보다 schema를 줄이거나 output을 단계별로 나눈다.
4. 재시도 전에 [20-rate-limit-reliability](20-rate-limit-reliability.md)의 retry/rate limit 기준도 함께 본다.

### 3. 사후 관측

```bash
py -3.13 workspace/execution/llm_usage_summary.py --by provider
py -3.13 workspace/execution/api_usage_tracker.py alerts --expected-providers google,deepseek,openai,anthropic
```

이 명령은 사후 사용량·fallback·비용을 보는 도구다. 호출 전 context 초과를 증명하지는 않는다.

## 구현 후보 체크리스트

1. provider/model별 `context_window`와 `max_output_tokens`를 local metadata로 둔다. 출처와 검증일을 source inventory에 남긴다.
2. `estimate_tokens(text, provider, model)`을 순수 함수로 추가한다. OpenAI는 tiktoken, 그 외 provider는 보수적 chars-per-token fallback부터 시작한다.
3. `validate_token_budget(messages, expected_output_tokens, model_limits, safety_margin_pct)`를 추가해 호출 전 warning/fail을 결정한다.
4. Anthropic/Gemini/OpenAI native count API는 별도 optional path로 둔다. 네트워크 preflight가 실패해도 core generation을 과도하게 막지 않도록 fallback 정책을 정한다.
5. 긴 tool output은 [09-agent-harness](09-agent-harness.md)의 `ContextWindow` offload/compaction 기능과 연결할지 별도 A/B로 검증한다.
6. 토큰 예산 failure는 usage/cost 로그와 별도로 기록해 "호출 전 차단"과 "호출 후 실패"를 구분한다.

## 지뢰밭

- Context window와 max output은 같은 값이 아니다. 입력이 한도 안이어도 output cap이 낮으면 JSON/스크립트가 잘릴 수 있다.
- post-call usage는 정확한 비용 관측에 유용하지만 preflight proof가 아니다.
- reasoning/thinking 모델은 보이는 출력 외에 thinking token budget을 쓸 수 있다. output cap을 너무 낮게 잡으면 답변 품질이나 completeness가 흔들릴 수 있다.
- tiktoken 기반 chat counting은 OpenAI 계열에도 모델/메시지 포맷별 오차가 있을 수 있다. 임계치 근처에서는 보수 margin을 둔다.
- `ContextWindow` 모듈은 구현·테스트는 있으나 production LLM path에는 미배선이다. 존재만 보고 자동 compaction이 켜져 있다고 가정하지 않는다.

## 출처

- 공식: OpenAI API Docs, *Compare models*: <https://developers.openai.com/api/docs/models/compare>
- 공식: OpenAI Cookbook, *How to count tokens with tiktoken*: <https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken>
- 공식: Claude API Docs, *API overview*: <https://platform.claude.com/docs/en/api/overview>
- 공식: Claude API Docs, *Count tokens in a Message*: <https://platform.claude.com/docs/en/api/messages/count_tokens>
- 공식: Google AI for Developers, *Understand and count tokens*: <https://ai.google.dev/gemini-api/docs/tokens>
- 공식: Google AI for Developers, *Models API*: <https://ai.google.dev/api/models>
- 코드 근거: `workspace/execution/llm_client.py`, `projects/blind-to-x/pipeline/draft_providers.py`, `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`, `workspace/execution/harness_context.py`

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
