# 12 · LLM 소비 기능 인벤토리

> "이 repo에서 **무엇이** LLM을 부르나"의 전수 지도. [06-per-project](06-per-project.md)가 **3개 생성 라우터**의 구조라면, 이 페이지는 그 라우터를 **쓰는 쪽**(진입점) 목록이다.
> `caller_script` 라벨 + `from execution.llm_client` import를 코드로 grep해 작성, 2026-06-08 현재 HEAD. ✅=검증된 직접 소비처, ⚠️=미배선/미확인.
> 관련: [01-architecture](01-architecture.md), [09-agent-harness](09-agent-harness.md), [11-reasoning-models](11-reasoning-models.md).

## 왜 인벤토리가 필요한가

- 비용/관측은 **`caller_script`로 그룹핑**된다([03-cost-caching](03-cost-caching.md)). 어떤 라벨이 실재하는지 알아야 `llm_usage_summary --by caller`를 읽는다.
- 새 LLM 기능 추가 시 **기존 패턴을 재사용**하려면 누가 이미 LLMClient를 쓰는지 알아야 한다([07-playbooks](07-playbooks.md) A).
- 이름이 "AI"인데 **실제로 LLM을 안 쓰는** 도구가 있다(아래 ⚠️) → 오해 방지.

## 직접 소비처 (검증) — `caller_script` 라벨 있음

| 진입점 | 역할 | caller_script | file\:line |
|--------|------|---------------|-----------|
| `topic_auto_generator.py` | 채널별 주제 생성(트렌드 반영) | `topic_auto_generator` | L89 |
| `pr_self_review.py` | AI 기반 PR 셀프 리뷰 | `pr_self_review` | L244 |
| `github_stats.py` | GitHub 통계 요약/해설 | `execution/github_stats.py` | L57 |
| `notion_client.py` | Notion 연동 중 LLM 보조 | `execution/notion_client.py` | L76 |
| `langfuse_preflight.py`(루트 execution) | 관측 smoke trace(실호출) | `execution/langfuse_preflight.py` | L228 |
| blind-to-x `draft_providers.py` | async 드래프트 생성(별도 라우터) | `projects/blind-to-x/pipeline/draft_providers.py` | L63 |
| blind-to-x `cost_tracker.py` | 비용 적재(workspace 미러) | `…/cost_tracker.py` | L69 |

> `caller_script`는 사용량 추적 라벨이다. 미지정 시 자동 추정([01-architecture](01-architecture.md)). 새 진입점은 **반드시 의미 있는 라벨**을 줄 것 — 안 그러면 비용 귀속이 흐려진다.

## 추론 오케스트레이션 소비처 (LLMClient 주입)

[11-reasoning-models](11-reasoning-models.md) (B) 스택. 전부 `LLMClient`를 받아 그 위에서 동작 → fallback/비용/캐싱 상속.

| 모듈 | 역할 |
|------|------|
| `smart_router.py` | 복잡도 기반 로컬/클라우드 라우팅 |
| `thought_decomposer.py` | Forest-of-Thought 서브태스크 분해 |
| `confidence_verifier.py` | SAGE confidence 자기평가·조기종료 |
| `reasoning_engine.py` | Popper 반증 기반 패턴 학습 |
| `reasoning_chain.py` | 위 단계 체인 오케스트레이션 |
| `local_inference.py` · `workers.py` · `graph_engine.py` · `code_evaluator.py` | 로컬 추론 실행/평가 보조 |

## 하네스 소비처 (LLMClient 래핑, **dormant**)

[09-agent-harness](09-agent-harness.md). `LLMClient`를 **감싸지만** 현재 프로덕션 미배선.

| 모듈 | 역할 | 상태 |
|------|------|------|
| `harness_middleware.py`(`HarnessSession`) | 관측+루프+예산 래퍼 | 구현·테스트, 미배선 |
| `harness_context.py`(`ContextWindow`) | 컴팩션·오프로드(요약에 HarnessSession 사용) | 구현·테스트, 미배선 |
| `harness_eval.py`(`GeneratorEvaluator`) | 생성-평가 루프 | 구현·테스트, 미배선 |

## 생성 라우터 본체 (참조)

세 라우터 자체는 [06-per-project](06-per-project.md)에 상술. 진입점이 아니라 **메커니즘**이다.

- workspace `LLMClient`(`llm_client.py`) — 표준. 위 직접/추론/하네스 소비처가 모두 이걸(또는 모듈 함수) 통한다.
- shorts-maker-v2 `LLMRouter` — shorts 파이프라인 전용(orchestrator/cli/topic_validator가 주입).
- blind-to-x async draft(`draft_generator`/`draft_providers`) — Best-of-N + 서킷브레이커.

## ⚠️ 이름은 "AI"지만 LLMClient 미참조 (검증된 오해 포인트)

grep 결과 다음은 **`llm_client`/`generate_json`/`LLMClient`를 참조하지 않는다**:

- `code_improver.py` (+ `_ci_models`/`_ci_analyzers`/`_ci_report`/`_ci_utils` 체인) — 디렉티브명은 "AI 코드 개선"이나 코드 체인에 LLM 호출 미발견. **정적/휴리스틱 분석으로 보이며 LLM 미배선**(LLM 경로가 있다면 별도/동적 — 미확인으로 표기).
- `error_analyzer.py`·`content_writer.py`·`health_check.py` — 동일 grep에서 LLMClient 미참조.

> 교훈: INDEX(`workspace/directives/INDEX.md`, 2026-05-08)의 directive↔script 매핑은 **의도**를 적은 것이고, 실제 LLM 배선과는 **다를 수 있다.** 인벤토리는 코드 grep을 진실의 원천으로 삼는다.

## 호출 패턴 3종 (어떤 걸 쓰나)

| 패턴 | 코드 | 언제 |
|------|------|------|
| 생성자 인스턴스 | `LLMClient(caller_script="x")` 후 `.generate_json(...)` | 일반적. 라벨·옵션(캐시TTL 등) 제어 필요 시 |
| 모듈 함수 | `from execution.llm_client import generate_json` | 간편 1회성. **`providers=`로 per-call provider 오버라이드 가능**([01-architecture](01-architecture.md)) |
| 하네스 래핑 | `HarnessSession(...).generate_json(...)` | 세션 예산/루프가드 필요한 에이전트 경로(현재 dormant) |

**권장**: 진입점은 **생성자 + 의미 있는 `caller_script`**가 기본([07-playbooks](07-playbooks.md) A). provider를 호출마다 바꿔야 할 때만 모듈 함수. 프로바이더를 **직접** 부르지 말 것(추적/fallback/브릿지를 우회하게 됨).

## 지뢰밭

- `caller_script` 미지정 진입점은 비용 귀속이 흐려진다 → 라벨 필수.
- "AI"·"개선"·"분석" 이름만 보고 LLM 소비처로 단정 말 것 — `code_improver` 등은 미참조(위).
- blind-to-x 진입점은 workspace `LLMClient`가 아니라 **자체 async draft 경로**를 쓴다([06-per-project](06-per-project.md)) — 비용도 `btx_costs.db`로 별도([03-cost-caching](03-cost-caching.md)).
- 인벤토리는 grep 스냅샷이다 — 새 소비처가 생기면 갱신([07-playbooks](07-playbooks.md) J).
- 이미지, 음성, 비디오 기능은 텍스트 LLM 소비처로 바로 세지 않는다. provider media API와 로컬 렌더링 경계는 [25-multimodal-audio-media-boundary](25-multimodal-audio-media-boundary.md)에서 별도로 확인한다.

## 출처

- 코드 근거(grep): `caller_script=` 라벨 + `from execution.llm_client` import, `workspace/execution/*` 및 `projects/blind-to-x/pipeline/*` (2026-06-08 현재 HEAD).
- INDEX 대조: `workspace/directives/INDEX.md` (2026-05-08, **stale 가능** — 코드 grep 우선).

*코드 검증: 현재 HEAD*
