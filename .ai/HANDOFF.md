# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-23 |
| 도구 | Claude Code (Opus 4.6) |
| 작업 | render_step→VideoRendererBackend 연동, 감사 Phase 1 완료 확인, LLM E2E 테스트 7건, 고도화 v2 Phase 0~4 전 완료 확인 |

## 현재 시스템 상태

- blind-to-x: 스케줄러 자동 실행 모니터링 중 (S4U 전환 후 1주간)
- shorts-maker-v2: render_step이 VideoRendererBackend 경유 로딩/쓰기로 전환됨
- 전체 테스트: Root 815+, shorts 695 passed (48.52%), btx 486 passed (51.98%)
- 감사 보고서: Phase 1~3 전 항목 완료, 고도화 v2 Phase 0~4 전 항목 완료

## 다음 도구가 해야 할 일 (우선순위)

1. golden render test: 30초 샘플 영상 렌더링 후 해상도/오디오 sync 자동 검증
2. MCP 서버 Tier 3 on-demand 전환 (RAM ~3.7GB 확보)
3. shorts-maker-v2 v3.0 Multi-language + SaaS 전환 설계 (탐색적)

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
