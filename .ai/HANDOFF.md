# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-25 |
| 도구 | Codex |
| 작업 | T-028 완료 — shorts render utility coverage uplift (`ending/outro/srt_export` 테스트 보강) |

## 현재 시스템 상태

- **QC 기준선 (2026-03-25 최신)**:
  - blind-to-x: **534 passed, 16 skipped** (`test_cost_db_security.py` 포함)
  - shorts-maker-v2: **776 passed, 8 skipped**
  - root: **914 passed, 1 skipped**
  - 전체: **2224 passed, 25 skipped, 0 failed**
- **시스템 QC runner (`qaqc_runner.py`)**: security scan **CLEAR**, full suite **`APPROVED`**
- **스케줄러**: Windows Task Scheduler 실제 상태와 최신 infra check가 **`6/6 Ready`**로 일치. 원인은 `schtasks` CSV를 UTF-8 모드에서 잘못 디코딩한 locale 오탐이었고 수정 완료
- **shorts coverage uplift (2026-03-25)**: 신규 테스트로 `render/ending_card.py` **94%**, `render/outro_card.py` **93%**, `render/srt_export.py` **95%** 확보 (`test_end_cards.py` 7 passed, `test_srt_export.py` 12 passed)
- **남은 핵심 이슈**: 없음 (`test_golden_render_moviepy`는 2026-03-25 full QC에서 재발 없음)

## 다음 도구가 해야 할 일 (우선순위)

1. 시스템 고도화 v2 Phase 5 후속: shorts 저커버리지 모듈(`cli.py`, `audio_postprocess.py`, `animations.py`) 중 결정론적 유틸부터 계속 보강
2. 테스트 보강을 몇 조각 더 쌓은 뒤 shorts 전체 coverage 재측정 또는 full QC 재실행

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- `execution/qaqc_runner.py`는 Windows에서 `schtasks` CSV를 읽을 때 `locale.getpreferredencoding(False)` 대신 `locale.getencoding()`을 써야 `-X utf8` 모드에서도 `준비` 상태가 깨지지 않음
- Windows 한글 사용자 경로 + `curl_cffi` 조합에서 CA 경로 Error 77이 재현됨
- `execution/qaqc_runner.py`는 `-o addopts=`로 프로젝트별 coverage/capture addopts를 비활성화하고, security scan에서 line-level `# noqa`와 triage metadata 문자열을 무시함
- `shorts-maker-v2` 카드 렌더 테스트는 Windows 폰트(`malgun.ttf`/`arial.ttf`)가 있어야 안정적이다. 기본 폰트만으로는 한글/이모지 렌더가 깨질 수 있음
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
