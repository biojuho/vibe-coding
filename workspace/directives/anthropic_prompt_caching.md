# Anthropic Prompt Caching 적용

> **목적**: Anthropic API 호출에서 cache_control을 활성화해 표준 입력 대비 90%까지 비용 절감. 2026년 초 기본 cache TTL이 60분 → 5분으로 변경된 이후의 정확한 운영 패턴을 고정한다.

## 범위 (In/Out)

- **In**: `workspace/execution/llm_client.py`의 `anthropic` provider 분기, `projects/blind-to-x/pipeline/draft_providers.py`의 `_call_anthropic_async`
- **Out**: OpenAI/Gemini/DeepSeek 등 다른 프로바이더 (각자 캐싱 모델이 다름)

## 입력/출력

- **입력**: `system_prompt`(재사용 큰 블록), `user_prompt`(가변), `cache_strategy: "5m"|"1h"|"off"` 옵션
- **출력**: 응답 + `usage.cache_creation_input_tokens`, `usage.cache_read_input_tokens` 기록 → 워크스페이스 `api_usage` 테이블의 신규 컬럼 2개

## 사용 도구

- **anthropic-python** SDK ≥ `0.39.0` — `cache_control={"type": "ephemeral"}` 지원
- 가격 모델 (2026 기준):
  - 캐시 write: 표준 입력 × 1.25 (5분), × 2.0 (1시간)
  - 캐시 hit: 표준 입력 × 0.10 (90% 할인)
  - **손익분기**: 5분 캐시는 1회만 재히트되어도 본전, 1시간 캐시는 2회 재히트 필요

## 단계

### 1. 캐시 후보 식별

- 다음 조건을 만족하는 system 프롬프트만 캐시:
  - 길이 ≥ 1024 토큰 (Anthropic 최소 캐시 블록)
  - 호출 빈도 5분 내 ≥ 2회 (default 5분 TTL 기준)
- 1차 후보:
  - `projects/blind-to-x/pipeline/draft_prompts.py`의 reviewer-memory 포함 system 프롬프트
  - `projects/shorts-maker-v2/src/shorts_maker_v2/pipeline/script_step.py`의 채널 톤 가이드
  - workspace orchestrator의 `.ai/CONTEXT.md` + `.ai/HANDOFF.md` 합본 (재히트 빈도 높음)

### 2. LLMClient 인터페이스 확장

- `LLMClient.generate_*`에 `cache_strategy: str = "off"` 추가
- `anthropic` 분기에서 `cache_strategy="5m"`이면 system 메시지 마지막 블록에 `cache_control` 주입
- `cache_strategy="1h"`는 `cache_control={"type": "ephemeral", "ttl": "1h"}` 형태로 매우 드물게 변하는 거대 컨텍스트(예: 운영 SOP 전체 합본)에만 적용
- 다른 provider는 옵션 무시 (no-op)

### 3. 사용량 추적 컬럼 추가

- `workspace_db`의 `api_usage` 테이블에 컬럼 추가:
  - `cache_creation_tokens INTEGER DEFAULT 0`
  - `cache_read_tokens INTEGER DEFAULT 0`
- 마이그레이션은 idempotent ALTER (기존 8DB 통합 패턴 따라감)

### 4. 검증

- 동일 system 프롬프트로 5분 안에 2회 호출 → 2번째 응답의 `cache_read_input_tokens > 0`
- `workspace/tests/test_llm_client_anthropic_cache.py`:
  - `cache_strategy="off"` → 기존 페이로드와 비트 단위 동일
  - `cache_strategy="5m"` → system 메시지 끝에 `cache_control` 블록
- 비용 모니터: `directives/api_monitoring.md`의 일일 리포트에 cache hit ratio 추가

## 예외 상황 (Edge Cases)

- **system 프롬프트가 1024 토큰 미만**: 캐시 효과 없음 — `cache_strategy` 자동 다운그레이드 + 1회 warning 로그
- **모델 이름 변경**: cache는 모델별로 격리됨 → 모델 변경 시 cache miss 폭증, 변경 직후 1시간은 비용 일시 증가 정상
- **Batch API 동시 사용**: Batch API는 자체 50% 할인 + 캐싱 병행 가능. 우선순위는 **Batch 먼저, 캐싱 나중에** 적용 (별도 SOP에서 결합 평가)
- **TTL 5분 너무 짧을 때**: 호출 간격이 5분을 자주 넘기면 1시간 TTL 검토 — 단 write 비용 2배 주의

## 파일 매핑

| 파일 | 변경 종류 |
|------|---------|
| `workspace/execution/llm_client.py` | `cache_strategy` 파라미터 + anthropic 분기 |
| `projects/blind-to-x/pipeline/draft_providers.py` | `_call_anthropic_async`에 cache_strategy 전달 |
| `projects/blind-to-x/pipeline/draft_generator.py` | reviewer-memory 프롬프트 호출 시 `cache_strategy="5m"` |
| `workspace/execution/api_usage_tracker.py` | cache_creation_tokens / cache_read_tokens 기록 |
| `workspace/tests/test_llm_client_anthropic_cache.py` | 신규 |
| `workspace/migrations/<date>_api_usage_cache_columns.sql` | 신규 |

## 비고

- `directives/llm_observability_langfuse.md`와 함께 적용하면 cache hit ratio가 Langfuse trace에도 자동 기록됨
- 절감 효과 측정: 도입 전후 1주 평균 `daily_cost_anthropic` 비교, 30% 이상 절감 미달 시 후보 프롬프트 재검토
- Vertex AI/Bedrock 경유 호출은 캐시 호환성 다름 — 직결 Anthropic API만 적용
