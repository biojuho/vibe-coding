# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-24 |
| 도구 | Claude Code |
| 작업 | QC 전체 재측정 — blind-to-x ✅, shorts 62.58% (golden_render flaky 1건 격리 시 통과) |

## 현재 시스템 상태

- **QC 기준선 (2026-03-24 최신)**:
  - blind-to-x: Ruff ✅ 0건 / **522 passed, 53.35%** ✅
  - shorts-maker-v2: **775 passed, 62.58%** / 1 flaky (`test_golden_render_moviepy` — 단독 실행 시 통과, full suite 자원 경합)
  - 전체 소요: blind 4분 24초, shorts 15분 45초
- **시스템 QC runner (`qaqc_runner.py`)**: 여전히 REJECTED (shorts 300s timeout, curl_cffi CA Error 77 미해결)
- **남은 핵심 이슈**: T-023 shorts full suite timeout 격리, T-024 qaqc_runner 판정 보정

## 다음 도구가 해야 할 일 (우선순위)

1. **T-023** shorts-maker-v2 full suite timeout 원인 분리 (느린 테스트 격리 또는 timeout 상향)
2. **T-024** `execution/qaqc_runner.py` 시스템 판정 보정 (`root tests`/`execution/tests` 분리 반영, blind known env failure 처리 전략 정리)
3. **T-004** 스케줄러 모니터링 계속 (S4U 전환 후 1주 관찰)

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- Windows 한글 사용자 경로 + `curl_cffi` 조합에서 CA 경로 Error 77이 재현됨. Blind 스크래퍼는 직접 브라우저 폴백 경로 유지 필요
- Windows PowerShell heredoc에서 한글 select 값을 Notion에 직접 PATCH하면 `??` 옵션이 생길 수 있음. live 수정은 option ID 또는 `\\u` escape 문자열 사용
- `execution/qaqc_runner.py`의 현재 기본 경로는 shorts `tests/legacy/`와 root `tests`+`execution/tests`를 한 번에 줍기 때문에 QC false fail 가능
- coverage 재측정 중 `shorts-maker-v2` 기본 `pytest`는 `tests/legacy/`까지 줍기 때문에 `python -m pytest tests/unit tests/integration -q` 경로 지정 필요
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
