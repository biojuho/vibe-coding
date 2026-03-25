# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 시 이 파일을 읽고, 작업 완료 시 상태를 업데이트합니다.
> 담당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-038 | shorts `render_step.py`/`edge_tts_client.py` coverage uplift (`54%`/`97%`, targeted suite `170 passed`) | Codex | 2026-03-25 |
| T-033 | Phase 5 문서화 — `enhancement_plan_v2.md`에 Phase 5A/5B 확장, i18n 분리 대상 명세 | Claude | 2026-03-25 |
| T-036 | shorts `video_renderer_backend` 조사 — dead code 아님 (듀얼 렌더러 설계), 조치 불필요 | Claude | 2026-03-25 |
| T-037 | shorts `tests/legacy/` 조사 — ShortsFactory 테스트, QC 범위 외 유지 결정 | Claude | 2026-03-25 |
| T-032 | Full QC 재실행 — **2362 passed, 0 failed, APPROVED** | Claude | 2026-03-25 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (누구든 가능)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 삭제
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)
