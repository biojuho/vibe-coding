# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 시 이 파일을 읽고, 작업 완료 시 상태를 업데이트합니다.
> 담당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-030 | shorts animations/broll_overlay/openai_client coverage uplift (62%→70%+) | Claude | HIGH | 2026-03-25 |
| T-031 | blind-to-x commands/ 테스트 보강 (dry_run.py, one_off.py 0%→80%+) | any | MEDIUM | 2026-03-25 |
| T-032 | Full QC 재실행 + coverage 재측정 (shorts/blind-to-x XML 갱신) | any | HIGH | 2026-03-25 |
| T-033 | 시스템 고도화 v2 Phase 5 문서화 (enhancement_plan_v2.md 확장) | any | MEDIUM | 2026-03-25 |
| T-034 | shorts v3.0 Phase A i18n 기술 검증 (PoC: locales/ 프롬프트 분리) | Claude | LOW | 2026-03-25 |
| T-036 | shorts `video_renderer_backend` 실연결 여부 정리 (orchestrator 전달 또는 dead code 정리) | any | MEDIUM | 2026-03-25 |
| T-037 | shorts legacy helper API 테스트를 공식 QC 범위에 포함할지 결정 (`tests/legacy/` 정리) | any | MEDIUM | 2026-03-25 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-035 | blind-to-x ASCII CA bundle fix + QAQC security status compatibility 복구 | Codex | 2026-03-25 |
| T-029 | shorts CLI/audio postprocess coverage uplift (`cli.py` 67%, `audio_postprocess.py` 85%) | Codex | 2026-03-25 |
| T-028 | shorts render utility coverage uplift (`ending_card.py`, `outro_card.py`, `srt_export.py`) 테스트 보강 | Codex | 2026-03-25 |
| T-027 | `execution/qaqc_runner.py` 스케줄러 locale 파싱 수정 (`schtasks` `6/6 Ready` 복구) + full QC 재검증 | Codex | 2026-03-25 |
| T-026 | system QC security scan 6건 triage 완료 — security scan `CLEAR`, full QC `APPROVED` 복구 | Codex | 2026-03-24 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (누구든 가능)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 삭제
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)
