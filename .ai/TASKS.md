# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 시 이 파일을 읽고, 작업 완료 시 상태를 업데이트합니다.
> 담당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-003 | shorts-maker-v2 v3.0 Multi-language + SaaS 전환 설계 | any | LOW | 2026-03-23 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|
| T-002 | 시스템 고도화 v2 Phase 5 (고급 최적화 + 문서화) | Codex | 2026-03-23 | P1-4 LLM fallback 검증 완료, 남은 문서/coverage 후속 정리 중 |
| T-004 | blind-to-x 스케줄러 자동 실행 모니터링 | Gemini | 2026-03-23 | S4U 전환 후 1주간 관찰 |

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-001 | shorts-maker-v2 render_step <-> RenderAdapter 연동 | Codex | 2026-03-23 |
| T-005 | AI 도구 협업 시스템 구축 | Claude Code | 2026-03-23 |
| T-006 | blind-to-x main.py 모노리스 분리 | Gemini | 2026-03-23 |
| T-007 | Root QA gate Windows 복구 (coverage 81%) | Claude Code | 2026-03-21 |
| T-009 | blind-to-x 멘션 품질 근본 개선 | Claude Code | 2026-03-21 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (누구든 가능)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 삭제
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)
