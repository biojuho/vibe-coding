# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-13 |
| Tool | Gemini (Antigravity) |
| Work | **T-161 & T-189 완료**: `browser_subagent` 런타임 오류(`0xc0000005`)를 로컬 Node.js Playwright 스크립트(`screenshot.js`)로 우회하여 시각 검증 진행. 로그인 검증 우회 후 화면 캡처로 T-161 UI 검수 완전 클로즈. 추가로 현재 `.env`의 `DATABASE_URL`에 `YOUR_PASSWORD`가 플레이스홀더 그대로 설정되어 있어 런타임에 Prisma DB 접속 문제가 발생함을 발견. |
| Next Priorities | 1. `hanwoo-dashboard` `DATABASE_URL` 올바른 비밀번호 적용. 2. T-191(`.ai/archive` 인코딩 삭제 검토) 또는 T-192(`.claude/` gitignore 정책 수정) 진행. 3. 백로그에서 새로운 개발 태스크 시작. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-13 |
| Tool | Claude Code (Opus 4.6 1M) |
| Work | **T-190 완료**: claude-mem 도입 대안으로 `execution/session_log_search.py` (SQLite FTS5 기반 세션 로그 검색) 신규. `.ai/SESSION_LOG.md` 테이블 포맷 + `.ai/archive/` 헤딩 포맷 3종(`\|`, em dash, 손상된 `??`) 듀얼 파서, `normalize_query()`로 하이픈 토큰 자동 인용, mtime 기반 lazy reindex, 142 엔트리(2026-03-13~2026-04-11). `.claude/commands/search-log.md` 슬래시 커맨드 + `.claude/settings.json` SessionStart 훅(자동 reindex) 추가 — 단 **`.claude/`가 gitignore 되어 있어 로컬 전용**. ruff/py_compile clean, 한글 쿼리 검증 OK. |
| Next Priorities | 1. 다음 세션 시작 시 SessionStart 훅이 실제 발화하는지(`.tmp/session_log_search.db` mtime) 확인. 2. `.claude/` 정책 결정 — `/search-log`를 팀/멀티툴 공유하려면 gitignore 예외 필요. 3. T-191(손상된 archive 파일 복구) 판단. 4. `hanwoo-dashboard` T-189 브라우저 자동화 환경 복구는 여전히 대기. |

## Notes

- **T-190 세션 로그 검색 도구 (2026-04-13)**:
  - 스크립트: `execution/session_log_search.py` (stdlib only, FTS5)
  - 인덱스: `.tmp/session_log_search.db` (gitignore됨, 재생성 가능)
  - 로컬 전용 자산: `.claude/commands/search-log.md`, `.claude/settings.json` SessionStart 훅 — `.gitignore:78`이 `.claude/` 전체 제외
  - 쿼리 예: `python execution/session_log_search.py notion timeout`, `/search-log --tool Codex --since 2026-04-01 feedback loop`
  - 알려진 제약: `.ai/archive/SESSION_LOG_before_2026-03-23.md`는 파일 자체 인코딩 손상(em dash→`??`), 5개 엔트리만 잡힘
- **T-161 QC 결과 (2026-04-13)**:
  - QA STEP 2에서 FAIL — `DashboardClient.js:32`가 `AlertBanners.js`에서 import하나 CSS 변수 전환은 `widgets.js` dead export에만 적용
  - STEP 3에서 수정: `AlertBanners.js` 전면 재작성, `widgets.js` dead code 제거
  - 커밋: `f2448a4`, `ef02a60`, `46a2349` (3개 T-161 관련)
  - 서버 검증: `200 OK` on `http://localhost:3001`
  - 시각 검증: blocked (`0xc0000005` Playwright)
- The local Python 3.13 `code-review-graph` package on this machine now has an unversioned UTF-8 patch in `site-packages`. If the package is reinstalled or upgraded, the old Windows `cp949` crash can return until the same fix is reapplied upstream.
- `projects/blind-to-x/tests/unit/conftest.py` now clears `NOTION_DATABASE_ID` and any `NOTION_PROP_*` overrides before each unit test.
- UTF-8 markdown files in `.ai/` and `workspace/directives/` are fine on disk; earlier garbling came from the Windows cp949 console path, not file corruption.
- Do not revert unrelated in-progress edits elsewhere in the worktree.
