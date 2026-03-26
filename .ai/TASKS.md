# TASKS - AI 칸반 보드

> 모든 세션은 시작 전에 이 파일을 읽고, 종료 전에 상태를 갱신합니다.
> 지정 담당이 있는 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-050 | `projects/shorts-maker-v2` 기준 full QC 재실행 및 기준값 갱신 | any | MEDIUM | 2026-03-26 |
| T-053 | 점유 중인 빈 루트 `shorts-maker-v2/` 잔여 디렉터리 정리 | any | LOW | 2026-03-26 |
| T-049 | `thumbnail_step.py` Pillow deprecation warning 정리 (`Image.fromarray(..., mode=...)`) | any | LOW | 2026-03-26 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-052 | 루트 구조를 `workspace/` + `projects/` 기준으로 단순화하고 경로 계약/문서/QAQC 허브를 새 레이아웃에 맞게 정리 | Codex | 2026-03-26 |
| T-051 | `orchestrator.py` unit tests 31개 추가 (15%→80%), shorts 1076 passed, coverage 78% | Claude | 2026-03-26 |
| T-043 | `orchestrator`/`render_step` 상위 en-US smoke + integration-heavy coverage 보강 | Codex | 2026-03-26 |
| T-042 | `.ai/CONTEXT.md` 지뢰밭 정리 및 `SESSION_LOG` 로테이션 정리 | Codex | 2026-03-25 |
| T-047 | `script_step.py` AST/i18n 복구 및 schema alias 검증 정리 | Codex | 2026-03-25 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any`
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지하고 오래된 항목은 제거
- 태스크 시작 시 TODO에서 IN_PROGRESS로 이동하고 시작일 기록
- 태스크 완료 시 IN_PROGRESS에서 DONE으로 이동하고 완료일 기록
- 새로 발견한 후속 작업은 TODO에 추가
