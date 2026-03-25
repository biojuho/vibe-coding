# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 전에 이 파일을 읽고, 작업 완료 후 상태를 업데이트합니다.
> 해당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-043 | Phase 5A-4 후속: `orchestrator`/`render_step` 상위 smoke 또는 integration-heavy coverage 추가 | any | MEDIUM | 2026-03-25 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-042 | Phase 5A-3: `.ai/CONTEXT.md` 지뢰밭 정리 및 SESSION_LOG 로테이션 정리 | Codex | 2026-03-25 |
| T-047 | `script_step.py` AST/i18n 복구 및 schema alias 검증 정리 (`13 passed`) | Codex | 2026-03-25 |
| T-045 | Phase 5B-1 후속: `script_step.py` locale `field_names`/`channel_review_criteria` 경계 복구 | Codex | 2026-03-25 |
| T-046 | shorts coverage uplift: `render_step.py` 54%→62% (+44 tests), `edge_tts_client.py` 91% (+15 tests), 전체 2498 passed | Claude | 2026-03-25 |
| T-044 | shorts `en-US` config smoke 추가 (`34 passed`) | Codex | 2026-03-25 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (도구 무관)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 제거
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)