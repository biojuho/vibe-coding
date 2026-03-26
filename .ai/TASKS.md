# TASKS - AI 칸반 보드

> 모든 세션은 시작 전에 이 파일을 읽고, 종료 전에 상태를 갱신합니다.
> 지정 담당이 있는 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-056 | Blind-to-X 다음 자연 실행 후 새 `scheduled_*.log`와 `LastTaskResult=0` 확인 | any | HIGH | 2026-03-26 |


## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-055 | Blind-to-X 자동 스케줄 경로 복구 및 `C:\btx` ASCII launcher 정비 | Codex | 2026-03-26 |
| T-054 | 트렌드 기반 주제 자동 발굴 기능 (--auto-topic) 완성 | Antigravity | 2026-03-26 |
| T-053 | 루트 `shorts-maker-v2/` 빈 폴더 확인 — 이미 정리됨 | Antigravity | 2026-03-26 |
| T-050-B | `__init__.py` lazy-import monkeypatch 호환 수정 → **1077 passed, 13 skipped, 0 failed** | Antigravity | 2026-03-26 |
| T-049 | `thumbnail_step.py` Pillow deprecation warning 수정 (`Image.fromarray` mode 제거) | Claude | 2026-03-26 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any`
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지하고 오래된 항목은 제거
- 태스크 시작 시 TODO에서 IN_PROGRESS로 이동하고 시작일 기록
- 태스크 완료 시 IN_PROGRESS에서 DONE으로 이동하고 완료일 기록
- 새로 발견한 후속 작업은 TODO에 추가
