# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-23 |
| 도구 | Codex |
| 작업 | 서브프로젝트 coverage 기준선 재측정, `shorts-maker-v2` 커버리지 보강 테스트 29건 추가, 후속 재측정 메모 기록 |

## 현재 시스템 상태

- blind-to-x: 스케줄러 자동 실행 모니터링 중 (S4U 전환 후 1주간)
- shorts-maker-v2: render_step이 VideoRendererBackend 경유 로딩/쓰기로 전환됨
- coverage 기준선: shorts-maker-v2 **704 passed / 12 skipped / 54.98%**, blind-to-x **487 passed / 5 skipped / 51.72%**
- shorts-maker-v2: `test_content_calendar_extended.py`, `test_planning_step.py`, `test_qc_step.py`, `test_channel_router.py` 추가 — **29 passed**
- 감사 보고서: Phase 1~3 전 항목 완료, 고도화 v2 Phase 0~4 전 항목 완료

## 다음 도구가 해야 할 일 (우선순위)

1. shorts-maker-v2 전체 coverage 재측정 재실행 → 새 테스트 29건 반영 후 수치 기록
2. coverage uplift 계속: shorts의 `render_step`, `thumbnail_step`, `llm_router` / blind-to-x의 `feed_collector`, `commands`, `notion` 계열 우선
3. golden render test: 30초 샘플 영상 렌더링 후 해상도/오디오 sync 자동 검증

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- coverage 재측정 중 `shorts-maker-v2` 기본 `pytest`는 `tests/legacy/`까지 줍기 때문에 `python -m pytest tests/unit tests/integration -q` 경로 지정 필요
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
