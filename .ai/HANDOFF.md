# HANDOFF - AI 컨텍스트 릴레이 메모

> 이 파일은 50줄 이내로 유지합니다. 상세 작업 이력은 `SESSION_LOG.md`, 확정 결정은 `DECISIONS.md`를 확인합니다.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-26 |
| 도구 | Codex |
| 작업 | T-055 완료 — Blind-to-X 자동 스케줄 canonical path/ASCII launcher 복구 |

## 현재 상태

- **QC 기준선 (2026-03-26)**:
  - blind-to-x: **541 passed, 16 skipped**
  - shorts-maker-v2: **1107 passed, 12 skipped**
  - root: **915 passed, 1 skipped**
  - 전체: **2533 passed, 29 skipped, 0 failed**
  - AST: **20/20 OK**, Security: **CLEAR**
- Canonical layout active: `workspace/` + `projects/` + `infrastructure/`
- Blind-to-X scheduler repo paths repaired: `projects/blind-to-x` + `workspace/execution`
- `C:\btx\run.bat` / `C:\btx\run_pipeline.bat` now point at canonical launchers
- n8n bridge `healthcheck` and `btx_dry_run` both passed with new defaults

## 다음 우선순위

1. T-056: 다음 자연 실행 후 `scheduled_*.log` 생성과 `LastTaskResult=0` 확인
2. 필요 시 관리자 권한으로 `register_schedule.ps1` / `register_task.ps1` 재실행해 PowerShell ScheduledTasks cmdlet 권한 문제 재확인

## 주의사항

- 현재 `git status`의 대량 삭제는 실제 삭제가 아니라 `workspace/`와 `projects/`로 이동된 구조 변경이다.
- PowerShell `Register-ScheduledTask` / `Unregister-ScheduledTask`는 이 머신에서 `Access is denied`가 발생했다. `schtasks`는 동작했으며 `BlindToX_Pipeline`은 그 경로로 복구했다.
- 이번 세션에서는 운영 부작용을 피하려고 Windows 작업을 강제 실행하지 않았다. 5개 시간대 작업은 기존에도 `C:\btx\run.bat`를 쓰고 있었으므로 다음 자연 실행에서 복구 여부가 확인된다.
