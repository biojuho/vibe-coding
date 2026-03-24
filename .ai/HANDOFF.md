# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-24 |
| 도구 | Codex |
| 작업 | T-026 완료 — security scan triage 반영, full QC `APPROVED` 복구 |

## 현재 시스템 상태

- **QC 기준선 (2026-03-24 최신)**:
  - blind-to-x: **534 passed, 16 skipped** (`test_cost_db_security.py` 포함)
  - shorts-maker-v2: **776 passed, 8 skipped** / full suite 849.77s
  - root: **913 passed, 1 skipped**
  - 전체: **2223 passed, 25 skipped, 0 failed**
- **시스템 QC runner (`qaqc_runner.py`)**: security scan **CLEAR**, full suite **`APPROVED`**
- **스케줄러**: latest infra check에서 `0/6 Ready`로 집계됨. 이전 handoff의 `BlindToX_Pipeline Ready`와 차이가 있어 다음 운영 작업 시 수동 확인 권장
- **남은 핵심 이슈**: 없음 (관찰: `test_golden_render_moviepy` flaky 재발 여부)

## 다음 도구가 해야 할 일 (우선순위)

1. `test_golden_render_moviepy` flaky가 다시 나타나는지 다음 full QC에서 관찰
2. 스케줄러를 다시 만질 때 Windows Task Scheduler 실제 상태와 runner의 `0/6 Ready` 집계를 대조 확인

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- Windows 한글 사용자 경로 + `curl_cffi` 조합에서 CA 경로 Error 77이 재현됨
- `execution/qaqc_runner.py`는 `-o addopts=`로 프로젝트별 coverage/capture addopts를 비활성화하고, security scan에서 line-level `# noqa`와 triage metadata 문자열을 무시함
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
