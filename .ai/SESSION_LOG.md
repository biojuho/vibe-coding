# SESSION_LOG - Recent 7 Days

## 2026-03-28 | Codex | system-wide QC recovery + shared runner approval

### 작업 요약

시스템 전체 QC를 실행해 `REJECTED` 상태를 `APPROVED`까지 복구했다. 초기에 `blind-to-x`는 `langgraph` 미설치와 러너 timeout 때문에 깨졌고, root는 `graph_engine` optional dependency 처리 부재, `TesterWorker`의 Windows UTF-8 디코드 문제, `llm_fallback_chain` 테스트 기대치 드리프트가 겹쳐 실패했다. 이를 정리하면서 `reasoning_engine`의 SQL false positive도 제거했다.

이후 `blind-to-x` 쪽에서는 `EditorialReviewer`의 `langgraph` fallback, `TweetDraftGenerator`의 `llm.cache_db_path` 준수, 그리고 현재 draft tag contract(`reply`, `creator_take`)에 맞춘 테스트 정비를 진행했다. 마지막으로 `workspace/execution/qaqc_runner.py`를 수정해 `blind-to-x`를 unit/integration split-run + 900s budget으로 실행하도록 바꿔 shared QC false timeout을 해결했다.

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `workspace/execution/workers.py` | 수정 | child Python을 `-X utf8` + `encoding='utf-8'`로 실행해 Windows subprocess decode failure 제거 |
| `workspace/execution/graph_engine.py` | 수정 | `langgraph` 미설치 시 fallback orchestration으로 동작하도록 보강 |
| `workspace/execution/reasoning_engine.py` | 수정 | 고정 쿼리 분기화로 shared security scan false positive 제거 |
| `workspace/execution/qaqc_runner.py` | 수정 | `blind-to-x` split-run + 900s timeout budget으로 false timeout 해결 |
| `workspace/tests/test_llm_fallback_chain.py` | 수정 | `ollama` 포함 현재 provider order와 환경 격리에 맞게 테스트 갱신 |
| `projects/blind-to-x/pipeline/editorial_reviewer.py` | 수정 | `langgraph` 미설치 환경 fallback loop 추가 |
| `projects/blind-to-x/pipeline/draft_generator.py` | 수정 | `llm.cache_db_path`를 사용하는 persistent `DraftCache` 인스턴스 도입 |
| `projects/blind-to-x/tests/unit/test_cost_controls.py` | 수정 | current draft tag contract에 맞는 cache fixture 응답으로 갱신 |
| `projects/blind-to-x/tests/unit/test_optimizations.py` | 수정 | cache-related gemini mocks를 최신 tag contract에 맞게 갱신 |
| `projects/blind-to-x/tests/unit/test_quality_gate_retry.py` | 수정 | stricter CTA rules 및 인스턴스 cache 주입 방식에 맞게 테스트 갱신 |
| `projects/knowledge-dashboard/public/qaqc_result.json` | 갱신 | latest shared QC result (`APPROVED`) 반영 |
| `.ai/HANDOFF.md`, `.ai/TASKS.md`, `.ai/CONTEXT.md`, `.ai/SESSION_LOG.md` | 수정 | 세션 결과와 다음 우선순위 반영 |
| `.ai/archive/SESSION_LOG_before_2026-03-28.md` | 신규 | 1000줄 초과에 따른 기존 세션 로그 아카이브 |

### 검증 결과

- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_graph_engine.py workspace\tests\test_llm_fallback_chain.py -q --tb=short --no-header -o addopts=` -> **46 passed**
- `venv\Scripts\python.exe -X utf8 -m pytest workspace\tests\test_qaqc_runner.py workspace\tests\test_qaqc_runner_extended.py -q --tb=short --no-header -o addopts=` -> **30 passed**
- `venv\Scripts\python.exe -m ruff check workspace\execution\workers.py workspace\execution\graph_engine.py workspace\execution\reasoning_engine.py workspace\execution\qaqc_runner.py workspace\tests\test_llm_fallback_chain.py` -> clean
- `venv\Scripts\python.exe -X utf8 -m pytest tests\unit\test_quality_improvements.py tests\unit\test_cost_controls.py::test_draft_cache_persists_across_generator_instances tests\unit\test_optimizations.py::TestDraftGeneratorCache::test_second_call_uses_cache tests\unit\test_optimizations.py::TestDraftGeneratorCache::test_different_content_not_cached tests\unit\test_quality_gate_retry.py -q --tb=short --no-header -o addopts=` (`projects/blind-to-x`) -> targeted suites passed
- `venv\Scripts\python.exe -X utf8 -m pytest tests --ignore=tests/integration/test_curl_cffi.py -q --tb=short --no-header -o addopts=` (`projects/blind-to-x`) -> **561 passed, 16 skipped, 1 warning**
- `venv\Scripts\python.exe -X utf8 workspace\execution\qaqc_runner.py` -> **`APPROVED`** / `blind-to-x` **551 passed, 16 skipped** / `shorts-maker-v2` **1075 passed, 12 skipped** / `root` **1034 passed, 1 skipped** / total **2660 passed, 29 skipped**

### 다음 도구에게 메모

- Shared QC blocker였던 T-057은 해결됨. 다음 우선순위는 `T-059 knowledge-dashboard lint`, `T-058 shorts-maker-v2 order-dependent full-suite failure`, `T-071/T-072 evaluator work`.
- `blind-to-x` draft-generation 테스트를 추가할 때는 provider mock이 `<twitter>`, `<reply>`, `<creator_take>`를 함께 반환해야 현재 validation contract를 통과한다.
- `workspace/execution/graph_engine.py`와 `projects/blind-to-x/pipeline/editorial_reviewer.py`는 `langgraph`가 없어도 테스트/기본 실행이 가능하지만, 실제 LangGraph 기능이 필요한 확장 작업에서는 설치 환경 여부를 다시 확인하는 편이 안전하다.
