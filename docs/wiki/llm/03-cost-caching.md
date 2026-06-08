# 03 · 비용 · 캐싱

> LLM 비용 추적·예산·이상 알림과 **2종 캐시**.
> 인용은 별도 표기 없으면 `workspace/execution/llm_client.py` / `api_usage_tracker.py` 기준, 2026-06-08 검증.
> 운영 SOP: [anthropic_prompt_caching.md](../../../workspace/directives/anthropic_prompt_caching.md), [api_monitoring.md](../../../workspace/directives/api_monitoring.md).

## 2종 캐시 — 절대 혼동 금지

### (A) 로컬 응답 캐시 — `.tmp/llm_cache.db`

동일 `(providers, system_prompt, user_prompt, round(temperature,4))`를 다시 호출하면 **저장된 응답을 그대로** 반환한다(프로바이더 호출 0회 = 비용 0).

- 키: `sha256(...)` (L221–223), 테이블 `llm_cache(key PK, content, created_at REAL)` (L243).
- TTL: `cache_ttl_sec` 기본 **259200초(72h)**, `0`이면 비활성 (L292).
- 조회/저장: `_run_simple_loop` 시작에서 hit이면 즉시 반환(L618–624), 성공 후 저장(L660–661).
- 정리: `cache_cleanup(ttl_sec=259200)` 만료 항목 삭제 (L260–271).
- 주의: 비결정 작업(매번 다른 출력을 원함)에는 `cache_ttl_sec=0` 권장. 응답 `content` 자체가 `.tmp/llm_cache.db`에 남으므로, private/source-sensitive 입력은 [27-data-retention-privacy-logging](27-data-retention-privacy-logging.md)의 로컬 retention 기준을 먼저 적용한다.

### (B) Anthropic 프롬프트 캐시 — `cache_strategy`

Anthropic 서버가 **system 프롬프트 토큰을 캐싱**해 재호출 입력 비용을 최대 90% 절감. (A)와 무관.

- 파라미터: `cache_strategy="off"|"5m"|"1h"` — 공개 함수 → `_run_simple_loop` → `_generate_once`로 전달 (L394, 692/721, 1065/1083).
- **Anthropic 분기에서만** `cache_control={"type":"ephemeral"}`를 system 블록에 부착, `1h`면 `"ttl":"1h"` 추가 (L463–475). 나머지 8개 프로바이더는 무시.
- 응답에서 `cache_creation_input_tokens`/`cache_read_input_tokens`를 읽음 (L481–482).

#### 캐시 후보 기준 (directive 기준)

- system 프롬프트 ≥ **1024 토큰** (Anthropic 최소 캐시 블록) **그리고** 5분 내 ≥ 2회 재호출 → `cache_strategy="5m"`.
- 거의 안 변하는 거대 컨텍스트(운영 SOP 합본 등)만 `1h`(write 2배 주의).
- 작거나 매번 다른 프롬프트는 `off` 유지.

## 비용 가중치 (캐시 토큰)

`_cache_creation_multiplier` (L252–257):

| 토큰 유형 | 배수(입력 단가 대비) | 손익분기 |
|-----------|----------------------|----------|
| 캐시 write (5m / off) | **×1.25** | 1회만 재히트해도 본전 |
| 캐시 write (1h) | **×2.0** | 2회 재히트 필요 |
| 캐시 read(hit) | **×0.10** (90% 할인) | — |

적용 위치(동일 공식이 3곳에 존재):
- `_log_usage` (L509–514): `(cache_creation/1000 × input_price × mult) + (cache_read/1000 × input_price × 0.10)`
- `api_usage_tracker.log_api_call` 자동 비용 계산 (L186–193, 기본 mult 1.25)
- blind-to-x `cost_tracker.add_text_generation_cost` (L197–198)

## 5-tuple 반환

`_generate_once` → `(content, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)` (L395). **Anthropic만** 뒤 두 값을 채우고, 나머지는 `0, 0`.

> 콜사이트는 반드시 5개로 언팩. 3개로 언팩하면 `not enough values to unpack`.

## 사용량/비용 DB

### 워크스페이스 — `.tmp/workspace.db` 테이블 `api_calls`

- 정의/적재: `api_usage_tracker.py` (`DB_PATH` L29, CREATE TABLE L111).
- 컬럼: id, provider, model, endpoint, tokens_input, tokens_output, cost_usd, caller_script, bridge_mode, reason_codes, repair_count, fallback_used, language_score, provider_used, timestamp + 마이그레이션 추가 `cache_creation_tokens`/`cache_read_tokens` (L130–143).
- 단가표 `PRICING`은 **USD per 1K tokens** (llm_client.py L149–162). 예: `claude-sonnet-4-6` = in 0.003 / out 0.015. 무료(gemini-2.5-flash, glm-4-flash, groq, ollama) = 0.

### blind-to-x — `.tmp/btx_costs.db` (프로젝트 로컬)

- `cost_db.py` (`_DEFAULT_DB_PATH` L25). 테이블: daily_text_costs / daily_image_costs / draft_analytics / provider_failures(서킷브레이커) 등.
- 단가는 **per 1M tokens**, anthropic 기준선이 **haiku-4-5**(in 0.80 / out 4.00, `DEFAULT_TEXT_PRICING` cost_tracker.py L21–30).
- 기본은 프로젝트 로컬 DB가 진실의 원천. `BTX_USAGE_FORWARD=1`일 때만 workspace `api_calls`로 미러 (cost_tracker.py L54–74).

> ⚠️ **단위/기준 차이**: workspace `PRICING`은 per-1K·sonnet 기준, btx는 per-1M·haiku 기준이라 **두 DB의 `cost_usd`를 단순 합산하면 안 된다**. 통합 리포트는 출처를 구분해서 본다.

## 예산

| 범위 | 기본값 | 출처 |
|------|--------|------|
| 워크스페이스 월간 | **30.0 USD** (`MONTHLY_LLM_BUDGET_USD`로 오버라이드) | api_usage_tracker.py L65 |
| blind-to-x 일간 | **3.0 USD** | config.yaml L131-132 / cost_db.py L420 |

- 절감 추정 기준선: `claude-sonnet-4`(in 0.003 / out 0.015 per 1K) — 모든 호출을 프리미엄으로 했다면의 가정 대비 (`get_savings_estimate` L574–598).
- btx는 영속 DB 합계로 예산 초과를 검사(in-memory 아님, `is_budget_exceeded` cost_tracker.py L293–308).

## 이상 알림 — `api_usage_tracker.py alerts`

`detect_alerts`가 3가지 anomaly 검출 (L610–719):

| 알림 | 조건(기본) | CLI 플래그 |
|------|------------|-----------|
| fallback rate | provider별 fallback 비율 > **50%** (호출 ≥5건일 때) | `--fallback-pct` |
| cost spike | 최근 window 비용이 직전 window 대비 > **+100%** | `--cost-spike-pct` |
| dead provider | `--expected-providers` 중 **14일**간 호출 0 | `--dead-days` |

```bash
py -3.13 workspace/execution/api_usage_tracker.py alerts            # 기본 7일 window
py -3.13 workspace/execution/api_usage_tracker.py alerts --days 14 --cost-spike-pct 80
```

- **exit code**: 알림 있으면 `1`, 없으면 `0` (L763–773) → cron/n8n에서 분기 가능.
- 검출만 하고 발송은 외부(cron/n8n/Telegram)에 위임. `min_calls_for_rate=5`로 저표본 노이즈 컷.

## 사용량 요약 — `llm_usage_summary.py`

```bash
py -3.13 workspace/execution/llm_usage_summary.py                   # 최근 7일
py -3.13 workspace/execution/llm_usage_summary.py --by provider --json
```

- JSONL(`.tmp/llm_metrics/*.jsonl`) + SQLite `api_calls`를 병합(1초 단위 timestamp+provider+model+tokens dedup, **JSONL 우선**).
- 집계: overall/provider/model/caller별 cost, **cache_hit_ratio**, fallback_rate, error_rate, avg/p95 latency. 순수 stdlib.

## 비용 절감 체크리스트

1. **무료/저가 우선**: 기본 fallback 순서가 이미 비용효율 순. 굳이 비싼 프로바이더를 1순위로 강제하지 말 것.
2. **Anthropic 캐싱**: 큰 재사용 system 프롬프트는 `cache_strategy="5m"`. → 위 후보 기준.
3. **로컬 응답 캐시**: 동일 입력 반복 작업은 `cache_ttl_sec` 활용(비결정 작업은 0).
4. **프롬프트 변경 무효화**: 입력만으로 만든 캐시 키는 프롬프트 템플릿 변경을 숨길 수 있다. 사용자-facing workflow는 [26-prompt-provenance-versioning](26-prompt-provenance-versioning.md)의 `prompt_hash`/`prompt_version` 규칙을 캐시 artifact에 포함하거나 prompt 변경 시 cache clear를 기록한다.
5. **Batch API**: OpenAI/Anthropic/Gemini/Groq 모두 공식 문서상 비실시간 대량 처리에 약 50% 할인 경로가 있다. 단, streaming/async fallback과 다르며 캐시 할인과의 stack 여부도 provider별로 다르다([24-batch-async-latency](24-batch-async-latency.md)).
6. **모니터링**: `alerts`를 cron으로 돌려 cost spike/dead provider 조기 감지.
