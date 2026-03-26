# HANDOFF - AI 컨텍스트 릴레이 메모

> 이 파일은 50줄 이내로 유지합니다. 상세 작업 이력은 `SESSION_LOG.md`, 확정 결정은 `DECISIONS.md`를 확인합니다.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-26 |
| 도구 | Codex |
| 작업 | 시스템 전체 QC 수행 — CONDITIONALLY_APPROVED 원인 분해 |

## 현재 상태

- **최신 QC (2026-03-26 저녁)**:
  - `workspace/execution/qaqc_runner.py` -> **CONDITIONALLY_APPROVED**
  - blind-to-x: shared runner에서 **TIMEOUT**. 하지만 standalone 재검증은 unit **468 passed, 15 skipped (328.89s)** + integration **63 passed, 1 skipped (25.61s)**
  - shorts-maker-v2: full-suite 재실행마다 실패 지점이 바뀜 (`test_planning_step.py`, `test_render_step_phase5.py`), 각 실패 테스트 단독 실행은 **PASS**
  - root: **919 passed, 1 skipped**
  - AST: **20/20 OK**, Security: **CLEAR**
- Frontend 보조 점검:
  - `hanwoo-dashboard` lint: **warning 1개** (`src/app/layout.js` Google Fonts head link)
  - `knowledge-dashboard` lint: **error 2개 + warning 1개**
- Python 정적 점검:
  - `ruff check workspace projects/blind-to-x projects/shorts-maker-v2/src infrastructure/n8n` -> **41 errors**
- Canonical layout active: `workspace/` + `projects/` + `infrastructure/`
- Blind-to-X scheduler repo paths repaired: `projects/blind-to-x` + `workspace/execution`
- `C:\btx\run.bat` / `C:\btx\run_pipeline.bat` now point at canonical launchers
- n8n bridge `healthcheck` and `btx_dry_run` both passed with new defaults

## 다음 우선순위

1. T-058: `shorts-maker-v2` full-suite order-dependent/flaky failure 원인 추적 및 고정
2. T-057: `qaqc_runner.py`의 blind-to-x timeout 300s를 현실화하거나 run 분리
3. T-059: `knowledge-dashboard` lint 오류 2건 수정
4. T-056: 다음 자연 실행 후 `scheduled_*.log` 생성과 `LastTaskResult=0` 확인

## 주의사항

- 현재 `git status`의 대량 삭제는 실제 삭제가 아니라 `workspace/`와 `projects/`로 이동된 구조 변경이다.
- PowerShell `Register-ScheduledTask` / `Unregister-ScheduledTask`는 이 머신에서 `Access is denied`가 발생했다. `schtasks`는 동작했으며 `BlindToX_Pipeline`은 그 경로로 복구했다.
- `blind-to-x`는 실제 회귀 실패보다 **QC 러너 timeout budget 부족** 가능성이 크다. 첫 red만 보고 코드 회귀로 단정하지 말 것.
- `shorts-maker-v2`는 전체 스위트에서만 실패가 튀고 isolated rerun은 통과했다. 전역 상태/monkeypatch 누수 가능성을 우선 의심할 것.
