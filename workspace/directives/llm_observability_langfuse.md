# LLM 관측(Observability) — Langfuse 셀프호스트

> **목적**: 7-provider fallback 체인의 호출 가시성(provider/model/cost/token/cache
> usage/failure reason)을 워크스페이스에 통합한다. Local-First(ADR-002)에 맞춰
> Langfuse Cloud가 아닌 로컬 셀프호스트만 사용한다.

## 범위

- **In**: `workspace/execution/llm_client.py` 동기 LLM 호출,
  `projects/blind-to-x/pipeline/draft_providers.py` async provider 시도,
  로컬 JSONL 메트릭 보조 기록, Langfuse v3 Docker Compose.
- **Later**: `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py`의
  async provider 시도 단위 observation.
- **Out**: LangSmith, Helicone Cloud, 외부 SaaS trace 전송.

## 입력/출력

- **입력**: provider, model, endpoint, token usage, cache usage, cost, caller metadata.
- **출력**: 로컬 Langfuse trace/generation observation, `.tmp/llm_metrics/*.jsonl`
  보조 로그.

## 사용 도구

- Langfuse v3 self-hosted stack: web, worker, Postgres, ClickHouse, Redis, MinIO.
- Langfuse Python SDK v3/v4 compatible manual observation:
  `get_client().start_observation(..., as_type="generation")`.

## 절차

1. `infrastructure/langfuse/docker-compose.yml`로 로컬 v3 스택을 기동한다.
   모든 포트는 `127.0.0.1`에만 바인딩한다.
2. `.env`에 `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`를 넣고
   추적이 필요할 때만 `LANGFUSE_ENABLED=1`로 전환한다.
3. `LANGFUSE_ENABLED!=1`이거나 키가 없으면 훅은 SDK import도 하지 않고 no-op
   이어야 한다.
4. SDK 미설치, 네트워크 오류, 잘못된 키는 silent drop 처리한다. 관측 실패가 LLM
   호출을 막으면 안 된다.
5. 회귀 테스트는 disabled no-op, missing-key no-op, enabled observation 생성,
   SDK import failure silent drop을 고정한다.

## 파일 매핑

| 파일 | 변경 종류 |
| --- | --- |
| `infrastructure/langfuse/docker-compose.yml` | 신규 v3 로컬 스택 |
| `infrastructure/langfuse/README.md` | 신규 운영 문서 |
| `.env.example` | `LANGFUSE_*` 키 추가 |
| `workspace/execution/llm_client.py` | `_emit_langfuse_trace` + `_log_usage` 후크 |
| `workspace/execution/llm_metrics.py` | JSONL 보조 메트릭 |
| `projects/blind-to-x/pipeline/draft_providers.py` | async provider attempt trace 후크 |
| `workspace/tests/test_llm_client_langfuse.py` | 회귀 테스트 |
| `projects/blind-to-x/tests/unit/test_draft_providers.py` | async trace 후크 테스트 |

## 예외 상황

- **Langfuse 컨테이너 다운**: silent drop. 호출 결과는 그대로 반환한다.
- **SDK 미설치**: `LANGFUSE_ENABLED=0`일 때 import 시도 금지, `1`이어도 예외 삼킴.
- **PII**: prompt 원문은 기본 trace metadata에 넣지 않는다. 필요 시 별도 승인 후
  로컬 보관 정책과 함께 확장한다.
