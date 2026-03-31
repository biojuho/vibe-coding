# CONTEXT.md 지뢰밭 아카이브 (Minefield Archive)

> 과거 `.ai/CONTEXT.md`의 `지뢰밭` 섹션에 있었으나, 해결되었거나 재발 빈도가 크게 낮아진 이슈들의 기록입니다. (주로 2026년 3월 9일 ~ 3월 25일 항목)

| 일자 | 도구 | 내용 | 대응 방법 (적용 완료) |
| --- | --- | --- | --- |
| 2026-03-09 | Antigravity | Windows Task Scheduler 한글 경로 XML 깨짐 | ASCII-only 경로(`C:\btx\`) + 환경변수 참조로 해결 |
| 2026-03-09 | Antigravity | Notion `rich_text` 2000자 제한에서 태그 길이도 거절 | 안전 마진 1990자로 truncate 적용 |
| 2026-03-12 | Claude Code | FastMCP 1.26 `description` kwarg 미지원 | `FastMCP("name", instructions="...")` 패턴으로 변경 |
| 2026-03-12 | Antigravity | SQLite 테이블명 f-string SQL Injection | `_validate_table_name()` 화이트리스트 도입 |
| 2026-03-16 | Antigravity | `Path(__file__).parents[N]` depth 가정 실패 | 실행 위치에서 `resolve()` 검증을 먼저 수행 |
| 2026-03-16 | Antigravity | frozen dataclass에 `copy.deepcopy()` 사용 시 FrozenInstanceError | `dataclasses.replace()` 사용 |
| 2026-03-17 | Claude Code | WordBoundary 미수신으로 karaoke 자막 완전 불능 | `_approximate_word_timings()` fallback 도입 |
| 2026-03-17 | Claude Code | `group_into_chunks()` 반환은 tuple인데 dict처럼 접근 | `for start, end, text in chunks` 패턴 적용 |
| 2026-03-17 | Claude Code | SSML prosody가 TTS 발화시간을 1.5배 이상 늘림 | CPS 2.8 하향 + 43초 초과 자동 경고 적용 |
| 2026-03-23 | Codex | `tests/test_qaqc_history_db.py` 고정 타임스탬프 의존 | fixture를 상대시간 기준으로 변경하고 안정화 |
| 2026-03-23 | Codex | PowerShell heredoc + 한글 문자열로 Notion select PATCH 시 깨짐 | live Notion 수정은 select option ID 또는 `\u` escape 사용 |
| 2026-03-25 | Codex | TTS 호출부에 `project.language` 전파 누락 | `MediaStep`/EdgeTTS 호출 시 `language=self.config.project.language`를 명시 전달 |
| 2026-03-25 | Codex | faster-whisper가 locale(`en-US`)보다 short code(`en`)에서 더 안정적 | `whisper_aligner.py`에서 locale을 short code로 정규화해 전달 |
| 2026-03-25 | Codex | locale 추가 후 `captions.yaml` 기본 폰트가 없으면 렌더 경로가 흔들림 | `locales/<lang>/captions.yaml`를 같이 만들고, config fallback을 locale 파일로 연결 |

*기록일: 2026-03-25*