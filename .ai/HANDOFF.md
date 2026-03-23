# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-24 |
| 도구 | Codex |
| 작업 | T-023/T-024 완료 — `qaqc_runner.py` 안정화, full QC `CONDITIONALLY_APPROVED` 복구 |

## 현재 시스템 상태

- **QC 기준선 (2026-03-24 최신)**:
  - blind-to-x: **531 passed, 16 skipped** (`test_curl_cffi.py`는 known env issue로 runner ignore)
  - shorts-maker-v2: **776 passed, 8 skipped** / full suite 849.77s
  - root: **910 passed, 1 skipped** (`tests/` + `execution/tests/` 분리 실행)
  - 전체: **2217 passed, 25 skipped, 0 failed**
- **시스템 QC runner (`qaqc_runner.py`)**: `REJECTED` → **`CONDITIONALLY_APPROVED`** 복구 (테스트 실패/timeout 없음, security scan 6건만 잔여)
- **스케줄러**: `BlindToX_Pipeline` Ready, 3시간 간격 실운영 전환됨 (--dry-run 제거)
- **남은 핵심 이슈**: T-026 security scan 6건 triage, intermittent golden render flaky 재발 여부 관찰

## 다음 도구가 해야 할 일 (우선순위)

1. **T-026** security scan 6건 triage (`blind-to-x/pipeline/cost_db.py`, `execution/content_db.py`, `sqlite-multi-mcp/server.py`)
2. `test_golden_render_moviepy` flaky가 다시 나타나는지 다음 full QC에서 관찰
3. 스케줄러 실운영 상태 계속 모니터링


## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- Windows 한글 사용자 경로 + `curl_cffi` 조합에서 CA 경로 Error 77이 재현됨. Blind 스크래퍼는 직접 브라우저 폴백 경로 유지 필요
- Windows PowerShell heredoc에서 한글 select 값을 Notion에 직접 PATCH하면 `??` 옵션이 생길 수 있음. live 수정은 option ID 또는 `\\u` escape 문자열 사용
- `execution/qaqc_runner.py`는 이제 `-o addopts=`로 프로젝트별 coverage/capture addopts를 비활성화하고, root는 `tests`/`execution/tests`를 분리 실행함
- coverage 재측정 중 `shorts-maker-v2` 기본 `pytest`는 `tests/legacy/`까지 줍기 때문에 `python -m pytest tests/unit tests/integration -q` 경로 지정 필요
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
