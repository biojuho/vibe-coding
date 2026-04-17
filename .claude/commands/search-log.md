---
description: .ai/SESSION_LOG + archive 통합 FTS5 검색 (BM25 랭킹). 예 - /search-log notion timeout
argument-hint: <query> [--tool X] [--since YYYY-MM-DD] [--limit N]
---

아래 명령을 그대로 실행하고 stdout 결과를 사용자에게 출력해. 결과 해석/요약/보충 설명은 하지 마 — 사용자가 원문을 읽어야 함.

```bash
python execution/session_log_search.py $ARGUMENTS
```

지원 쿼리 문법:
- `notion timeout` — AND (기본)
- `notion OR slack` — OR 연산자
- `"exact phrase"` — 정확한 구문
- `blind*` — prefix 검색
- `hanwoo-dashboard` 같은 하이픈 토큰은 자동 인용 처리됨

필터:
- `--tool Codex` / `--tool Claude` / `--tool Gemini`
- `--since 2026-04-01`
- `--limit 5` (기본 10)
- `--stats` (인덱스 통계)
- `--reindex` (강제 재생성, 보통 mtime 기반 자동 재빌드됨)

인덱스 위치: `.tmp/session_log_search.db` (재생성 가능, 커밋 금지)
