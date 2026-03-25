# TASKS - AI 도구 칸반 보드

> 각 도구는 세션 시작 시 이 파일을 읽고, 작업 완료 시 상태를 업데이트합니다.
> 담당 도구가 지정된 태스크는 해당 도구가 우선 처리합니다.

## TODO

| ID | 태스크 | 담당 도구 | 우선순위 | 생성일 |
|----|--------|-----------|----------|--------|
| T-042 | Phase 5A-3: `.ai/CONTEXT.md` 지뢰밭 정리 및 SESSION_LOG 로테이션 정리 | any | MEDIUM | 2026-03-25 |
| T-043 | Phase 5A-4: shorts `render_step.py` integration-heavy 분기 coverage 추가 검토 | any | MEDIUM | 2026-03-25 |
| T-045 | Phase 5B-1 후속: `script_step.py`의 `_CHANNEL_REVIEW_CRITERIA` extra copy 및 legacy 필드명 i18n 범위 결정 | any | MEDIUM | 2026-03-25 |

## IN_PROGRESS

| ID | 태스크 | 담당 도구 | 시작일 | 메모 |
|----|--------|-----------|--------|------|

## DONE (최근 5건)

| ID | 태스크 | 완료 도구 | 완료일 |
|----|--------|-----------|--------|
| T-044 | shorts `en-US` config smoke 추가 (`ScriptStep -> MediaStep -> caption render`, `34 passed`) | Codex | 2026-03-25 |
| T-041 | shorts 실제 `en-US` locale pack 추가 (`script_step`/`edge_tts`/`captions`) + `whisper_aligner` locale 정규화 (`78 passed`) | Codex | 2026-03-25 |
| T-040 | shorts i18n PoC 2차 확장 (`script_step.py` persona keywords/review copy, `edge_tts_client.py` locale voice mapping, targeted suite `86 passed`) | Codex | 2026-03-25 |
| T-039 | shorts `script_step.py` i18n PoC (`locales/ko-KR/script_step.yaml`, locale loader, `37 passed`) | Codex | 2026-03-25 |
| T-038 | shorts `render_step.py`/`edge_tts_client.py` coverage uplift (`54%`/`97%`, targeted suite `170 passed`) | Codex | 2026-03-25 |

## 규칙

- ID는 `T-XXX` 형식으로 순번 증가
- 담당 도구: `Claude` / `Codex` / `Gemini` / `any` (누구든 가능)
- 우선순위: `CRITICAL` > `HIGH` > `MEDIUM` > `LOW`
- DONE은 최근 5건만 유지, 오래된 것은 삭제
- 태스크를 시작하면 TODO → IN_PROGRESS로 이동하고 시작일 기입
- 완료하면 IN_PROGRESS → DONE으로 이동하고 완료일 기입
- 새 태스크 발견 시 TODO에 추가 (다음 도구가 판단)
