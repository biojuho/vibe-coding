# 19 · Objective Loop Audit

## 목적

`execution/llm_wiki_audit.py`는 README 색인, 로컬 링크, 외부 출처 freshness, source/code/config manifest, release-summary contract를 검증한다. 하지만 그것만으로는 사용자가 요청한 "LLM Wiki 자율 보강 루프"의 모든 요구가 실제 산출물에 매핑됐는지 증명하지 못한다.

`execution/llm_wiki_objective_audit.py`는 그 빈틈을 메운다. 이 스크립트는 현재 repo evidence를 읽어 completion-audit 호환 manifest를 만들고, 다음 요구를 각각 artifact/evidence/blocker로 분해한다.

| 요구 | 대표 evidence |
|------|---------------|
| 0단계 현황 파악 | `docs/wiki/llm/README.md`, `.ai/SESSION_LOG.md`의 T-1573 및 후속 cycle |
| gap 선정 | `.ai/HANDOFF.md`, `.ai/TASKS.md`, source/runtime gap page |
| 외부 조사 | `source-inventory.json`, source-backed page count |
| A/B 비교 | A/B decision page count, maintenance/runtime 비교표 |
| 최신 반영 | `code-facts.json`, `config-facts.json`, unexpected warning count |
| 적용 및 검증 | `llm_wiki_audit.py`, focused tests, release-summary helper |
| 사이클 보고 | HANDOFF/TASKS/SESSION_LOG의 최신 cycle |
| 중복/드리프트 방지 | source/code/config/release-summary gates |
| 종료 조건 | selector boundary와 "user says stop" 조건 |

## 실행

```bash
py -3.13 execution/llm_wiki_objective_audit.py --output .tmp/llm-wiki-objective-audit-current.json --json
py -3.13 .agents/skills/auto-research/scripts/completion_audit.py .tmp/llm-wiki-objective-audit-current.json --json --allow-incomplete
```

두 번째 명령은 의도적으로 `--allow-incomplete`를 쓴다. 루프형 목표는 사용자가 중단을 말하기 전까지 complete로 주장하면 안 되고, 현재 workspace selector가 `dirty_worktree_handoff_current` 또는 T-251 같은 외부/user-owned boundary를 보고하면 manifest도 blocked 상태를 유지한다.

## A/B 판단

| 기준 | A. relay 문서를 사람이 직접 읽고 판단 | B. objective manifest + completion audit |
|------|--------------------------------------|-----------------------------------------|
| prompt 요구 누락 감지 | 사람이 항목을 기억해야 함 | 요구별 item이 비어 있거나 blocker가 있으면 audit issue |
| repo evidence 재사용 | 각 cycle마다 손으로 요약 | 구조화된 `artifacts`와 `evidence` 재사용 |
| 완료 주장 방지 | relay 문구 해석에 의존 | blocker가 있으면 completion audit이 `incomplete` |
| CI/릴리스 연결 | 별도 YAML/스크립트 필요 | 기존 `completion_audit.py` manifest format 사용 |
| 구현 범위 | 코드 변경 없음 | 작은 deterministic Python wrapper와 focused tests |

**결정:** B를 채택한다. 기존 구조 감사는 그대로 유지하고, objective audit은 "사용자 프롬프트의 요구사항이 artifact로 증명됐는가"만 담당한다.

## 해석 규칙

- `summary.llm_wiki_audit_status=pass`는 wiki 구조와 freshness가 유효하다는 뜻이다.
- `summary.status=blocked`는 실패가 아니라 active-loop 경계일 수 있다. `items[].blockers`를 확인한다.
- `종료 조건` item은 사용자가 중단을 말하기 전까지 blocker를 남긴다.
- selector가 `dirty_worktree_handoff_current`이면 새 제품 변경을 시작하지 말고 현재 handoff evidence와 scoped authorization boundary를 유지한다.
- 외부 URL, 코드 fact, config fact가 바뀌면 기존 `llm_wiki_audit.py --write-*` 명령으로 manifest를 먼저 재생성한 뒤 objective audit을 다시 실행한다.

## 출처

- 공식: Python `argparse` standard library documentation: <https://docs.python.org/3/library/argparse.html>
- 공식: Python `json` standard library documentation: <https://docs.python.org/3/library/json.html>
- 공식: GitHub Docs, workflow commands and job summaries: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands>
- 코드 근거: `execution/llm_wiki_objective_audit.py`, `workspace/tests/test_llm_wiki_objective_audit.py`, `.agents/skills/auto-research/scripts/completion_audit.py`

*외부 자료 검증일: 2026-06-08 · 코드 검증: 현재 HEAD*
