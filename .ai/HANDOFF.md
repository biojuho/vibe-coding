# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-23 |
| 도구 | Codex |
| 작업 | 시스템 QC 재실행 — `execution/qaqc_runner.py` 기준 REJECTED. blind-to-x 3 fail, root 2 fail, shorts 경로/timeout 이슈를 분리 진단하고 후속 TODO 추가 |

## 현재 시스템 상태

- shorts `thumbnail_step.py`: **신규 테스트 31건** (모드 분기, 예외, AI 프롬프트, 배경 추출)
- shorts `llm_router.py`: **17건 전 통과** — lazy import patch 경로 버그(`genai`/`types`) 수정 완료
- btx `notion_upload.py`: **99% coverage** (L246 dead code만 남음)
- btx `feed_collector.py` / `commands/dry_run.py` / `commands/one_off.py`: **100% coverage**
- blind-to-x: **라이브 필터 검증 완료** — `INAPPROPRIATE_TITLE_KEYWORDS`, `혐오` 감정 거부 동작 확인
- blind-to-x: **Notion 검토 큐 정리 완료** — 레거시 unsafe 1건 `반려` 처리 완료
- blind-to-x focused QC는 533 passed로 통과했지만, **전체 blind-to-x 테스트 재실행**에서는 `tests/unit/test_cost_controls.py` 3건 실패
- root 테스트: `tests/test_qaqc_history_db.py` 2건 실패 (`days=1` + 하드코딩 타임스탬프 조합)
- shorts-maker-v2: `execution/qaqc_runner.py`가 `tests/legacy/test_ssml.py`까지 수집해 collection error를 내고, 권장 경로 `tests/unit tests/integration --no-cov --maxfail=1`도 **15분 초과 timeout**
- 보안 스캔 46건은 현재 regex가 `.agents/`, 번들 JS, 일반 f-string 로그까지 잡는 **false positive 다수**

## 다음 도구가 해야 할 일 (우선순위)

1. **T-020** blind-to-x `test_cost_controls.py` 회귀 3건 수정 — 현재 시스템 QC의 가장 명확한 실제 코드 blocker
2. **T-022/T-023** `execution/qaqc_runner.py` 경로 정리 + shorts-maker-v2 full suite timeout 원인 분리
3. **T-021** root `qaqc_history_db` 테스트를 상대시간 기준으로 고쳐 시스템 QC false fail 제거
4. **T-016** blind-to-x 전체 `--review-only` 배치 스모크 — **LLM/이미지 비용 발생하므로 사용자 승인 후** 실행

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
