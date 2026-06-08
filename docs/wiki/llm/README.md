# LLM Wiki — Vibe Coding 워크스페이스

> 이 프로젝트가 **LLM을 어떻게 쓰는지** 한곳에 모은 지식 베이스다.
> 운영 절차(SOP)는 `workspace/directives/`에 있고, 이 위키는 그 위에서
> **전체 구조 + 검증된 외부 레퍼런스 + 작업 플레이북**을 제공한다.
>
> - 코드 사실(file\:line)은 2026-06-08 기준 `workspace/execution/llm_client.py` 등 실제 소스에서 검증했다.
> - 외부 프로바이더 데이터(모델/가격/한도)는 2026-06-08에 공식 문서를 웹으로 확인했다. 가격은 수시로 바뀌므로 **과금 직전 공식 페이지 재확인**이 원칙이다.

## 한 줄 요약

워크스페이스의 모든 LLM 호출은 **`execution.llm_client.LLMClient`** (9-프로바이더 비용효율 순 자동 fallback)을 통하는 것이 표준이다. 한국어 자동화 파이프라인은 `*_bridged` 변형을 쓰고, 비용·캐싱·관측·평가는 별도 계층으로 분리돼 있다.

## 색인

| # | 페이지 | 내용 |
|---|--------|------|
| 01 | [아키텍처](01-architecture.md) | 9-프로바이더 fallback, `LLMClient` 호출 흐름, 언어 브릿지, 2종 캐시, 3개 로깅 싱크 |
| 02 | [프로바이더 레퍼런스](02-providers.md) | 9개 프로바이더의 **검증된** 모델·가격·한도·공식 문서 표 + 노후 default 모델 정비 권고 |
| 03 | [비용 · 캐싱](03-cost-caching.md) | 로컬 응답 캐시 vs Anthropic 프롬프트 캐시, 비용 가중치, 비용 DB, 이상 알림, 예산 |
| 04 | [관측 (Langfuse)](04-observability.md) | Langfuse v3 셀프호스트, opt-in, 5단계 preflight |
| 05 | [품질 평가 (promptfoo)](05-eval.md) | 골든/부정셋 회귀 평가, 주간 실행, judge 모델 |
| 06 | [프로젝트별 라우터](06-per-project.md) | workspace `LLMClient` vs shorts-maker-v2 `LLMRouter` vs blind-to-x async |
| 07 | [플레이북](07-playbooks.md) | "LLM 기능 추가/디버깅/비용 절감" 등 자주 하는 작업 단계 |

## 빠른 시작

```python
# 워크스페이스 내부(execution/)에서 — 표준 사용법
from execution.llm_client import LLMClient

client = LLMClient()                       # 비용효율 순 기본 우선순위
data = client.generate_json(system_prompt="...", user_prompt="...")
text = client.generate_text(system_prompt="...", user_prompt="...")

# 한국어 출력 강제가 필요한 자동화 파이프라인
safe = client.generate_json_bridged(system_prompt="...", user_prompt="...")
```

```bash
# 프로바이더 연결/키 상태 점검 (실제 API 호출)
py -3.13 workspace/execution/llm_client.py test
py -3.13 workspace/execution/llm_client.py status        # API 호출 없이 키/모델/순서만

# 사용량·비용 요약 (JSONL + SQLite 병합, 기본 최근 7일)
py -3.13 workspace/execution/llm_usage_summary.py
# 비용/폴백/dead-provider 이상 알림 (cron/n8n용, 알림 있으면 exit 1)
py -3.13 workspace/execution/api_usage_tracker.py alerts
```

## 관련 운영 SOP (workspace/directives/)

이 위키는 아래 SOP를 **대체하지 않고 묶는다**. 절차 세부는 각 directive를 본다.

- [`llm_fallback.md`](../../../workspace/directives/llm_fallback.md) — fallback 체인 운영
- [`local_inference.md`](../../../workspace/directives/local_inference.md) — Ollama 로컬 추론 + SmartRouter/Reasoning
- [`deepseek_ko_bridge.md`](../../../workspace/directives/deepseek_ko_bridge.md) — 한국어 브릿지가 필요한 이유
- [`anthropic_prompt_caching.md`](../../../workspace/directives/anthropic_prompt_caching.md) — 프롬프트 캐싱 비용 절감
- [`llm_observability_langfuse.md`](../../../workspace/directives/llm_observability_langfuse.md) — Langfuse 관측
- [`llm_eval_promptfoo.md`](../../../workspace/directives/llm_eval_promptfoo.md) — promptfoo 회귀 평가
- [`api_monitoring.md`](../../../workspace/directives/api_monitoring.md) — API 사용량/헬스체크

## 핵심 코드 위치

| 역할 | 파일 |
|------|------|
| 통합 클라이언트(표준) | `workspace/execution/llm_client.py` |
| 언어 브릿지 정책 | `workspace/execution/language_bridge.py` |
| 사용량/비용 추적 | `workspace/execution/api_usage_tracker.py` |
| JSONL 메트릭 | `workspace/execution/llm_metrics.py` |
| 사용량 리포터 | `workspace/execution/llm_usage_summary.py` |
| Langfuse preflight | `execution/langfuse_preflight.py` (루트 execution) |
| Shorts 전용 라우터 | `projects/shorts-maker-v2/src/shorts_maker_v2/providers/llm_router.py` |
| blind-to-x async 생성 | `projects/blind-to-x/pipeline/draft_generator.py`, `draft_providers.py` |
| promptfoo 평가 러너 | `execution/run_eval_blind_to_x.py` (루트 execution) |

> ⚠️ 디렉터리 2개 주의: LLM **코어**(`llm_client.py`/`api_usage_tracker.py`/`language_bridge.py`/`llm_metrics.py`/`llm_usage_summary.py`)는 **`workspace/execution/`**에, **eval·preflight**(`run_eval_blind_to_x.py`/`blind_to_x_eval_extract.py`/`ai_batch_runner.py`/`langfuse_preflight.py`)는 **루트 `execution/`**에 있다. 둘은 서로 다른 폴더다.

## 이 위키 유지보수

- 코드가 바뀌면(프로바이더 추가, default 모델 변경, 비용 가중치 조정) 해당 페이지의 **file\:line 인용과 표를 갱신**한다.
- 외부 프로바이더 데이터는 분기마다 또는 과금 영향이 큰 작업 전에 [02-providers](02-providers.md)의 "재검증" 절차로 갱신한다.
- 큰 사실 변경은 `.ai/SESSION_LOG.md`에 기록하고, 메모리 인덱스(`MEMORY.md`)와 충돌하면 메모리를 갱신한다.

*최종 작성: 2026-06-08 · 코드 검증 기준 커밋: `f94a25e9` 계열 현재 HEAD*
