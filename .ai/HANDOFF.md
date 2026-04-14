# HANDOFF - AI Context Relay

> See `SESSION_LOG.md` for recent session history and `DECISIONS.md` for stable architecture decisions.

## Latest Update

| Field | Value |
|---|---|
| Date | 2026-04-14 |
| Tool | Codex |
| Work | **T-200 완료**: Antigravity Amazon Q 장애를 추적해 downloaded AmazonQ LSP `1.64.0` 선택 경로가 실패하는 것을 확인했고, `C:\Users\박주호\AppData\Roaming\Antigravity\User\globalStorage\state.vscdb`의 cached manifest에서 `1.64.0`을 `isDelisted=true`로 패치해 다음 선택 버전이 `1.63.0`이 되도록 고정했다. 백업은 `C:\Temp\codex-debug\backups\state.vscdb.20260414-194311.bak`. |
| Next Priorities | 1. Antigravity를 완전히 재시작해 Amazon Q가 `1.63.0`으로 붙는지 확인. 2. 재발 시 Antigravity의 Unicode/header 관련 오류와 remote manifest overwrite 여부 추가 확인. 3. 기존 우선순위인 **T-199**, **T-198**, **T-194** 계속 진행. |

## Previous Update

| Field | Value |
|---|---|
| Date | 2026-04-13 |
| Tool | Gemini (Antigravity) |
| Work | **T-161 & T-189 완료**: `browser_subagent` 런타임 오류(`0xc0000005`)를 로컬 Node.js Playwright 스크립트(`screenshot.js`)로 우회하여 시각 검증. T-161 UI 검수 완전 클로즈. |
| Next Priorities | 1. `hanwoo-dashboard` `DATABASE_URL` 올바른 비밀번호 적용. 2. 백로그 태스크 시작. |

## Notes

- **T-200 Amazon Q 로컬 우회 (2026-04-14)**:
  - 증상 로그: `Amazon Q Logs.log`에서 downloaded LSP `1.64.0`이 `exitcode=10`으로 실패하고 bundled LSP fallback 발생.
  - `wmic process ... WorkingSetSize` 경고는 보조 증상으로 보이며, 실제 root cause는 downloaded resolver 경로 쪽에 더 가까움.
  - 상태 키: `state.vscdb`의 `amazonwebservices.amazon-q-vscode` -> `aws.toolkit.lsp.manifest`.
  - 패치 결과: `1.64.0`만 delist 처리했고, 현재 manifest 기준 선택 버전은 `1.63.0`.
  - 로컬 자산 확인: `C:\Users\박주호\AppData\Local\aws\toolkits\language-servers\AmazonQ\1.63.0` 존재.
  - 실행 중인 Antigravity 세션은 기존 선택을 들고 있으므로 전체 앱 재시작이 필요함.
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
