# HANDOFF - AI 도구 간 릴레이 핸드오프

> 이 파일은 50줄 이내로 유지합니다. 세션 종료 시 반드시 업데이트하세요.
> 상세 이력은 `SESSION_LOG.md`, 결정사항은 `DECISIONS.md`를 참조하세요.

## 마지막 세션

| 항목 | 내용 |
|------|------|
| 날짜 | 2026-03-23 |
| 도구 | Codex |
| 작업 | blind-to-x Notion 검토 큐 live audit — 레거시 unsafe 1건 `반려` 처리, 감사 메모 추가, 실수로 생긴 `승인 상태=??` 옵션 제거 |

## 현재 시스템 상태

- shorts `thumbnail_step.py`: **신규 테스트 31건** (모드 분기, 예외, AI 프롬프트, 배경 추출)
- shorts `llm_router.py`: **17건 전 통과** — lazy import patch 경로 버그(`genai`/`types`) 수정 완료
- btx `notion_upload.py`: **99% coverage** (L246 dead code만 남음)
- btx `feed_collector.py` / `commands/dry_run.py` / `commands/one_off.py`: **100% coverage**
- blind-to-x: **라이브 필터 검증 완료** — `INAPPROPRIATE_TITLE_KEYWORDS`, `혐오` 감정 거부, ImageCache stale evict 모두 동작 확인
- blind-to-x: **Notion 검토 큐 정리 완료** — 421페이지 audit 결과 unsafe 키워드 잔존 1건만 발견, `검토필요`→`반려` 처리 후 현재 unsafe 항목 `검토필요` 0건

## 다음 도구가 해야 할 일 (우선순위)

1. blind-to-x `--review-only` 배치 스모크 — **LLM/이미지 비용 발생하므로 사용자 승인 후** 실행
2. coverage 전체 재측정 — 이번 세션 추가 테스트 반영 후 shorts/btx 수치 확인
3. 필요 시 blind-to-x live audit 재실행 — 대화형 PowerShell에서는 Notion select 값을 이름 대신 option ID/유니코드 escape로 다룰 것

## 주의사항

- render_step.py의 커스텀 이펙트(ken_burns, 전환효과, 카라오케)는 MoviePy 전용 유지
- `.githooks/pre-commit`에 `ruff format --check` 추가됨 — 커밋 전 포맷 확인 필요
- Windows cp949 콘솔 이모지 크래시 주의 — llm_router.py는 `_safe_console_print()` 우회
- Windows 한글 사용자 경로 + `curl_cffi` 조합에서 CA 경로 Error 77이 재현됨. Blind 스크래퍼는 직접 브라우저 폴백 경로 유지 필요
- Windows PowerShell heredoc에서 한글 select 값을 Notion에 직접 PATCH하면 `??` 옵션이 생길 수 있음. live 수정은 option ID 또는 `\\u` escape 문자열 사용
- coverage 재측정 중 `shorts-maker-v2` 기본 `pytest`는 `tests/legacy/`까지 줍기 때문에 `python -m pytest tests/unit tests/integration -q` 경로 지정 필요
- 작업 트리에 기존 미정리 변경이 많음. 무관한 파일은 되돌리지 말 것

## 규칙

- 세션 종료 시 "마지막 세션" 테이블과 "다음 도구가 해야 할 일"을 반드시 갱신
- 50줄 초과 시 오래된 주의사항을 제거하여 유지
- 긴급 이슈는 맨 위에 `> URGENT:` 블록으로 표시
