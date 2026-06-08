# 20 · Rate Limit · Retry · Reliability

> LLM 호출이 429, quota, timeout, provider 장애를 만났을 때 현재 워크스페이스가 어떻게 반응하는지와 다음 개선 후보를 분리해 둔 운영 문서.
> 코드 위치는 2026-06-08 현재 `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `projects/blind-to-x/pipeline/cost_db.py` 기준이다.

## 왜 따로 보나

[01-architecture](01-architecture.md)는 fallback 루프를 설명하고, [03-cost-caching](03-cost-caching.md)은 비용/알림을 설명하며, [07-playbooks](07-playbooks.md)는 장애 대응 절차를 짧게 다룬다. 하지만 rate limit은 다음 네 가지가 같이 맞아야 운영 사고를 줄일 수 있다.

This page covers retry timing and provider reliability. For the broader taxonomy that separates retryable provider errors from auth/config failures, model refusals, structured-output failures, and product gates, see [29-error-taxonomy-refusal-fallback-boundary](29-error-taxonomy-refusal-fallback-boundary.md).

| 관점 | 필요한 판단 | 현재 위치 |
|---|---|---|
| 프로바이더 제한 | RPM/TPM/RPD 중 어느 bucket이 찼는지 | 외부 공식 문서, provider 콘솔 |
| HTTP 의미 | 429와 `Retry-After`를 어떻게 해석할지 | RFC 6585, RFC 9110 |
| 로컬 구현 | retry 횟수, backoff, non-retryable 분기 | `LLMClient._run_simple_loop` |
| 운영 관측 | fallback rate, dead provider, cost spike | `api_usage_tracker.py alerts`, `llm_usage_summary.py` |

## 현재 구현 사실

| 항목 | 현재 동작 | 근거 |
|---|---|---|
| 기본 재시도 횟수 | provider당 `max_retries=2` | `llm_client.py` L288, L630 |
| 백오프 | 다음 시도 전 `min(2**attempt, 10)`초 sleep | `llm_client.py` L678-L680 |
| jitter | 없음 | 같은 sleep 경로에 난수 없음 |
| `Retry-After` 파싱 | 없음 | 예외 객체/응답 헤더를 읽는 helper 없음 |
| provider fallback | 한 provider가 소진되면 다음 provider로 전환 | `llm_client.py` L601-L684 |
| non-retryable 분기 | invalid key, unauthorized, quota, billing 계열 keyword면 같은 provider 재시도 중단 | `NON_RETRYABLE_KEYWORDS` L137-L146, `_is_non_retryable` L568-L570 |
| timeout | OpenAI/OpenAI-compatible client에만 `request_timeout_sec` 전달 | `llm_client.py` L342-L380 |
| Anthropic/Gemini timeout | 클라이언트 생성 시 timeout 미전달 | `llm_client.py` L360-L380 |
| workspace circuit breaker | 없음 | core `LLMClient`에는 provider 실패 지속 cooldown 저장소 없음 |
| blind-to-x circuit breaker | `provider_failures.skip_until`과 fail_count 기반 1h→72h skip | `cost_db.py` L436-L494, `config.example.yaml` circuit_breaker |

이 표의 핵심은 "현재도 실패를 무한 반복하지는 않는다"와 "하지만 provider가 알려주는 대기 시간까지 존중하지는 않는다"이다. 따라서 대량 실행 전에 외부 queue/concurrency를 낮추는 조치가 여전히 필요하다.

## 공식 기준

- OpenAI rate limit 문서는 RPM/RPD/TPM/TPD 등 여러 bucket 중 하나라도 초과하면 제한에 걸릴 수 있고, 응답 헤더로 limit/remaining/reset 정보를 제공한다고 설명한다.
- OpenAI는 rate limit 완화책으로 random exponential backoff를 제안하며, 실패한 요청도 per-minute limit에 포함될 수 있다고 경고한다.
- Anthropic은 Messages API rate limit을 RPM, input tokens per minute, output tokens per minute으로 측정하고, 429에는 어떤 limit을 넘었는지와 `retry-after` header를 제공한다고 설명한다. 급격한 사용 증가에는 acceleration limit도 있을 수 있다.
- Gemini API는 RPM, input TPM, RPD 차원을 기준으로 제한을 설명하고, 429 `RESOURCE_EXHAUSTED`는 rate limit 초과로 분류한다.
- RFC 6585의 429는 "too many requests" 상태이며, 응답은 조건 설명과 `Retry-After` header를 포함할 수 있다.
- RFC 9110의 `Retry-After` 값은 HTTP-date 또는 delay-seconds다.

## A/B 비교

| 기준 | A. 현재 단순 retry+fallback | B. header-aware retry budget |
|---|---|---|
| 구현 복잡도 | 이미 구현됨 | 예외/응답 헤더 추출, delay parser, jitter, 최대 대기 예산 필요 |
| 429 대응 | 2회 재시도 후 다음 provider | `Retry-After` 또는 reset header를 우선 반영 |
| 동시 실행 안정성 | 여러 worker가 같은 초에 다시 칠 수 있음 | jitter로 동시 재시도 폭주 완화 |
| quota/billing 오류 | keyword로 빠르게 provider 전환 | 유지해야 함. quota/billing은 backoff로 해결되지 않음 |
| 운영 관측 | 사후 fallback/dead-provider 알림 | 사후 알림 + retry delay/cooldown metric 가능 |
| 위험 | provider 제한을 더 태울 수 있음 | 구현 검증 전에는 SDK별 예외 구조 차이 위험 |

**현재 채택:** A를 현재 동작으로 문서화하고 운영 절차를 명확히 한다.

**다음 코드 후보:** B. 단, 바로 전환하지 말고 작은 helper부터 시작한다. 후보 범위는 `Retry-After`/OpenAI reset header 파싱, jitter 포함 exponential backoff, provider별 최대 sleep budget, timeout 전달 비대칭 해소, workspace core provider cooldown 저장소다.

## 운영 절차

### 1. 호출 전 상태 확인

```bash
py -3.13 workspace/execution/llm_client.py status
py -3.13 workspace/execution/llm_client.py test --provider google
```

`status`는 API 호출 없이 키/모델/순서만 보여준다. 실제 장애 확인은 `test --provider <provider>`로 좁혀 실행한다.

### 2. 429 또는 rate limit 로그가 보이면

1. 같은 명령을 즉시 반복하지 않는다. 현재 `LLMClient`는 header-aware sleep을 하지 않으므로 사람이 반복하면 제한 bucket을 더 태울 수 있다.
2. provider 공식 문서에서 제한 차원을 먼저 확인한다. OpenAI/Anthropic/Gemini 모두 request bucket과 token bucket을 별도로 본다.
3. batch/cron/n8n 작업이면 concurrency, batch size, max output tokens를 낮춘다.
4. Anthropic 429에 `retry-after`가 보이면 그 시간보다 짧게 재호출하지 않는다. 현재 core client는 이 값을 자동 반영하지 않는다.
5. billing, unauthorized, invalid key, insufficient quota 계열이면 재시도보다 키/결제/권한 확인이 먼저다.

### 3. 사후 관측

```bash
py -3.13 workspace/execution/api_usage_tracker.py alerts --expected-providers google,deepseek,openai,anthropic
py -3.13 workspace/execution/llm_usage_summary.py --by provider
```

- `alerts`는 fallback rate, cost spike, dead provider를 본다.
- `llm_usage_summary.py --by provider`는 provider별 fallback/error/cost를 빠르게 보여준다.
- blind-to-x 경로는 workspace core와 별개로 provider failure를 DB에 저장하고 circuit을 닫거나 연다. 해당 프로젝트 장애는 `projects/blind-to-x/.tmp/btx_costs.db` 기준으로도 확인해야 한다.

## 구현 후보 체크리스트

다음 cycle에서 코드를 건드릴 경우에는 이 순서가 가장 작다.

1. `Retry-After` delay parser를 순수 함수로 추가하고 RFC 9110의 HTTP-date/delay-seconds를 테스트한다.
2. `_retry_delay_for_error(error, attempt)` helper를 만들어 header 값이 있으면 우선, 없으면 jitter 포함 exponential backoff를 반환한다.
3. provider별 최대 sleep budget을 두어 interactive 작업이 오래 묶이지 않게 한다.
4. Anthropic/Gemini SDK의 현재 timeout 인자 지원을 공식 문서/SDK 문서로 재확인한 뒤 timeout 비대칭을 줄인다.
5. workspace core에도 blind-to-x와 비슷한 provider cooldown을 둘지 A/B 한다. 단, 짧은 one-off 작업에서는 과한 상태 저장일 수 있다.

## 출처

- 공식: OpenAI API Docs, *Rate limits*: <https://developers.openai.com/api/docs/guides/rate-limits>
- 공식: Anthropic Claude API Docs, *Rate limits*: <https://platform.claude.com/docs/en/api/rate-limits>
- 공식: Google AI for Developers, *Gemini API rate limits*: <https://ai.google.dev/gemini-api/docs/rate-limits>
- 공식: Google AI for Developers, *Gemini API troubleshooting*: <https://ai.google.dev/gemini-api/docs/troubleshooting>
- 표준: RFC 6585, Section 4, *429 Too Many Requests*: <https://www.rfc-editor.org/rfc/rfc6585#section-4>
- 표준: RFC 9110, Section 10.2.3, *Retry-After*: <https://www.rfc-editor.org/rfc/rfc9110#section-10.2.3>
- 코드 근거: `workspace/execution/llm_client.py`, `workspace/execution/api_usage_tracker.py`, `workspace/execution/llm_usage_summary.py`, `projects/blind-to-x/pipeline/cost_db.py`, `projects/blind-to-x/config.example.yaml`

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
