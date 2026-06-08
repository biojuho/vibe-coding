# 09 · 에이전트 하네스 계층 (Harness Engineering AI)

> `workspace/execution/harness_*.py` 6개 모듈 = LLM **생성** 위에 얹는 **에이전트 실행 안전·신뢰성** 계층. 도구 권한·샌드박스·예산/루프 가드·컨텍스트 압축·생성-평가 루프.
> 설계 근거: **ADR-025 "Harness Engineering AI" (Phase 0–3)**. 코드 검증 2026-06-08 현재 HEAD.
> 외부 기준: Anthropic *Building Effective Agents* / *Effective Context Engineering*(1차 출처, 아래 §출처).

## ⚠️ 상태 배너 — 구현·테스트 완료, **프로덕션 미배선(dormant)**

6개 모듈은 전부 **구현되고 단위 테스트가 있다**(각 `test_harness_*.py`). 그러나 **현재 프로덕션 LLM 호출/파이프라인 어디에도 배선돼 있지 않다**:

- `HarnessSession`(middleware)·`GeneratorEvaluator`(eval)·`ContextWindow`(context)·`ToolRegistry`(tool_registry)는 **자기 테스트 파일에서만** import된다(grep 확인). 파이프라인 미사용.
- 유일한 프로덕션 통합점은 blind-to-x `pipeline/harness_guard.py` 하나뿐인데, `HARNESS_ENABLED=1`일 때만 동작(**기본 off**)이고 게다가 **stale-API 버그로 켜도 사실상 no-op**(아래 §통합 상태).

> **그래서 이 페이지의 가치**: ① 이 능력들이 **이미 존재**하니 다시 만들지 말 것, ② 지금은 **아무것도 보호/개선하고 있지 않으니** 활성 상태로 가정하지 말 것, ③ 활성화하려면 통합 갭(harness_guard stale-API)을 먼저 고칠 것.

## 6개 모듈 ↔ 개념 ↔ Anthropic 1차 출처

| 모듈 | 역할 | 대응 Anthropic 패턴 | Phase | 상태 |
|------|------|--------------------|-------|------|
| `harness_tool_registry.py` | deny-by-default 도구 권한 + HITL + 세션 예산 | 에이전트 가드레일/권한 | 0 | 구현+테스트, 미배선 |
| `harness_security_checklist.py` | secret/path/command 위생 + preflight | — | 0 | [08-security](08-security.md) |
| `harness_sandbox.py` | Docker/subprocess 실행 격리 | 코드 실행 격리 | 0 | 구현+테스트, 통합 stale |
| `harness_middleware.py` | 관측 + 루프 감지 + 예산(HarnessSession) | 에이전트 가드레일 | 1 | 구현+테스트, 미배선 |
| `harness_context.py` | 자동 컴팩션 + 도구출력 오프로드 | 컨텍스트 엔지니어링 | 2–3 | 구현+테스트, 미배선 |
| `harness_eval.py` | 생성-평가 루프 | evaluator-optimizer 워크플로 | 2–3 | 구현+테스트, 미배선 |

---

## 1) `harness_tool_registry.py` — 도구 권한 (deny-by-default)

에이전트가 **무엇을** 할 수 있는지를 명시적 allowlist로 강제. 미등록 도구는 **항상 거부**.

- `RiskLevel` = SAFE / MODERATE / DANGEROUS (L41–46).
- `ToolPermission(name, risk_level, allowed_path_globs, requires_hitl, max_invocations_per_session, description)` — 프로즌 (L54–76).
  - `allowed_path_globs`: write/execute를 글롭 패턴으로 경로 스코핑(비면 무제약).
  - `requires_hitl`: True면 실행 전 사람 승인.
  - `max_invocations_per_session`: 세션당 호출 상한(`0`=무제한) — 폭주 가드.
- `check(tool_name, *, path, agent_id)` → `CheckResult(allowed, reason, requires_hitl)` — **순수**(카운터/로그 부작용 없음) (L158–201). 검사 순서: 등록 여부 → 예산 → 경로 글롭 → 트래버설 → HITL 플래그.
- `authorize(...)` — check + **부작용**(세션 카운터 증가, audit 로그, HITL 핸들러 호출) (L203–234). HITL 핸들러 미등록 + `requires_hitl`면 **거부**(L248–257).
- `set_hitl_handler(cb)` — `(tool_name, path) -> bool` 콜백 (L132–138).

> OWASP **LLM06 Excessive Agency**의 직접 통제 수단(권한 최소화 + HITL). [08-security](08-security.md) 매핑.

## 2) `harness_sandbox.py` — 실행 격리

- `SandboxManager(docker_available=None)` — Docker 자동 감지(`_check_docker`), 없으면 **subprocess 격리로 폴백**(cwd/env 제약) (L136–148).
- `SandboxConfig`(프로즌, L56–83): `name`, `image="python:3.14-slim"`, `memory_limit="512m"`, `cpu_limit=1.0`, `network_mode=NetworkMode.NONE`, `volume_mounts`, `env_vars`, `timeout=300`, `working_dir="/workspace"`, `allowed_commands`.
- 라이프사이클: `create → start → stop → destroy` (+`get`) (L158–232). Docker는 `docker run -d --memory --cpus --network …`.
- `NetworkMode` = NONE(기본) / HOST(dev) / BRIDGE (L43–48). 기본 **네트워크 차단**.

## 3) `harness_middleware.py` — `HarnessSession` (관측·루프·예산)

`LLMClient`를 **감싸는**(around) 3중 미들웨어. **`LLMClient` 내부는 손대지 않는다.**

```python
session = HarnessSession(agent_id="blind-to-x-pipeline", max_tokens=500_000, max_cost_usd=2.0)
result = session.generate_json(system_prompt="...", user_prompt="...")   # LLMClient처럼 사용
print(session.summary())
```

- **관측**: `CallRecord`(request_id, agent_id, prompt 해시, provider/model/tokens/cost/latency/success/cache_hit) (L49–75). request-ID 상관, 지연 측정, 구조화 이벤트 로그.
- **루프 감지**: `prompt_fingerprint`(system+user 해시+모드, L72–75)로 슬라이딩 윈도에서 **반복 호출 패턴** 탐지 → 무한루프 조기 차단.
- **예산**: `SessionBudget(max_tokens, max_cost_usd, max_calls)` (L78–115). `check()`가 소진 시 거부 사유 반환 → **early-stop**. (`0`=무제한)

> 워크스페이스 전역 비용/관측([03-cost-caching](03-cost-caching.md)/[04-observability](04-observability.md))은 **호출 단위**, HarnessSession 예산은 **세션 단위**다(다른 층). 둘은 보완 관계.

## 4) `harness_context.py` — `ContextWindow` (컴팩션·오프로드)

긴 에이전트 세션의 두 문제를 해결: ① 컨텍스트 과적 → 품질 저하, ② 거대 도구 출력.

- `ContextWindow(max_tokens_estimate=100_000, compact_at_pct=80, offload_threshold_chars=5_000, offload_dir=.tmp/context_offload, keep_recent=6)` (L97–113).
- `add_tool_result(...)`: `offload_threshold_chars`(5000) 초과 도구 출력은 **`.tmp/`로 오프로드**하고 컨텍스트엔 요약+경로만 남김. ← Anthropic "tool result offloading".
- `should_compact()`/`compact(session)`: 사용량이 `compact_at_pct`(80%) 넘으면 **오래된 메시지를 요약**(최근 `keep_recent`=6개는 보존). 요약엔 `HarnessSession`을 씀.
- 토큰 추정: `_CHARS_PER_TOKEN=3`(영어~4/한국어~2의 보수적 평균, L44–45).

> Anthropic 컨텍스트 엔지니어링 4전략(offload·retrieve·isolate·compress) 중 **offload + compress**의 직접 구현.

## 5) `harness_eval.py` — `GeneratorEvaluator` (생성-평가 루프)

Anthropic **evaluator-optimizer** 워크플로의 구현. 모델을 바꾸지 않고 환각·형식위반·품질회귀를 잡는다.

```python
ge = GeneratorEvaluator(
    evaluator_criteria=["유효 JSON에 title/body 키", "title 80자 미만", "body는 한국어"],
    max_rounds=3,
)
result = ge.run(system_prompt="...", user_prompt="...")   # → GeneratorEvaluatorResult
```

- 3역할: **Generator**(생성) → **Evaluator**(명시 기준으로 PASS/FAIL 채점) → **Orchestrator**(피드백을 generator에 되먹이며 `max_rounds`까지 반복) (docstring L4–9).
- `EvaluationResult(passed, score 0~1, feedback, criteria_results)` (L49–57). evaluator는 "ALL 기준 통과해야 passed=true"인 **엄격 채점** system 프롬프트 사용 (L74–92).
- `GeneratorEvaluatorResult(final_output, rounds_used, passed, total_latency_ms, evaluation_log)` (L59–67).

---

## 통합 상태 — `harness_guard.py` (정직한 진단)

blind-to-x `pipeline/harness_guard.py`가 유일한 프로덕션 진입점이다. `HARNESS_ENABLED=1`일 때만 동작(기본 off → 전부 no-op, L32–34). 그러나 **켜도 두 함수 모두 stale-API라 조용히 실패**한다:

- `run_preflight`(L63–101): `SecurityChecklist(project_root=root)` + `result.get("passed")` ↔ 실제 `__init__(workspace_root=…)` + 반환은 `SecurityReport` 데이터클래스 → `TypeError`/`AttributeError` → 광범위 `except Exception`이 삼켜 `{"passed": True, "skipped": False}`로 통과 ([08-security](08-security.md)에서 상술).
- `create_sandbox_context`(L104–141): `manager.get_predefined_profiles()`를 호출하지만 `SandboxManager`엔 **그런 메서드가 없다**(`create/start/stop/destroy/get`뿐 — 사전정의는 모듈상수 `BLIND_TO_X_SANDBOX`로 존재) → `AttributeError`. 설령 거기까지 갔어도 폴백 `SandboxConfig(allowed_paths=…, max_memory_mb=…, max_cpu_percent=…, timeout_seconds=…, network_access=…)`는 **실제에 없는 필드**(실제는 `memory_limit`/`cpu_limit`/`network_mode`/`timeout`/`volume_mounts`)를 쓴다. → 어느 쪽이든 광범위 except에 삼켜져 **None 반환**.

**결론**: harness_guard는 모듈들의 **이전 API**를 상대로 작성됐고 그 사이 모듈이 진화했다. 즉 하네스는 "구현됐지만 배선이 끊긴" 상태. 활성화하려면 harness_guard를 현재 API에 맞춰 다시 배선해야 한다(후속 코드 작업 후보 — 이 위키는 문서 전용이라 미변경).

## A/B — 출력 신뢰성: 세 메커니즘 비교

이 repo엔 LLM 출력 품질을 지키는 메커니즘이 **3개** 있고 역할이 겹쳐 보인다. 언제 무엇을 쓰는지:

| | **harness_eval (생성-평가)** | **promptfoo ([05-eval](05-eval.md))** | **language_bridge ([01](01-architecture.md), [34](34-language-bridge-locale-i18n-boundary.md))** |
|---|---|---|---|
| 시점 | **런타임**(매 생성마다) | **오프라인**(변경 시 회귀) | **런타임**(매 생성마다) |
| 잡는 것 | 임의 기준(환각·형식·품질) | 프롬프트/모델 회귀 | 한국어·모지바케·자모만 |
| 비용 | 라운드마다 추가 호출(↑) | CI/주간 1회 | repair 시 1~2회 |
| 기준 | 호출자가 명시(criteria 리스트) | YAML rubric/assert | 고정(한글 비율 등) |
| 현재 상태 | **dormant**(미배선) | ✅ 가동(blind-to-x) | ✅ 가동 |
| 적합 작업 | 고가치·기준명확·반복가치 큰 생성 | 배포 전 품질 게이팅 | 한국어 자동화 전반 |

**권장**: 일상 한국어 생성은 **language_bridge로 충분**(가장 저렴). **배포/프롬프트 변경 검증**은 **promptfoo**(오프라인이라 런타임 비용 0). **harness_eval**은 *비용을 더 써도 정확도가 중요한* 소수 고가치 생성(예: 최종 발행 카피)에 **선별 적용**한다 — Anthropic 지침대로 "명확한 평가 기준 + 반복 개선이 측정가능한 가치"일 때만. 셋은 배타가 아니라 **층위가 다르다**(런타임 언어 / 런타임 품질 / 오프라인 회귀).

Eval evidence is also layered. [36-evaluation-dataset-llm-judge-rubric-boundary](36-evaluation-dataset-llm-judge-rubric-boundary.md) keeps runtime generator-evaluator logs, promptfoo offline regression, deterministic assertions, LLM-as-judge rubrics, and human review as separate evidence fields.

## 언제 하네스를 쓰나 (workflow vs agent)

Anthropic 구분: **workflow**(LLM·도구를 사전 정의된 코드 경로로 오케스트레이션) vs **agent**(LLM이 스스로 도구·과정을 동적 결정). 이 repo의 생성 파이프라인은 대부분 **workflow**다(고정 경로). 그래서:

- 단순 생성(topic/draft/script) → **`LLMClient` 직접 호출**로 충분(하네스 불필요).
- 도구를 동적으로 쓰는 **agent** 경로를 만들 때 → tool_registry(권한)+sandbox(격리)+middleware(예산/루프)+context(압축)를 **함께** 켠다. 단 현재는 배선이 끊겨 있으니 먼저 harness_guard를 고친다.
- provider computer-use나 브라우저 조작 agent를 붙일 때도 같은 경계가 적용된다. release evidence는 [33-computer-use-browser-qa-boundary](33-computer-use-browser-qa-boundary.md)의 deterministic browser QA로 따로 남긴다.

## 지뢰밭

- 6개 모듈 전부 **구현+테스트됐으나 프로덕션 미배선**. "있으니 동작 중"으로 오해 말 것.
- 유일 통합점 harness_guard는 **stale-API**라 `HARNESS_ENABLED=1`이어도 preflight/sandbox가 조용히 무력화.
- `HarnessSession`은 `LLMClient`를 감싸므로, 활성화 시 비용/관측 싱크가 **이중 집계**되지 않도록 주의([03-cost-caching](03-cost-caching.md)).
- `ContextWindow` 토큰 추정은 휴리스틱(`_CHARS_PER_TOKEN=3`)이라 실제 토크나이저와 오차. 임계 근처에선 보수적으로.

## 출처 (1차 우선, 2026-06-08 확인)

- Anthropic, *Building Effective Agents* (evaluator-optimizer·orchestrator-workers·workflow vs agent): <https://www.anthropic.com/engineering/building-effective-agents>
- Anthropic, *Effective Context Engineering for AI Agents* (offload·compaction·tool result clearing): <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Claude Cookbook, *Context engineering: memory, compaction, and tool clearing*: <https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools>
- 코드 근거: `workspace/execution/harness_{tool_registry,sandbox,middleware,context,eval,security_checklist}.py`, `projects/blind-to-x/pipeline/harness_guard.py` (2026-06-08 현재 HEAD)

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
