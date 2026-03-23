# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 시 이 파일을 읽고, 작업 완료 시 상태를 업데이트합니다.
> 담당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-023 | shorts-maker-v2 `tests/unit tests/integration` 전체 suite timeout 원인 점검 | any | HIGH | 2026-03-23 |
| T-024 | `execution/qaqc_runner.py` 시스템 판정 안정화 (`root tests`/`execution/tests` 분리 반영, blind `curl_cffi` known env 처리) | any | HIGH | 2026-03-24 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|
| T-004 | blind-to-x 스케줄러 자동 실행 모니터링 | Gemini | 2026-03-23 | S4U 전환 후 1주간 관찰 |

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-016 | blind-to-x `--review-only` 배치 스모크 — 3건 업로드 확인(검토필요 상태) | Gemini | 2026-03-24 |
| T-019 | blind-to-x Ruff 28건 정리 (E402/F401/E741/E731 등) | Claude Code | 2026-03-23 |
| T-017 | blind-to-x Notion 검토 큐의 기존 부적절/레거시 항목 점검 및 정리 | Codex | 2026-03-23 |
| T-022 | `execution/qaqc_runner.py` shorts test_paths legacy 제외 (unit+integration) | Claude Code | 2026-03-23 |
| T-021 | root `tests/test_qaqc_history_db.py` 날짜 하드코딩 제거 (7/7 통과) | Claude Code | 2026-03-23 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (누구든 가능)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 삭제
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)
